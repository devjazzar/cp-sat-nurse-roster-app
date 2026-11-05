"""Solving a unit's month: only its manager."""
from __future__ import annotations

import datetime as dt
from typing import Literal
from uuid import UUID

from django.db import transaction
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Field, Query, Router, Schema, Status
from ninja.errors import HttpError

from accounts.authz import SignedIn
from accounts.models import Role
from accounts.sessions import not_activity
from audit.log import record
from hospital.api import StrictSchema, refuse
from hospital.models import HospitalSettings
from nurses import membership
from nurses.api import MonthText
from nurses.models import NurseProfile
from ops import solver_client
from ops.models import TechnicalSettings
from ops.queue import enqueue
from ops.solver_client import SolverRefused, SolverUnreachable
from rosters.drafts import frozen_month
from solves.input import Assembled, assemble, solver_refusal
from solves.models import ACTIVE_STATES, Solve, SolveFailure, SolveState
from solves.result import has_a_roster_to_keep, in_dates, precheck_of
from solves.tasks import run_solve
from units.models import Unit
from units.scope import unit_in_scope

router = Router(tags=["solves"])
manager = SignedIn(Role.UNIT_MANAGER)


class MonthFilter(Schema):
    month: MonthText | None = Field(None, description="YYYY-MM. The month after the hospital's current one when left out, "
                                                      "since that is the one usually being rostered.")


def chosen_month(month: str | None) -> dt.date:
    if month:
        return dt.date.fromisoformat(f"{month}-01")
    this = membership.this_month()
    return (this + dt.timedelta(days=32)).replace(day=1)


def _time_limits(unit: Unit) -> tuple[int, int]:
    """The default and the cap. A unit's default can be above the cap if the System Admin lowered it after the unit's save."""
    cap = TechnicalSettings.load().time_limit_cap_seconds
    return min(unit.default_time_limit, cap), cap


def _names(nurses: list[NurseProfile]) -> list[str]:
    return [nurse.user.full_name or nurse.user.username for nurse in nurses]


def _what_stops_it(unit: Unit, month: dt.date, assembled: Assembled) -> str | None:
    if month < membership.this_month():
        return "This month is over, so it cannot be solved."
    frozen = frozen_month(unit, month)
    if frozen:
        return frozen
    if Solve.objects.filter(unit=unit, month=month, state__in=ACTIVE_STATES).exists():
        return "A solve of this month is already queued or running."
    if not assembled.nurses:
        return "This unit has no nurses in this month."
    if assembled.to_check:
        return (f"Check the allowed shifts of {', '.join(_names(assembled.to_check))} first: a transfer emptied them, "
                "as none of their shifts are worked here.")
    return None


class Summary(Schema):
    nurses: int
    leave_days: int = Field(description="Recorded leave within the nurses' dates.")
    outside_days: int = Field(description="Days before a start date or after an end date, credited like leave.")
    pins: int = Field(description="Pinned cells that reach this solve.")


class Warnings(Schema):
    hospital_rules_need_review: bool
    unit_rules_need_review: bool
    unreviewed_scores: int = Field(description="Nurses of the month whose attributes no manager has ever saved, so their "
                                               "score is still the default.")
    left_out: list[str] = Field(description="Names of managers with a nurse profile whose account is deactivated.")


class SolvePreview(Schema):
    month: str
    summary: Summary
    warnings: Warnings
    precheck: list[str] | None = Field(description="Reasons the month may have no roster. Empty when none are known; null "
                                                   "when the check could not run.")
    rules_refusal: str | None = Field(description="Why the solver would refuse the rules as they stand. Not a failed solve: "
                                                  "review the unit rules.")
    refusal: str | None = Field(description="Why no solve can start for this month, whatever the rules say.")
    time_limit_default: int
    time_limit_cap: int


@router.get("/{unit_id}/solves/preview", response=SolvePreview, auth=manager, operation_id="previewSolve")
def preview(request: HttpRequest, unit_id: UUID, filters: Query[MonthFilter]) -> SolvePreview:
    unit = unit_in_scope(request.user, unit_id)
    month = chosen_month(filters.month)
    default, cap = _time_limits(unit)
    assembled = assemble(unit, month, time_limit=default)
    stopped_by = _what_stops_it(unit, month, assembled)
    refusal = solver_refusal(assembled.input) if assembled.nurses else None
    issues = None
    if refusal is None and assembled.nurses:
        try:
            issues = [in_dates(issue, month) for issue in solver_client.precheck(assembled.input)]
        except SolverRefused as e:
            refusal = str(e)
        except SolverUnreachable:
            pass
    return SolvePreview(
        month=month.strftime("%Y-%m"),
        summary=Summary(nurses=len(assembled.nurses), leave_days=assembled.leave_days,
                        outside_days=sum(map(len, assembled.outside_days.values())), pins=assembled.pins),
        warnings=Warnings(hospital_rules_need_review=HospitalSettings.load().rules_need_review,
                          unit_rules_need_review=unit.rules_need_review,
                          unreviewed_scores=assembled.unreviewed_scores, left_out=_names(assembled.left_out)),
        precheck=issues, rules_refusal=refusal, refusal=stopped_by, time_limit_default=default, time_limit_cap=cap)


class StartSolveBody(StrictSchema):
    month: MonthText
    time_limit_seconds: int = Field(ge=1, description="At most the System Admin's cap.")


