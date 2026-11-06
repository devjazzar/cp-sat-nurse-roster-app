"""What solves have been run and what each answered. A unit's history and its results are its manager's, and the CNO's and the
Deputy CNO's for a month whose roster is submitted or approved: a draft is the unit management's alone. The System Admin's history across units is `hospital_router`, and may say nothing a nurse could be
read from, so its row is a list of named fields and never takes free text: `Solve.error`, a result's `message` and `precheck`
and every explanation can name a nurse and a date, as they come from the solver's words."""
from __future__ import annotations

import datetime as dt
from typing import Literal
from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Field, Query, Router, Schema
from ninja.errors import HttpError

from accounts.authz import SignedIn
from accounts.models import Role, User
from audit.log import record
from hospital.models import HospitalSettings
from nurses.api import MonthText
from rosters import drafts
from rosters.grids import GridView, by_name, full_names, grid_view
from rosters.models import Roster, RosterVersion, VersionOrigin
from rosters.versions import differences
from rosters.review import SEEN_BY_APPROVERS
from solves.api import chosen_month, manager
from solver_service.grid import validate_grid
from solves.models import ReplanOutcomeWord, Solve, SolveFailureWord, SolveState
from solves.result import LARGEST, cost_of, explanation, has_a_roster_to_keep, in_dates, precheck_of, statistics_of
from units.models import Unit
from units.scope import HOSPITAL_WIDE, unit_in_scope

router = Router(tags=["solve history"])
hospital_router = Router(tags=["solve history"], auth=SignedIn(Role.SYSTEM_ADMIN))
reader = SignedIn(Role.UNIT_MANAGER, Role.CNO, Role.DEPUTY_CNO)
ONLY_THE_MANAGER_RESTORES = "Only the unit's manager can restore a result."


class PageFilter(Schema):
    older_than: UUID | None = Field(None, description="The `older_than` of the page before.")
    limit: int = Field(50, ge=1, le=200)


class UnitHistoryFilter(PageFilter):
    month: MonthText | None = Field(None, description="YYYY-MM. Every month when left out.")


class SolveRow(Schema):
    """Nothing here may come from the solver's or the worker's words: the System Admin reads every field."""

    id: UUID
    month: str
    state: Literal[SolveState.QUEUED, SolveState.RUNNING, SolveState.SUCCEEDED, SolveState.FAILED, SolveState.CANCELLED]
    failure: SolveFailureWord | None
    requested_by: str
    requested_at: dt.datetime
    finished_at: dt.datetime | None
    elapsed_seconds: float
    time_limit_seconds: int
    attempts: int
    cost: int | None
    found_roster: bool = Field(description="Whether it ended with a roster it could keep.")


class UnitSolveRow(SolveRow):
    """The System Admin's row never has these: a re-plan's date is about a roster."""
    in_draft: bool = Field(description="Whether its month's draft came from this solve. The draft may have been edited by hand "
                                       "since, and then holds more than this result. After a re-plan put its roster in force, "
                                       "that roster's grid is the re-plan's.")
    replan_from: dt.date | None = Field(description="Set on a re-plan: the first date it planned again.")
    replan_outcome: ReplanOutcomeWord | None = Field(
        description="What a re-plan's end did to the roster in force. Null for a solve, before the end, and for a re-plan that "
                    "kept no roster.")


class HospitalSolveRow(SolveRow):
    unit: str


class UnitHistory(Schema):
    solves: list[UnitSolveRow]
    older_than: UUID | None


class HospitalHistory(Schema):
    solves: list[HospitalSolveRow]
    older_than: UUID | None


def _row_fields(solve: Solve) -> dict:
    return {"id": solve.pk, "month": solve.month.strftime("%Y-%m"), "state": solve.state, "failure": solve.failure or None,
            "requested_by": solve.requested_by.full_name or solve.requested_by.username,
            "requested_at": timezone.localtime(solve.requested_at),
            "finished_at": timezone.localtime(solve.finished_at) if solve.finished_at else None,
            "elapsed_seconds": solve.elapsed_seconds, "time_limit_seconds": solve.time_limit_seconds,
            "attempts": solve.attempts, "cost": cost_of(solve.result), "found_roster": has_a_roster_to_keep(solve.result)}


def _unit_row(solve: Solve, in_draft: set[UUID]) -> UnitSolveRow:
    return UnitSolveRow(**_row_fields(solve), in_draft=solve.pk in in_draft, replan_from=solve.replan_from,
                        replan_outcome=solve.replan_outcome or None)


