"""The CNO's lists, which every role may read: the shift catalogue, the leave types, the skill catalogue, the public
holidays and the Ramadan dates."""
from __future__ import annotations

import datetime as dt
import re
from typing import Annotated, Literal
from uuid import UUID

from django.db import transaction
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Path, Query, Router, Schema
from ninja.errors import HttpError
from nurse_roster.calendar import GREGORIAN_RANGE
from pydantic import AfterValidator, BeforeValidator, Field, StringConstraints, field_validator

from accounts.authz import SignedIn
from accounts.models import Role
from audit.log import record
from hospital.api import StrictSchema, differing, refuse, save_unless_taken
from hospital.catalogue import derived_ramadan_dates
from hospital.models import (FixedRamadanMonth, HospitalSettings, LeaveType, PublicHoliday, Shift, ShiftRename, Skill,
                             SkillRename)
from hospital.rules import changes
from nurses.membership import carry_rename_through_allowed_shifts, this_month
from nurses.models import NurseSkill
from ops.api import ClockTime
from rosters.drafts import carry_rename_through_grids, current_code, using_shift
from rosters.pins import counted_uses
from solves.models import ACTIVE_STATES, Solve
from units.models import Unit
from units.rules import units_using, with_shift_codes

router = Router(tags=["hospital"])
cno = SignedIn(Role.CNO)
RESERVED_CODE = "L"  # nurse_roster.problem.RESERVED_SHIFT: the solver's CSV export marks leave with it.
# The whole years the Umm al-Qura data covers; the holidays and the Ramadan dates keep to them alike.
FIRST_YEAR, LAST_YEAR = GREGORIAN_RANGE[0].year + 1, GREGORIAN_RANGE[1].year - 1
MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


def no_nul(value: str) -> str:
    # PostgreSQL cannot hold one; it would otherwise be a 500.
    if "\x00" in value:
        raise ValueError("cannot contain a NUL character")
    return value


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100), AfterValidator(no_nul)]
Colour = Annotated[str, Field(pattern="^#[0-9a-fA-F]{6}$", examples=["#0284c7"]), AfterValidator(str.lower)]


def iso_date(value: object) -> dt.date:
    # A schema's strict mode would refuse every date, because JSON has only strings, and its lax mode
    # would take a number of seconds or a time of day as one.
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("must be a date as YYYY-MM-DD")
    day = dt.date.fromisoformat(value)
    if not FIRST_YEAR <= day.year <= LAST_YEAR:
        raise ValueError(f"must be between {FIRST_YEAR} and {LAST_YEAR}")
    return day


IsoDate = Annotated[dt.date, BeforeValidator(iso_date)]


class YearFilter(Schema):
    year: int = Field(ge=FIRST_YEAR, le=LAST_YEAR)


# ---- shifts ---------------------------------------------------------------------------------------
class ShiftBody(StrictSchema):
    # The first character keeps a spreadsheet from reading an export's cell as a formula, which the solver
    # also insists on; eight is what a roster grid's cell can show.
    code: str = Field(pattern="^[A-Za-z0-9][A-Za-z0-9_-]{0,7}$", description="The name the solver and rosters use.")
    display_name: Name
    hours: int = Field(ge=1, le=24)
    start_time: ClockTime
    end_time: ClockTime = Field(description="Earlier than the start time when the shift runs past midnight.")
    colour: Colour
    active: bool

    @field_validator("code")
    @classmethod
    def not_reserved(cls, value: str) -> str:
        if value.upper() == RESERVED_CODE:
            raise ValueError(f"{RESERVED_CODE} is reserved: exports mark leave with it")
        return value


class ShiftRenameSchema(Schema):
    old_code: str
    new_code: str
    at: dt.datetime = Field(description="In the hospital's time zone.")

    @staticmethod
    def resolve_at(rename: ShiftRename) -> dt.datetime:
        return timezone.localtime(rename.at)


