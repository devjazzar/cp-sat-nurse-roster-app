"""Problem definition: the data contract between the app and the solver.

Two rule layers: GeneralRules (hospital-wide) and DepartmentRules (per department / unit).
Day indices are 0-based within the month. Weekdays: 0=Mon .. 4=Fri, 5=Sat, 6=Sun.
Nothing here carries a unit's numbers: every rule, switch and weight comes from the input
(`request.py` builds a Problem from a dated request; this is the solver's internal contract).
"""
from __future__ import annotations

import calendar as _cal
import copy
import json
import math
import re
from dataclasses import dataclass, field, fields, asdict
from datetime import date
from pathlib import Path
from typing import IO

# Size limits. The model is O(nurses x horizon x shifts), so an unbounded `days` or history
# is a hang / memory bomb once a front end accepts files; weights above ~10^6 overflow the
# int64 objective (CP-SAT answers MODEL_INVALID without saying why).
MAX_DAYS = 62            # a month, with slack
MAX_HISTORY = 62         # previous-month tail per nurse
MAX_NURSES = 1000
MAX_SHIFTS = 12
MAX_SHIFT_HOURS = 24     # a shift never exceeds a day
MAX_WEIGHT = 10 ** 6
MAX_HOURS = 10 ** 6      # overtime caps, YTD overtime, a carried hours balance
MAX_PARAM = 1000         # rule counts (max in a row, switches), balances, caps
MAX_REST_DAYS = 7        # night_rest_days: its clause encoding lists every day of the gap, so
                         # the model grows with the square of it; a week is beyond any real rule
SCHEMA_VERSION = 4       # of the problem JSON. 3 (2026-11-03): every rule, switch and weight is
                         # explicit; no migration from 1 or 2 (they relied on defaults). 4 (2026-11-08):
                         # a nurse's optional `preferences_not_kept` (absent = 0) doubles the price of
                         # her undesired and desired days (ADR 0013); a version-3 file is refused
                         # like any other (the request, version 1, takes the field as optional)
MAX_NAME = 100           # nurse ids and shift names (the CSV reader's field limit is 128 kB)
_MONTH = re.compile(r"(\d{4})-(\d{2})")


@dataclass(slots=True)
class Nurse:
    id: str
    gender: str = "F"                  # "M" / "F"
    team_leader: bool = False
    score: float = 0.8                 # performance score 0.00 .. 1.00
    ramadan_reduced: bool = False      # eligible for 6 h/day during Ramadan
    breastfeeding: bool = False        # daily hours reduced by 1 (8->7, Ramadan 6->5)
    ytd_overtime: int = 0              # overtime hours already worked this year
    hours_balance: int = 0             # carried from last month: +h still owed, -h worked ahead
    night_balance: float = 0.0         # cumulative nights above (+) / below (-) fair share, in shifts
    friday_balance: float = 0.0        # cumulative Fridays above (+) / below (-) fair share
    unavailable: list[int] = field(default_factory=list)  # leave days (sick, educational,
                                                          # marriage, bereavement...): off, and
                                                          # credited as regular hours worked
    undesired_days: list[int] = field(default_factory=list)  # requests: prefers not to work (soft)
    desired_days: list[int] = field(default_factory=list)    # requests: prefers to work (soft)
    pinned: dict[int, str] = field(default_factory=dict)     # day -> shift name or "" (off): fixed
                                                             # by the admin or already worked (hard)
    allowed_shifts: list[str] | None = None               # None = any department shift (hard)
    previous: list[str] = field(default_factory=list)     # last days of previous month, oldest
                                                          # first: shift name or "" for off
    last_shift_kind: str | None = None # "night" / "day" (any other work) / None (none known): the kind
                                       # of the last shift worked before `previous` begins, the switch
                                       # rule's memory whatever the number of off days since and however
                                       # the unit has since renamed its shifts (carry_over.last_shift_kind)
    rest_owed: int = 0                 # off days still owed to the last night before `previous`
                                       # begins: the night-rest rule's memory (carry_over.rest_owed)
    preferences_not_kept: int = 0      # her undesired / desired days the month before did not keep
                                       # (carry_over.preferences_not_kept): above 0, each of hers this
                                       # month costs twice its weight, whatever the count (ADR 0013)


def preference_factor(nurse: Nurse) -> int:
    """How many times each of the nurse's undesired and desired days counts its weight: twice
    after a month that did not keep one of hers, else once (ADR 0013). The model and the
    validator both read it, so a solve's cost and a validation's agree."""
    return 2 if nurse.preferences_not_kept > 0 else 1


@dataclass(slots=True)
class Weights:
    """Every weight is given by the input (0 = rule off). No unit's tuning lives in the code."""
    night_rest: int              # per N -> D with too little rest
    dept_overtime: int           # per hour over the department cap
    nurse_overtime: int          # per hour of individual overtime (keeps reduced-hours staff at contract)
    nurse_shortfall: int         # per hour under contract carried to next month (< one shift)
    avoidable_shortfall: int     # per hour a nurse ends short beyond a remainder below one shift and the
                                 # hours her recorded and free days cannot give (Problem.unreachable_hours):
                                 # far above the others, so no preference idles her while a shift of hers
                                 # is still free, yet never an infeasibility (what she can still work is
                                 # bounded by every other hard rule at once)
    fair_day: int                # per 0.1 shift a nurse's D count deviates from her proportional
    fair_night: int              #   share (beyond a free half-shift tolerance); same for N
    fair_weekend: int            # per 0.1 shift a nurse's Fridays deviate from her fair share
    score_deficit: int           # per 0.01 score-point x person a shift falls below the target
    score_spread: int            # per 0.01 between the strongest and weakest shift average
    excess_weekend: int          # per weekend worked above the department maximum
    shift_switch: int            # per D/N switch above the department maximum
    undesired_day: int           # per requested-off day worked
    desired_day: int             # per requested-work day not worked
    change: int                  # per cell that differs from the published roster (re-solves)


