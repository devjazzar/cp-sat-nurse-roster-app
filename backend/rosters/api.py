"""A unit's roster of a month: only its manager, for now. Ticket 14 opens reading to the approvers."""
from __future__ import annotations

import datetime as dt
from typing import Annotated, Literal
from uuid import UUID

from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from ninja import Field, Query, Router, Schema
from ninja.errors import HttpError

from audit.log import record
from hospital.api import StrictSchema, refuse
from hospital.catalogue_api import IsoDate
from hospital.models import HospitalSettings, Shift
from nurses import membership
from nurses.api import MonthText
from nurses.models import NurseProfile
from rosters.drafts import MONTH_OVER, in_current_codes
from rosters.editing import Checked, DraftEdits, Edit, check_saved, scored, with_edits
from rosters.grids import GridView, full_names, grid_view
from rosters.models import Roster
from rosters.pins import AsideWhy, lost_to_leave, month_pins
from solves.api import MonthFilter, SolveProgress, chosen_month, manager, progress_of
from solves.input import assemble, changes_since
from solves.models import ACTIVE_STATES, Solve, SolveState
from solves.result import in_dates
from units.models import Unit
from units.scope import unit_in_scope

router = Router(tags=["rosters"])


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
    refusal: str | None = Field(description="Why this draft cannot be edited now. Ticket 14 adds a frozen roster here.")
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
                                                   "validated again at submit (ticket 14).")


class RosterMonth(Schema):
    month: str
    active_solve: SolveProgress | None
    last_solve: SolveProgress | None = Field(description="The latest to have ended, if it is newer than the draft or there "
                                                         "is none: why the draft is not what was last asked for. A restore "
                                                         "is newer than what it follows, as the manager has seen those.")
    draft: Draft | None


def _why_not_edit(month: dt.date) -> str | None:
    """Ticket 14: a submitted or approved roster is frozen, and that belongs here."""
    return MONTH_OVER if month < membership.this_month() else None


def _grid_check(checked: Checked, month: dt.date) -> GridCheck:
    if checked.reason:
        return GridCheck(reason=in_dates(checked.reason, month), ok=None, violations=[], cost=None)
    violations = checked.answer["violations"]
    names = full_names(row["nurse"] for row in violations if row["nurse"])
    return GridCheck(reason=None, ok=checked.answer["ok"], cost=checked.answer["cost"],
                     violations=[GridViolation(rule=row["rule"], hospital_id=row["nurse"], full_name=names.get(row["nurse"], ""),
                                               date=row["date"], text=in_dates(row["text"], month)) for row in violations])


def _editor(roster: Roster, solve_input: dict) -> DraftEditor:
    codes = roster.unit.rules.get("shifts", [])
    return DraftEditor(
        refusal=_why_not_edit(roster.month),
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


def _draft(roster: Roster) -> Draft:
    solve = roster.solve
    changes = changes_since(solve.input, roster.unit, roster.month)
    change_names = full_names(change["hospital_id"] for change in changes)
    edited = roster.grid != in_current_codes(solve.result["roster"])
    # The solve's own cost and its roster's soundness hold only for the month it was given.
    check = _grid_check(check_saved(roster), roster.month) if edited or changes else None
    pins = month_pins(roster.unit, roster.month)
    return Draft(**grid_view(roster.grid, solve).dict(), solve_id=solve.pk, solved_at=timezone.localtime(solve.finished_at),
                 restored_at=timezone.localtime(roster.restored_at) if roster.restored_at else None,
                 edited=edited, cost=check.cost if check else solve.result["cost"], solved_cost=solve.result["cost"], check=check,
                 stopped_early=solve.state == SolveState.CANCELLED,
                 pins=[DraftPin(hospital_id=pin.nurse.user.username, full_name=pin.nurse.user.full_name, date=pin.date,
                                shift=pin.code, origin=pin.origin, set_aside=pin.aside) for pin in pins.rows],
                 pins_lost_to_leave=_lost_to_leave(roster),
                 editor=_editor(roster, assemble(roster.unit, roster.month).input),
                 changes=[DraftChange(hospital_id=change["hospital_id"], what=change["what"],
                                      full_name=change_names.get(change["hospital_id"], "")) for change in changes])


def _not_the_draft(ended: Solve | None, roster: Roster | None) -> Solve | None:
    if ended is None or roster is None:
        return ended
    return ended if ended.pk != roster.solve_id and ended.finished_at > roster.updated_at else None


def _roster_month(unit: Unit, month: dt.date) -> RosterMonth:
    solves = Solve.objects.filter(unit=unit, month=month)
    active = solves.filter(state__in=ACTIVE_STATES).first()
    roster = Roster.objects.select_related("solve", "unit").filter(unit=unit, month=month).first()
    ended = solves.exclude(state__in=ACTIVE_STATES).order_by("-finished_at", "-id").first()
    last = _not_the_draft(ended, roster)
    return RosterMonth(month=month.strftime("%Y-%m"), active_solve=progress_of(active) if active else None,
                       last_solve=progress_of(last) if last else None, draft=_draft(roster) if roster else None)


@router.get("/{unit_id}/roster", response=RosterMonth, auth=manager, operation_id="getRosterMonth")
def roster_month(request: HttpRequest, unit_id: UUID, filters: Query[MonthFilter]) -> RosterMonth:
    return _roster_month(unit_in_scope(request.user, unit_id), chosen_month(filters.month))


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
        refused = _why_not_edit(month)
        if refused:
            raise HttpError(409, refused)
        roster = _draft_of(unit, month, for_update=True)
        editing = DraftEdits(roster)
        refusals = [(("edits", index), reason) for index, edit in enumerate(edits) if (reason := editing.refusal(edit))]
        if refusals:
            refuse(*refusals)
        pins, cells = editing.save(edits, request.user)
        if pins or cells:
            record("roster.draft_edited", actor=request.user, target=f"{unit.name}, {body.month}", request=request,
                   after={"pins": pins, "cells": cells})
    return _roster_month(unit, month)