class SolveProgress(Schema):
    id: UUID
    month: str
    state: Literal[SolveState.QUEUED, SolveState.RUNNING, SolveState.SUCCEEDED, SolveState.FAILED, SolveState.CANCELLED]
    queue_ahead: int | None = Field(description="Solves of any unit that go first. Null once this one has started.")
    time_limit_seconds: int
    stop_requested: bool
    elapsed_seconds: float
    best_cost: int | None
    improvements: int
    attempts: int
    requested_at: dt.datetime
    finished_at: dt.datetime | None
    failure: Literal[SolveFailure.SOLVER, SolveFailure.REFUSED] | None = Field(
        description="`refused` is a matter of the rules, to be shown as such and not as a failed solve.")
    error: str
    found_roster: bool = Field(description="Whether this solve ended with a roster it could keep, which became the draft "
                                            "then. A later solve or a restore may have replaced it since.")
    message: str = Field(description="Why the solver found no roster, in its words.")
    precheck: list[str] = Field(description="What the solver's own precheck said, once it has ended.")


def progress_of(solve: Solve) -> SolveProgress:
    result = solve.result or {}
    return SolveProgress(id=solve.pk, month=solve.month.strftime("%Y-%m"), state=solve.state, queue_ahead=solve.queue_ahead,
                         time_limit_seconds=solve.time_limit_seconds, stop_requested=solve.stop_requested,
                         elapsed_seconds=solve.elapsed_seconds, best_cost=solve.best_cost, improvements=solve.improvements,
                         attempts=solve.attempts, requested_at=timezone.localtime(solve.requested_at),
                         finished_at=timezone.localtime(solve.finished_at) if solve.finished_at else None,
                         failure=solve.failure or None, error=in_dates(solve.error, solve.month),
                         found_roster=has_a_roster_to_keep(result),
                         message=in_dates(result.get("message") or "", solve.month), precheck=precheck_of(result, solve.month))


@router.post("/{unit_id}/solves", response={201: SolveProgress}, auth=manager, operation_id="startSolve")
def start_solve(request: HttpRequest, unit_id: UUID, body: StartSolveBody) -> Status:
    """The solve input is stored as it stands now, whatever changes while the solve waits for its turn."""
    month = dt.date.fromisoformat(f"{body.month}-01")
    with transaction.atomic():
        HospitalSettings.load(for_update=True)  # A rename would otherwise pass between reading the rules and the shifts.
        unit = unit_in_scope(request.user, unit_id, for_update=True)
        _, cap = _time_limits(unit)
        if body.time_limit_seconds > cap:
            refuse((("time_limit_seconds",), f"The System Admin's cap is {cap} seconds."))
        assembled = assemble(unit, month, time_limit=body.time_limit_seconds)
        stopped_by = _what_stops_it(unit, month, assembled)
        if stopped_by:
            raise HttpError(409, stopped_by)
        refusal = solver_refusal(assembled.input)
        if refusal:
            raise HttpError(409, f"The solver refuses the rules as they stand, so review the unit rules: {refusal}")
        solve = Solve.objects.create(unit=unit, month=month, requested_by=request.user,
                                     time_limit_seconds=body.time_limit_seconds, input=assembled.input,
                                     outside_days=assembled.outside_days)
        solve.job_id = enqueue(run_solve, solve_id=str(solve.pk))
        solve.save(update_fields=["job_id"])
        record("solve.started", actor=request.user, target=solve.audit_target, request=request,
               after={"time_limit_seconds": body.time_limit_seconds})
    return Status(201, progress_of(solve))


def _solve_of(request: HttpRequest, unit_id: UUID, solve_id: UUID) -> tuple[Unit, Solve]:
    unit = unit_in_scope(request.user, unit_id)
    return unit, get_object_or_404(Solve, pk=solve_id, unit=unit)


@router.get("/{unit_id}/solves/{solve_id}", response=SolveProgress, auth=manager, operation_id="getSolveProgress")
def solveprogress_of(request: HttpRequest, unit_id: UUID, solve_id: UUID) -> SolveProgress:
    """A timer calls this, so it does not count as the manager being there, whatever it answers: a test holds it."""
    not_activity(request)
    _, solve = _solve_of(request, unit_id, solve_id)
    return progress_of(solve)


@router.post("/{unit_id}/solves/{solve_id}/stop", response=SolveProgress, auth=manager, operation_id="stopSolve")
def stop_solve(request: HttpRequest, unit_id: UUID, solve_id: UUID) -> SolveProgress:
    """A queued solve ends here. A running one is the worker's to stop, which keeps the best roster found. Asking again, or
    after the end, changes nothing."""
    unit = unit_in_scope(request.user, unit_id)
    with transaction.atomic():
        solve = get_object_or_404(Solve.objects.select_for_update(), pk=solve_id, unit=unit)
        if solve.state in ACTIVE_STATES and not solve.stop_requested:
            solve.stop_requested = True
            if solve.state == SolveState.QUEUED:
                solve.state = SolveState.CANCELLED
                solve.finished_at = timezone.now()
            solve.save(update_fields=["stop_requested", "state", "finished_at"])
            record("solve.stopped", actor=request.user, target=solve.audit_target, request=request)
    return progress_of(solve)