@dataclass(slots=True)
class GeneralRules:
    """Hospital-wide rules. Every field is given by the input."""
    shift_hours: dict[str, int]         # every shift any department may use, e.g. D/N 12 h, A/B/C 8 h
    hours_per_day: int                  # regular hours owed per working day
    ramadan_hours_per_day: int          # for nurses with ramadan_reduced, on Ramadan days
    breastfeeding_reduction: int        # hours per working day
    weekend_weekdays: list[int]         # 0=Mon .. 6=Sun, e.g. [4] for Friday
    forbidden_successions: list[tuple[str, str]]   # (today, tomorrow) pairs that may not follow
    forbidden_successions_enabled: bool
    hours_rule_enabled: bool            # off: any number of shifts, no overtime / shortfall
    overtime_caps_enabled: bool         # off: no monthly / yearly per-nurse overtime cap
    overtime_month_cap: int             # hard, per nurse
    overtime_year_cap: int              # hard, per nurse (uses Nurse.ytd_overtime)
    dept_overtime_cap: int              # soft, per department per month
    weights: Weights


@dataclass(slots=True)
class Headcount:
    shift: str                          # anchor shift, e.g. "D"
    weekday_min: int
    weekday_max: int
    weekend_min: int
    weekend_max: int
    also_counts: list[str] = field(default_factory=list)  # overlapping shifts counted too (unused for ER)


@dataclass(slots=True)
class DepartmentRules:
    """One unit's rules. Every field is given by the input."""
    name: str
    shifts: list[str]                    # the shifts this unit works, each in general.shift_hours
    headcounts: list[Headcount]          # one per anchor shift
    headcount_enabled: bool              # off: no min/max headcount per anchor shift
    require_team_leader: bool            # on every anchor shift (pure shift staff)
    require_both_genders: bool           # on every anchor shift (pure shift staff)
    score_target: float                  # soft: average score of each anchor shift should reach this
    score_target_weekend: float          # same, on weekend shifts
    score_balance: bool                  # soft: keep shift averages close together
    score_balance_mode: str              # "band": penalise avg above score_band_hi (linear, fast);
                                         # "spread": minimise max−min avg (ratio vars, weak bound)
    score_band_hi: float
    score_band_hi_weekend: float         # band ceiling on weekend shifts
    night_shift: str
    day_shift: str
    night_rest_days: int                 # N -> D needs this many off days between (0 = off)
    night_rest_hard: bool                # True: hard rule; False: soft, weight night_rest
    fair_shifts: list[str]
    fair_tolerance: float                # shifts of deviation from the proportional share that are free
    fair_weekends: bool                  # spread weekend days worked evenly
    carry_fairness: bool                 # carried night/weekend balances shift this month's targets
    carry_cap: float                     # max target adjustment per month, in shifts
    max_consecutive_shifts: int          # hard; a "cycle" is this many shifts in a row
    double_cycle_rest: int               # hard: cycle, 1 day off, cycle -> at least this many days off
    max_weekends: int                    # soft: weekend days worked per month
    no_mixed_blocks: bool                # hard: consecutive working days are all D or all N
    max_switches: int                    # D<->N switches per month (month boundary counts)
    switches_hard: bool                  # True: hard cap; False: soft, weight shift_switch


