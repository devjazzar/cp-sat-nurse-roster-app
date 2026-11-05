"""A unit's roster of a month: only its manager, for now. Ticket 14 opens reading to the approvers."""
from __future__ import annotations

import datetime as dt
from typing import Literal
from uuid import UUID

from django.http import HttpRequest
from django.utils import timezone
from ninja import Field, Query, Router, Schema

from rosters.grids import GridView, full_names, grid_view
from rosters.models import Roster
from solves.api import MonthFilter, SolveProgress, chosen_month, manager, progress_of
from solves.input import changes_since
from solves.models import ACTIVE_STATES, Solve, SolveState
from units.scope import unit_in_scope

router = Router(tags=["rosters"])


class DraftChange(Schema):
    hospital_id: str
    full_name: str
    what: Literal["gender", "leave", "joined", "left"]


class Draft(GridView):
    solve_id: UUID
    solved_at: dt.datetime
    restored_at: dt.datetime | None = Field(description="When the manager restored this result as the draft. Null when the "
                                                        "draft is what its solve left.")
    cost: int
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


def _draft(roster: Roster) -> Draft:
    solve = roster.solve
    changes = changes_since(solve.input, roster.unit, roster.month)
    change_names = full_names(change["hospital_id"] for change in changes)
    return Draft(**grid_view(roster.grid, solve).dict(), solve_id=solve.pk, solved_at=timezone.localtime(solve.finished_at),
                 restored_at=timezone.localtime(roster.restored_at) if roster.restored_at else None,
                 cost=solve.result["cost"], stopped_early=solve.state == SolveState.CANCELLED,
                 changes=[DraftChange(hospital_id=change["hospital_id"], what=change["what"],
                                      full_name=change_names.get(change["hospital_id"], "")) for change in changes])


def _not_the_draft(ended: Solve | None, roster: Roster | None) -> Solve | None:
    if ended is None or roster is None:
        return ended
    return ended if ended.pk != roster.solve_id and ended.finished_at > roster.updated_at else None


@router.get("/{unit_id}/roster", response=RosterMonth, auth=manager, operation_id="getRosterMonth")
def roster_month(request: HttpRequest, unit_id: UUID, filters: Query[MonthFilter]) -> RosterMonth:
    unit = unit_in_scope(request.user, unit_id)
    month = chosen_month(filters.month)
    solves = Solve.objects.filter(unit=unit, month=month)
    active = solves.filter(state__in=ACTIVE_STATES).first()
    roster = Roster.objects.select_related("solve", "unit").filter(unit=unit, month=month).first()
    ended = solves.exclude(state__in=ACTIVE_STATES).order_by("-finished_at", "-id").first()
    last = _not_the_draft(ended, roster)
    return RosterMonth(month=month.strftime("%Y-%m"), active_solve=progress_of(active) if active else None,
                       last_solve=progress_of(last) if last else None, draft=_draft(roster) if roster else None)
