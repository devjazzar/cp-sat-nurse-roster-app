"""The CNO's files about nurses: the import template, previewing and confirming an import, and the staff list.
Reading and judging an import is `nurses.importing`. Who belongs where is `nurses.membership`."""
from __future__ import annotations

from collections import Counter

from django.db import transaction
from django.http import HttpRequest, HttpResponse
from ninja import File, Form, Router, Schema, Status
from ninja.errors import HttpError
from ninja.files import UploadedFile

from accounts.authz import SignedIn
from accounts.models import Role, User
from accounts.provisioning import UsernameTaken, create_user, new_passwords
from audit.log import record
from hospital.api import refuse
from nurses import importing, membership
from nurses.api import new_profile, with_units
from nurses.models import NurseProfile
from nurses.spreadsheets import csv_response
from units.models import Unit

router = Router(tags=["nurses"])
cno = SignedIn(Role.CNO)

STAFF_LIST_COLUMNS = (*importing.COLUMNS, "End date", "Role", "Status", "Transfers to come")
_A_CSV_FILE = {"responses": {200: {"description": "A CSV file.", "content": {"text/csv": {"schema": {"type": "string"}}}}}}


class ImportProblem(Schema):
    column: str | None
    message: str


class ImportRow(Schema):
    line: int
    hospital_id: str
    full_name: str
    gender: str
    unit: str
    start_date: str
    problems: list[ImportProblem]


class ImportPreview(Schema):
    rows: list[ImportRow]
    token: str | None


class SheetRow(Schema):
    hospital_id: str
    full_name: str
    unit: str
    generated_password: str


class PasswordSheet(Schema):
    """Holds passwords, so it asks not to be stored."""
    rows: list[SheetRow]


class _ChangedSincePreview(Exception):
    pass


def _lines_of(file: UploadedFile) -> list[importing.Line]:
    try:
        return importing.read_file(file.read())
    except importing.FileRefused as refusal:
        refuse((("file",), str(refusal)))


@router.get("/import/template", auth=cno, operation_id="downloadNurseImportTemplate", openapi_extra=_A_CSV_FILE)
def import_template(request: HttpRequest) -> HttpResponse:
    return csv_response("nurse-import-template.csv", [importing.COLUMNS])


@router.post("/import/preview", response=ImportPreview, auth=cno, operation_id="previewNurseImport")
def preview_import(request: HttpRequest, response: HttpResponse, file: File[UploadedFile]) -> importing.Preview:
    """Every row's problems. It saves nothing and keeps nothing: confirming sends the file again."""
    response["Cache-Control"] = "no-store"
    return importing.check(_lines_of(file))


def _create(request: HttpRequest, nurses: list[importing.NewNurse]) -> list[SheetRow]:
    """Hashes first, holding no lock, since it is the slow part. Then one transaction, in the order every other change
    takes its locks: users, then units. A hospital ID taken meanwhile is the constraint's to catch, and a unit changed
    meanwhile shows under its lock, and a CNO deactivated meanwhile adds nobody. Users go in by hospital ID, so that
    two imports of the same IDs wait for each other instead of deadlocking on the unique index."""
    passwords = dict(zip((nurse.hospital_id for nurse in nurses), new_passwords(len(nurses))))
    with transaction.atomic():
        if not User.objects.filter(pk=request.user.pk, role=Role.CNO, is_active=True).exists():
            raise HttpError(403, "Your role may not do this.")
        try:
            users = {nurse.hospital_id: create_user(request, username=nurse.hospital_id, full_name=nurse.full_name,
                                                    role=Role.STAFF_NURSE, password=passwords[nurse.hospital_id])[0]
                     for nurse in sorted(nurses, key=lambda nurse: nurse.hospital_id.lower())}
        except UsernameTaken:
            raise _ChangedSincePreview from None
        previewed = {nurse.unit.pk: nurse.unit for nurse in nurses}
        locked = {unit.pk: unit for unit in Unit.objects.select_for_update().filter(pk__in=previewed).order_by("pk")}
        if any(pk not in locked or locked[pk].archived or locked[pk].name != unit.name for pk, unit in previewed.items()):
            raise _ChangedSincePreview
        record("nurses.imported", actor=request.user, request=request,
               after={"count": len(nurses), "units": Counter(nurse.unit.name for nurse in nurses)})
        for nurse in nurses:
            new_profile(request, users[nurse.hospital_id], locked[nurse.unit.pk], nurse.gender, nurse.start_date)
    return [SheetRow(hospital_id=nurse.hospital_id, full_name=nurse.full_name, unit=nurse.unit.name,
                     generated_password=passwords[nurse.hospital_id].plain) for nurse in nurses]


@router.post("/import/confirm", response={201: PasswordSheet, 409: ImportPreview}, auth=cno, operation_id="confirmNurseImport")
def confirm_import(request: HttpRequest, response: HttpResponse, file: File[UploadedFile], token: Form[str]) -> Status:
    """`token` is the preview's. The file is judged again from the start: with any problem, or when it no longer means
    what was previewed, nothing is saved and the answer is 409 with the preview as it now stands."""
    response["Cache-Control"] = "no-store"
    lines = _lines_of(file)
    preview = importing.check(lines)
    if preview.token is None or preview.token != token:
        return Status(409, preview)
    try:
        return Status(201, PasswordSheet(rows=_create(request, [row.nurse for row in preview.rows])))
    except _ChangedSincePreview:
        return Status(409, importing.check(lines))


def _staff_list_row(nurse: NurseProfile) -> list[str]:
    current, *coming = membership.from_now_on(nurse)
    user = nurse.user
    return [user.username, user.full_name, nurse.gender, current.unit.name, nurse.start_date.isoformat(),
            nurse.end_date.isoformat() if nurse.end_date else "", user.get_role_display(),
            "Active" if user.is_active else "Deactivated",
            "; ".join(f"{placement.unit.name} from {placement.from_month:%Y-%m}" for placement in coming)]


@router.get("/export", auth=cno, operation_id="exportStaffList", openapi_extra=_A_CSV_FILE)
def export_staff_list(request: HttpRequest) -> HttpResponse:
    """Every nurse the CNO's list shows, deactivated ones too, by name. Its first columns are the import's."""
    return csv_response(f"staff-list-{membership.today():%Y-%m-%d}.csv",
                        [STAFF_LIST_COLUMNS, *map(_staff_list_row, with_units(NurseProfile.objects.all()))])
