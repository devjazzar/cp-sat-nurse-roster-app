"""A unit's roster of a month. Its manager solves, edits and submits it; the CNO and the Deputy CNO read a submitted or an
approved one, and approve or reject what is submitted (`rosters.review`). A draft is the unit management's alone, so they see
only that one exists."""
from __future__ import annotations

import datetime as dt
from typing import Annotated, Literal
from uuid import UUID

from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from ninja import Field, Query, Router, Schema
from ninja.errors import HttpError

from accounts.authz import SignedIn
from accounts.models import Role, User
from audit.log import record
from hospital.api import StrictSchema, refuse
from hospital.catalogue_api import IsoDate
from hospital.models import HospitalSettings, Shift
from nurses import membership
from nurses.api import MonthText
from nurses.models import NurseProfile
from rosters import review
from rosters.drafts import MONTH_OVER, in_current_codes, why_frozen
from rosters.editing import Checked, DraftEdits, Edit, check_saved, scored, with_edits
from rosters.grids import GridView, full_names, grid_view
from rosters.models import Roster, RosterState
from rosters.pins import AsideWhy, lost_to_leave, month_pins
from solves.api import MonthFilter, SolveProgress, chosen_month, manager, progress_of
from solves.input import assemble, changes_since
from solves.models import ACTIVE_STATES, Solve, SolveState
from solves.result import in_dates
from units.models import Unit
from units.scope import HOSPITAL_WIDE, unit_in_scope

router = Router(tags=["rosters"])
approver = SignedIn(Role.CNO, Role.DEPUTY_CNO)
reader = SignedIn(Role.UNIT_MANAGER, Role.CNO, Role.DEPUTY_CNO)
ONLY_THE_MANAGER = "Only the unit's manager changes its roster or submits it."
ONLY_APPROVERS = "Only the CNO or the Deputy CNO approve or reject a roster."


class DraftChange(Schema):
    hospital_id: str
    full_name: str
    what: Literal["gender", "leave", "joined", "left", "pins"]


class GridViolation(Schema):
    rule: str
    hospital_id: str | None
    full_name: str
    date: dt.date | None
    text: str


class GridCheck(Schema):
    """What the solver's own code says of a grid. `reason` says why it could not, and the rest is then null."""
    reason: str | None = Field(description="Why this could not be worked out: the solver's code cannot read the month as it "
                                           "stands.")
    ok: bool | None = Field(description="Whether it breaks no hard rule.")
    violations: list[GridViolation]
    cost: int | None


class DraftPin(Schema):
    hospital_id: str
    full_name: str
    date: dt.date
    shift: str = Field(description="The shift's code. Empty for a day off.")
    origin: Literal["manager", "request", "swap"]
    set_aside: AsideWhy | None = Field(description="Why this pin counts for nothing at present and reaches no solve. It is kept, "
                                                   "and counts again if that stops being so. Null for a pin that counts.")


class PinLostToLeave(Schema):
    hospital_id: str
    full_name: str
    date: dt.date
    shift: str
    by: str = Field(description="Who recorded the leave.")


class EditorShift(Schema):
    code: str
    display_name: str
    colour: str
    hours: int


class EditorNurse(Schema):
    hospital_id: str
    allowed_shifts: list[str] | None = Field(description="Null for any the unit works.")
    credited: list[dt.date] = Field(description="Their days of leave and days outside their dates, as they stand now.")


class DraftEditor(Schema):
    refusal: str | None = Field(description="Why this draft cannot be edited now: the month is over, the roster is submitted or "
                                            "approved, or the reader is not its manager.")
    shifts: list[EditorShift] = Field(description="What a cell can be pinned to: the unit's shifts.")
    nurses: list[EditorNurse]


