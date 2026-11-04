"""The request: what a caller sends the solver for one solve of one unit's month.

It is the only input the solver takes. Everything is explicit (every rule, switch and weight;
no unit's numbers live in the code), days are ISO dates, and the month itself is given:
the server derives the day count, the first weekday and the Ramadan days from it. The
loader validates the request, maps dates to the 0-based indices of the internal
`Problem`, and returns the problem together with the solver settings. Only ValueError
leaves, prefixed `request: <field path>: ...`.

    {"version": 1, "month": "2026-03",
     "ramadan_days": {"from": "2026-02-18", "to": "2026-03-19"},      # optional, see below
     "public_holidays": ["2026-03-10"],
     "general": {... every GeneralRules field, "weights": {... every Weights field}},
     "department": {... every DepartmentRules field},
     "nurses": [{"id": "N01", "gender": "M", "team_leader": true, "score": 0.99,
                 "ramadan_reduced": false, "breastfeeding": false, "ytd_overtime": 100,
                 "hours_balance": 0, "night_balance": 0.0, "friday_balance": 0.0,
                 "leave": ["2026-03-04"], "undesired_days": [], "desired_days": [],
                 "pinned": {"2026-03-01": "D"}, "allowed_shifts": null,
                 "previous": ["D", "D", "", "N", "N", "N", "", "", "D", "D"],
                 "last_shift_kind": null, "rest_owed": 0}],
     "solver": {"time_limit_seconds": 20, "reproducible": false},
     "published": {"N01": {"2026-03-01": "D", "2026-03-02": "", ...}},   # optional
     "replan_from": "2026-03-12",                                      # optional
     "renamed_shifts": {"N": "Night"}}                                 # optional

`ramadan_days`: absent or null = derived from the Umm al-Qura calendar; [] = none; a list of
dates = exactly those; {"from", "to"} = the inclusive range (which may start or end outside
the month, as Ramadan straddles months) intersected with the month, for the dates fixed
after the moon sighting. A nurse's six lists may be absent (absent = none); her scalars are
required, among them the two memories the rules keep across any number of days, which a
result carries over so the history itself stays one month long: `last_shift_kind`, the kind
("night" / "day" for any other work / null when none is known) of the last shift she worked
before `previous` begins (the switch rule's memory; a kind, so it survives a renamed or
retired shift), and `rest_owed`, the off days still owed to her last night before `previous`
begins (the night-rest rule's memory, 0 when none). A name in `previous` the unit no longer
defines is accepted as work of no kind (neither night nor day; precheck says so);
`renamed_shifts` maps the old name of a renamed shift to its current one in every history.
`published` is the roster in force, in the shape the result's `roster` has, and
`replan_from` the first date to re-plan (earlier days are recorded facts); the first day
after the month marks the whole month as elapsed, for the month-end reconciliation that
turns the recorded facts into next month's carry-over.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

from .calendar import MonthInfo, parse_date, parse_month
from .problem import SCHEMA_VERSION, Problem, read_json

REQUEST_VERSION = 1
REPRODUCIBLE_WALL_FACTOR = 10    # reproducible: wall-clock guard = this x the deterministic budget.
                                 # CP-SAT's deterministic clock runs slower than the wall clock with
                                 # one worker (4-5 s per unit measured on a 10-nurse month), so the
                                 # guard must leave room for the budget to be what stops the search

_ROOT_REQUIRED = ("version", "month", "public_holidays", "general", "department", "nurses", "solver")
_ROOT_OPTIONAL = ("ramadan_days", "published", "replan_from", "renamed_shifts")
_NURSE_REQUIRED = ("id", "gender", "team_leader", "score", "ramadan_reduced", "breastfeeding",
                   "ytd_overtime", "hours_balance", "night_balance", "friday_balance",
                   "last_shift_kind", "rest_owed")
_KINDS = (None, "night", "day")
_NURSE_DATES = ("leave", "undesired_days", "desired_days")
_NURSE_OPTIONAL = _NURSE_DATES + ("pinned", "allowed_shifts", "previous")
_SOLVER_FIELDS = ("time_limit_seconds", "reproducible")
_DAY_REF = re.compile(r"\bday (\d+)\b")


@dataclass(frozen=True, slots=True)
class SolverSettings:
    time_limit_seconds: float
    reproducible: bool

    def solve_kwargs(self, workers: int) -> dict:
        """Arguments for `model.solve`. Reproducible: one worker, a fixed seed and a
        deterministic-time budget of `time_limit_seconds` units (CP-SAT's own clock, which
        runs slower than the wall clock), so the same request gives the same roster on any
        machine; the wall clock, at REPRODUCIBLE_WALL_FACTOR times the budget, then only
        stops a runaway search (the result's `solver.deterministic` says if it did)."""
        t = self.time_limit_seconds
        if self.reproducible:
            return dict(time_limit=REPRODUCIBLE_WALL_FACTOR * t, workers=1, seed=0, deterministic_time=t)
        return dict(time_limit=t, workers=workers, seed=0)


@dataclass(frozen=True, slots=True)
class Request:
    """Frozen, like its month and settings: what the result reports about the calendar, the
    cutoff and the solver settings is bound to what was loaded, and `build_result` checks it
    against the solution. The problem is a mutable object the solver snapshots on entry."""
    month: MonthInfo
    problem: Problem                 # calendar applied, published set, replan_from applied
    solver: SolverSettings
    replan_from: int | None          # 0-based cutoff (== days: all elapsed), None: all planned
    differ: int                      # recorded past cells that differ from the published plan


def read_request(path: str | Path) -> Request:
    return load_request(read_json(path, where="request"))


def load_request(raw: object) -> Request:
    if not isinstance(raw, dict):
        raise ValueError("request: must be a JSON object")
    _keys(raw, "request", _ROOT_REQUIRED, _ROOT_OPTIONAL)
    if raw["version"] is not REQUEST_VERSION and raw["version"] != REQUEST_VERSION or isinstance(raw["version"], bool):
        raise ValueError(f"request: version must be {REQUEST_VERSION}, got {raw['version']!r}")
    try:
        month = parse_month(raw["month"])
    except ValueError as e:
        raise ValueError(f"request: {e}") from None
    ramadan = _ramadan(month, raw.get("ramadan_days"))
    holidays = _dates(month, raw["public_holidays"], "request: public_holidays")
    shifts = _shift_names(raw["department"])
    renames = _renames(raw.get("renamed_shifts"), shifts)
    nurses, ids = [], []
    for i, nd in enumerate(_list(raw["nurses"], "request: nurses")):
        n = _nurse(month, nd, f"request: nurses[{i}]", shifts, renames)
        nurses.append(n)
        ids.append(n["id"])
    settings = _settings(raw["solver"])
    published = _published(month, raw.get("published"), ids, shifts) if "published" in raw else None
    replan = None
    if "replan_from" in raw and raw["replan_from"] is not None:
        replan = month.cutoff_index(raw["replan_from"], "request: replan_from")
        if published is None:
            raise ValueError("request: replan_from needs a published roster")
    d = {"version": SCHEMA_VERSION, "days": month.days, "first_weekday": month.first_weekday, "month": month.label,
         "nurses": nurses, "general": raw["general"], "department": raw["department"],
         "public_holidays": holidays, "ramadan_days": ramadan, "published": published, "planning_from": 0}
    try:
        p = Problem.from_dict(d, check_planning=replan is None)
        differ = p.replan_from(replan) if replan is not None else 0
    except ValueError as e:
        raise ValueError(_translate(str(e), month)) from None
    return Request(month, p, settings, replan, differ)


# ---- pieces ---------------------------------------------------------------------------------------
def _keys(raw: object, where: str, required: tuple, optional: tuple = ()) -> dict:
    if not isinstance(raw, dict):
        raise ValueError(f"{where}: expected an object, got {type(raw).__name__}")
    unknown = set(raw) - set(required) - set(optional)
    if unknown:
        raise ValueError(f"{where}: unknown field(s) {sorted(unknown)}")
    missing = [k for k in required if k not in raw]
    if missing:
        raise ValueError(f"{where}: missing field(s) {missing}")
    return raw


def _list(v: object, where: str) -> list:
    if not isinstance(v, list):
        raise ValueError(f"{where}: must be a list, got {type(v).__name__}")
    return v


def _dates(month: MonthInfo, v: object, where: str) -> list[int]:
    out = [month.index(x, f"{where}[{i}]") for i, x in enumerate(_list(v, where))]
    seen: set[int] = set()
    for d in out:
        if d in seen:
            raise ValueError(f"{where}: {month.iso(d)} is listed twice")
        seen.add(d)
    return out


def _ramadan(month: MonthInfo, v: object) -> list[int]:
    where = "request: ramadan_days"
    if v is None:
        return list(month.ramadan_days)
    if isinstance(v, dict):
        _keys(v, where, ("from", "to"))
        lo, hi = parse_date(v["from"], f"{where}.from"), parse_date(v["to"], f"{where}.to")
        if lo > hi:
            raise ValueError(f"{where}: from {v['from']} is after to {v['to']}")
        days = [d for d in range(month.days) if lo <= month.date(d) <= hi]
        if not days:
            raise ValueError(f"{where}: no day of {month.label} lies within {v['from']}..{v['to']}")
        return days
    return _dates(month, v, where)


def _shift_names(department: object) -> list[str] | None:
    """The unit's shift names when the department block names them properly, so a shift a
    nurse refers to can be checked here with its date; otherwise `Problem.check` reports."""
    if isinstance(department, dict) and isinstance(department.get("shifts"), list) \
            and all(isinstance(s, str) for s in department["shifts"]):
        return department["shifts"]
    return None


def _shift(v: object, where: str, shifts: list[str] | None, *, off_ok: bool) -> None:
    if not isinstance(v, str) or (shifts is not None and v != "" and v not in shifts) or (v == "" and not off_ok):
        raise ValueError(f"{where}: {v!r} is not a department shift")


def _renames(raw: object, shifts: list[str] | None) -> dict[str, str]:
    """`renamed_shifts`: {old name: current name}, applied to every history (`previous`)."""
    where = "request: renamed_shifts"
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"{where}: must be an object {{old name: current name}}")
    for old, new in raw.items():
        if not isinstance(old, str) or not old.strip():       # "" is an off day, never a shift
            raise ValueError(f"{where}: {old!r} is not a shift name")
        if not isinstance(new, str) or (shifts is not None and new not in shifts):
            raise ValueError(f"{where}[{old}]: {new!r} is not a department shift")
        if shifts is not None and old in shifts:
            raise ValueError(f"{where}: {old!r} is still a department shift")
    return dict(raw)


