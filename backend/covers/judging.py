"""Who could take a cover, and what its shift-day still lacks: the one place a cover is judged and worded.

A cover adds one nurse to a shift-day of the roster in force (ADR 0011). The nurses who could be that one are the month's staff
nurses off that day (on the grid, in the month, within their dates, not on leave, allowed the shift), not held off by an
accepted request, and whose taking it newly breaks no hard rule, judged as a swap is: the grid with her cell set to the shift,
put in as a pin, checked with the solver's own code in this process against the month as it stands. A hard rule the roster in
force already breaks is not hers, so a shift-day already short does not empty its own list: a headcount broken less, as one
more nurse on a short shift-day breaks it, is not broken anew. A manager's pin or a swap's to a day off is noted as replaced;
a cell in a waiting swap is left in, since any version expires that swap.

The list is ranked by how far below her owed hours this month each stands, then by least overtime this year, then by name, with
the figures from the solver's own per-nurse accounting on the roster in force, the arithmetic My month uses. Nothing of it is
stored: it is read again each time it is asked for.

Only the unit's manager reads any of this, as they read the leave and the attributes it rests on. Ticket 27 judges an
acceptance again for its nurse alone, through `exclusion`, and words a refusal for her."""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field

from nurse_roster.request import load_request

from accounts.models import Role
from hospital.models import Shift
from nurses.models import NurseProfile
from rosters.approved import ApprovedMonth, Change, violation_key, with_pins
from rosters.editing import Checked, accounted, scored
from rosters.models import PinOrigin, Roster
from rosters.pins import long_date
from solves.input import assemble
from solves.result import in_dates

# The solver's rules of a shift-day as a whole, and how its text names the shift-day: "headcount: day 8 D = 0, want 1..1",
# "team leader: day 8 D has none", "gender: day 8 D has only {'F'}" (`nurse_roster/validate.py`).
SHIFT_DAY_RULES = ("headcount", "team_leader", "gender")
_SHIFT_DAY = re.compile(r"^[a-z ]+: day -?\d+ (\S+) ")
_HEADCOUNT = re.compile(r"= (\d+), want (\d+)\.\.(\d+)")
LACKS = {"team_leader": "No team leader", "gender": "Not both genders"}


@dataclass(frozen=True)
class CouldTake:
    nurse: NurseProfile
    hospital_id: str
    name: str
    worked: int
    owed: int | None  # None with the hospital's hours rule off, which counts nothing owed.
    overtime_this_year: int
    makes_whole: bool
    replaces: str | None  # The origin of her pin to a day off there, which her taking it replaces.

    @property
    def below_owed(self) -> int:
        return self.worked - self.owed if self.owed is not None else 0


@dataclass
class CoverJudged:
    reason: str | None = None
    lack: list[str] = field(default_factory=list)
    full: str | None = None
    nurses: list[CouldTake] = field(default_factory=list)


def _shift_day(violation: dict) -> tuple[str, str] | None:
    """The shift-day a violation of a shift-day rule is about, as (date, shift code), or None for any other."""
    if violation["rule"] not in SHIFT_DAY_RULES or violation["nurse"] or not violation["date"]:
        return None
    found = _SHIFT_DAY.match(violation["text"])
    return (violation["date"], found[1]) if found else None


def _beyond(violation: dict) -> int:
    """How far a headcount is outside its range."""
    present, low, high = (int(number) for number in _HEADCOUNT.search(violation["text"]).groups())
    return low - present if present < low else present - high


def newly_broken(before: Checked, after: Checked) -> list[dict]:
    """What `after` breaks that `before` did not, or breaks further. The solver's text says how far a rule is broken, so one
    broken further reads as new (`rosters.approved.violation_key`); a headcount is compared by how far it is outside its range,
    since its text changes as it comes nearer."""
    old = before.answer["violations"] if before.answer else []
    already = {violation_key(row) for row in old}
    headcounts = {_shift_day(row): _beyond(row) for row in old if row["rule"] == "headcount" and _shift_day(row)}
    new = []
    for violation in after.answer["violations"]:
        where = _shift_day(violation)
        if violation["rule"] == "headcount" and where in headcounts:
            if _beyond(violation) > headcounts[where]:
                new.append(violation)
        elif violation_key(violation) not in already:
            new.append(violation)
    return new


def _on(violations: list[dict], day: dt.date, code: str) -> list[dict]:
    return [row for row in violations if _shift_day(row) == (day.isoformat(), code)]