class Draft(GridView):
    solve_id: UUID
    solved_at: dt.datetime
    restored_at: dt.datetime | None = Field(description="When the manager restored this result as the draft. Null when the "
                                                        "draft is what its solve left.")
    edited: bool = Field(description="Whether the grid differs from what its solve answered.")
    cost: int | None = Field(description="This grid's on the month as it stands, which is its solve's while neither the grid nor "
                                         "the month has changed since. Null if it could not be worked out.")
    solved_cost: int
    check: GridCheck | None = Field(description="What the grid breaks on the month as it stands. Null while neither the grid nor "
                                                "the month has changed since its solve, whose roster breaks none.")
    pins: list[DraftPin]
    pins_lost_to_leave: list[PinLostToLeave] = Field(description="Pins leave has replaced since this draft's solve was started, "
                                                                 "whoever recorded it, until a newer solve has taken that in.")
    editor: DraftEditor
    stopped_early: bool
    changes: list[DraftChange] = Field(description="What has changed since this draft was solved. Warned of here, and "
                                                   "checked again at submit and at approval.")


class Waiting(Schema):
    submitted_by: str
    submitted_at: dt.datetime
    new_since: list[DraftChange] = Field(description="Those of `changes` that have come since it was submitted, such as leave "
                                                     "recorded while it waits: the manager was not warned of these.")


class Rejection(Schema):
    rejected_by: str
    rejected_at: dt.datetime
    comment: str


class Approval(Schema):
    approved_by: str
    approved_at: dt.datetime
    version: int = Field(description="The roster version in force.")


class RosterMonth(Schema):
    month: str
    state: Literal["none", "draft", "submitted", "approved"] = Field(description="`none` until a solve keeps a roster.")
    submitted: Waiting | None = Field(description="While it waits for a decision.")
    last_rejection: Rejection | None = Field(description="The latest rejection, kept through the submits after it.")
    approved: Approval | None
    submit_refusal: str | None = Field(description="Why the manager cannot submit it now: also a hard rule it breaks on the "
                                                   "month as it stands, which `draft.check` lists.")
    approve_refusal: str | None = Field(description="Why it cannot be approved now, the same check included.")
    reject_refusal: str | None
    active_solve: SolveProgress | None
    last_solve: SolveProgress | None = Field(description="The latest to have ended, if it is newer than the draft or there "
                                                         "is none: why the draft is not what was last asked for. A restore "
                                                         "is newer than what it follows, as the manager has seen those.")
    draft: Draft | None = Field(description="The roster's grid and what it answered, whatever its state. Null for the CNO and the "
                                            "Deputy CNO while it is a draft.")


def _why_not_edit(roster: Roster, user: User) -> str | None:
    """One place for the page and the save: a frozen roster (`why_frozen`) and a month that is over refuse a pin."""
    if user.role != Role.UNIT_MANAGER:
        return ONLY_THE_MANAGER
    return why_frozen(roster) or (MONTH_OVER if roster.month < membership.this_month() else None)


def _grid_check(checked: Checked, month: dt.date) -> GridCheck:
    if checked.reason:
        return GridCheck(reason=in_dates(checked.reason, month), ok=None, violations=[], cost=None)
    violations = checked.answer["violations"]
    names = full_names(row["nurse"] for row in violations if row["nurse"])
    return GridCheck(reason=None, ok=checked.answer["ok"], cost=checked.answer["cost"],
                     violations=[GridViolation(rule=row["rule"], hospital_id=row["nurse"], full_name=names.get(row["nurse"], ""),
                                               date=row["date"], text=in_dates(row["text"], month)) for row in violations])


def _editor(roster: Roster, solve_input: dict, user: User) -> DraftEditor:
    codes = roster.unit.rules.get("shifts", [])
    return DraftEditor(
        refusal=_why_not_edit(roster, user),
        shifts=[EditorShift(code=shift.code, display_name=shift.display_name, colour=shift.colour, hours=shift.hours)
                for shift in Shift.objects.filter(code__in=codes, active=True)],
        nurses=[EditorNurse(hospital_id=row["id"], allowed_shifts=row["allowed_shifts"], credited=row["leave"])
                for row in solve_input["nurses"]])