class ShiftSchema(Schema):
    """Not the request's schema: what is stored is shown as it is, whatever the rules were when it was saved."""
    id: UUID
    code: str
    display_name: str
    hours: int
    start_time: str
    end_time: str
    colour: str
    active: bool
    renames: list[ShiftRenameSchema] = Field(description="Every change of this shift's code, oldest first.")

    @staticmethod
    def resolve_start_time(shift: Shift) -> str:
        return shift.start_time.strftime("%H:%M")

    @staticmethod
    def resolve_end_time(shift: Shift) -> str:
        return shift.end_time.strftime("%H:%M")

    @staticmethod
    def resolve_renames(shift: Shift) -> list[ShiftRename]:
        return list(shift.renames.all())


def _shift_fields(shift: Shift) -> dict:
    return {"code": shift.code, "display_name": shift.display_name, "hours": shift.hours,
            "start_time": shift.start_time.strftime("%H:%M"), "end_time": shift.end_time.strftime("%H:%M"),
            "colour": shift.colour, "active": shift.active}


def _write_shift(shift: Shift, body: ShiftBody) -> None:
    shift.code, shift.display_name, shift.hours = body.code, body.display_name, body.hours
    shift.start_time, shift.end_time = dt.time.fromisoformat(body.start_time), dt.time.fromisoformat(body.end_time)
    shift.colour, shift.active = body.colour, body.active
    shift.save()


def _refuse_a_taken_code(code: str, shift_id: UUID | None) -> None:
    """Also a code another shift used to hold: the record says that name in an old history means that
    shift, so it cannot start to mean this one. A shift may go back to a code of its own."""
    held = Shift.objects.filter(code__iexact=code).exclude(pk=shift_id).exists()
    held_before = ShiftRename.objects.filter(old_code__iexact=code).exclude(shift_id=shift_id).exists()
    if held or held_before:
        refuse((("code",), f"{code} is {'already in use' if held else 'the old code of another shift'}"))


@router.get("/shifts", response=list[ShiftSchema], operation_id="listShifts")
def list_shifts(request) -> list[Shift]:
    """Retired shifts too: a code on an old roster still needs its name."""
    return list(Shift.objects.prefetch_related("renames"))


@router.post("/shifts", response={201: ShiftSchema}, auth=cno, operation_id="createShift")
def create_shift(request, body: ShiftBody) -> tuple[int, Shift]:
    with transaction.atomic():
        HospitalSettings.load(for_update=True)  # One writer at a time, so a taken code cannot slip through.
        _refuse_a_taken_code(body.code, None)
        shift = Shift()
        _write_shift(shift, body)
        record("shift.created", actor=request.user, target=shift.code, after=_shift_fields(shift), request=request)
    return 201, shift


@router.put("/shifts/{shift_id}", response=ShiftSchema, auth=cno, operation_id="updateShift")
def update_shift(request, shift_id: UUID, body: ShiftBody) -> Shift:
    """Hold the rules' lock throughout: a forbidden succession only ever names an active shift, and a live unit's
    rules likewise, which both this and saving either set of rules must see the other's finished work to keep true."""
    with transaction.atomic():
        settings = HospitalSettings.load(for_update=True)
        shift = get_object_or_404(Shift, pk=shift_id)
        before, after = _shift_fields(shift), body.model_dump()
        old, new = differing(before, after)
        if not new:
            return shift
        pairs = settings.rules["forbidden_successions"]
        if before["active"] and not body.active and any(before["code"] in pair for pair in pairs):
            refuse((("active",), f"{before['code']} is named in the forbidden successions of the hospital rules. "
                                 "Remove those pairs first."))
        if before["active"] and not body.active:
            # A pin that counts is on a shift its unit works (`rosters.pins`), so this covers those too.
            units = units_using(before["code"])
            if units:
                refuse((("active",), f"{before['code']} is in the unit rules of {', '.join(units)}. "
                                     "The unit's manager has to take it out of them first."))
        if "hours" in new:
            _refuse_hours_in_use(before["code"])
        if "code" in new:
            _refuse_a_taken_code(body.code, shift.pk)
            ShiftRename.objects.create(shift=shift, old_code=before["code"], new_code=body.code, by=request.user)
            _carry_rename_through_the_rules(request, settings, before["code"], body.code)
            _carry_rename_through_the_units(request, before["code"], body.code)
            carry_rename_through_allowed_shifts(before["code"], body.code)
            carry_rename_through_grids(before["code"], body.code)
        _write_shift(shift, body)
        record("shift.changed", actor=request.user, target=shift.code, before=old, after=new, request=request)
    return shift


