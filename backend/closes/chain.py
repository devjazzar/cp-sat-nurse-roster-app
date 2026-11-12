"""The carry-over chain (ADR 0004, docs/ARCHITECTURE.md section 5). A nurse's month starts from the carry-over of her latest closed
month, projected forward through each approved roster in between by the same computation a close makes: the solver package's
carry-over of a month with every day recorded, worked out with no search (`solver_service.grid`, ADR 0009). A month with no
approved roster carries what came into it on, with no shift history. A close takes no projection: its chain is closed months only.
The carry-over handed into January has overtime-to-date and both fairness balances reset to zero.

The nurse's unit is the one each month falls under for her (`membership.placement_in`), so a transferred nurse's carry-over follows
her into the new unit from the month the transfer takes effect."""
from __future__ import annotations

import bisect
import datetime as dt
import logging
from dataclasses import dataclass

from solver_service.grid import month_facts, nurses_of

from closes.models import CarryOver, CarrySource, MonthClose
from nurses import membership
from nurses.models import NurseProfile
from rosters.models import Roster, RosterState

logger = logging.getLogger(__name__)

# A solve input's nurse fields that one month hands to the next: a result's `carry_over` block, field for field.
# `preferences_not_kept` (ticket 28) is passed through as is: 0 until the app feeds preferences (tickets 29 and 30).
# `overtime_balance` (ticket 49) likewise: the solver hands it on unchanged until a unit shares its overtime (ticket 51); its opening
# value and its January reset are ticket 50's.
CARRIED = ("ytd_overtime", "hours_balance", "night_balance", "friday_balance", "previous", "last_shift_kind", "rest_owed",
           "preferences_not_kept", "overtime_balance")
NO_HISTORY = {"previous": [], "last_shift_kind": None, "rest_owed": 0, "preferences_not_kept": 0}
# The carried values added since the first closes: a close stored before the solver carried the count (ticket 28), or the overtime
# balance (ticket 49), has none, and hands on 0, as nothing was priced then.
CARRIED_SINCE = {"preferences_not_kept": 0, "overtime_balance": 0.0}
NEW_YEAR = {"ytd_overtime": 0, "night_balance": 0.0, "friday_balance": 0.0}


def next_month(month: dt.date) -> dt.date:
    return (month + dt.timedelta(days=32)).replace(day=1)


def month_before(month: dt.date) -> dt.date:
    return (month - dt.timedelta(days=1)).replace(day=1)


@dataclass(frozen=True)
class Carried:
    """What a month hands to the next: `values` in the solve input's field names, where they come from, the month they are
    carried out of (None for the opening values), and the year they are of."""
    values: dict
    source: CarrySource
    out_of: dt.date | None
    year: int

    def into(self, month: dt.date) -> dict:
        """The values as `month` starts from them: overtime-to-date and both fairness balances start again in a later year, the
        carry-over into January, from December or across months with no roster, and opening values entered the year before."""
        if month.year > self.year:
            return self.values | NEW_YEAR
        return dict(self.values)


def _added(nurse: NurseProfile) -> dt.date:
    """The month a nurse's opening values stand at: her first placement's, which is the month she was added, or her start's if
    that was earlier (`membership.place_new_nurse`)."""
    first = nurse.placements.order_by("from_month").first()
    return first.from_month if first else nurse.start_date.replace(day=1)


def opening(nurse: NurseProfile) -> dict:
    return {"ytd_overtime": nurse.ytd_overtime, "hours_balance": nurse.hours_balance, "night_balance": nurse.night_balance,
            "friday_balance": nurse.friday_balance, "overtime_balance": 0.0, **NO_HISTORY}


def closes_in_force(**filters) -> dict[tuple, MonthClose]:
    """The latest close of each unit's month: closing again replaces what the one before it said, without rewriting it."""
    found = {}
    for close in MonthClose.objects.filter(**filters).order_by("unit_id", "month", "-closed_at", "-id"):
        found.setdefault((close.unit_id, close.month), close)
    return found


def latest_closed(nurse: NurseProfile, before: dt.date) -> CarryOver | None:
    """Her carry-over out of the latest month before `before` closed with her in it, from that month's close in force."""
    rows = list(CarryOver.objects.filter(nurse=nurse, source=CarrySource.CLOSED, month__lt=before)
                .select_related("close").order_by("-month", "-close__closed_at"))
    if not rows:
        return None
    in_force ={close.pk for close in closes_in_force(unit_id__in={row.unit_id for row in rows},
                                                     month__in={row.month for row in rows}).values()}
    return next((row for row in rows if row.close_id in in_force), None)