def _lost_to_leave(roster: Roster) -> list[PinLostToLeave]:
    # A newer solve than the draft's took that leave in, even if an older result has been restored since.
    ended = Solve.objects.filter(unit=roster.unit, month=roster.month).exclude(state__in=ACTIVE_STATES)
    newest = ended.order_by("-requested_at").first()
    rows = lost_to_leave(roster.unit, roster.month, max(roster.solve.requested_at, newest.requested_at))
    return [PinLostToLeave(hospital_id=row.nurse.user.username, full_name=row.nurse.user.full_name, date=row.date, shift=row.code,
                           by=row.removed_by.full_name or row.removed_by.username) for row in rows]


def _changes(changes: list[dict]) -> list[DraftChange]:
    names = full_names(change["hospital_id"] for change in changes)
    return [DraftChange(hospital_id=change["hospital_id"], what=change["what"], full_name=names.get(change["hospital_id"], ""))
            for change in changes]


def _checked(roster: Roster, changes: list[dict]) -> Checked | None:
    """None while neither the grid nor the month has changed since its solve, whose own answer then holds: it breaks no hard
    rule, since a roster that does never becomes a draft."""
    edited = roster.grid != in_current_codes(roster.solve.result["roster"])
    return check_saved(roster) if edited or changes else None


def _draft(roster: Roster, changes: list[dict], checked: Checked | None, user: User) -> Draft:
    solve = roster.solve
    edited = roster.grid != in_current_codes(solve.result["roster"])
    # The solve's own cost and its roster's soundness hold only for the month it was given.
    check = _grid_check(checked, roster.month) if checked else None
    pins = month_pins(roster.unit, roster.month)
    return Draft(**grid_view(roster.grid, solve).dict(), solve_id=solve.pk, solved_at=timezone.localtime(solve.finished_at),
                 restored_at=timezone.localtime(roster.restored_at) if roster.restored_at else None,
                 edited=edited, cost=check.cost if check else solve.result["cost"], solved_cost=solve.result["cost"], check=check,
                 stopped_early=solve.state == SolveState.CANCELLED,
                 pins=[DraftPin(hospital_id=pin.nurse.user.username, full_name=pin.nurse.user.full_name, date=pin.date,
                                shift=pin.code, origin=pin.origin, set_aside=pin.aside) for pin in pins.rows],
                 pins_lost_to_leave=_lost_to_leave(roster),
                 editor=_editor(roster, assemble(roster.unit, roster.month).input, user), changes=_changes(changes))


def _not_the_draft(ended: Solve | None, roster: Roster | None) -> Solve | None:
    if ended is None or roster is None:
        return ended
    return ended if ended.pk != roster.solve_id and ended.finished_at > roster.updated_at else None


def _waiting(roster: Roster) -> Waiting | None:
    submission = review.waiting(roster)
    if submission is None:
        return None
    return Waiting(submitted_by=review.name_of(submission.submitted_by), submitted_at=timezone.localtime(submission.submitted_at),
                   new_since=_changes(review.new_since(submission)))


def _rejection(roster: Roster) -> Rejection | None:
    rejected = review.last_rejection(roster)
    return rejected and Rejection(rejected_by=review.name_of(rejected.decided_by), rejected_at=timezone.localtime(rejected.decided_at),
                                  comment=rejected.comment)


def _approval(roster: Roster) -> Approval | None:
    approved = review.approval(roster)
    return approved and Approval(approved_by=review.name_of(approved.decided_by), approved_at=timezone.localtime(approved.decided_at),
                                 version=roster.versions.count())


