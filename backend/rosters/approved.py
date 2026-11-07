"""An approved roster's month as a change to the roster in force reads it, and how such a change is checked with the solver's own
code: what a swap (ticket 20) and a cover (ticket 26) share. Each words its own reasons, for its own readers; nothing here says
anything to anyone."""
from __future__ import annotations

import copy
import datetime as dt
from dataclasses import dataclass

from hospital.models import Shift
from nurses.models import NurseProfile
from rosters.drafts import current_code
from rosters.editing import Checked
from rosters.models import PinnedCell, Roster
from rosters.pins import Judge
from rosters.versions import Grid


@dataclass(frozen=True)
class Change:
    """One cell asked for: a nurse's date and what it should hold, a shift's code or None for a day off."""
    hospital_id: str
    date: dt.date
    shift: str | None

    @property
    def day(self) -> str:
        return self.date.isoformat()


class ApprovedMonth:
    """An approved roster's month, read once for every cell a change asks for."""

    def __init__(self, roster: Roster):
        self.roster, self.unit, self.month = roster, roster.unit, roster.month
        self.judge = Judge(self.unit, self.month)
        self.serving = {nurse.user.username: nurse for nurse in self.judge.nurses.values()}
        on_grid = NurseProfile.objects.filter(user__username__in=list(roster.grid)).select_related("user")
        self.on_grid = {nurse.user.username: nurse for nurse in on_grid}
        worked = Shift.objects.filter(active=True, code__in=self.unit.rules.get("shifts", []))
        self.shifts = {shift.code: shift for shift in worked}
        self.pins = {(pin.nurse_id, pin.date): pin for pin in PinnedCell.objects.current().in_month(self.month)
                     .filter(unit=self.unit).select_related("shift")}

    def cell(self, hospital_id: str, day: dt.date) -> str:
        return self.roster.grid.get(hospital_id, {}).get(day.isoformat(), "")

    def shift_of(self, code: str | None) -> Shift | None:
        return self.shifts.get(current_code(code)) if code else None

    def grid_after(self, changes: list[Change]) -> Grid:
        grid = copy.deepcopy(self.roster.grid)
        for change in changes:
            shift = self.shift_of(change.shift)
            grid[change.hospital_id][change.day] = shift.code if shift else ""
        return grid


def with_pins(solve_input: dict, month: ApprovedMonth, changes: list[Change]) -> dict:
    """The input as the change would make it: each changed cell a pin, so the solver's `pin` rule holds the new cell, and a
    manager's pin there, which the change replaces, does not count against it."""
    edited = copy.deepcopy(solve_input)
    rows = {row["id"]: row for row in edited["nurses"]}
    for change in changes:
        row = rows.get(change.hospital_id)
        if row is not None:
            shift = month.shift_of(change.shift)
            row.setdefault("pinned", {})[change.day] = shift.code if shift else ""
    return edited


def violation_key(violation: dict) -> tuple:
    """The solver's text tells the shifts of one day apart, and says how far a rule is broken: one broken further is new."""
    return violation["rule"], violation["nurse"], violation["date"], violation["text"]


def already_broken(before: Checked) -> set[tuple]:
    """A hard rule the roster in force already breaks is not the change's, since an edit may save one (ticket 16)."""
    return {violation_key(row) for row in before.answer["violations"]} if before.answer else set()
