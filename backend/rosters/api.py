"""A unit's roster of a month: only its manager, for now. Ticket 14 opens reading to the approvers."""
from __future__ import annotations

import datetime as dt
from typing import Literal
from uuid import UUID

from django.http import HttpRequest
from django.utils import timezone
from ninja import Field, Query, Router, Schema

from accounts.models import User
from hospital.models import Shift
from rosters.models import Roster
from solves.api import MonthFilter, SolveProgress, chosen_month, manager, progress_of
from solves.input import changes_since
from solves.models import ACTIVE_STATES, Solve, SolveState
from units.scope import unit_in_scope

router = Router(tags=["rosters"])


class GridShift(Schema):
    code: str
    display_name: str
    colour: str
    hours: int


class GridDay(Schema):
    date: dt.date
    weekend: bool
    holiday: bool


class GridCell(Schema):
    shift: str = Field(description="The shift's code. Empty for a day not worked.")
    kind: Literal["shift", "off", "leave", "outside"] = Field(
        description="`outside` is before a start date or after an end date, credited like leave.")


class GridRow(Schema):
    hospital_id: str
    full_name: str
    cells: list[GridCell]


class RulePenalty(Schema):
    rule: str = Field(description="The soft rule's name: the same as its weight's.")
    penalty: int


class DraftChange(Schema):
    hospital_id: str
    full_name: str
    what: Literal["gender", "leave", "joined", "left"]


class Draft(Schema):
    solve_id: UUID
    updated_at: dt.datetime
    cost: int
    stopped_early: bool
    days: list[GridDay]
    rows: list[GridRow]
    shifts: list[GridShift]
    penalties: list[RulePenalty]
    changes: list[DraftChange] = Field(description="What has changed since this draft was solved. Warned of here, and "
                                                   "validated again at submit (ticket 14).")


class RosterMonth(Schema):
    month: str
    active_solve: SolveProgress | None
    last_solve: SolveProgress | None = Field(description="The latest to have ended, if it is newer than the draft or there "
                                                         "is none: why the draft is not what was last asked for.")
    draft: Draft | None


def _full_names(hospital_ids) -> dict[str, str]:
    return dict(User.objects.filter(username__in=hospital_ids).values_list("username", "full_name"))


def _draft(roster: Roster) -> Draft:
    solve = roster.solve
    general, result = solve.input["general"], solve.result
    days = sorted({day for row in roster.grid.values() for day in row})
    holidays = set(solve.input["public_holidays"])
    credited = {row["id"]: set(row.get("leave", [])) for row in solve.input["nurses"]}
    names = _full_names(roster.grid)

    def cell(hospital_id: str, day: str, code: str) -> GridCell:
        """As the draft was solved. What has changed since is `changes`."""
        if code:
            return GridCell(shift=code, kind="shift")
        if day in solve.outside_days.get(hospital_id, ()):
            return GridCell(shift="", kind="outside")
        return GridCell(shift="", kind="leave" if day in credited.get(hospital_id, ()) else "off")

    rows = [GridRow(hospital_id=hospital_id, full_name=names.get(hospital_id, ""),
                    cells=[cell(hospital_id, day, row[day]) for day in days])
            for hospital_id, row in sorted(roster.grid.items(), key=lambda item: (names.get(item[0], "").lower(), item[0]))]
    used = {code for row in roster.grid.values() for code in row.values() if code}
    changes = changes_since(solve.input, roster.unit, roster.month)
    change_names = _full_names(change["hospital_id"] for change in changes)
    return Draft(solve_id=solve.pk, updated_at=timezone.localtime(roster.updated_at), cost=result["cost"],
                 stopped_early=solve.state == SolveState.CANCELLED,
                 days=[GridDay(date=day, weekend=dt.date.fromisoformat(day).weekday() in general["weekend_weekdays"],
                               holiday=day in holidays) for day in days],
                 rows=rows,
                 shifts=[GridShift(code=shift.code, display_name=shift.display_name, colour=shift.colour, hours=shift.hours)
                         for shift in Shift.objects.filter(code__in=used)],
                 penalties=[RulePenalty(rule=rule, penalty=penalty) for rule, penalty in sorted(result["penalties"].items())],
                 changes=[DraftChange(hospital_id=change["hospital_id"], what=change["what"],
                                      full_name=change_names.get(change["hospital_id"], "")) for change in changes])


@router.get("/{unit_id}/roster", response=RosterMonth, auth=manager, operation_id="getRosterMonth")
def roster_month(request: HttpRequest, unit_id: UUID, filters: Query[MonthFilter]) -> RosterMonth:
    unit = unit_in_scope(request.user, unit_id)
    month = chosen_month(filters.month)
    solves = Solve.objects.filter(unit=unit, month=month)
    active = solves.filter(state__in=ACTIVE_STATES).first()
    roster = Roster.objects.select_related("solve", "unit").filter(unit=unit, month=month).first()
    ended = solves.exclude(state__in=ACTIVE_STATES).order_by("-finished_at", "-id").first()
    last = ended if ended is not None and (roster is None or ended.pk != roster.solve_id) else None
    return RosterMonth(month=month.strftime("%Y-%m"), active_solve=progress_of(active) if active else None,
                       last_solve=progress_of(last) if last else None, draft=_draft(roster) if roster else None)