def _roster_month(unit: Unit, month: dt.date, user: User) -> RosterMonth:
    solves = Solve.objects.filter(unit=unit, month=month)
    roster = Roster.objects.select_related("solve", "unit").filter(unit=unit, month=month).first()
    approving = user.role in HOSPITAL_WIDE
    label = month.strftime("%Y-%m")
    if roster is None or (approving and roster.state not in review.SEEN_BY_APPROVERS):
        none = "This month has no roster yet." if roster is None else None
        return RosterMonth(month=label, state=roster.state if roster else "none", submitted=None, last_rejection=None,
                           approved=None, active_solve=None if approving else _active(solves), draft=None,
                           last_solve=None if approving else _last(solves, roster),
                           submit_refusal=ONLY_THE_MANAGER if approving else none or None,
                           approve_refusal=review.why_not_decide(roster) if approving else ONLY_APPROVERS,
                           reject_refusal=review.why_not_decide(roster) if approving else ONLY_APPROVERS)
    changes = changes_since(roster.solve.input, unit, month)
    checked = _checked(roster, changes)
    return RosterMonth(
        month=label, state=roster.state, submitted=_waiting(roster), last_rejection=_rejection(roster),
        approved=_approval(roster), active_solve=None if approving else _active(solves),
        last_solve=None if approving else _last(solves, roster), draft=_draft(roster, changes, checked, user),
        submit_refusal=ONLY_THE_MANAGER if approving else review.why_not_submit(roster, checked),
        approve_refusal=review.why_not_approve(roster, checked) if approving else ONLY_APPROVERS,
        reject_refusal=review.why_not_decide(roster) if approving else ONLY_APPROVERS)


def _active(solves) -> SolveProgress | None:
    active = solves.filter(state__in=ACTIVE_STATES).first()
    return progress_of(active) if active else None


def _last(solves, roster: Roster | None) -> SolveProgress | None:
    last = _not_the_draft(solves.exclude(state__in=ACTIVE_STATES).order_by("-finished_at", "-id").first(), roster)
    return progress_of(last) if last else None


@router.get("/{unit_id}/roster", response=RosterMonth, auth=reader, operation_id="getRosterMonth")
def roster_month(request: HttpRequest, unit_id: UUID, filters: Query[MonthFilter]) -> RosterMonth:
    """The CNO and the Deputy CNO read any unit's, and see a draft only as one that exists, with no solve of it."""
    return _roster_month(unit_in_scope(request.user, unit_id), chosen_month(filters.month), request.user)


# A whole month of a large unit, and no more.
MAX_EDITS = 3100


class EditBody(StrictSchema):
    hospital_id: str = Field(min_length=1, max_length=150)
    date: IsoDate
    action: Literal["shift", "off", "clear"] = Field(description="Pin a shift, pin a day off, or clear the cell's pin.")
    shift: str | None = Field(None, max_length=8, description="The shift's code, with `shift`.")


class EditsBody(StrictSchema):
    month: MonthText
    edits: Annotated[list[EditBody], Field(max_length=MAX_EDITS)]


def _edits_of(body: EditsBody) -> list[Edit]:
    return [Edit(hospital_id=edit.hospital_id, date=edit.date, action=edit.action, shift=edit.shift) for edit in body.edits]


def _refuse_nonsense(body: EditsBody) -> list[Edit]:
    """Whatever the month holds, these could never be meant, so they are 422s for a save and a check alike."""
    edits = _edits_of(body)
    wrong = [(("edits", index), f"{edit.day} is not in {body.month}.")
             for index, edit in enumerate(edits) if edit.date.strftime("%Y-%m") != body.month]
    wrong += [(("edits", index), "Choose a shift.")
              for index, edit in enumerate(edits) if edit.action == "shift" and not edit.shift]
    seen = set()
    for index, edit in enumerate(edits):
        if (edit.hospital_id, edit.date) in seen:
            wrong.append((("edits", index), "This cell is edited twice."))
        seen.add((edit.hospital_id, edit.date))
    if wrong:
        refuse(*wrong)
    return edits


def _draft_of(unit: Unit, month: dt.date, *, for_update: bool = False) -> Roster:
    rows = Roster.objects.select_for_update(of=("self",)) if for_update else Roster.objects
    roster = rows.select_related("solve", "unit").filter(unit=unit, month=month).first()
    if roster is None:
        raise HttpError(409, "This month has no draft yet. Solve it first.")
    return roster