@dataclass(slots=True)
class Problem:
    days: int
    first_weekday: int                   # weekday of day 0
    nurses: list[Nurse]
    general: GeneralRules
    department: DepartmentRules
    public_holidays: list[int] = field(default_factory=list)
    ramadan_days: list[int] = field(default_factory=list)
    published: list[list[str]] | None = None   # the roster in force (nurse x day, shift name or
                                               # ""), baseline for nondisruptive re-solves
    planning_from: int = 0               # the planning cutoff: days before it have happened (every
                                         # cell pinned) and are facts; a hard rule broken wholly
                                         # before it is reported, not enforced (replan_from sets it)
    version: int = SCHEMA_VERSION      # of the JSON schema this object follows (checked, never migrated)
    month: str | None = None           # "YYYY-MM" the problem was built for (the request loader sets
                                       # it; checked against days / first_weekday): part of the
                                       # fingerprint, so a result can only be reported for the month
                                       # that was solved, never for another of the same shape

    # ---- derived -----------------------------------------------------------
    def history_len(self) -> int:
        return max((len(n.previous) for n in self.nurses), default=0)

    def weekday(self, d: int) -> int:
        return (self.first_weekday + d) % 7

    def is_weekend(self, d: int) -> bool:
        return self.weekday(d) in self.general.weekend_weekdays

    def daily_hours(self, nurse: Nurse, d: int) -> int:
        """Regular hours owed for working day d (0 on Fridays / public holidays)."""
        if self.is_weekend(d) or d in self.public_holidays:
            return 0
        g = self.general
        h = g.ramadan_hours_per_day if (nurse.ramadan_reduced and d in self.ramadan_days) else g.hours_per_day
        if nurse.breastfeeding:
            h -= g.breastfeeding_reduction
        return h

    def contract_hours(self, nurse: Nurse) -> int:
        """Monthly hours owed before any leave credit."""
        return sum(self.daily_hours(nurse, d) for d in range(self.days))

    def leave_credit(self, nurse: Nurse) -> int:
        """Leave days count as worked at the regular daily rate."""
        return sum(self.daily_hours(nurse, d) for d in set(nurse.unavailable) if 0 <= d < self.days)

    def required_hours(self, nurse: Nurse) -> int:
        """Hours to work in shifts this month = contract − leave credit + carried balance,
        never below 0: an advance credit the month cannot absorb (e.g. a month of leave) is
        not new overtime, it stays a credit (`unused_credit`) and is carried on."""
        return max(0, self.contract_hours(nurse) - self.leave_credit(nurse) + nurse.hours_balance)

    def unused_credit(self, nurse: Nurse) -> int:
        """Hours of carried advance credit this month cannot consume (carried on, negative)."""
        return max(0, -(self.contract_hours(nurse) - self.leave_credit(nurse) + nurse.hours_balance))

    def carry_over(self, nurse: Nurse, worked_hours: int) -> int:
        """Next month's `hours_balance` given the hours worked in shifts: the shortfall still
        owed (+), or the advance credit not used (−). Overtime is paid, not carried. With
        the hours rule off nothing is accounted, so nothing is carried."""
        if not self.general.hours_rule_enabled:
            return 0
        short = max(0, self.required_hours(nurse) - worked_hours)
        return short - self.unused_credit(nurse)

    def min_shift_hours(self, nurse: Nurse) -> int:
        allowed = nurse.allowed_shifts or self.department.shifts
        return min(self.general.shift_hours[s] for s in allowed)

    def max_shortfall(self, nurse: Nurse) -> int:
        """Hours a nurse may end under her requirement (carried to next month): less than
        one shift, so a full extra shift is never forced for a remainder."""
        return self.min_shift_hours(nurse) - 1

    def overtime_cap(self, nurse: Nurse) -> int:
        g = self.general
        if not g.overtime_caps_enabled:
            return 24 * self.days                # effectively unbounded
        return max(0, min(g.overtime_month_cap, g.overtime_year_cap - nurse.ytd_overtime))

    def replan_from(self, day: int) -> int:
        """Mid-month re-solve: days before `day` (0-based) are fact. A cell already pinned is
        a recorded fact (a completed swap, a sick cover) and is kept; a leave day was off; every
        other past cell is filled from the published roster, and `planning_from` is set to
        `day` so a hard rule the past broke (an uncovered shift, a long run) is reported, not
        enforced, while obligations reaching into the free days (rest after a night, the run
        limit, hours) still are. From `day` on, the published roster stays the baseline the
        `change` weight keeps the new roster close to (recorded facts that differ from it are
        pinned, so they are not charged as changes). Returns the number of past cells whose
        fact differs from the published roster."""
        if self.published is None:
            raise ValueError("replan_from needs a published roster")
        if not _is_int(day) or not 0 <= day <= self.days:
            raise ValueError(f"replan_from: day must be within 0..{self.days}, got {day!r}")
        proposed = copy.deepcopy(self)                        # validate against the requested
        proposed.planning_from = day                          # cutoff without changing the caller
        # Check structure before reading the baseline. Off placeholders complete the past
        # for this check; existing records stay intact and use the prospective cutoff.
        if isinstance(proposed.nurses, list):
            for nurse in proposed.nurses:
                if isinstance(nurse, Nurse) and isinstance(nurse.pinned, dict):
                    for d in range(day):
                        nurse.pinned.setdefault(d, "")
        proposed.check()
        differ = 0
        for original, nurse, row in zip(self.nurses, proposed.nurses, proposed.published):
            pins = dict(original.pinned)
            leave = set(nurse.unavailable)
            for d in range(day):
                if d not in pins:
                    pins[d] = "" if d in leave else row[d]
                differ += pins[d] != row[d]
            nurse.pinned = pins
        proposed.check()                                      # all completed facts must validate
        for nurse, candidate in zip(self.nurses, proposed.nurses):
            nurse.pinned = candidate.pinned
        self.planning_from = day
        return differ

    def elapsed_hours(self, nurse: Nurse) -> int:
        """Hours already worked before the planning cutoff, from the pins."""
        h = self.general.shift_hours
        return sum(h[s] for d, s in nurse.pinned.items() if s and d < self.planning_from)

    def max_hours(self, nurse: Nurse) -> int:
        """The most hours the nurse can work this month: her pinned shifts (recorded or fixed by
        the admin) plus her longest allowed shift on every free day (from the cutoff on, not on
        leave). The hours of her requirement beyond it (`unreachable_hours`) cannot be worked
        whatever the solver does: they and a remainder below one shift are exempt from the
        `avoidable_shortfall` penalty (model and validator alike), and the whole shortfall is
        carried over as her debt."""
        h = self.general.shift_hours
        longest = max(h[s] for s in (nurse.allowed_shifts or self.department.shifts))
        leave = set(nurse.unavailable)
        total = 0
        for d in range(self.days):
            if d in nurse.pinned:
                total += h[nurse.pinned[d]] if nurse.pinned[d] else 0
            elif d >= self.planning_from and d not in leave:
                total += longest
        return total

    def unreachable_hours(self, nurse: Nurse) -> int:
        """Hours of the requirement no roster can work this month (see `max_hours`)."""
        return max(0, self.required_hours(nurse) - self.max_hours(nurse))

    def recorded_differences(self) -> int:
        """Recorded past cells (pins before the cutoff) that differ from the published roster:
        what `replan_from` returned, re-derived from the problem itself."""
        if self.published is None:
            return 0
        return sum(1 for nu, row in zip(self.nurses, self.published)
                   for d, s in nu.pinned.items() if d < self.planning_from and s != row[d])

    def published_matrix(self) -> list[list[int]] | None:
        """The published roster as an assignment matrix (shift index or -1)."""
        if self.published is None:
            return None
        idx = {s: i for i, s in enumerate(self.department.shifts)}
        return [[idx[c] if c else -1 for c in row] for row in self.published]

    def successions(self) -> list[tuple[str, str]]:
        """Forbidden successions in force: the general list (when switched on) plus the
        department's no-mixed-blocks rule, which forbids a D/N switch on consecutive days."""
        g, dep = self.general, self.department
        out = [tuple(t) for t in g.forbidden_successions] if g.forbidden_successions_enabled else []
        if dep.no_mixed_blocks:
            out += [(dep.day_shift, dep.night_shift), (dep.night_shift, dep.day_shift)]
        return list(dict.fromkeys(out))

    # ---- JSON -----------------------------------------------------------------
    def to_json(self, out: str | Path | IO[str]) -> None:
        """`out`: a file path, or an open text stream."""
        text = json.dumps(asdict(self), indent=1)
        if isinstance(out, (str, Path)):
            Path(out).write_text(text)
        else:
            out.write(text)

    @staticmethod
    def from_json(path: str | Path, *, check_planning: bool = True) -> "Problem":
        return Problem.from_dict(read_json(path), check_planning=check_planning)

    @staticmethod
    def from_dict(raw: dict, *, check_planning: bool = True) -> "Problem":
        """Every field of the rule objects and every nurse scalar is required: no unit's
        numbers live in the code. Only a nurse's day lists, pins, `allowed_shifts`,
        `previous`, `last_shift_kind`, `rest_owed` and `preferences_not_kept`, a headcount's `also_counts`, and the root's
        holidays, Ramadan days, `published`, `planning_from` and `month` may be absent (absent = none). An explicitly empty
        list stays empty. The result is checked (`check`) so malformed input fails here, not
        in the solver. Every malformed input raises ValueError (never TypeError), with the
        field path. With check_planning=False, only cutoff-dependent pin checks are deferred;
        the caller must apply its published baseline and call replan_from before solving."""
        if not isinstance(raw, dict):
            raise ValueError("problem must be a JSON object")
        _require(Problem, raw, "problem", optional=_ROOT_OPTIONAL)
        try:
            g = dict(_require(GeneralRules, raw["general"], "general"))
            g["weights"] = _build(Weights, g["weights"], "general.weights")
            general = _build(GeneralRules, g, "general")
            dp = dict(_require(DepartmentRules, raw["department"], "department"))
            dp["headcounts"] = [_build(Headcount, h, f"department.headcounts[{i}]", optional={"also_counts"})
                                for i, h in enumerate(_list(dp["headcounts"], "department.headcounts"))]
            nurses = [_build(Nurse, n, f"nurses[{i}]", optional=_NURSE_OPTIONAL)
                      for i, n in enumerate(_list(raw["nurses"], "nurses"))]
            for nu in nurses:                                 # JSON object keys are strings
                if isinstance(nu.pinned, dict):
                    pins: dict = {}
                    for k, v in nu.pinned.items():
                        day = int(k) if isinstance(k, str) and k.lstrip("-").isdigit() else k
                        if day in pins:                       # "0" and "00": never pick a winner
                            raise ValueError(f"nurses[{nu.id!r}].pinned: day {day} is given twice")
                        pins[day] = v
                    nu.pinned = pins
            p = Problem(days=raw["days"], first_weekday=raw["first_weekday"], nurses=nurses,
                        public_holidays=list(_list(raw.get("public_holidays", []), "public_holidays")),
                        ramadan_days=list(_list(raw.get("ramadan_days", []), "ramadan_days")),
                        general=general, department=_build(DepartmentRules, dp, "department"),
                        published=raw.get("published"), planning_from=raw.get("planning_from", 0),
                        version=raw["version"], month=raw.get("month"))
        except TypeError as e:                                # anything the guards above missed
            raise ValueError(f"problem: malformed input ({e})") from None
        if isinstance(p.general.forbidden_successions, list):
            p.general.forbidden_successions = [tuple(t) if isinstance(t, (list, tuple)) else t
                                               for t in p.general.forbidden_successions]
        p.check(check_planning=check_planning)
        return p

    # ---- input validation -------------------------------------------------------
    def check(self, *, check_planning: bool = True) -> None:
        """Raise ValueError on the first malformed field. Called by from_dict, build_model,
        validate and precheck so every entry point sees the same contract. Types are
        checked strictly (a string "false" is not a flag, a string "DN" is not a list), the
        names a rule refers to must resolve, and sizes are bounded. Only ValueError leaves.
        check_planning=False defers pin eligibility and elapsed-prefix completeness until
        replan_from applies the requested cutoff; all structural checks still run."""
        try:
            self._check(check_planning=check_planning)
        except (TypeError, OverflowError, AttributeError) as e:
            raise ValueError(f"problem: malformed input ({e})") from None

    def _check(self, *, check_planning: bool = True) -> None:
        g, dep = self.general, self.department
        err = lambda msg: ValueError(f"problem: {msg}")
        if not isinstance(g, GeneralRules) or not isinstance(g.weights, Weights):
            raise err("general must be a GeneralRules object with Weights")
        if not isinstance(dep, DepartmentRules):
            raise err("department must be a DepartmentRules object")
        if not _is_int(self.days) or not 1 <= self.days <= MAX_DAYS:
            raise err(f"days must be an integer within 1..{MAX_DAYS}, got {self.days!r}")
        if not _is_int(self.first_weekday) or not 0 <= self.first_weekday < 7:
            raise err(f"first_weekday must be 0..6, got {self.first_weekday!r}")
        if not _is_int(self.planning_from) or not 0 <= self.planning_from <= self.days:
            raise err(f"planning_from must be an integer within 0..{self.days}, got {self.planning_from!r}")
        if self.month is not None:
            m = _MONTH.fullmatch(self.month) if isinstance(self.month, str) else None
            if m is None or not 1 <= int(m.group(2)) <= 12:
                raise err(f"month must be YYYY-MM or null, got {self.month!r}")
            y, mo = int(m.group(1)), int(m.group(2))
            try:
                shape = (_cal.monthrange(y, mo)[1], date(y, mo, 1).weekday())
            except ValueError:
                raise err(f"month {self.month} is outside the calendar") from None
            if shape != (self.days, self.first_weekday):
                raise err(f"month {self.month} has {shape[0]} days from weekday {shape[1]}, "
                          f"not {self.days} from {self.first_weekday}")
        if not isinstance(self.nurses, list) or not self.nurses:
            raise err("nurses must be a non-empty list")
        if len(self.nurses) > MAX_NURSES:
            raise err(f"at most {MAX_NURSES} nurses, got {len(self.nurses)}")
        for name in ("forbidden_successions_enabled", "hours_rule_enabled", "overtime_caps_enabled"):
            if not isinstance(getattr(g, name), bool):
                raise err(f"general.{name} must be true or false, got {getattr(g, name)!r}")
        for name in ("headcount_enabled", "require_team_leader", "require_both_genders", "score_balance",
                     "night_rest_hard", "fair_weekends", "carry_fairness", "no_mixed_blocks", "switches_hard"):
            if not isinstance(getattr(dep, name), bool):
                raise err(f"department.{name} must be true or false, got {getattr(dep, name)!r}")
        if not isinstance(dep.name, str):
            raise err("department.name must be a string")
        if not isinstance(g.shift_hours, dict):
            raise err("general.shift_hours must be an object {shift: hours}")
        for s, h in g.shift_hours.items():
            if not _is_name(s):
                raise err(f"general.shift_hours: shift name {s!r} must be a non-empty string without a "
                          f"leading = + - @ ' or control character")
            if s == RESERVED_SHIFT:
                raise err(f"general.shift_hours: shift name {s!r} is reserved (the CSV export marks leave days with it); "
                          f"rename the shift, e.g. 'LT'")
            if len(s) > MAX_NAME:
                raise err(f"general.shift_hours: shift name longer than {MAX_NAME} characters")
            if not _is_int(h) or not 0 < h <= MAX_SHIFT_HOURS:
                raise err(f"general.shift_hours[{s!r}] must be an integer within 1..{MAX_SHIFT_HOURS}")
        shifts = _list(dep.shifts, "department.shifts")
        if not shifts or not all(_is_name(s) for s in shifts) or len(set(shifts)) != len(shifts):
            raise err(f"department.shifts must be a non-empty list of distinct names, got {shifts!r}")
        if len(shifts) > MAX_SHIFTS:
            raise err(f"department.shifts: at most {MAX_SHIFTS} shifts")
        for s in shifts:
            if s not in g.shift_hours:
                raise err(f"department.shifts: shift {s!r} has no entry in general.shift_hours")
        for name in ("hours_per_day", "ramadan_hours_per_day", "breastfeeding_reduction"):
            if not _is_int(getattr(g, name)) or not 0 <= getattr(g, name) <= 24:
                raise err(f"general.{name} must be an integer within 0..24")
        if g.ramadan_hours_per_day > g.hours_per_day:
            raise err("general.ramadan_hours_per_day must not exceed hours_per_day")
        if g.breastfeeding_reduction > g.ramadan_hours_per_day:
            raise err("general.breastfeeding_reduction must not exceed the (Ramadan) daily hours, "
                      "or a working day would owe negative hours")
        for name in ("overtime_month_cap", "overtime_year_cap", "dept_overtime_cap"):
            if not _is_int(getattr(g, name)) or not 0 <= getattr(g, name) <= MAX_HOURS:
                raise err(f"general.{name} must be an integer within 0..{MAX_HOURS}")
        for f in [fl.name for fl in fields(Weights)]:
            if not _is_int(getattr(g.weights, f)) or not 0 <= getattr(g.weights, f) <= MAX_WEIGHT:
                raise err(f"general.weights.{f} must be an integer within 0..{MAX_WEIGHT}")
        for wd in _list(g.weekend_weekdays, "general.weekend_weekdays"):
            if not _is_int(wd) or not 0 <= wd < 7:
                raise err(f"general.weekend_weekdays entries must be 0..6, got {wd!r}")
        for pair in _list(g.forbidden_successions, "general.forbidden_successions"):
            if not isinstance(pair, (list, tuple)) or len(pair) != 2 or not all(_is_name(s) for s in pair):
                raise err(f"general.forbidden_successions entry {pair!r} must be a pair of shift names")
            for s in pair:
                if s not in g.shift_hours:
                    raise err(f"general.forbidden_successions: shift {s!r} has no entry in general.shift_hours")
        for name in ("max_consecutive_shifts", "double_cycle_rest", "max_weekends", "max_switches"):
            if not _is_int(getattr(dep, name)) or not 0 <= getattr(dep, name) <= MAX_PARAM:
                raise err(f"department.{name} must be an integer within 0..{MAX_PARAM}")
        if not _is_int(dep.night_rest_days) or not 0 <= dep.night_rest_days <= MAX_REST_DAYS:
            raise err(f"department.night_rest_days must be an integer within 0..{MAX_REST_DAYS}")
        for name in ("score_target", "score_target_weekend", "score_band_hi", "score_band_hi_weekend"):
            v = getattr(dep, name)
            if not _is_num(v) or not 0.0 <= v <= 1.0:
                raise err(f"department.{name} must be a number within 0..1, got {v!r}")
        band_on = dep.score_balance and dep.score_balance_mode == "band" and g.weights.score_spread > 0
        if band_on and g.weights.score_deficit > 0 and \
                (dep.score_target > dep.score_band_hi or dep.score_target_weekend > dep.score_band_hi_weekend):
            raise err("department.score_target must not exceed score_band_hi while both the deficit "
                      "and the band penalty are on (every shift would pay one of them)")
        for name in ("fair_tolerance", "carry_cap"):
            v = getattr(dep, name)
            if not _is_num(v) or not 0 <= v <= MAX_PARAM:
                raise err(f"department.{name} must be a number within 0..{MAX_PARAM}, got {v!r}")
        if dep.score_balance_mode not in ("band", "spread"):
            raise err(f"department.score_balance_mode must be 'band' or 'spread', got {dep.score_balance_mode!r}")
        # the shifts the night rules refer to must exist, or the rules would silently vanish
        for name in ("night_shift", "day_shift"):
            if not _is_name(getattr(dep, name)):
                raise err(f"department.{name} must be a shift name")
        rest_on = dep.night_rest_days > 0 and (dep.night_rest_hard or g.weights.night_rest > 0)
        night_rules = (rest_on or dep.no_mixed_blocks or dep.switches_hard
                       or g.weights.shift_switch > 0 or dep.carry_fairness)
        if night_rules:
            for name in ("night_shift", "day_shift"):
                if getattr(dep, name) not in shifts:
                    raise err(f"department.{name} {getattr(dep, name)!r} is not a department shift "
                              f"(needed by the night rest / mixed block / switch / carry rules)")
        if dep.night_shift == dep.day_shift:
            raise err("department.night_shift and day_shift must differ")
        seen = set()
        for hc in _list(dep.headcounts, "department.headcounts"):
            if not isinstance(hc, Headcount):
                raise err(f"department.headcounts: entries must be objects, got {hc!r}")
            if hc.shift not in shifts:
                raise err(f"department.headcounts: shift {hc.shift!r} is not a department shift")
            if hc.shift in seen:
                raise err(f"department.headcounts: duplicate headcount for shift {hc.shift!r}")
            seen.add(hc.shift)
            also = _list(hc.also_counts, f"department.headcounts[{hc.shift}].also_counts")
            if not all(_is_name(x) for x in also):
                raise err(f"department.headcounts[{hc.shift}]: also_counts entries must be shift names")
            if hc.shift in also or len(set(also)) != len(also):
                raise err(f"department.headcounts[{hc.shift}]: also_counts must not repeat a shift or name the anchor")
            for s in also:
                if s not in shifts:
                    raise err(f"department.headcounts[{hc.shift}]: also_counts shift {s!r} is not a department shift")
            for k in ("weekday_min", "weekday_max", "weekend_min", "weekend_max"):
                if not _is_int(getattr(hc, k)) or not 0 <= getattr(hc, k) <= MAX_NURSES:
                    raise err(f"department.headcounts[{hc.shift}].{k} must be an integer within 0..{MAX_NURSES}")
            if hc.weekday_min > hc.weekday_max or hc.weekend_min > hc.weekend_max:
                raise err(f"department.headcounts[{hc.shift}]: min above max")
        fair = _list(dep.fair_shifts, "department.fair_shifts")
        if not all(_is_name(x) for x in fair):
            raise err(f"department.fair_shifts entries must be shift names, got {fair!r}")
        if len(set(fair)) != len(fair):
            raise err(f"department.fair_shifts must not repeat a shift (the penalty would count twice): {fair!r}")
        for s in fair:
            if s not in shifts:
                raise err(f"department.fair_shifts: fair shift {s!r} is not a department shift")
            if s not in seen:
                raise err(f"department.fair_shifts: fair shift {s!r} has no headcount entry, so its fair share is undefined")
        for label, days in (("public_holidays", self.public_holidays), ("ramadan_days", self.ramadan_days)):
            for d in _list(days, label):
                if not _is_int(d) or not 0 <= d < self.days:
                    raise err(f"{label}: day index {d!r} outside 0..{self.days - 1}")
            if len(set(days)) != len(days):
                raise err(f"{label}: a day is listed twice")
        ids = set()
        for nu in self.nurses:
            if not isinstance(nu, Nurse):
                raise err(f"nurses entries must be objects, got {nu!r}")
            if not isinstance(nu.id, str) or not nu.id.strip() or nu.id.startswith("'") or "\n" in nu.id:
                raise err(f"nurse id must be a non-empty string, not starting with an apostrophe "
                          f"(the CSV export escapes formula prefixes with one), got {nu.id!r}")
            if len(nu.id) > MAX_NAME:
                raise err(f"nurse id longer than {MAX_NAME} characters")
            if nu.id in ids:
                raise err(f"duplicate nurse id {nu.id!r}")
            ids.add(nu.id)
            if nu.gender not in ("M", "F"):
                raise err(f"{nu.id}: gender must be 'M' or 'F'")
            for name in ("team_leader", "ramadan_reduced", "breastfeeding"):
                if not isinstance(getattr(nu, name), bool):
                    raise err(f"{nu.id}: {name} must be true or false, got {getattr(nu, name)!r}")
            if not _is_num(nu.score) or not 0.0 <= nu.score <= 1.0:
                raise err(f"{nu.id}: score must be within 0..1")
            if not _is_int(nu.ytd_overtime) or not 0 <= nu.ytd_overtime <= MAX_HOURS:
                raise err(f"{nu.id}: ytd_overtime must be an integer within 0..{MAX_HOURS}")
            if nu.allowed_shifts is not None:
                allowed = _list(nu.allowed_shifts, f"{nu.id}.allowed_shifts")
                if not allowed:
                    raise err(f"{nu.id}: allowed_shifts is empty (use null for any shift, "
                              f"or unavailable days for leave)")
                for s in allowed:
                    if s not in shifts:
                        raise err(f"{nu.id}: allowed shift {s!r} is not a department shift")
            # a carried balance is a remainder below one shift of the month that produced it when
            # that month was planned (new shortfalls stay below her own shortest shift,
            # max_shortfall), but the whole debt of a month whose recorded days could not reach
            # the requirement (an elapsed under-hours fact), so the bound is only a sanity bound,
            # independent of any shift length or eligibility, which may both have changed since
            if not _is_int(nu.hours_balance) or abs(nu.hours_balance) > MAX_HOURS:
                raise err(f"{nu.id}: hours_balance must be an integer within ±{MAX_HOURS}")
            for name in ("night_balance", "friday_balance"):
                v = getattr(nu, name)
                if not _is_num(v) or abs(v) > MAX_PARAM:
                    raise err(f"{nu.id}: {name} must be a number within ±{MAX_PARAM}")
            for name in ("unavailable", "undesired_days", "desired_days"):
                days = _list(getattr(nu, name), f"{nu.id}.{name}")
                for d in days:
                    if not _is_int(d) or not 0 <= d < self.days:
                        raise err(f"{nu.id}: {name} day {d!r} outside 0..{self.days - 1}")
                if len(set(days)) != len(days):           # a repeated day would count twice
                    raise err(f"{nu.id}: {name} lists a day twice")
            leave, want_off, want_on = set(nu.unavailable), set(nu.undesired_days), set(nu.desired_days)
            if want_off & want_on:
                raise err(f"{nu.id}: day {min(want_off & want_on)} is both desired and undesired")
            # a request on a leave day is superseded by the leave (not an error: leave is added
            # after requests were made); the model and validator ignore such requests
            if not isinstance(nu.pinned, dict):
                raise err(f"{nu.id}.pinned must be an object {{day: shift or \"\"}}")
            for d, s in nu.pinned.items():
                if not _is_int(d) or not 0 <= d < self.days:
                    raise err(f"{nu.id}: pinned day {d!r} outside 0..{self.days - 1}")
                if not isinstance(s, str) or (s != "" and s not in shifts):
                    raise err(f"{nu.id}: pinned shift {s!r} on day {d} is not a department shift")
                if check_planning and s and d >= self.planning_from and nu.allowed_shifts is not None \
                        and s not in nu.allowed_shifts:            # an elapsed shift is a fact
                    raise err(f"{nu.id}: pinned shift {s!r} on day {d} is not in her allowed shifts")
                if s and d in leave:
                    raise err(f"{nu.id}: day {d} is on leave but pinned to {s!r}")
            for d in range(self.planning_from if check_planning else 0):
                if d not in nu.pinned:
                    raise err(f"{nu.id}: day {d} is before planning_from ({self.planning_from}) but not "
                              f"pinned; elapsed days must be fully recorded (replan_from does this)")
            prev = _list(nu.previous, f"{nu.id}.previous")
            if len(prev) > MAX_HISTORY:
                raise err(f"{nu.id}: history longer than {MAX_HISTORY} days")
            for s in prev:                                    # a name the unit no longer defines is
                if not isinstance(s, str) or (s != "" and (not _is_name(s) or len(s) > MAX_NAME)):
                    raise err(f"{nu.id}: history entry {s!r} is not a shift name or \"\"")   # other work
            if nu.last_shift_kind not in (None, "night", "day"):
                raise err(f"{nu.id}: last_shift_kind must be \"night\", \"day\" or null, got {nu.last_shift_kind!r}")
            if not _is_int(nu.rest_owed) or not 0 <= nu.rest_owed <= MAX_REST_DAYS:
                raise err(f"{nu.id}: rest_owed must be an integer within 0..{MAX_REST_DAYS}")
            if not _is_int(nu.preferences_not_kept) or not 0 <= nu.preferences_not_kept <= MAX_DAYS:
                raise err(f"{nu.id}: preferences_not_kept must be an integer within 0..{MAX_DAYS}")

        need = needed_history(self.department, self.general)
        if need > MAX_HISTORY:                                # a carried history could not hold it
            raise err(f"the pattern rules look back {need} days (max_consecutive_shifts, double_cycle_rest, "
                      f"night_rest_days), more than a history may hold ({MAX_HISTORY}); lower them")
        if not _is_int(self.version) or self.version != SCHEMA_VERSION:
            raise err(f"version must be {SCHEMA_VERSION} (the schema this code follows), got {self.version!r}")
        if self.published is not None:
            pub = _list(self.published, "published")
            if len(pub) != len(self.nurses):
                raise err(f"published must have one row per nurse ({len(self.nurses)}), got {len(pub)}")
            for nu, row in zip(self.nurses, pub):
                cells = _list(row, f"published[{nu.id}]")
                if len(cells) != self.days:
                    raise err(f"published[{nu.id}] must have {self.days} cells, got {len(cells)}")
                for d, c in enumerate(cells):
                    if not isinstance(c, str) or (c != "" and c not in shifts):
                        raise err(f"published[{nu.id}] day {d}: {c!r} is not a department shift")