def _nurse(month: MonthInfo, nd: object, where: str, shifts: list[str] | None,
           renames: dict[str, str] = {}) -> dict:
    _keys(nd, where, _NURSE_REQUIRED, _NURSE_OPTIONAL)
    if not isinstance(nd["id"], str) or not nd["id"].strip():
        raise ValueError(f"{where}.id: must be a non-empty string, got {nd['id']!r}")
    n = {k: nd[k] for k in _NURSE_REQUIRED}
    for key, target in (("leave", "unavailable"), ("undesired_days", "undesired_days"),
                        ("desired_days", "desired_days")):
        if key in nd:
            n[target] = _dates(month, nd[key], f"{where}.{key}")
    both = set(n.get("undesired_days", ())) & set(n.get("desired_days", ()))
    if both:
        raise ValueError(f"{where}: {month.iso(min(both))} is both desired and undesired")
    if "pinned" in nd:
        pins = nd["pinned"]
        if not isinstance(pins, dict):
            raise ValueError(f"{where}.pinned: must be an object {{date: shift or \"\"}}")
        leave = set(n.get("unavailable", ()))
        n["pinned"] = {}
        for text, s in pins.items():
            d = month.index(text, f"{where}.pinned")
            _shift(s, f"{where}.pinned[{text}]", shifts, off_ok=True)
            if s and d in leave:
                raise ValueError(f"{where}.pinned[{text}]: on leave but pinned to {s!r}")
            n["pinned"][d] = s
    if "allowed_shifts" in nd:
        allowed = nd["allowed_shifts"]
        if allowed is not None:
            for i, s in enumerate(_list(allowed, f"{where}.allowed_shifts")):
                _shift(s, f"{where}.allowed_shifts[{i}]", shifts, off_ok=False)
        n["allowed_shifts"] = allowed
    if "previous" in nd:                                      # any shift name: one the unit no longer
        prev = []                                             # defines is work of no kind (precheck)
        for i, s in enumerate(_list(nd["previous"], f"{where}.previous")):
            if not isinstance(s, str) or (s != "" and not s.strip()):
                raise ValueError(f"{where}.previous[{i}]: {s!r} is not a shift name or \"\"")
            prev.append(renames.get(s, s) if s else s)        # an off day is never renamed
        n["previous"] = prev
    if nd["last_shift_kind"] not in _KINDS:
        raise ValueError(f"{where}.last_shift_kind: must be \"night\", \"day\" or null, got {nd['last_shift_kind']!r}")
    owed = nd["rest_owed"]
    if not isinstance(owed, int) or isinstance(owed, bool) or owed < 0:
        raise ValueError(f"{where}.rest_owed: must be a whole number of days, 0 or more, got {owed!r}")
    return n