class EditRefusal(Schema):
    hospital_id: str
    date: dt.date
    reason: str


class DraftCheck(GridCheck):
    cost_before: int | None = Field(description="The saved grid's, worked out the same way.")
    delta: int | None = Field(description="`cost` less `cost_before`.")
    refusals: list[EditRefusal] = Field(description="Edits a save would refuse, which are left out of this answer.")


@router.post("/{unit_id}/roster/check", response=DraftCheck, auth=manager, operation_id="checkDraftEdits")
def check_edits(request: HttpRequest, unit_id: UUID, body: EditsBody) -> DraftCheck:
    """The draft as these edits would make it, against the month as it stands, on the solver's own code in this process: `Checked`
    says why. Saves nothing and writes no audit entry."""
    unit = unit_in_scope(request.user, unit_id)
    month = dt.date.fromisoformat(f"{body.month}-01")
    edits = _refuse_nonsense(body)
    roster = _draft_of(unit, month)
    refused = _why_not_edit(roster, request.user)
    if refused:
        raise HttpError(409, refused)
    editing = DraftEdits(roster)
    reasons = [editing.refusal(edit) for edit in edits]
    refusals = [EditRefusal(hospital_id=edit.hospital_id, date=edit.date, reason=reason)
                for edit, reason in zip(edits, reasons) if reason]
    good = [edit for edit, reason in zip(edits, reasons) if not reason]
    solve_input = assemble(unit, month).input
    before = scored(solve_input, roster.grid)
    after = scored(with_edits(solve_input, editing, good), editing.grid_after(good))
    delta = after.cost - before.cost if after.cost is not None and before.cost is not None else None
    return DraftCheck(**_grid_check(after, month).dict(), cost_before=before.cost, delta=delta, refusals=refusals)


@router.post("/{unit_id}/roster/pins", response=RosterMonth, auth=manager, operation_id="saveDraftPins")
def save_pins(request: HttpRequest, unit_id: UUID, body: EditsBody) -> RosterMonth:
    """All of it or none of it. Under the catalogue's lock, which a solve's start and end, a restore and a rename hold, then each
    nurse's, which a leave write holds and which comes before a unit's in a transfer. A solve already under way was given the
    month without these: it may run on, its roster takes them on top when it ends, and the draft says so through `changes`. The
    audit entry names the unit and the month and how many pins and cells changed, and no nurse, date or shift: the System Admin
    sees no roster."""
    month = dt.date.fromisoformat(f"{body.month}-01")
    edits = _refuse_nonsense(body)
    with transaction.atomic():
        HospitalSettings.load(for_update=True)
        wanted = [edit.hospital_id for edit in edits]
        list(NurseProfile.objects.select_for_update(of=("self", "user")).select_related("user")
             .filter(user__username__in=wanted).order_by("pk"))
        unit = unit_in_scope(request.user, unit_id, for_update=True)
        roster = _draft_of(unit, month, for_update=True)
        refused = _why_not_edit(roster, request.user)
        if refused:
            raise HttpError(409, refused)
        editing = DraftEdits(roster)
        refusals = [(("edits", index), reason) for index, edit in enumerate(edits) if (reason := editing.refusal(edit))]
        if refusals:
            refuse(*refusals)
        pins, cells = editing.save(edits, request.user)
        if pins or cells:
            record("roster.draft_edited", actor=request.user, target=f"{unit.name}, {body.month}", request=request,
                   after={"pins": pins, "cells": cells})
    return _roster_month(unit, month, request.user)


class MonthBody(StrictSchema):
    month: MonthText


class RejectBody(MonthBody):
    comment: str = Field(min_length=1, max_length=2000, description="Why, for the unit's manager, who sees it with the draft.")


def _target(unit: Unit, month: dt.date) -> str:
    return f"{unit.name}, {month:%Y-%m}"