def needed_history(dep: DepartmentRules, general: GeneralRules | None = None) -> int:
    """Days of previous-month history the active pattern rules look back on (0 when no rule
    crosses the month boundary). Without `general`, every weight-switched rule counts as on.
    The two memories that reach further (`last_shift_kind`, `rest_owed`) are explicit, so this
    bounds everything a carried history must hold: `check` refuses rules that need more than
    MAX_HISTORY, which the carry-over could not preserve."""
    K, R = dep.max_consecutive_shifts, dep.double_cycle_rest
    w = general.weights if general else None
    night = dep.night_shift in dep.shifts
    need = 0
    if general is None or general.forbidden_successions_enabled or (dep.no_mixed_blocks and night):
        need = 1                                              # successions
    if night and (dep.switches_hard or w is None or w.shift_switch > 0):
        need = max(need, 1)                                   # switch memory
    if K > 0:
        need = max(need, K)
        if R > 1:
            need = max(need, 2 * K + R)                       # W^K O W^K then R off
    if dep.night_rest_days > 0 and night and (dep.night_rest_hard or w is None or w.night_rest > 0):
        other = any(s not in (dep.night_shift, dep.day_shift) for s in dep.shifts)
        need = max(need, dep.night_rest_days * (K + 1) if other and K > 0 else dep.night_rest_days)
    return need


