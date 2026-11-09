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
from requesting.models import Preference, PreferenceKind, PreferenceState
from rosters.drafts import current_codes, in_current_codes
from rosters.pins import month_pins
from units.models import Unit
from units.rules import unit_block


@dataclass
class Assembled:
    input: dict
    left_out: list[NurseProfile] = field(default_factory=list)
    to_check: list[NurseProfile] = field(default_factory=list)
    unreviewed_scores: int = 0
    leave_days: int = 0
    pins: int = 0
    outside_days: dict[str, list[str]] = field(default_factory=dict)
    # {hospital ID: making.chain.Carried}: what each nurse's month starts from, and where that comes from.
    carried: dict = field(default_factory=dict)

    @property
    def nurses(self) -> list[dict]:
        return self.input["nurses"]


def _days_of(month: dt.date) -> list[dt.date]:
    return [month.replace(day=day) for day in range(1, membership.last_day_of(month).day + 1)]


def _credited(nurse: NurseProfile, month: dt.date) -> tuple[list[str], int, list[str]]:
    """Her `leave`, in order and each once, with how many of those are recorded leave and which are outside her dates. A
    date recorded and since left outside them by a correction counts as outside, as the Leave page flags it."""
    outside = {day.isoformat() for day in _days_of(month) if membership.outside_dates(nurse, day)}
    recorded = set(leave_dates(nurse, month))
    return sorted(recorded | outside), len(recorded - outside), sorted(outside)


def _preferred(unit: Unit, month: dt.date) -> dict[str, dict[str, list[str]]]:
    """{hospital ID: {"undesired_days": [...], "desired_days": [...]}}, each list in date order and only when it has a day: the
    live preferences made in this unit's windows for the month (ADR 0013). One on a day she is on leave or outside her dates
    stays in, since the solver ignores a day it holds off. One a transfer left on another unit's record is that unit's, and
    she is not in its month, so it reaches no solve."""
    rows = (Preference.objects.filter(window__unit=unit, date__year=month.year, date__month=month.month,
                                      state=PreferenceState.MADE).order_by("date").values_list("nurse__user__username",
                                                                                               "kind", "date"))
    preferred: dict[str, dict[str, list[str]]] = {}
    for hospital_id, kind, day in rows:
        field = "undesired_days" if kind == PreferenceKind.DAY_OFF else "desired_days"
        preferred.setdefault(hospital_id, {}).setdefault(field, []).append(day.isoformat())
    return preferred