def _page(solves: QuerySet[Solve], filters: PageFilter) -> tuple[list[Solve], UUID | None]:
    """A solve's id is UUIDv7, so its order is the order they were asked for, and nothing else has to break a tie."""
    found = solves.select_related("requested_by", "unit").defer("input").order_by("-id")
    if filters.older_than:
        found = found.filter(id__lt=filters.older_than)
    page = list(found[:filters.limit + 1])
    has_more = len(page) > filters.limit
    page = page[:filters.limit]
    return page, page[-1].pk if has_more else None


@hospital_router.get("", response=HospitalHistory, operation_id="listHospitalSolveHistory")
def hospital_history(request: HttpRequest, filters: Query[PageFilter]) -> HospitalHistory:
    page, older_than = _page(Solve.objects.all(), filters)
    return HospitalHistory(solves=[HospitalSolveRow(**_row_fields(solve), unit=solve.unit.name) for solve in page],
                           older_than=older_than)


def _solves_in_drafts(unit: Unit) -> set[UUID]:
    return set(Roster.objects.filter(unit=unit).values_list("solve_id", flat=True))


def _solves_seen_by(user: User, unit: Unit) -> QuerySet[Solve]:
    solves = Solve.objects.filter(unit=unit)
    if user.role in HOSPITAL_WIDE:
        return solves.filter(month__in=Roster.objects.filter(unit=unit, state__in=SEEN_BY_APPROVERS).values("month"))
    return solves


@router.get("/{unit_id}/solve-history", response=UnitHistory, auth=reader, operation_id="listUnitSolveHistory")
def unit_history(request: HttpRequest, unit_id: UUID, filters: Query[UnitHistoryFilter]) -> UnitHistory:
    """For the CNO and the Deputy CNO, only the months whose roster is submitted or approved."""
    unit = unit_in_scope(request.user, unit_id)
    solves = _solves_seen_by(request.user, unit)
    if filters.month:
        solves = solves.filter(month=chosen_month(filters.month))
    page, older_than = _page(solves, filters)
    in_draft = _solves_in_drafts(unit)
    return UnitHistory(solves=[_unit_row(solve, in_draft) for solve in page],
                       older_than=older_than)


class RuleMatch(Schema):
    hospital_id: str | None = Field(description="Null when the rule is about the unit as a whole.")
    full_name: str
    date: dt.date | None = Field(description="Null when it is about the month as a whole.")
    amount: int
    text: str


class RuleResult(Schema):
    rule: str = Field(description="The soft rule's name: the same as its weight's.")
    penalty: int
    weight: int | None = Field(description="Null, as are the next three, when the explanation could not be worked out.")
    amount: int | None = Field(description="How much of the rule was broken, in `counted_in`.")
    counted_in: str | None
    largest: list[RuleMatch] = Field(description=f"Its {LARGEST} largest occurrences.")
    others: int = Field(description="How many more occurrences it has.")


class Violation(Schema):
    rule: str
    hospital_id: str | None
    full_name: str
    date: dt.date | None
    text: str


class NurseAccounting(Schema):
    hospital_id: str
    full_name: str
    contract: int
    leave_credit: int
    required: int
    hours_worked: int
    overtime: int
    shortfall: int
    shifts: dict[str, int] = Field(description="How many of each, under the code each shift has now.")
    cost: int


class SolverStatistics(Schema):
    status: str
    stopped_by: str | None
    objective: float | None
    best_bound: float | None
    solve_seconds: float | None
    build_seconds: float | None
    deterministic_time: float | None
    improvements: int
    workers: int | None
    time_limit_seconds: float | None
    variables: int | None
    constraints: int | None
    objective_terms: int | None


class ReplanChange(Schema):
    hospital_id: str
    full_name: str
    date: dt.date
    before: str = Field(description="The roster in force's shift when the re-plan started, under today's code. Empty for a day "
                                    "not worked.")
    after: str = Field(description="The re-plan's.")


class ReplanRule(Schema):
    rule: str = Field(description="The soft rule's name: the same as its weight's.")
    before: int = Field(description="What it cost in the roster in force, on the re-plan's input.")
    after: int = Field(description="What it costs in the re-plan's roster.")


