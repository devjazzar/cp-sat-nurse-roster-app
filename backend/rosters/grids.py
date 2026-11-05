"""A grid as a page shows it, whether it is the draft's or one a stored result holds."""
from __future__ import annotations

import datetime as dt
from typing import Iterable, Literal

from ninja import Field, Schema

from accounts.models import User
from hospital.models import Shift
from rosters.drafts import current_codes
from solves.models import Solve


class GridShift(Schema):
    code: str
    display_name: str
    colour: str
    hours: int = Field(description="As the solve that made this grid was given them.")


class GridDay(Schema):
    date: dt.date
    weekend: bool
    holiday: bool


class GridCell(Schema):
    shift: str = Field(description="The shift's code. Empty for a day not worked.")
    kind: Literal["shift", "off", "leave", "outside"] = Field(
        description="`outside` is before a start date or after an end date, credited like leave.")


class GridRow(Schema):
    hospital_id: str
    full_name: str
    cells: list[GridCell]


class GridView(Schema):
    days: list[GridDay]
    rows: list[GridRow]
    shifts: list[GridShift]


def full_names(hospital_ids: Iterable[str]) -> dict[str, str]:
    return dict(User.objects.filter(username__in=list(hospital_ids)).values_list("username", "full_name"))


def by_name(hospital_ids: Iterable[str], names: dict[str, str]) -> list[str]:
    return sorted(hospital_ids, key=lambda hospital_id: (names.get(hospital_id, "").lower(), hospital_id))


def grid_view(grid: dict[str, dict[str, str]], solve: Solve) -> GridView:
    """`grid` with the codes in use now, and each cell as it was when `solve` was given it: what has changed since is
    `solves.input.changes_since`."""
    general = solve.input["general"]
    days = sorted({day for row in grid.values() for day in row})
    holidays = set(solve.input["public_holidays"])
    credited = {row["id"]: set(row.get("leave", [])) for row in solve.input["nurses"]}
    names = full_names(grid)

    def cell(hospital_id: str, day: str, code: str) -> GridCell:
        if code:
            return GridCell(shift=code, kind="shift")
        if day in solve.outside_days.get(hospital_id, ()):
            return GridCell(shift="", kind="outside")
        return GridCell(shift="", kind="leave" if day in credited.get(hospital_id, ()) else "off")

    used = {code for row in grid.values() for code in row.values() if code}
    renamed = current_codes(general["shift_hours"])
    hours_then = {renamed[code]: hours for code, hours in general["shift_hours"].items()}
    return GridView(
        days=[GridDay(date=day, weekend=dt.date.fromisoformat(day).weekday() in general["weekend_weekdays"],
                      holiday=day in holidays) for day in days],
        rows=[GridRow(hospital_id=hospital_id, full_name=names.get(hospital_id, ""),
                      cells=[cell(hospital_id, day, grid[hospital_id][day]) for day in days])
              for hospital_id in by_name(grid, names)],
        shifts=[GridShift(code=shift.code, display_name=shift.display_name, colour=shift.colour,
                          hours=hours_then.get(shift.code, shift.hours))
                for shift in Shift.objects.filter(code__in=used)])
