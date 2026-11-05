"""A nurse's own hours in the version in force, worked out on the month as it stands with the solver's own arithmetic
(`nurse_roster.problem.Problem`), the same as a result's `nurses` block. A stored result's block is not used: it is the solve's
grid, not the version's, which hand edits and later versions change, and it holds every colleague's leave."""
from __future__ import annotations

from dataclasses import dataclass

from nurse_roster.request import load_request

from solves.input import assemble
from units.models import Unit

import datetime as dt


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
    `carried` are None with the hospital's hours rule off, which counts nothing owed."""
    try:
        problem = load_request(assemble(unit, month).input).problem
    except ValueError:
        return None
    nurse = next((nurse for nurse in problem.nurses if nurse.id == hospital_id), None)
    hours = problem.general.shift_hours
    codes = [code for code in row.values() if code]
    if nurse is None or any(code not in hours for code in codes):
        return None
    worked = sum(hours[code] for code in codes)
    counted = problem.general.hours_rule_enabled
    owed = problem.required_hours(nurse)
    return OwnHours(worked=worked, leave_credit=problem.leave_credit(nurse), owed=owed if counted else None,
                    overtime=max(0, worked - owed) if counted else 0,
                    carried=problem.carry_over(nurse, worked) if counted else None,
                    shifts={code: codes.count(code) for code in dict.fromkeys(codes)})