class ReplanComparison(Schema):
    """The re-plan against the roster in force it started from. Both are costed on the re-plan's own input, so they compare;
    the roster in force is its own baseline, so its `change` is always 0, and the re-plan's is the price of the cells it
    changed."""
    replan_from: dt.date
    recorded_cells_differ: int | None = Field(description="Days before the date whose facts differ from the roster in force, as "
                                                          "the solver counted them. Null when it found no roster.")
    based_on: int = Field(description="The version in force when it started.")
    version: int | None = Field(description="The version it made. Null when it made none.")
    outcome: ReplanOutcomeWord | None
    changes: list[ReplanChange] = Field(description="Each cell its roster changes, by nurse then date. Empty with no roster.")
    cost_before: int | None = Field(description="Null when the solver's code could not cost the roster in force.")
    cost_after: int | None
    rules: list[ReplanRule] = Field(description="Each soft rule that costs something in either, the largest difference first. "
                                                "Empty when `cost_before` is null.")


class SolveResult(Schema):
    solve: UnitSolveRow
    error: str = Field(description="Why the last attempt failed, also when a retry then worked.")
    message: str = Field(description="Why the solver found no roster or it could not be kept, in its words.")
    precheck: list[str]
    violations: list[Violation] = Field(description="Hard rules its roster breaks. Such a roster does not become a draft.")
    elapsed_violations: list[Violation] = Field(description="Recorded facts that broke hard rules: days already over, which "
                                                             "no solve could change.")
    unit_cost: int | None = Field(description="What it costs apart from any one nurse.")
    rules: list[RuleResult] = Field(description="Each soft rule that costs something, the costliest first.")
    explained: bool = Field(description="False when the solver's code could not explain the stored roster.")
    nurses: list[NurseAccounting]
    statistics: SolverStatistics | None
    grid: GridView | None = Field(description="The roster it answered, under the codes in use now. Null when it found none.")
    restore_refusal: str | None = Field(description="Why this result cannot be restored as the draft now.")
    replan: ReplanComparison | None = Field(description="Set on a re-plan: its comparison with the roster in force it started "
                                                        "from. Its elapsed violations are `elapsed_violations`.")


def _with_names(rows: list[dict], names: dict[str, str], month: dt.date) -> list[Violation]:
    return [Violation(rule=row["rule"], hospital_id=row["nurse"], full_name=names.get(row["nurse"], ""), date=row["date"],
                       text=in_dates(row["text"], month)) for row in rows]


def _rule_results(solve: Solve, explained: dict[str, dict] | None, names: dict[str, str]) -> list[RuleResult]:
    """The result's own penalties, whatever the explanation says, as the result is what was kept."""
    result = solve.result or {}

    def row(rule: str, penalty: int) -> RuleResult:
        found = (explained or {}).get(rule)
        if found is None:
            return RuleResult(rule=rule, penalty=penalty, weight=None, amount=None, counted_in=None, largest=[], others=0)
        largest = [RuleMatch(hospital_id=match["nurse"], full_name=names.get(match["nurse"], ""), date=match["date"],
                             amount=match["amount"], text=in_dates(match["text"], solve.month))
                   for match in found["matches"][:LARGEST]]
        return RuleResult(rule=rule, penalty=penalty, weight=found["weight"], amount=found["raw"], counted_in=found["unit"],
                          largest=largest, others=max(0, len(found["matches"]) - LARGEST))

    costly = [(rule, penalty) for rule, penalty in (result.get("penalties") or {}).items() if penalty]
    return [row(rule, penalty) for rule, penalty in sorted(costly, key=lambda item: (-item[1], item[0]))]


def _accounting(row: dict, hospital_id: str, name: str) -> NurseAccounting:
    shifts = row.get("shifts") or {}
    codes = drafts.current_codes(shifts)
    return NurseAccounting(hospital_id=hospital_id, full_name=name, contract=row["contract"], leave_credit=row["leave_credit"],
                           required=row["required"], hours_worked=row["hours_worked"], overtime=row["overtime"],
                           shortfall=row["shortfall"], shifts={codes[code]: count for code, count in shifts.items()},
                           cost=row["cost"])