def _refuse_hours_in_use(code: str) -> None:
    """A roster's hours were worked out with the shift's hours as they stood, and so were those of a solve on its way."""
    uses = [f"{roster.unit.name}, {roster.month:%B %Y}" for roster in using_shift(code)]
    waiting = Solve.objects.select_related("unit").filter(state__in=ACTIVE_STATES)
    uses += [f"{solve.unit.name}, {solve.month:%B %Y}" for solve in waiting
             if code in {current_code(shift) for shift in solve.input["department"]["shifts"]}]
    uses += [f"{unit.name}, {month:%B %Y}" for unit, month in counted_uses(code, this_month())]
    if uses:
        refuse((("hours",), f"The hours of {code} cannot change while the roster of an open month uses it: "
                            f"{'; '.join(dict.fromkeys(uses))}."))


def _carry_rename_through_the_rules(request, settings: HospitalSettings, old_code: str, new_code: str) -> None:
    pairs = [[new_code if code == old_code else code for code in pair]
             for pair in settings.rules["forbidden_successions"]]
    after = settings.rules | {"forbidden_successions": pairs}
    old, new = changes(settings.rules, after)
    if new:
        settings.rules = after
        settings.save()
        record("hospital_rules.changed", actor=request.user, target="hospital rules", before=old, after=new,
               request=request)


def _carry_rename_through_the_units(request, old_code: str, new_code: str) -> None:
    """Archived units too, because a block has to go on naming shifts that exist. The review flag stays as it is: a
    new name is not a review. The rows are locked because `units.api.update_unit` saves the whole row."""
    for unit in Unit.objects.select_for_update().order_by("pk"):  # By id, as an import locks them, so neither waits on the other.
        after = with_shift_codes(unit.rules, {old_code: new_code})
        old, new = differing(unit.rules, after)
        if new:
            unit.rules = after
            unit.save(update_fields=["rules"])
            record("unit_rules.changed", actor=request.user, target=unit.name, before=old, after=new, request=request)


# ---- leave types ----------------------------------------------------------------------------------
class LeaveTypeBody(StrictSchema):
    name: Name
    active: bool


class LeaveTypeSchema(Schema):
    id: UUID
    name: str
    active: bool


def _write_leave_type(row: LeaveType, body: LeaveTypeBody) -> None:
    row.name, row.active = body.name, body.active
    save_unless_taken(row, "name", f"{body.name} is already a leave type")


@router.get("/leave-types", response=list[LeaveTypeSchema], operation_id="listLeaveTypes")
def list_leave_types(request) -> list[LeaveType]:
    return list(LeaveType.objects.all())


@router.post("/leave-types", response={201: LeaveTypeSchema}, auth=cno, operation_id="createLeaveType")
def create_leave_type(request, body: LeaveTypeBody) -> tuple[int, LeaveType]:
    with transaction.atomic():
        row = LeaveType()
        _write_leave_type(row, body)
        record("leave_type.created", actor=request.user, target=row.name, after=body.model_dump(), request=request)
    return 201, row


@router.put("/leave-types/{leave_type_id}", response=LeaveTypeSchema, auth=cno, operation_id="updateLeaveType")
def update_leave_type(request, leave_type_id: UUID, body: LeaveTypeBody) -> LeaveType:
    with transaction.atomic():
        row = get_object_or_404(LeaveType.objects.select_for_update(), pk=leave_type_id)
        old, new = differing({"name": row.name, "active": row.active}, body.model_dump())
        if new:
            _write_leave_type(row, body)
            record("leave_type.changed", actor=request.user, target=row.name, before=old, after=new, request=request)
    return row