def _settings(raw: object) -> SolverSettings:
    where = "request: solver"
    _keys(raw, where, _SOLVER_FIELDS)
    t = raw["time_limit_seconds"]
    if not isinstance(t, (int, float)) or isinstance(t, bool) or not math.isfinite(t) or t <= 0:
        raise ValueError(f"{where}.time_limit_seconds: must be a positive number of seconds, got {t!r}")
    if not isinstance(raw["reproducible"], bool):
        raise ValueError(f"{where}.reproducible: must be true or false, got {raw['reproducible']!r}")
    return SolverSettings(float(t), raw["reproducible"])


def _published(month: MonthInfo, raw: object, ids: list[str], shifts: list[str] | None) -> list[list[str]] | None:
    where = "request: published"
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"{where}: must be an object {{nurse id: {{date: shift or \"\"}}}}")
    unknown = set(raw) - set(ids)
    if unknown:
        raise ValueError(f"{where}: unknown nurse {sorted(unknown)[0]!r}")
    dates = month.dates()
    out = []
    for nid in ids:
        if nid not in raw:
            raise ValueError(f"{where}: no roster for nurse {nid!r}")
        row = raw[nid]
        if not isinstance(row, dict):
            raise ValueError(f"{where}[{nid}]: must be an object {{date: shift or \"\"}}")
        for text in row:
            month.index(text, f"{where}[{nid}]")
        missing = [t for t in dates if t not in row]
        if missing:
            raise ValueError(f"{where}[{nid}]: missing date {missing[0]}")
        cells = []
        for text in dates:
            _shift(row[text], f"{where}[{nid}][{text}]", shifts, off_ok=True)
            cells.append(row[text])
        out.append(cells)
    return out


def _translate(msg: str, month: MonthInfo) -> str:
    """A `Problem` error as a request error: its prefix, and any 0-based day it names."""
    if msg.startswith("problem: "):
        msg = msg[len("problem: "):]
    elif msg.startswith("problem "):
        msg = msg[len("problem "):]

    def to_date(m: re.Match) -> str:
        d = int(m.group(1))
        return month.iso(d) if 0 <= d < month.days else m.group(0)
    return "request: " + _DAY_REF.sub(to_date, msg)
