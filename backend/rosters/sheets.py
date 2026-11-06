"""A roster version as a table: one row a nurse by name, one column a date, then the hours of its shifts and a count of each shift.
The CSV, the Excel workbook and the print page are all this one table (`rosters.exports_api`, and a nurse's own in
`rosters.reading_api`).

A table leaves the system on paper or as a file, so it holds what a colleague may read and no more: a cell is the version's shift
or nothing, and a day of leave or outside a nurse's dates is nothing, like any day off. Its hours are therefore worked out from
the cells alone: what a month owes a nurse, or their overtime, would say how much leave they had."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Literal

from django.utils import timezone
from ninja import Field, Schema

from hospital.models import HospitalSettings, PublicHoliday, Shift
from nurses import membership
from rosters.drafts import current_codes, in_current_codes
from rosters.grids import GridDay, by_name, full_names
from rosters.models import RosterVersion


def days_of(month: dt.date) -> list[GridDay]:
    """Every date of the month, with the hospital's weekend and public holidays as they stand."""
    weekend = HospitalSettings.load().rules["weekend_weekdays"]
    holidays = set(PublicHoliday.objects.filter(date__year=month.year, date__month=month.month).values_list("date", flat=True))
    last = membership.last_day_of(month).day
    return [GridDay(date=day, weekend=day.weekday() in weekend, holiday=day in holidays)
            for day in (month.replace(day=number) for number in range(1, last + 1))]


class MyDay(Schema):
    date: dt.date
    kind: Literal["shift", "off", "leave", "outside"] = Field(
        description="The reader's own day. `outside` is before their start date or after their end date.")


@dataclass(frozen=True)
class SheetShift:
    code: str
    display_name: str
    hours: int

    @property
    def heading(self) -> str:
        return f"{self.display_name} ({self.code})"


@dataclass(frozen=True)
class SheetRow:
    hospital_id: str
    full_name: str
    shifts: list[str]
    hours: int
    counts: list[int]


@dataclass(frozen=True)
class Sheet:
    version: RosterVersion
    days: list[GridDay]
    shifts: list[SheetShift]
    rows: list[SheetRow]

    def table(self) -> list[list[str | int | dt.date]]:
        """The header, then a row a nurse, with each cell its own type: a date heading is a date, and the hours and counts are
        numbers, so a workbook reads them as such."""
        header = ["Hospital ID", "Full name", *(day.date for day in self.days), "Shift hours",
                  *(shift.heading for shift in self.shifts)]
        return [header, *([row.hospital_id, row.full_name, *row.shifts, row.hours, *row.counts] for row in self.rows)]


def _hours_by_code(version: RosterVersion) -> dict[str, int]:
    """A shift's hours as the solve behind this version was given them: its own, or for a hand edit the one of the version it was
    made on. A shift's hours cannot change while a month not over uses it, so these are the month's; a code that solve was not
    given, added by hand since, takes the catalogue's."""
    earlier = version.roster.versions.filter(number__lt=version.number, solve__isnull=False).select_related("solve").first()
    # Version 1 always has one, the approval's; the roster's own is the last resort should that ever not hold.
    solve = version.solve or (earlier.solve if earlier else version.roster.solve)
    given = solve.input["general"]["shift_hours"]
    renamed = current_codes(given)
    return {renamed[code]: hours for code, hours in given.items()}


def sheet_of(version: RosterVersion) -> Sheet:
    grid = in_current_codes(version.grid)
    days = days_of(version.roster.month)
    used = {code for row in grid.values() for code in row.values() if code}
    given = _hours_by_code(version)
    shifts = [SheetShift(code=shift.code, display_name=shift.display_name, hours=given.get(shift.code, shift.hours))
              for shift in Shift.objects.filter(code__in=used)]
    hours = {shift.code: shift.hours for shift in shifts}
    names = full_names(grid)
    rows = []
    for hospital_id in by_name(grid, names):
        cells = [grid[hospital_id].get(day.date.isoformat(), "") for day in days]
        rows.append(SheetRow(hospital_id=hospital_id, full_name=names.get(hospital_id, ""), shifts=cells,
                             hours=sum(hours[code] for code in cells if code),
                             counts=[cells.count(shift.code) for shift in shifts]))
    return Sheet(version=version, days=days, shifts=shifts, rows=rows)


class SheetShiftOut(Schema):
    code: str
    display_name: str
    hours: int = Field(description="As the solve behind the version was given them.")


class SheetRowOut(Schema):
    hospital_id: str
    full_name: str
    shifts: list[str] = Field(description="One for each of `days`: the shift's code, or empty for a day not worked, leave included.")
    hours: int = Field(description="Hours of the shifts on this row.")
    counts: list[int] = Field(description="How many of each of `shifts` this row works, in that order.")


class RosterSheet(Schema):
    """A version as its print page shows it, and as its files hold it."""
    unit: str
    month: str
    version: int
    in_force: int = Field(description="The number of the version in force, which is `version` unless a later one replaced it.")
    made_at: dt.datetime
    days: list[GridDay]
    shifts: list[SheetShiftOut]
    rows: list[SheetRowOut] = Field(description="Everyone on the version, by name.")
    mine: list[MyDay] | None = Field(None, description="On a nurse's own sheet, their own row, one for each of `days`, which "
                                                       "may say leave. Null on anyone else's sheet, and when they are not on it.")


def as_schema(sheet: Sheet, *, mine: list[MyDay] | None = None) -> RosterSheet:
    version = sheet.version
    roster = version.roster
    return RosterSheet(
        unit=roster.unit.name, month=roster.month.strftime("%Y-%m"), version=version.number,
        in_force=roster.versions.first().number, made_at=timezone.localtime(version.created_at), days=sheet.days,
        shifts=[SheetShiftOut(code=shift.code, display_name=shift.display_name, hours=shift.hours) for shift in sheet.shifts],
        rows=[SheetRowOut(hospital_id=row.hospital_id, full_name=row.full_name, shifts=row.shifts, hours=row.hours,
                          counts=row.counts) for row in sheet.rows],
        mine=mine)
