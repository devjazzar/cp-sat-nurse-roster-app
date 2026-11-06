"""A nurse's own hours in the version in force, worked out on the month as it stands with the solver's own arithmetic
(`nurse_roster.problem.Problem`), the same as a result's `nurses` block. A stored result's block is not used: it is the solve's
grid, not the version's, which hand edits and later versions change, and it holds every colleague's leave."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from nurse_roster.request import load_request

from hospital.models import Shift
from rosters.drafts import current_code
from solves.input import assemble
from units.models import Unit


@dataclass(frozen=True)
class OwnHours:
    worked: int
    leave_credit: int
    owed: int | None
    overtime: int
    carried: int | None
    shifts: dict[str, int]


def own_hours(unit: Unit, month: dt.date, hospital_id: str, row: dict[str, str]) -> OwnHours | None:
    """None when the month as it stands no longer has this nurse in it, or the solver's code cannot read it. `owed` and
    `carried` are None with the hospital's hours rule off, which counts nothing owed.

    Leave wins over a shift, as everywhere: a shift the version still holds on a day of leave recorded since (ticket 16 has the
    new version that takes it off) is not counted as worked, since the day already counts through the leave credit."""
    try:
        problem = load_request(assemble(unit, month).input).problem
    except ValueError:
        return None
    nurse = next((nurse for nurse in problem.nurses if nurse.id == hospital_id), None)
    if nurse is None:
        return None
    credited = {month.replace(day=day + 1).isoformat() for day in nurse.unavailable}
    codes = [code for day, code in sorted(row.items()) if code and day not in credited]
    hours = dict(Shift.objects.filter(code__in=codes).values_list("code", "hours"))
    if any(code not in hours for code in codes):
        return None
    worked = sum(hours[code] for code in codes)
    counted = problem.general.hours_rule_enabled
    owed = problem.required_hours(nurse)
    return OwnHours(worked=worked, leave_credit=problem.leave_credit(nurse), owed=owed if counted else None,
                    overtime=max(0, worked - owed) if counted else 0,
                    carried=problem.carry_over(nurse, worked) if counted else None,
                    shifts={code: codes.count(code) for code in dict.fromkeys(codes)})


def closed_hours(close, hospital_id: str) -> OwnHours | None:
    """A closed month's figures for one nurse, as its close stored them (`closes.models.MonthClose`): fact, whatever has been
    corrected since. Its shifts under their codes now. None when the close did not have them in the month."""
    row = close.result["nurses"].get(hospital_id)
    if row is None:
        return None
    counted = close.input["general"]["hours_rule_enabled"]
    shifts: dict[str, int] = {}
    for code, count in row["shifts"].items():
        if count:
            now = current_code(code)
            shifts[now] = shifts.get(now, 0) + count
    return OwnHours(worked=row["hours_worked"], leave_credit=row["leave_credit"], owed=row["required"] if counted else None,
                    overtime=row["overtime"], carried=row["carry_over"]["hours_balance"] if counted else None, shifts=shifts)
