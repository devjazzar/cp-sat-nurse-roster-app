"""Rosters read across units, and the roster a nurse reads. The CNO and the Deputy CNO see every unit's state per month and the
rosters waiting for them. A nurse sees the approved roster of the unit their month falls under, with colleagues' names and
shifts only: nothing here for anyone but the reader comes from `Leave`, a result's `nurses`, or a stored input's `nurses`, so a
colleague's day of leave is the same `""` as any day off. Their own row may say leave."""
from __future__ import annotations

import datetime as dt
from typing import Literal
from uuid import UUID

from django.db.models import Q
from django.http import HttpRequest
from django.utils import timezone
from ninja import Field, Query, Router, Schema

from accounts.authz import SignedIn
from accounts.models import Role
from hospital.models import HospitalSettings, PublicHoliday, Shift
from nurses import membership
from nurses.api import MonthText
from nurses.models import Leave, NurseProfile
from rosters import review
from rosters.drafts import in_current_codes
from rosters.grids import GridDay, by_name, full_names
from rosters.models import Roster, RosterState
from solves.api import chosen_month
from solves.input import changes_since
from units.models import Unit

router = Router(tags=["rosters"])
approver = SignedIn(Role.CNO, Role.DEPUTY_CNO)
OVERVIEW_MONTHS = 4

State = Literal["none", "draft", "submitted", "approved"]


class OverviewFilter(Schema):
    month: MonthText | None = Field(None, description="YYYY-MM, the first month shown. The hospital's current one when left out.")


class OverviewUnit(Schema):
    id: UUID
    name: str
    archived: bool
    states: list[State] = Field(description="One for each of `months`, in order.")


class Overview(Schema):
    months: list[str]
    units: list[OverviewUnit] = Field(description="Every unit not archived, and an archived one with a roster in these months.")


def _months_from(first: dt.date, count: int) -> list[dt.date]:
    months = [first]
    for _ in range(count - 1):
        months.append((months[-1] + dt.timedelta(days=32)).replace(day=1))
    return months


@router.get("/overview", response=Overview, auth=approver, operation_id="getRosterOverview")
def overview(request: HttpRequest, filters: Query[OverviewFilter]) -> Overview:
    first = dt.date.fromisoformat(f"{filters.month}-01") if filters.month else membership.this_month()
    months = _months_from(first, OVERVIEW_MONTHS)
    states = {(unit_id, month): state for unit_id, month, state in
              Roster.objects.filter(month__in=months).values_list("unit_id", "month", "state")}
    with_rosters = {unit_id for unit_id, _ in states}
    units = Unit.objects.filter(Q(archived=False) | Q(pk__in=with_rosters))
    return Overview(months=[month.strftime("%Y-%m") for month in months], units=[
        OverviewUnit(id=unit.pk, name=unit.name, archived=unit.archived,
                     states=[states.get((unit.pk, month), "none") for month in months]) for unit in units])


class WaitingRoster(Schema):
    unit_id: UUID
    unit: str
    month: str
    submitted_by: str
    submitted_at: dt.datetime
    changed_since: bool = Field(description="Whether something has changed since it was submitted that its manager was not "
                                            "warned of, such as leave recorded while it waits.")


@router.get("/submitted", response=list[WaitingRoster], auth=approver, operation_id="listSubmittedRosters")
def submitted(request: HttpRequest) -> list[WaitingRoster]:
    """Oldest first, as they have waited longest."""
    rosters = Roster.objects.filter(state=RosterState.SUBMITTED).select_related("unit", "solve")
    rows = []
    for roster in rosters:
        waiting = review.waiting(roster)
        seen = {(change["hospital_id"], change["what"]) for change in waiting.changes_at_submit}
        now = {(change["hospital_id"], change["what"]) for change in changes_since(roster.solve.input, roster.unit, roster.month)}
        rows.append(WaitingRoster(unit_id=roster.unit_id, unit=roster.unit.name, month=roster.month.strftime("%Y-%m"),
                                  submitted_by=review.name_of(waiting.submitted_by),
                                  submitted_at=timezone.localtime(waiting.submitted_at), changed_since=bool(now - seen)))
    return sorted(rows, key=lambda row: row.submitted_at)


class NurseShift(Schema):
    code: str
    display_name: str
    colour: str


