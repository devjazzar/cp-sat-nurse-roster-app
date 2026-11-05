"""What a solve and the shift catalogue do to rosters."""
from __future__ import annotations

from hospital.models import ShiftRename
from rosters.models import Roster
from solves.models import Solve


def current_code(code: str) -> str:
    """No other shift can ever take a code a shift held, so an old code means one shift for good."""
    rename = ShiftRename.objects.select_related("shift").filter(old_code=code).first()
    return rename.shift.code if rename else code


def replace_grid(solve: Solve, grid: dict[str, dict[str, str]]) -> Roster:
    """The draft of the solve's month, created or with its grid replaced. A shift renamed while the solve ran is carried
    here, so hold the catalogue's lock (`HospitalSettings.load(for_update=True)`) so that a rename cannot slip past."""
    codes = {code: current_code(code) for row in grid.values() for code in row.values() if code}
    live = {nurse: {day: codes.get(code, code) for day, code in row.items()} for nurse, row in grid.items()}
    roster, _ = Roster.objects.update_or_create(unit=solve.unit, month=solve.month, defaults={"grid": live, "solve": solve})
    return roster


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
