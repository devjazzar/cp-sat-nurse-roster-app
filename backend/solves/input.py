"""The solve input: everything the solver needs for one unit and one month, built from the database, and what the unit's
manager needs to know about that month before starting."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from nurse_roster.request import load_request

from hospital.catalogue import ramadan_dates
from hospital.models import HospitalSettings, PublicHoliday, Shift
from hospital.rules import general_block
from nurses import membership
from nurses.models import NurseProfile
from nurses.rostering import leave_dates, nurse_block
from units.models import Unit
from units.rules import unit_block


@dataclass
class Assembled:
    input: dict
    left_out: list[NurseProfile] = field(default_factory=list)
    to_check: list[NurseProfile] = field(default_factory=list)
    unreviewed_scores: int = 0
    leave_days: int = 0
    outside_days: dict[str, list[str]] = field(default_factory=dict)

    @property
    def nurses(self) -> list[dict]:
        return self.input["nurses"]


def _no_longer_serving(nurse: NurseProfile) -> bool:
    """An account deactivated while the profile runs on, which only happens to a manager: a staff nurse's account ends with
    their end date (`nurses.tasks.close_ended_nurses`). A deactivated nurse whose end date has come worked until then, so
    their month still counts. Nobody can say when this one stopped."""
    return not nurse.user.is_active and (nurse.end_date is None or nurse.end_date > membership.today())


def _days_of(month: dt.date) -> list[dt.date]:
    return [month.replace(day=day) for day in range(1, membership.last_day_of(month).day + 1)]


def _credited(nurse: NurseProfile, month: dt.date) -> tuple[list[str], int, list[str]]:
    """Her `leave`, in order and each once, with how many of those are recorded leave and which are outside her dates. A
    date recorded and since left outside them by a correction counts as outside, as the Leave page flags it."""
    outside = {day.isoformat() for day in _days_of(month) if membership.outside_dates(nurse, day)}
    recorded = set(leave_dates(nurse, month))
    return sorted(recorded | outside), len(recorded - outside), sorted(outside)


def assemble(unit: Unit, month: dt.date, *, time_limit: int = 1) -> Assembled:
    """`time_limit` matters only to an input that will be sent. Pins join a nurse's block with ticket 13. Leave wins over one: the solver refuses a shift pinned on a leave date, so
    such a pair, if a row ever holds one, must drop the pin here and not reach the solver as a failed solve."""
    shift_hours = {shift.code: shift.hours for shift in Shift.objects.filter(active=True)}
    label = month.strftime("%Y-%m")
    assembled = Assembled(input={
        "version": 1,
        "month": label,
        "ramadan_days": [day.isoformat() for day in ramadan_dates(label)],
        "public_holidays": [holiday.date.isoformat() for holiday in PublicHoliday.objects.filter(
            date__year=month.year, date__month=month.month)],
        "general": general_block(HospitalSettings.load(), shift_hours=shift_hours),
        "department": unit_block(unit),
        "nurses": [],
        "solver": {"time_limit_seconds": time_limit, "reproducible": False},
    })
    nurses = membership.rostered_in(unit, month).select_related("user").order_by("user__username")
    for nurse in nurses:
        if _no_longer_serving(nurse):
            assembled.left_out.append(nurse)
            continue
        placement = membership.placement_in(nurse, month)
        leave, recorded, outside = _credited(nurse, month)
        assembled.nurses.append(nurse_block(nurse, placement) | {"leave": leave})
        assembled.leave_days += recorded
        if outside:
            assembled.outside_days[nurse.user.username] = outside
        assembled.unreviewed_scores += not nurse.attributes_saved
        if placement.allowed_shifts_to_check:
            assembled.to_check.append(nurse)
    return assembled


def solver_refusal(solve_input: dict) -> str | None:
    """Why the solver would refuse this input, with no call to it: the same loader, in this image. A unit seeded with a gap
    and a one-shift unit after the CNO raised a weight end up here, as "review the unit rules" and not as a failed solve."""
    try:
        load_request(solve_input)
    except ValueError as e:
        return str(e)
    return None


def changes_since(solve_input: dict, unit: Unit, month: dt.date) -> list[dict]:
    """What has changed since this input was stored that the draft was not solved for: a gender, a nurse's credited days, or
    who is in the month. Start and end dates count through their credited days, so a correction that moves nothing in this
    month does not warn. Other attributes are outside what the user asked for here."""
    solved = {row["id"]: row for row in solve_input["nurses"]}
    now = {row["id"]: row for row in assemble(unit, month).nurses}
    changes = []
    for hospital_id in sorted(solved | now):
        before, after = solved.get(hospital_id), now.get(hospital_id)
        if before is None:
            changes.append({"hospital_id": hospital_id, "what": "joined"})
        elif after is None:
            changes.append({"hospital_id": hospital_id, "what": "left"})
        else:
            if before["gender"] != after["gender"]:
                changes.append({"hospital_id": hospital_id, "what": "gender"})
            if before.get("leave", []) != after["leave"]:
                changes.append({"hospital_id": hospital_id, "what": "leave"})
    return changes
