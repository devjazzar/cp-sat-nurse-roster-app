"""What the catalogue starts with. The hours are the reviewed set the solver was shaped on; the forbidden
successions in `hospital.rules.DEFAULT_RULES` name these codes. Names, times and colours are ours for the
CNO to correct, and hospital/tests/test_shifts.py holds the codes and hours to the solver's."""
from __future__ import annotations

from datetime import date, time

from django.db import transaction
from nurse_roster.calendar import parse_month

from hospital.models import FixedRamadanMonth, LeaveType, Shift

DEFAULT_SHIFTS = [
    ("D", "Day", 12, time(7), time(19), "#0284c7"),
    ("N", "Night", 12, time(19), time(7), "#4338ca"),
    ("A", "Morning", 8, time(7), time(15), "#16a34a"),
    ("B", "Evening", 8, time(15), time(23), "#d97706"),
    ("C", "Late night", 8, time(23), time(7), "#7c3aed"),
]

# Every type counts the same for a nurse's hours, so nothing here may suggest otherwise, such as "Unpaid".
DEFAULT_LEAVE_TYPES = ["Annual", "Compassionate", "Educational", "Emergency", "Maternity", "Sick"]


def seed_catalogue() -> None:
    """Only into an empty table: nothing here is ever deleted, so empty means never seeded, and a shift
    the CNO has renamed must not come back under its old name."""
    with transaction.atomic():
        if not Shift.objects.exists():
            for code, display_name, hours, start_time, end_time, colour in DEFAULT_SHIFTS:
                Shift.objects.create(code=code, display_name=display_name, hours=hours, start_time=start_time,
                                     end_time=end_time, colour=colour)
        if not LeaveType.objects.exists():
            LeaveType.objects.bulk_create(LeaveType(name=name) for name in DEFAULT_LEAVE_TYPES)


def derived_ramadan_dates(month: str) -> list[date]:
    """The solver's own derivation, so a page and a solve cannot disagree. Only its calendar module is
    used here: the solver container is still the only place that solves."""
    info = parse_month(month)
    return [info.date(day) for day in info.ramadan_days]


def ramadan_dates(month: str) -> list[date]:
    """The Ramadan days of a month ("YYYY-MM"): the CNO's when fixed, else the calendar's."""
    fixed = FixedRamadanMonth.objects.filter(month=month).first()
    return fixed.dates if fixed else derived_ramadan_dates(month)