def assemble(unit: Unit, month: dt.date, *, time_limit: int = 1, chain=None, facts: bool = False) -> Assembled:
    """`time_limit` matters only to an input that will be sent. A pin joins its nurse's block only if it counts: leave wins
    over one, as the solver refuses a shift pinned on a leave date, and `rosters.pins` sets aside that pair and every other a
    row can come to hold, so that none reaches the solver as a failed solve. `facts` is a close's, of a month that is over
    (`rosters.pins.month_pins`).

    Each nurse starts from her carry-over (`closes.chain`): the latest closed month's, projected forward through the approved
    rosters in between, or her opening values. `chain` is the reading to share, a close's among them, which takes no projection.
    A history naming a shift since renamed is read under its code now (`renamed_shifts`)."""
    from closes.chain import CARRIED, Chain  # The chain assembles the months before, through this.

    chain = chain or Chain()
    pins = month_pins(unit, month, facts=facts)
    shift_hours = {shift.code: shift.hours for shift in Shift.objects.filter(active=True)}
    label = month.strftime("%Y-%m")
    assembled = Assembled(input={
        "version": 2,
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
    preferred = _preferred(unit, month)
    for nurse in nurses:
        if membership.no_longer_serving(nurse):
            assembled.left_out.append(nurse)
            continue
        placement = membership.placement_in(nurse, month)
        leave, recorded, outside = _credited(nurse, month)
        pinned = pins.counted.get(nurse.user.username)
        carried = assembled.carried[nurse.user.username] = chain.carry_in(nurse, month)
        values = carried.into(month)
        assembled.nurses.append(nurse_block(nurse, placement) | {key: values[key] for key in CARRIED} | {"leave": leave}
                                | preferred.get(nurse.user.username, {}) | ({"pinned": pinned} if pinned else {}))
        assembled.pins += len(pinned or ())
        assembled.leave_days += recorded
        if outside:
            assembled.outside_days[nurse.user.username] = outside
        assembled.unreviewed_scores += not nurse.attributes_saved
        if placement.allowed_shifts_to_check:
            assembled.to_check.append(nurse)
    renamed = _renamed_in_histories(assembled)
    if renamed:
        assembled.input["renamed_shifts"] = renamed
    return assembled


def _renamed_in_histories(assembled: Assembled) -> dict[str, str]:
    """A history keeps the codes it was worked out with. A code renamed since is mapped to the unit's shift it now is; one the unit
    does not work is work of no kind to the solver either way."""
    shifts = set(assembled.input["department"].get("shifts", []))
    codes = current_codes(code for row in assembled.nurses for code in row["previous"] if code)
    return {old: new for old, new in sorted(codes.items()) if old != new and new in shifts and old not in shifts}


def assemble_replan(unit: Unit, month: dt.date, replan_from: dt.date, in_force: dict[str, dict[str, str]], *,
                    time_limit: int = 1, chain=None, facts: bool = False) -> Assembled:
    """A re-plan's input: the month as `assemble` builds it, with the roster in force as `published` and the date to plan again
    from. The solver itself makes every earlier day a fact: a pin that counts, of any origin, wins; then leave and the days
    outside a nurse's dates, which it holds off; then the roster in force. A pin set aside reaches no solve, so its day is the
    roster in force's like any other. `published` holds exactly the month's nurses, as the solver asks: a nurse not on the roster
    in force (one who joined since) worked nothing, and a row of a nurse no longer in the month is left out, so the new version
    has none."""
    assembled = assemble(unit, month, time_limit=time_limit, chain=chain, facts=facts)
    in_force = in_current_codes(in_force)
    days = [day.isoformat() for day in _days_of(month)]
    assembled.input["published"] = {row["id"]: {day: in_force.get(row["id"], {}).get(day, "") for day in days}
                                     for row in assembled.nurses}
    assembled.input["replan_from"] = replan_from.isoformat()
    return assembled


def recorded_cells_differ(solve_input: dict) -> int | None:
    """How many days before the date the facts make different from the roster in force: leave since, a pin. None if the solver
    would refuse the input."""
    try:
        return load_request(solve_input).differ
    except ValueError:
        return None


def solver_refusal(solve_input: dict) -> str | None:
    """Why the solver would refuse this input, with no call to it: the same loader, in this image. A unit seeded with a gap
    and a one-shift unit after the CNO raised a weight end up here, as "review the unit rules" and not as a failed solve."""
    try:
        load_request(solve_input)
    except ValueError as e:
        return str(e)
    return None


def _pins_as_they_are_called_now(row: dict) -> dict[str, str]:
    """A rename is no change: a stored input keeps the code as it was."""
    pinned = row.get("pinned", {})
    codes = current_codes(code for code in pinned.values() if code)
    return {day: codes.get(code, code) for day, code in pinned.items()}


def changes_since(solve_input: dict, unit: Unit, month: dt.date, *, since: dt.datetime | None = None) -> list[dict]:
    """What has changed since this input was stored that the draft was not solved for: a gender, a nurse's credited days,
    who is in the month, the pins that count, or her preferences (an input stored before them had none). Start and end dates count through their credited days, so a correction
    that moves nothing in this month does not warn. Other attributes are outside what the user asked for here.

    With `since`, when the input was stored, also each nurse a month before whom has closed since (ticket 21): the input started
    from a projected carry-over, and the close worked out the real one. A re-plan's end does not ask this, so a close never makes
    a re-plan outdated (ADR 0009)."""
    solved = {row["id"]: row for row in solve_input["nurses"]}
    assembled = assemble(unit, month)
    now = {row["id"]: row for row in assembled.nurses}
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
            if _pins_as_they_are_called_now(before) != after.get("pinned", {}):
                changes.append({"hospital_id": hospital_id, "what": "pins"})
            if any(before.get(days, []) != after.get(days, []) for days in ("undesired_days", "desired_days")):
                changes.append({"hospital_id": hospital_id, "what": "preferences"})
            if since is not None and _closed_since(hospital_id, assembled.carried[hospital_id], since):
                changes.append({"hospital_id": hospital_id, "what": "closed"})
    return changes


def _closed_since(hospital_id: str, carried, since: dt.datetime) -> bool:
    """Whether a month her carry-over comes through has closed after `since`: the month before, or an earlier one projected
    forward from."""
    from closes.chain import CarrySource
    from closes.models import CarryOver

    if carried.source == CarrySource.OPENING:
        return False
    return CarryOver.objects.filter(source=CarrySource.CLOSED, month__lte=carried.out_of, close__closed_at__gt=since,
                                    nurse__user__username=hospital_id).exists()