# ---- skills ---------------------------------------------------------------------------------------
class SkillBody(StrictSchema):
    name: Name = Field(description="What nurses' records, unit rules and solve inputs call it.")
    expires: bool = Field(description="Every nurse who holds it has an expiry for it, the last day it counts.")
    required_to_work: bool = Field(description="From the day after its expiry, a nurse holding it works no shift.")
    active: bool = Field(description="Off retires it: it stays on this list, and the nurses who hold it keep it.")


class SkillRenameSchema(Schema):
    old_name: str
    new_name: str
    at: dt.datetime = Field(description="In the hospital's time zone.")

    @staticmethod
    def resolve_at(rename: SkillRename) -> dt.datetime:
        return timezone.localtime(rename.at)


class SkillSchema(Schema):
    id: UUID
    name: str
    expires: bool
    required_to_work: bool
    active: bool
    renames: list[SkillRenameSchema] = Field(description="Every change of this skill's name, oldest first.")

    @staticmethod
    def resolve_renames(skill: Skill) -> list[SkillRename]:
        return list(skill.renames.all())


def _skill_fields(skill: Skill) -> dict:
    return {"name": skill.name, "expires": skill.expires, "required_to_work": skill.required_to_work,
            "active": skill.active}


def _write_skill(skill: Skill, body: SkillBody) -> None:
    skill.name, skill.expires, skill.required_to_work, skill.active = (
        body.name, body.expires, body.required_to_work, body.active)
    # The constraint still decides should anything ever write without the catalogue's lock.
    save_unless_taken(skill, "name", f"{body.name} is already a skill")


def _refuse_a_taken_name(name: str, skill_id: UUID | None) -> None:
    """Also a name another skill used to hold, as for a shift's code: a stored solve input that says that name means
    that skill, so it cannot start to mean this one. A skill may go back to a name of its own, or change its case."""
    held = Skill.objects.filter(name__iexact=name).exclude(pk=skill_id).first()
    if held:
        refuse((("name",), f"{held.name} is already a skill"))
    held_before = SkillRename.objects.filter(old_name__iexact=name).exclude(skill_id=skill_id).first()
    if held_before:
        refuse((("name",), f"{held_before.old_name} is the old name of another skill"))


NAMED_AT_MOST = 3


def _refuse_records_without_expiry(skill: Skill) -> None:
    """Turning `expires` on would leave a record dateless, an unknown the solver cannot model: refused, naming a few of the
    nurses. Off again is allowed, and the dates stay. A nurse's skill write takes the same lock first (`nurses.skills_api`)."""
    names = list(NurseSkill.objects.current().filter(skill=skill, expiry__isnull=True)
                 .order_by(Lower("nurse__user__full_name"), "nurse_id").values_list("nurse__user__full_name", flat=True))
    if not names:
        return
    if len(names) > NAMED_AT_MOST + 1:
        who = f"{', '.join(names[:NAMED_AT_MOST])} and {len(names) - NAMED_AT_MOST} more"
    else:
        who = " and ".join([", ".join(names[:-1]), names[-1]] if len(names) > 1 else names)
    refuse((("expires",), f"{who} {'hold' if len(names) > 1 else 'holds'} {skill.name} with no expiry. "
                          "Take it off them first, then record it again with its expiry."))


@router.get("/skills", response=list[SkillSchema], operation_id="listSkills")
def list_skills(request) -> list[Skill]:
    """Retired skills too: a nurse's record of one, or a past roster, still names it."""
    return list(Skill.objects.prefetch_related("renames"))


@router.post("/skills", response={201: SkillSchema}, auth=cno, operation_id="createSkill")
def create_skill(request, body: SkillBody) -> tuple[int, Skill]:
    with transaction.atomic():
        HospitalSettings.load(for_update=True)  # One writer at a time, so a taken or old name cannot slip through.
        _refuse_a_taken_name(body.name, None)
        skill = Skill()
        _write_skill(skill, body)
        record("skill.created", actor=request.user, target=skill.name, after=_skill_fields(skill), request=request)
    return 201, skill