def _lack_words(violation: dict, month: dt.date) -> str:
    if violation["rule"] == "headcount":
        present, low, high = (int(number) for number in _HEADCOUNT.search(violation["text"]).groups())
        said = (f"Below its minimum headcount: {present} of at least {low}" if present < low
                else f"Above its maximum headcount: {present} of at most {high}")
    else:
        said = LACKS[violation["rule"]]
    return f"{said} (the solver's check: {in_dates(violation['text'], month)})."


class CoverMonth(ApprovedMonth):
    """The roster in force's month as a cover reads it, read once for every nurse judged."""

    def __init__(self, roster: Roster, day: dt.date, shift: Shift):
        super().__init__(roster)
        self.day, self.shift = day, shift
        self.input = assemble(self.unit, self.month).input
        self.before = scored(self.input, roster.grid)

    def exclusion(self, hospital_id: str) -> str | None:
        """Why this nurse could not take the cover before her grid is checked, as a key ticket 27 words for her: `not_on_grid`,
        `not_staff`, `works`, `not_in_month`, `outside_dates`, `leave`, `shift_not_allowed` or `request`."""
        nurse = self.on_grid.get(hospital_id)
        if hospital_id not in self.roster.grid or nurse is None:
            return "not_on_grid"
        if nurse.user.role != Role.STAFF_NURSE:
            return "not_staff"
        if self.cell(hospital_id, self.day):
            return "works"
        serving = self.serving.get(hospital_id)
        why = self.judge.day_why(serving.pk, self.day) if serving else "not_in_month"
        if why is not None:
            return why
        if self.judge.shift_why(serving.pk, self.shift) is not None:
            return "shift_not_allowed"
        pin = self.pins.get((nurse.pk, self.day))
        if pin is not None and pin.origin == PinOrigin.REQUEST:
            return "request"
        return None

    def with_her(self, hospital_id: str) -> tuple[Checked, list[dict]]:
        """Her grid's check, and the hard rules it newly breaks."""
        change = [Change(hospital_id, self.day, self.shift.code)]
        after = scored(with_pins(self.input, self, change), self.grid_after(change))
        return after, (newly_broken(self.before, after) if after.answer else [])

    def full(self) -> str | None:
        """Why one more nurse cannot help, when the shift-day is already at its maximum headcount."""
        problem = load_request(self.input).problem
        if not problem.department.headcount_enabled:
            return None
        index = (self.day - self.month).days
        for headcount in problem.department.headcounts:
            if headcount.shift != self.shift.code:
                continue
            high = headcount.weekend_max if problem.is_weekend(index) else headcount.weekday_max
            counted = {self.shift.code, *headcount.also_counts}
            present = sum(1 for row in self.roster.grid.values() if row.get(self.day.isoformat()) in counted)
            if present >= high:
                return (f"{self.shift.display_name} on {long_date(self.day)} already has {present} of at most {high}, so one "
                        f"more nurse would break its headcount. To change who works it, edit the roster.")
        return None


def judge(roster: Roster, day: dt.date, shift: Shift) -> CoverJudged:
    """The shift-day's lack and the ranked list of who could take it, on the month as it stands. A grid or rules the loader
    refuses are an answer to show, not an error."""
    month = CoverMonth(roster, day, shift)
    if month.before.reason:
        return CoverJudged(reason=f"The roster in force cannot be checked: {in_dates(month.before.reason, month.month)}")
    judged = CoverJudged(lack=[_lack_words(row, month.month) for row in _on(month.before.answer["violations"], day, shift.code)])
    judged.full = month.full()
    if judged.full:
        return judged
    figures = accounted(month.input, roster.grid) or {}
    counted = month.input["general"].get("hours_rule_enabled", True)
    for hospital_id in sorted(roster.grid):
        if month.exclusion(hospital_id) is not None:
            continue
        after, broken = month.with_her(hospital_id)
        if after.reason:
            judged.reason = f"A nurse's grid cannot be checked: {in_dates(after.reason, month.month)}"
            judged.nurses = []
            return judged
        if broken or hospital_id not in figures:
            continue
        nurse, row = month.on_grid[hospital_id], figures[hospital_id]
        pin = month.pins.get((nurse.pk, day))
        judged.nurses.append(CouldTake(
            nurse=nurse, hospital_id=hospital_id, name=nurse.user.full_name or hospital_id, worked=row["hours_worked"],
            owed=row["required"] if counted else None, overtime_this_year=row["carry_over"]["ytd_overtime"],
            makes_whole=not _on(after.answer["violations"], day, shift.code),
            replaces=pin.origin if pin is not None else None))
    judged.nurses.sort(key=lambda could: (could.below_owed, could.overtime_this_year, could.name.casefold(), could.hospital_id))
    return judged
