"""Pinned cells: which of a month's count, and what ending one means. A row can fall out of step with the rest of the database
in ways no refusal can stop, since a nurse's dates, leave and placements are others' to change. Whatever it comes to hold, it
is set aside here, in one place, rather than reach the solver as a failed solve, and the manager is told why. Nothing is
rewritten, as with leave a correction leaves outside a nurse's dates: if the dates come back, so does the pin."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Iterable, Literal

from django.utils import timezone

from accounts.models import User
from hospital.models import Shift
from nurses import membership
from nurses.models import Leave, NurseProfile
from rosters.models import PinEnded, PinnedCell
from units.models import Unit

def long_date(day: dt.date) -> str:
    return f"{day.day} {day:%B %Y}"


AsideWhy = Literal["not_in_month", "outside_dates", "leave", "shift_not_worked", "shift_not_allowed"]


class Judge:
    """Why a nurse could not hold a pin on a date in this unit's month, in the same words for a saved pin and a pending one."""

    def __init__(self, unit: Unit, month: dt.date):
        self.unit, self.month = unit, month
        self.nurses = {nurse.pk: nurse for nurse in membership.rostered_in(unit, month).select_related("user")
                       if not membership.no_longer_serving(nurse)}
        self.leave = set(Leave.objects.current().in_month(month).values_list("nurse_id", "date"))
        self.worked = {shift.pk: shift for shift in Shift.objects.filter(active=True, code__in=unit.rules.get("shifts", []))}

    def day_why(self, nurse_id, day: dt.date) -> AsideWhy | None:
        nurse = self.nurses.get(nurse_id)
        if nurse is None:
            return "not_in_month"
        if membership.outside_dates(nurse, day):
            return "outside_dates"
        return "leave" if (nurse_id, day) in self.leave else None

    def shift_why(self, nurse_id, shift: Shift | None) -> AsideWhy | None:
        if shift is None:
            return None
        if shift.pk not in self.worked:
            return "shift_not_worked"
        allowed = membership.placement_in(self.nurses[nurse_id], self.month).allowed_shifts
        return "shift_not_allowed" if allowed is not None and shift.code not in allowed else None

    def why(self, nurse_id, day: dt.date, shift: Shift | None) -> AsideWhy | None:
        return self.day_why(nurse_id, day) or self.shift_why(nurse_id, shift)


@dataclass
class MonthPins:
    # {hospital ID: {date: shift code or ""}}: each nurse's `pinned` in a solve input.
    counted: dict[str, dict[str, str]] = field(default_factory=dict)
    # Each pin of the month, with `aside` set on those that do not count.
    rows: list[PinnedCell] = field(default_factory=list)


def month_pins(unit: Unit, month: dt.date) -> MonthPins:
    judge = Judge(unit, month)
    pins = MonthPins()
    rows = PinnedCell.objects.current().in_month(month).filter(unit=unit).select_related("shift", "nurse__user")
    for pin in rows.order_by("nurse__user__username", "date"):
        pin.aside = judge.why(pin.nurse_id, pin.date, pin.shift)
        pins.rows.append(pin)
        if pin.aside is None:
            pins.counted.setdefault(pin.nurse.user.username, {})[pin.date.isoformat()] = pin.code
    return pins


def on_top(grid: dict[str, dict[str, str]], pins: MonthPins) -> dict[str, dict[str, str]]:
    """A nurse not in this grid joined after it was solved: their pins wait for the next solve."""
    return {nurse: row | {day: code for day, code in pins.counted.get(nurse, {}).items() if day in row}
            for nurse, row in grid.items()}


def end(rows: Iterable[PinnedCell], why: PinEnded, by: User) -> None:
    PinnedCell.objects.filter(pk__in=[row.pk for row in rows]).update(removed_at=timezone.now(), removed_by=by, removed_why=why)


def end_for_leave(nurse: NurseProfile, days: Iterable[dt.date], unit: Unit, by: User) -> list[PinnedCell]:
    """Leave wins over a pin. Any pin on these days ends, but the answer names only this unit's: one a transfer left behind is
    another manager's. Call it under the nurse's lock, as a leave write and a pin's save both hold it."""
    rows = list(PinnedCell.objects.current().filter(nurse=nurse, date__in=list(days)).select_related("shift"))
    end(rows, PinEnded.LEAVE, by)
    return [row for row in rows if row.unit_id == unit.pk]


def _counted_from_now_on(unit: Unit) -> list[PinnedCell]:
    """A month that is over can reach no solve, so nothing done now can leave its pins worse off."""
    months = {day.replace(day=1) for day in PinnedCell.objects.current().filter(unit=unit, date__gte=membership.this_month())
              .values_list("date", flat=True)}
    return [pin for month in sorted(months) for pin in month_pins(unit, month).rows if pin.aside is None]


def words_for(pins: Iterable[PinnedCell]) -> str:
    return "; ".join(f"{pin.nurse.user.full_name or pin.nurse.user.username} on {long_date(pin.date)}" for pin in pins)


def on_shifts_going(unit: Unit, shifts: list[str]) -> list[PinnedCell]:
    """Pins the unit's rules could no longer hold with only these shifts. Hold the unit's lock and the catalogue's, as both a
    save of the rules and of a pin do. The solver refuses a pin on a shift its unit does not work."""
    return [pin for pin in _counted_from_now_on(unit) if pin.shift and pin.code not in shifts]


def outside_allowed(nurse: NurseProfile, unit: Unit, allowed: list[str] | None) -> list[PinnedCell]:
    """Pins of this nurse that would break this list, which only makes a month infeasible. A list that empties allows any."""
    if allowed is None:
        return []
    return [pin for pin in _counted_from_now_on(unit) if pin.nurse_id == nurse.pk and pin.shift and pin.code not in allowed]


def lost_to_leave(unit: Unit, month: dt.date, since) -> list[PinnedCell]:
    """Pins of the unit's month that leave recorded after `since` ended, by nurse and date."""
    return list(PinnedCell.objects.in_month(month).filter(unit=unit, removed_why=PinEnded.LEAVE, removed_at__gt=since)
                .select_related("nurse__user", "shift", "removed_by").order_by("nurse__user__username", "date"))


def counted_uses(code: str, since: dt.date) -> list[tuple[Unit, dt.date]]:
    """The units' months from `since` on where a pin that counts holds this shift, soonest first. A month that is over can
    reach no solve, and a pin set aside no solve either, so neither may hold up the CNO: month close (ticket 21) has to read
    them itself."""
    pairs = PinnedCell.objects.current().filter(shift__code=code, date__gte=since).select_related("unit").order_by("date")
    uses: dict[tuple, tuple[Unit, dt.date]] = {}
    for pin in pairs:
        month = pin.date.replace(day=1)
        uses.setdefault((pin.unit_id, month), (pin.unit, month))
    return [(unit, month) for unit, month in uses.values() if _holds(month_pins(unit, month), code)]


def _holds(pins: MonthPins, code: str) -> bool:
    return any(pin.code == code and pin.aside is None for pin in pins.rows)