@router.put("/skills/{skill_id}", response=SkillSchema, auth=cno, operation_id="updateSkill")
def update_skill(request, skill_id: UUID, body: SkillBody) -> Skill:
    """A rename, a change of either flag and a retire alike: `active` off retires it, on brings it back."""
    with transaction.atomic():
        HospitalSettings.load(for_update=True)
        skill = get_object_or_404(Skill, pk=skill_id)
        old, new = differing(_skill_fields(skill), body.model_dump())
        if not new:
            return skill
        if new.get("expires"):
            _refuse_records_without_expiry(skill)
        if "name" in new:
            _refuse_a_taken_name(body.name, skill.pk)
            SkillRename.objects.create(skill=skill, old_name=old["name"], new_name=body.name, by=request.user)
        _write_skill(skill, body)
        record("skill.changed", actor=request.user, target=skill.name, before=old, after=new, request=request)
    return skill


# ---- public holidays ------------------------------------------------------------------------------
class PublicHolidayBody(StrictSchema):
    date: IsoDate
    name: Name


class PublicHolidaySchema(Schema):
    id: UUID
    date: dt.date
    name: str


def _holiday_fields(row: PublicHoliday) -> dict:
    return {"date": row.date.isoformat(), "name": row.name}


def _write_holiday(row: PublicHoliday, body: PublicHolidayBody) -> None:
    row.date, row.name = body.date, body.name
    save_unless_taken(row, "date", f"{body.date.isoformat()} is already a public holiday")


@router.get("/public-holidays", response=list[PublicHolidaySchema], operation_id="listPublicHolidays")
def list_public_holidays(request, filters: Query[YearFilter]) -> list[PublicHoliday]:
    return list(PublicHoliday.objects.filter(date__year=filters.year))


@router.post("/public-holidays", response={201: PublicHolidaySchema}, auth=cno, operation_id="createPublicHoliday")
def create_public_holiday(request, body: PublicHolidayBody) -> tuple[int, PublicHoliday]:
    with transaction.atomic():
        row = PublicHoliday()
        _write_holiday(row, body)
        record("public_holiday.created", actor=request.user, target=row.date.isoformat(),
               after=_holiday_fields(row), request=request)
    return 201, row


@router.put("/public-holidays/{holiday_id}", response=PublicHolidaySchema, auth=cno,
            operation_id="updatePublicHoliday")
def update_public_holiday(request, holiday_id: UUID, body: PublicHolidayBody) -> PublicHoliday:
    with transaction.atomic():
        row = get_object_or_404(PublicHoliday.objects.select_for_update(), pk=holiday_id)
        old, new = differing(_holiday_fields(row), body.model_dump(mode="json"))
        if new:
            _write_holiday(row, body)
            record("public_holiday.changed", actor=request.user, target=row.date.isoformat(),
                   before=old, after=new, request=request)
    return row


@router.delete("/public-holidays/{holiday_id}", response={204: None}, auth=cno, operation_id="deletePublicHoliday")
def delete_public_holiday(request, holiday_id: UUID) -> tuple[int, None]:
    """A holiday has no history of its own: an entry made by mistake goes, and the audit log keeps it."""
    with transaction.atomic():
        row = get_object_or_404(PublicHoliday.objects.select_for_update(), pk=holiday_id)
        record("public_holiday.removed", actor=request.user, target=row.date.isoformat(),
               before=_holiday_fields(row), request=request)
        row.delete()
    return 204, None


# ---- Ramadan dates --------------------------------------------------------------------------------
class RamadanFix(StrictSchema):
    first: IsoDate | None = Field(None, description="With `last`: every day from this one to that one.")
    last: IsoDate | None = None
    dates: list[IsoDate] | None = Field(None, description="Or exactly these days. Empty means none this month.")


class RamadanMonth(Schema):
    month: str
    source: Literal["derived", "fixed"] = Field(description="Fixed by the CNO, or derived from the calendar.")
    dates: list[dt.date] = Field(description="The month's Ramadan days.")
    derived_dates: list[dt.date] = Field(description="What the Umm al-Qura calendar says, whichever is in force.")