class ColleagueRow(Schema):
    """A name and a shift a day, and nothing else: a day of leave and a day off are both `""`."""
    hospital_id: str
    full_name: str
    shifts: list[str] = Field(description="One for each of `days`: the shift's code, or empty for a day not worked.")


class MyDay(Schema):
    date: dt.date
    kind: Literal["shift", "off", "leave", "outside"] = Field(
        description="The reader's own day. `outside` is before their start date or after their end date.")


class NurseRoster(Schema):
    approved_at: dt.datetime
    version: int
    days: list[GridDay]
    shifts: list[NurseShift]
    rows: list[ColleagueRow] = Field(description="Everyone on the roster, the reader too, by name.")
    mine: list[MyDay] | None = Field(description="The reader's own row, one for each of `days`. Null when they are not on it.")


class MyRosterMonth(Schema):
    month: str
    first_month: str = Field(description="The earliest month shown here: this one. Earlier months are not.")
    unit: str | None = Field(description="The unit this month falls under for the reader. Null with no nurse profile, or before "
                                         "their first placement.")
    roster: NurseRoster | None = Field(description="Null until that unit's roster of the month is approved, and for a month "
                                                   "before `first_month`.")


def _days(month: dt.date) -> list[GridDay]:
    weekend = HospitalSettings.load().rules["weekend_weekdays"]
    holidays = set(PublicHoliday.objects.filter(date__year=month.year, date__month=month.month).values_list("date", flat=True))
    last = membership.last_day_of(month).day
    return [GridDay(date=day, weekend=day.weekday() in weekend, holiday=day in holidays)
            for day in (month.replace(day=number) for number in range(1, last + 1))]


def _mine(nurse: NurseProfile, row: dict[str, str], days: list[GridDay]) -> list[MyDay]:
    leave = set(Leave.objects.current().filter(nurse=nurse, date__range=(days[0].date, days[-1].date))
                .values_list("date", flat=True))

    def kind(day: dt.date) -> str:
        if row.get(day.isoformat()):
            return "shift"
        if membership.outside_dates(nurse, day):
            return "outside"
        return "leave" if day in leave else "off"
    return [MyDay(date=day.date, kind=kind(day.date)) for day in days]


@router.get("/mine", response=MyRosterMonth, auth=SignedIn(Role.STAFF_NURSE, Role.UNIT_MANAGER), operation_id="getMyRoster")
def my_roster(request: HttpRequest, filters: Query[OverviewFilter]) -> MyRosterMonth:
    """Takes no nurse, so it answers only for the reader. A manager with a nurse profile is a nurse too. The unit is the one
    the month falls under for them, so across a transfer each month shows its own unit's roster, and a nurse due to start sees
    their unit's with no row of their own."""
    month = chosen_month(filters.month) if filters.month else membership.this_month()
    first = membership.this_month()
    nurse = NurseProfile.objects.filter(user=request.user).first()
    placement = membership.placement_in(nurse, month) if nurse else None
    answer = MyRosterMonth(month=month.strftime("%Y-%m"), first_month=first.strftime("%Y-%m"),
                           unit=placement.unit.name if placement else None, roster=None)
    if placement is None or month < first:
        return answer
    roster = Roster.objects.filter(unit=placement.unit, month=month, state=RosterState.APPROVED).first()
    if roster is None:
        return answer
    version = roster.versions.first()  # The latest, by `RosterVersion.Meta.ordering`: the one in force.
    grid = in_current_codes(version.grid)
    days = _days(month)
    names = full_names(grid)
    used = {code for row in grid.values() for code in row.values() if code}
    mine = nurse.user.username
    answer.roster = NurseRoster(
        approved_at=timezone.localtime(review.approval(roster).decided_at), version=version.number, days=days,
        shifts=[NurseShift(code=shift.code, display_name=shift.display_name, colour=shift.colour)
                for shift in Shift.objects.filter(code__in=used)],
        rows=[ColleagueRow(hospital_id=hospital_id, full_name=names.get(hospital_id, ""),
                           shifts=[grid[hospital_id].get(day.date.isoformat(), "") for day in days])
              for hospital_id in by_name(grid, names)],
        mine=_mine(nurse, grid[mine], days) if mine in grid else None)
    return answer