def has_closed(nurse: NurseProfile) -> bool:
    """Whether any month of hers has closed, which locks her opening values."""
    return CarryOver.objects.filter(nurse=nurse, source=CarrySource.CLOSED).exists()


class Chain:
    """One reading of the chain, memoised by unit and month: an assembly asks it once for each of a month's nurses, and those of a
    unit share each month before. `project=False` is a close's: closed months only, never a projection."""

    def __init__(self, *, project: bool = True):
        self.project = project
        self._out: dict[tuple, dict[str, dict]] = {}
        self._rosters: dict[tuple, Roster | None] = {}
        self._months: list[dt.date] | None = None

    def carry_in(self, nurse: NurseProfile, month: dt.date) -> Carried:
        """What `month` starts from for her. Without a closed month, from her opening values at the first approved roster that
        holds her, or her start: the months before had no roster in this application to carry anything."""
        closed = latest_closed(nurse, month)
        if closed is not None:
            carried = Carried(CARRIED_SINCE | closed.values, CarrySource.CLOSED, closed.month, closed.month.year)
            step = next_month(closed.month)
        else:
            carried, step = Carried(opening(nurse), CarrySource.OPENING, None, _added(nurse).year), self._first_roster(nurse, month)
        while step is not None and step < month:
            ahead = self._next_roster_month(step, month)
            # A month with no approved roster of any unit hands on what came into it, with no shift history (`_through`), so a
            # run of them is one step, however long: the work does not grow with how far ahead `month` is.
            last = month_before(ahead or month)
            if step <= last:
                carried = Carried(carried.into(last) | NO_HISTORY, carried.source, last, last.year)
            if ahead is None:
                return carried
            carried = self._through(nurse, ahead, carried)
            step = next_month(ahead)
        return carried

    def _next_roster_month(self, step: dt.date, month: dt.date) -> dt.date | None:
        """The first month from `step`, and before `month`, with an approved roster of any unit. The months are read once for
        the chain; a close's chain (`project=False`) projects through none, so reads none."""
        if self._months is None:
            self._months = (sorted(set(Roster.objects.filter(state=RosterState.APPROVED).values_list("month", flat=True)))
                            if self.project else [])
        found = self._months[bisect.bisect_left(self._months, step):]
        return found[0] if found and found[0] < month else None

    def _first_roster(self, nurse: NurseProfile, month: dt.date) -> dt.date | None:
        if not self.project:
            return None
        return (Roster.objects.filter(state=RosterState.APPROVED, month__lt=month, month__gte=nurse.start_date.replace(day=1),
                                       grid__has_key=nurse.user.username).order_by("month").values_list("month", flat=True).first())

    def _approved(self, unit_id, month: dt.date) -> Roster | None:
        key = (unit_id, month)
        if key not in self._rosters:
            self._rosters[key] = (Roster.objects.filter(unit_id=unit_id, month=month, state=RosterState.APPROVED)
                                  .select_related("unit").first())
        return self._rosters[key]

    def _through(self, nurse: NurseProfile, month: dt.date, carried: Carried) -> Carried:
        """What `month` hands on: its projection when it has an approved roster holding her, else what came into it, with no shift
        history, since no roster says what she worked."""
        into = carried.into(month)
        placement = membership.placement_in(nurse, month)
        roster = self._approved(placement.unit_id, month) if placement and self.project else None
        out = self.carry_out(roster).get(nurse.user.username) if roster else None
        if out is None:
            return Carried(into | NO_HISTORY, carried.source, month, month.year)
        return Carried({key: out[key] for key in CARRIED}, CarrySource.PROJECTED, month, month.year)

    def carry_out(self, roster: Roster) -> dict[str, dict]:
        """Each nurse's carry-over out of an approved roster's month, projected from its roster in force as a close would work it
        out. Empty when the solver's code cannot read the month, as a close would be refused: her chain then carries on as through
        a month with no roster."""
        from closes.making import close_input  # It assembles a month, which reads this chain.

        key = (roster.unit_id, roster.month)
        if key not in self._out:
            try:
                solve_input = close_input(roster.unit, roster.month, roster.grid, chain=self).input
                self._out[key] = {hospital_id: row["carry_over"]
                                  for hospital_id, row in nurses_of(solve_input, month_facts(solve_input)).items()}
            except ValueError as e:
                logger.warning("carry-over of %s, %s cannot be projected: %s", roster.unit.name, f"{roster.month:%Y-%m}", e)
                self._out[key] = {}
        return self._out[key]

