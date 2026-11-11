"""What the catalogue starts with. The hours are the reviewed set the solver was shaped on; the forbidden
successions in `hospital.rules.DEFAULT_RULES` name these codes. Names, times and colours are ours for the
CNO to correct, and hospital/tests/test_shifts.py holds the codes and hours to the solver's."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time, timedelta

from django.db import transaction
from hijridate import Gregorian
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


@dataclass(frozen=True, slots=True)
class CalendarRamadan:
    hijri_year: int
    days: list[date]  # The calendar's, in order: one unbroken run.

    @property
    def months(self) -> list[str]:
        return sorted({day.strftime("%Y-%m") for day in self.days})


def month_label(year: int, number: int) -> str:
    """"YYYY-MM" for a month counted from January of `year`; `number` may run past 1..12 either way."""
    year, index = divmod(year * 12 + number - 1, 12)
    return f"{year:04d}-{index + 1:02d}"


def calendar_ramadans(year: int) -> list[CalendarRamadan]:
    """Every Ramadan with a day in the Gregorian `year`, in date order, by the calendar. The days are the solver's month
    derivation, read from December before to January after: a Ramadan is at most 30 days, so one with a day in `year`
    lies within them. The Hijri year only names it, so it alone is converted here."""
    days = [day for number in range(0, 14) for day in derived_ramadan_dates(month_label(year, number))]
    runs: list[list[date]] = []
    for day in days:
        if runs and day == runs[-1][-1] + timedelta(days=1):
            runs[-1].append(day)
        else:
            runs.append([day])
    return [CalendarRamadan(Gregorian(run[0].year, run[0].month, run[0].day).to_hijri().year, run)
            for run in runs if any(day.year == year for day in run)]