def _locked_roster(unit: Unit, month: dt.date) -> Roster | None:
    return Roster.objects.select_for_update(of=("self",)).select_related("solve", "unit").filter(unit=unit, month=month).first()


@router.post("/{unit_id}/roster/submit", response=RosterMonth, auth=manager, operation_id="submitRoster")
def submit_roster(request: HttpRequest, unit_id: UUID, body: MonthBody) -> RosterMonth:
    """Checked again on the month as it stands, always: a draft out of date or edited by hand goes through with its warning,
    and is refused only if it breaks a hard rule or cannot be checked. Refused while a solve of the month is active, so a solve
    never ends on a frozen grid. Under the catalogue's lock, the month's nurses' and the unit's, in that order, as approving takes
    them. The audit entry names the unit and the month."""
    month = dt.date.fromisoformat(f"{body.month}-01")
    with transaction.atomic():
        HospitalSettings.load(for_update=True)
        # The nurses' lock too, so that no leave lands between the check and the month kept for the approver to compare with.
        review.lock_the_months_nurses(unit_in_scope(request.user, unit_id), month,
                                      Roster.objects.filter(unit_id=unit_id, month=month).first())
        unit = unit_in_scope(request.user, unit_id, for_update=True)
        roster = _locked_roster(unit, month)
        if roster is None:
            raise HttpError(409, "This month has no draft yet. Solve it first.")
        refusal = review.why_not_submit(roster, check_saved(roster))
        if refusal:
            raise HttpError(409, refusal)
        review.submit(roster, request.user)
        record("roster.submitted", actor=request.user, target=_target(unit, month), request=request)
    return _roster_month(unit, month, request.user)


@router.post("/{unit_id}/roster/approve", response=RosterMonth, auth=approver, operation_id="approveRoster")
def approve_roster(request: HttpRequest, unit_id: UUID, body: MonthBody) -> RosterMonth:
    """Checked again on the month as it stands, since leave may be recorded while it waits, and refused only if that fails. Under
    the catalogue's lock, then the month's nurses', which a leave write takes, then the unit's: no leave lands between the check
    and the approval, and of two approvers the second is told the first decided. The first approval makes version 1."""
    month = dt.date.fromisoformat(f"{body.month}-01")
    with transaction.atomic():
        HospitalSettings.load(for_update=True)
        unit = unit_in_scope(request.user, unit_id)
        review.lock_the_months_nurses(unit, month, Roster.objects.filter(unit=unit, month=month).first())
        unit = unit_in_scope(request.user, unit_id, for_update=True)
        roster = _locked_roster(unit, month)
        refusal = review.why_not_decide(roster) or review.why_not_approve(roster, check_saved(roster))
        if refusal:
            raise HttpError(409, refusal)
        version = review.approve(roster, request.user)
        record("roster.approved", actor=request.user, target=_target(unit, month), request=request,
               after={"version": version.number})
    return _roster_month(unit, month, request.user)


@router.post("/{unit_id}/roster/reject", response=RosterMonth, auth=approver, operation_id="rejectRoster")
def reject_roster(request: HttpRequest, unit_id: UUID, body: RejectBody) -> RosterMonth:
    """Back to draft, with the comment kept for the manager. The audit entry holds no comment, since it may name a nurse or
    their leave and the System Admin reads the log."""
    month = dt.date.fromisoformat(f"{body.month}-01")
    if not body.comment.strip():
        refuse((("comment",), "Say why, for the unit's manager."))
    with transaction.atomic():
        HospitalSettings.load(for_update=True)
        unit = unit_in_scope(request.user, unit_id, for_update=True)
        roster = _locked_roster(unit, month)
        refusal = review.why_not_decide(roster)
        if refusal:
            raise HttpError(409, refusal)
        review.reject(roster, request.user, body.comment.strip())
        record("roster.rejected", actor=request.user, target=_target(unit, month), request=request)
    return _roster_month(unit, month, request.user)
