"""What a solve and the shift catalogue do to rosters."""
from __future__ import annotations

from typing import Iterable

from django.utils import timezone

from hospital.models import Shift, ShiftRename
from nurses import membership
from rosters.models import Roster
from solves.models import ACTIVE_STATES, Solve
from solves.result import has_a_roster_to_keep


def current_code(code: str) -> str:
    """No other shift can ever take a code a shift held, so an old code means one shift for good."""
    rename = ShiftRename.objects.select_related("shift").filter(old_code=code).first()
    return rename.shift.code if rename else code


def current_codes(codes: Iterable[str]) -> dict[str, str]:
    return {code: current_code(code) for code in set(codes)}


def in_current_codes(grid: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    codes = current_codes(code for row in grid.values() for code in row.values() if code)
    return {nurse: {day: codes.get(code, code) for day, code in row.items()} for nurse, row in grid.items()}


def replace_grid(solve: Solve, grid: dict[str, dict[str, str]], *, restoring: bool = False) -> Roster:
    """The draft of the solve's month, created or with its grid replaced. A shift renamed while the solve ran is carried
    here, so hold the catalogue's lock (`HospitalSettings.load(for_update=True)`) so that a rename cannot slip past."""
    roster, _ = Roster.objects.update_or_create(unit=solve.unit, month=solve.month, defaults={
        "grid": in_current_codes(grid), "solve": solve, "restored_at": timezone.now() if restoring else None})
    return roster


def why_not_restore(solve: Solve) -> str | None:
    """Why this solve's result cannot become its month's draft now, or None. Hold the catalogue's lock and the unit's when it
    decides a restore. Its cost and each nurse's hours were worked out on the shifts as they stood then, so a shift whose
    hours moved or that has since been retired stops it: a draft could not hold those by any other way
    (`hospital.catalogue_api`). A rename does not: it is the same shift."""
    if solve.state in ACTIVE_STATES:
        return "This solve has not ended yet."
    if not has_a_roster_to_keep(solve.result):
        return "This solve left no roster to restore."
    if solve.month < membership.this_month():
        return "This month is over, so its draft cannot change."
    if Solve.objects.filter(unit=solve.unit, month=solve.month, state__in=ACTIVE_STATES).exists():
        return "A solve of this month is queued or running, and would replace this when it ends. Stop it or wait for it first."
    if Roster.objects.filter(unit=solve.unit, month=solve.month, solve=solve).exists():
        return "This result is the draft already."
    return _shift_since(solve)


def _shift_since(solve: Solve) -> str | None:
    hours_then = solve.input["general"]["shift_hours"]
    used = {code for row in solve.result["roster"].values() for code in row.values() if code}
    for code in sorted(used):
        shift = Shift.objects.filter(code=current_code(code)).first()
        if shift is None or not shift.active:
            return f"{code} has been retired since this solve, so this roster can no longer be worked. Solve the month again."
        if shift.hours != hours_then[code]:
            return (f"{shift.code} was {hours_then[code]} hours at this solve and is {shift.hours} now, so this roster's cost "
                    "and hours no longer hold. Solve the month again.")
    return None


def carry_rename_through_grids(old_code: str, new_code: str) -> None:
    """Call it under the catalogue's lock. A stored input and result stay what they were."""
    rosters = [roster for roster in Roster.objects.select_for_update() if _uses(roster, old_code)]
    for roster in rosters:
        roster.grid = {nurse: {day: new_code if code == old_code else code for day, code in row.items()}
                       for nurse, row in roster.grid.items()}
    Roster.objects.bulk_update(rosters, ["grid"])


def _uses(roster: Roster, code: str) -> bool:
    return any(code in row.values() for row in roster.grid.values())


def using_shift(code: str) -> list[Roster]:
    """The rosters of open months whose grid holds this shift, oldest first. Until month close exists (ticket 21) every month
    is open, and it narrows this."""
    return [roster for roster in Roster.objects.select_related("unit").order_by("month", "unit__name") if _uses(roster, code)]