def _replan_of(solve: Solve) -> ReplanComparison | None:
    if not solve.replan_from:
        return None
    result = solve.result or {}
    in_force = solve.input["published"]  # The roster in force when it started, in the solver's word for it.
    roster = result.get("roster")
    changes = differences(in_force, roster) if roster else []
    names = full_names(change.hospital_id for change in changes)
    try:
        before = validate_grid(solve.input, in_force)
    except ValueError:
        before = None
    rules = []
    if before is not None:
        after = result.get("penalties") or {}
        found = sorted(set(before["penalties"]) | set(after))
        rules = [ReplanRule(rule=rule, before=before["penalties"].get(rule, 0), after=after.get(rule, 0)) for rule in found
                 if before["penalties"].get(rule, 0) or after.get(rule, 0)]
        rules.sort(key=lambda row: -abs(row.after - row.before))
    version = RosterVersion.objects.filter(solve=solve, origin=VersionOrigin.REPLAN).first()
    return ReplanComparison(
        replan_from=solve.replan_from, recorded_cells_differ=(result.get("replan") or {}).get("recorded_cells_differ"),
        based_on=solve.replan_of, version=version.number if version else None, outcome=solve.replan_outcome or None,
        changes=[ReplanChange(hospital_id=change.hospital_id, full_name=names.get(change.hospital_id, ""), date=change.date,
                              before=change.before, after=change.after) for change in changes],
        cost_before=before["cost"] if before else None, cost_after=cost_of(result), rules=rules)


def _result_of(solve: Solve, unit: Unit, user: User) -> SolveResult:
    result = solve.result or {}
    accounting = result.get("nurses") or {}
    broken = (result.get("violations") or []) + (result.get("elapsed_violations") or [])
    roster = result.get("roster")
    named = {*accounting, *(roster or ()), *(row["nurse"] for row in broken if row["nurse"])}
    explained = explanation(solve.input, result)
    named |= {match["nurse"] for rule in (explained or {}).values() for match in rule["matches"][:LARGEST] if match["nurse"]}
    names = full_names(named)
    return SolveResult(
        solve=_unit_row(solve, _solves_in_drafts(unit)),
        error=in_dates(solve.error, solve.month), message=in_dates(result.get("message") or "", solve.month),
        precheck=precheck_of(result, solve.month),
        violations=_with_names(result.get("violations") or [], names, solve.month),
        elapsed_violations=_with_names(result.get("elapsed_violations") or [], names, solve.month),
        unit_cost=result.get("department_cost"), rules=_rule_results(solve, explained, names),
        explained=explained is not None,
        nurses=[_accounting(accounting[hospital_id], hospital_id, names.get(hospital_id, ""))
                for hospital_id in by_name(accounting, names)],
        statistics=SolverStatistics(**statistics_of(result)) if result else None,
        grid=grid_view(drafts.in_current_codes(roster), solve) if roster else None,
        restore_refusal=ONLY_THE_MANAGER_RESTORES if user.role in HOSPITAL_WIDE else drafts.why_not_restore(solve),
        replan=_replan_of(solve))


@router.get("/{unit_id}/solve-history/{solve_id}", response=SolveResult, auth=reader, operation_id="getSolveResult")
def solve_result(request: HttpRequest, unit_id: UUID, solve_id: UUID) -> SolveResult:
    """A solve of a month the CNO or the Deputy CNO may not see is the same 404 as one that does not exist."""
    unit = unit_in_scope(request.user, unit_id)
    solves = _solves_seen_by(request.user, unit).select_related("requested_by", "unit")
    return _result_of(get_object_or_404(solves, pk=solve_id), unit, request.user)


@router.post("/{unit_id}/solve-history/{solve_id}/restore", response=SolveResult, auth=manager, operation_id="restoreSolveResult")
def restore_result(request: HttpRequest, unit_id: UUID, solve_id: UUID) -> SolveResult:
    """Under the locks a solve's start and end take, so none of them passes between deciding and writing. The audit entry says
    which solve and its cost, as `roster.draft_replaced` does, and nothing of a nurse."""
    with transaction.atomic():
        HospitalSettings.load(for_update=True)
        unit = unit_in_scope(request.user, unit_id, for_update=True)
        solve = get_object_or_404(Solve.objects.select_related("requested_by", "unit"), pk=solve_id, unit=unit)
        refusal = drafts.why_not_restore(solve)
        if refusal:
            raise HttpError(409, refusal)
        drafts.replace_grid(solve, solve.result["roster"], restoring=True)
        record("roster.draft_restored", actor=request.user, target=solve.audit_target, request=request,
               after={"solve": str(solve.pk), "cost": solve.result["cost"]})
    return _result_of(solve, unit, request.user)