def _ramadan_month(month: str, fixed: list[dt.date] | None) -> dict:
    derived = derived_ramadan_dates(month)
    return {"month": month, "source": "derived" if fixed is None else "fixed",
            "dates": derived if fixed is None else fixed, "derived_dates": derived}


def _audited_ramadan(state: dict) -> dict:
    return {"source": state["source"], "dates": [day.isoformat() for day in state["dates"]]}


def _month_within_the_calendar(month: str) -> str:
    if not FIRST_YEAR <= int(month[:4]) <= LAST_YEAR:
        raise HttpError(422, f"The calendar covers {FIRST_YEAR} to {LAST_YEAR}.")
    return month


def _fixed_dates(month: str, body: RamadanFix) -> list[dt.date]:
    """Refused here because only the path says which month a date must fall in."""
    def outside(day: dt.date) -> bool:
        return day.strftime("%Y-%m") != month

    if body.dates is not None:
        if body.first or body.last:
            refuse((("dates",), "Give a range or a list, not both"))
        outsiders = [((("dates", index)), f"{day.isoformat()} is not in {month}")
                     for index, day in enumerate(body.dates) if outside(day)]
        if outsiders:
            refuse(*outsiders)
        if len(set(body.dates)) != len(body.dates):
            refuse((("dates",), "lists a day twice"))
        return sorted(body.dates)
    if not body.first and not body.last:
        refuse((("dates",), "Give a range or a list"))
    if not body.first:
        refuse((("first",), "A range needs its first day"))
    if not body.last:
        refuse((("last",), "A range needs its last day"))
    if outside(body.first):
        refuse((("first",), f"{body.first.isoformat()} is not in {month}"))
    if outside(body.last):
        refuse((("last",), f"{body.last.isoformat()} is not in {month}"))
    if body.last < body.first:
        refuse((("last",), "must not be before the first day"))
    return [body.first + dt.timedelta(days=offset) for offset in range((body.last - body.first).days + 1)]


Month = Annotated[str, Path(pattern=MONTH_PATTERN)]


def _fixed_row(month: str) -> FixedRamadanMonth | None:
    return FixedRamadanMonth.objects.select_for_update().filter(month=month).first()


@router.get("/ramadan", response=list[RamadanMonth], operation_id="listRamadanMonths")
def list_ramadan_months(request, filters: Query[YearFilter]) -> list[dict]:
    """Every month of the year: the sighting can put a day in a month the calendar gives none."""
    fixed = dict(FixedRamadanMonth.objects.filter(month__startswith=f"{filters.year}-").values_list("month", "dates"))
    months = [f"{filters.year}-{number:02d}" for number in range(1, 13)]
    return [_ramadan_month(month, fixed.get(month)) for month in months]


@router.put("/ramadan/{month}", response=RamadanMonth, auth=cno, operation_id="fixRamadanMonth")
def fix_ramadan_month(request, month: Month, body: RamadanFix) -> dict:
    dates = _fixed_dates(_month_within_the_calendar(month), body)
    with transaction.atomic():
        row = _fixed_row(month)
        before = _ramadan_month(month, row.dates if row else None)
        after = _ramadan_month(month, dates)
        if _audited_ramadan(before) != _audited_ramadan(after):
            FixedRamadanMonth.objects.update_or_create(month=month, defaults={"dates": dates})
            record("ramadan_dates.changed", actor=request.user, target=month, before=_audited_ramadan(before),
                   after=_audited_ramadan(after), request=request)
    return after


@router.delete("/ramadan/{month}", response=RamadanMonth, auth=cno, operation_id="unfixRamadanMonth")
def unfix_ramadan_month(request, month: Month) -> dict:
    """Back to the calendar."""
    _month_within_the_calendar(month)
    after = _ramadan_month(month, None)
    with transaction.atomic():
        row = _fixed_row(month)
        if row:
            before = _ramadan_month(month, row.dates)
            row.delete()
            record("ramadan_dates.changed", actor=request.user, target=month, before=_audited_ramadan(before),
                   after=_audited_ramadan(after), request=request)
    return after
