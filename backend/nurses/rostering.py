"""A nurse as a solve input carries them."""
from __future__ import annotations

import datetime as dt

from nurses.models import Leave, NurseProfile, Placement


def nurse_block(nurse: NurseProfile, placement: Placement) -> dict:
    """One entry of a solve input's `nurses`, in the placement's unit, with the opening values and no history. `solves.input`
    starts from it, adding leave and pins, and replaces those values and the history with her carry-over (`closes.chain`)."""
    return {"id": nurse.user.username, "gender": nurse.gender, "team_leader": nurse.team_leader, "score": nurse.score,
            "ramadan_reduced": nurse.ramadan_reduced, "breastfeeding": nurse.breastfeeding,
            "ytd_overtime": nurse.ytd_overtime, "hours_balance": nurse.hours_balance,
            "night_balance": nurse.night_balance, "friday_balance": nurse.friday_balance,
            "last_shift_kind": None, "rest_owed": 0, "allowed_shifts": placement.allowed_shifts}


def leave_dates(nurse: NurseProfile, month: dt.date) -> list[str]:
    """A nurse's `leave` in a month's solve input: ISO dates in order, each once, and no type, because a solve input is
    kept and read by people who may not see one. Ticket 11 adds the days outside the start and end dates, which are
    credited alike, as a set: a date recorded here can be one of those, and the solver refuses a day listed twice."""
    return [day.isoformat() for day in Leave.objects.current().in_month(month).filter(nurse=nurse).values_list("date", flat=True)]
