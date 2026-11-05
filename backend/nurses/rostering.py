"""A nurse as a solve input carries them."""
from __future__ import annotations

from nurses.models import NurseProfile, Placement


def nurse_block(nurse: NurseProfile, placement: Placement) -> dict:
    """One entry of a solve input's `nurses`, in the placement's unit: everything this app holds today. Ticket 11 starts
    from it, adding leave and pins, and replacing the opening values and empty history with the carry-over once one exists."""
    return {"id": nurse.user.username, "gender": nurse.gender, "team_leader": nurse.team_leader, "score": nurse.score,
            "ramadan_reduced": nurse.ramadan_reduced, "breastfeeding": nurse.breastfeeding,
            "ytd_overtime": nurse.ytd_overtime, "hours_balance": nurse.hours_balance,
            "night_balance": nurse.night_balance, "friday_balance": nurse.friday_balance,
            "last_shift_kind": None, "rest_owed": 0, "allowed_shifts": placement.allowed_shifts}