MAX_JSON_DEPTH = 200         # far beyond any real request, far below what can overflow a stack


def read_json(path: str | Path, *, where: str = "problem") -> object:
    return parse_json(Path(path).read_text(), where=where)


def parse_json(text: str | bytes, *, where: str = "problem") -> object:
    """The text's JSON value, with the two input-side guards every reader needs: a repeated
    key is an ambiguity the user has to resolve (`json.loads` would keep the last one), and a
    few thousand nested brackets must not surface as a RecursionError. Python 3.14's parser
    takes such nesting without complaint, so the depth is measured here as well, or the
    RecursionError would only move on to whatever walks the value next."""
    def no_duplicate_keys(pairs: list) -> dict:
        out: dict = {}
        for k, v in pairs:
            if k in out:
                raise ValueError(f"{where}: JSON object repeats the key {k!r}")
            out[k] = v
        return out
    try:
        value = json.loads(text, object_pairs_hook=no_duplicate_keys)
    except RecursionError:
        raise ValueError(f"{where}: JSON nested too deeply") from None
    stack = [(value, 1)]
    while stack:
        v, depth = stack.pop()
        if isinstance(v, (dict, list)):
            if depth > MAX_JSON_DEPTH:
                raise ValueError(f"{where}: JSON nested too deeply")
            stack.extend((c, depth + 1) for c in (v.values() if isinstance(v, dict) else v))
    return value


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_num(v) -> bool:
    if isinstance(v, bool):
        return False
    if isinstance(v, int):
        return abs(v) < 2 ** 53                              # before any float conversion
    return isinstance(v, float) and math.isfinite(v)


