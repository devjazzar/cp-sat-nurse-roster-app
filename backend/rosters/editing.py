"""A manager's hand edits of the draft: what each would do, whether it may, and what the grid would then break and cost."""
from __future__ import annotations

import copy
import datetime as dt
from dataclasses import dataclass
from typing import Literal

from solver_service.grid import validate_grid

from hospital.models import Shift
from nurses.models import NurseProfile
from rosters.drafts import current_code, in_current_codes
from rosters.models import PinEnded, PinnedCell, PinOrigin, Roster
from rosters.pins import Judge, end, long_date
from solves.input import assemble

Action = Literal["shift", "off", "clear"]


@dataclass(frozen=True)
class Edit:
    hospital_id: str
    date: dt.date
    action: Action
    shift: str | None = None

    @property
    def day(self) -> str:
        return self.date.isoformat()


class DraftEdits:
    """A draft and what may be done to it by hand, read once for all of a save's or a check's edits."""

    def __init__(self, roster: Roster):
        self.roster = roster
        self.judge = Judge(roster.unit, roster.month)
        self.nurses = {nurse.user.username: nurse for nurse in self.judge.nurses.values()}
        self.pins = {(pin.nurse.user.username, pin.date): pin for pin in PinnedCell.objects.current().in_month(roster.month)
                     .filter(unit=roster.unit).select_related("nurse__user", "shift")}
        self.shifts = {shift.code: shift for shift in Shift.objects.filter(code__in=roster.unit.rules.get("shifts", []))}

    def shift_of(self, edit: Edit) -> Shift | None:
        return self.shifts.get(current_code(edit.shift or ""))

    def refusal(self, edit: Edit) -> str | None:
        """Why this edit may not be made. Clearing is always open, on a pin set aside too: nothing it does can break a rule."""
        pin = self.pins.get((edit.hospital_id, edit.date))
        if pin is not None and pin.origin != PinOrigin.MANAGER:
            return f"This pin comes from an accepted {pin.origin}, on {long_date(edit.date)}, so change it there."
        if edit.action == "clear":
            return None
        nurse = self.nurses.get(edit.hospital_id)
        # In one sentence, and the same for a nurse of another unit as for no such nurse.
        if nurse is None or edit.day not in self.roster.grid.get(edit.hospital_id, ()):
            return f"{edit.hospital_id} has no cell on {long_date(edit.date)} in this roster."
        name = nurse.user.full_name or edit.hospital_id
        match self.judge.day_why(nurse.pk, edit.date):
            case "outside_dates":
                return f"{long_date(edit.date)} is outside {name}'s dates, so there is nothing to pin."
            case "leave":
                return f"{name} is on leave on {long_date(edit.date)}, and leave wins over a pin."
        if edit.action == "off":
            return None
        shift = self.shift_of(edit)
        if shift is None or self.judge.shift_why(nurse.pk, shift) == "shift_not_worked":
            return f"{edit.shift} is not one of this unit's shifts."
        if self.judge.shift_why(nurse.pk, shift) == "shift_not_allowed":
            return f"{shift.code} is not one of {name}'s allowed shifts."
        return None

    def cell_after(self, edit: Edit) -> str:
        """Clearing gives the cell back to its solve. On a credited day, leave wins, which is also how a manager takes a shift off
        a day that became leave after the solve; and a nurse no longer in the unit's month, such as one transferred out, works
        nothing here, so clearing takes their shift off."""
        if edit.action == "shift":
            return self.shift_of(edit).code
        if edit.action == "off":
            return ""
        nurse = self.nurses.get(edit.hospital_id)
        if nurse is None or self.judge.day_why(nurse.pk, edit.date) in ("leave", "outside_dates"):
            return ""
        solved = in_current_codes(self.roster.solve.result["roster"])
        return solved.get(edit.hospital_id, {}).get(edit.day, "")

    def grid_after(self, edits: list[Edit]) -> dict[str, dict[str, str]]:
        grid = copy.deepcopy(self.roster.grid)
        for edit in edits:
            if edit.day in grid.get(edit.hospital_id, ()):
                grid[edit.hospital_id][edit.day] = self.cell_after(edit)
        return grid

    def save(self, edits: list[Edit], by) -> tuple[int, int]:
        """How many pins and how many of the grid's cells this changed. Takes no lock of its own: see `rosters.api.save_pins`."""
        changed = 0
        for edit in edits:
            pin = self.pins.get((edit.hospital_id, edit.date))
            wanted = None if edit.action != "shift" else self.shift_of(edit)
            if pin is not None and edit.action != "clear" and pin.shift_id == (wanted.pk if wanted else None):
                continue
            if pin is not None:
                end([pin], PinEnded.CLEARED if edit.action == "clear" else PinEnded.REPLACED, by)
                changed += 1
            if edit.action != "clear":
                nurse: NurseProfile = self.nurses[edit.hospital_id]
                # A pin of the nurse's last unit, which a transfer left behind and set aside there: this month is this unit's.
                end(PinnedCell.objects.current().filter(nurse=nurse, date=edit.date).exclude(unit=self.roster.unit),
                    PinEnded.REPLACED, by)
                PinnedCell.objects.create(unit=self.roster.unit, nurse=nurse, date=edit.date, shift=wanted, pinned_by=by)
                changed += pin is None
        grid = self.grid_after(edits)
        cells = sum(grid[nurse][day] != code for nurse, row in self.roster.grid.items() for day, code in row.items())
        self.roster.grid = grid
        self.roster.save(update_fields=["grid"])  # `updated_at` stays: see its help text.
        return changed, cells


@dataclass
class Checked:
    """What a grid breaks and costs, or `reason` why that could not be worked out."""
    reason: str | None
    answer: dict | None = None

    @property
    def cost(self) -> int | None:
        return self.answer["cost"] if self.answer else None


def _on_the_month(solve_input: dict, grid: dict[str, dict[str, str]]) -> tuple[dict, dict[str, dict[str, str]]]:
    """The loader wants exactly the input's nurses. One who left has no say in the month, and one who joined since the solve
    has no shifts yet, nor any pin of theirs a cell to break: the draft already warns of both."""
    days = {day for row in grid.values() for day in row}
    rows = [row if row["id"] in grid else {key: value for key, value in row.items() if key != "pinned"}
            for row in solve_input["nurses"]]
    return {**solve_input, "nurses": rows}, {row["id"]: grid.get(row["id"]) or dict.fromkeys(days, "") for row in rows}


def scored(solve_input: dict, grid: dict[str, dict[str, str]]) -> Checked:
    """In this process with the solver's own code, like a stored result's explanation (`solves.result.explanation`), so a
    search under way or a solver that is down cannot stop it. A grid or rules the loader refuses are an answer to show, not an
    error."""
    try:
        return Checked(None, validate_grid(*_on_the_month(solve_input, grid)))
    except ValueError as e:
        return Checked(str(e))


def with_edits(solve_input: dict, month: DraftEdits, edits: list[Edit]) -> dict:
    """The input as it would be once these are saved, so the solver's `pin` rule reads the grid they make."""
    edited = copy.deepcopy(solve_input)
    rows = {row["id"]: row for row in edited["nurses"]}
    for edit in edits:
        row = rows.get(edit.hospital_id)
        if row is None:
            continue
        pinned = row.setdefault("pinned", {})
        if edit.action == "clear":
            pinned.pop(edit.day, None)
        else:
            pinned[edit.day] = month.cell_after(edit)
        if not pinned:
            del row["pinned"]
    return edited


def check_saved(roster: Roster) -> Checked:
    return scored(assemble(roster.unit, roster.month).input, roster.grid)