_CSV_PREFIX = ("=", "+", "-", "@", "'", "\t", "\r")
RESERVED_SHIFT = "L"       # the CSV export marks leave days with it


def _is_name(v) -> bool:
    """Non-empty string that survives the CSV export unchanged: no spreadsheet-formula or
    quote prefix (the writer would escape it), no newline."""
    return isinstance(v, str) and bool(v.strip()) and not v.startswith(_CSV_PREFIX) and "\n" not in v


def _list(v, where: str) -> list:
    """A JSON array (list / tuple); a string is not one, even though it iterates."""
    if not isinstance(v, (list, tuple)):
        raise ValueError(f"problem: {where} must be a list, got {type(v).__name__}")
    return list(v)


_ROOT_OPTIONAL = frozenset({"public_holidays", "ramadan_days", "published", "planning_from", "month"})
_NURSE_OPTIONAL = frozenset({"unavailable", "undesired_days", "desired_days", "pinned",
                             "allowed_shifts", "previous", "last_shift_kind", "rest_owed",
                             "preferences_not_kept"})


def _require(cls, raw, where: str, *, optional: frozenset | set = frozenset()) -> dict:
    """`raw` must be an object with exactly the fields `cls` declares, except the `optional`
    ones: an unknown key and a missing required one are both clear errors with the path."""
    if not isinstance(raw, dict):
        raise ValueError(f"problem: {where}: expected an object, got {type(raw).__name__}")
    names = [f.name for f in fields(cls)]
    unknown = set(raw) - set(names)
    if unknown:
        raise ValueError(f"problem: {where}: unknown field(s) {sorted(unknown)}")
    missing = [n for n in names if n not in raw and n not in optional]
    if missing:
        raise ValueError(f"problem: {where}: missing field(s) {missing}")
    return raw


def _build(cls, raw, where: str, *, optional: frozenset | set = frozenset()):
    """Construct a dataclass from a checked object (see _require)."""
    try:
        return cls(**_require(cls, raw, where, optional=optional))
    except TypeError as e:                                    # anything _require did not catch
        raise ValueError(f"problem: {where}: {e}") from None
