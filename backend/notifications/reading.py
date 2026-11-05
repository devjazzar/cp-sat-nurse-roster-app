"""A notification's words and where it leads, worked out as it is read from the identifiers it keeps, so they follow a rename and
a corrected name. They say only what the reader could read on the page it leads to, and nothing about any nurse: no leave, no
comment, no colleague. The link is the reader's own page for that month, by their role and what they hold now."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from uuid import UUID

from accounts.models import Role, User
from notifications.models import Event, Notification
from units.models import Unit


@dataclass(frozen=True)
class Link:
    page: str
    month: str
    unit_id: UUID | None = None


class _Names:
    """The units and users a page of notifications names, read in two queries."""

    def __init__(self, notes: list[Notification]):
        unit_ids = {note.payload.get("unit_id") for note in notes} - {None}
        user_ids = {note.payload.get("by") for note in notes} - {None}
        self.units = {str(unit.pk): unit for unit in Unit.objects.filter(pk__in=unit_ids)}
        self.users = {str(user.pk): user.full_name or user.username for user in User.objects.filter(pk__in=user_ids)}


def _month_name(month: str) -> str:
    return dt.date.fromisoformat(f"{month}-01").strftime("%B %Y")


def _solve_words(payload: dict, roster: str) -> str:
    match payload.get("outcome"):
        case "draft":
            return f"The solve of the {roster} has finished, and its roster is now the draft."
        case "stopped_draft":
            return f"The solve of the {roster} was stopped, and the best roster it found is now the draft."
        case "frozen":
            return f"The solve of the {roster} has ended. The roster had been submitted meanwhile, so it stays as it was."
        case "failed":
            return f"The solve of the {roster} failed. Its result says why."
        case _:
            return f"The solve of the {roster} has ended with no roster to keep. Its result says why."


def text_of(note: Notification, names: _Names) -> str:
    payload = note.payload
    unit = names.units.get(payload.get("unit_id"))
    roster = f"{unit.name if unit else 'a unit'} roster for {_month_name(payload['month'])}"
    by = names.users.get(payload.get("by"), "Someone")
    match note.event:
        case Event.ROSTER_SUBMITTED:
            return f"{by} submitted the {roster}."
        case Event.ROSTER_APPROVED:
            return f"{by} approved the {roster}. Version {payload['version']} is in force."
        case Event.ROSTER_REJECTED:
            return f"{by} rejected the {roster}. The comment is with the draft."
        case Event.SOLVE_ENDED:
            return _solve_words(payload, roster)
    return "Something has changed."


def link_of(note: Notification, reader: User, names: _Names) -> Link | None:
    payload = note.payload
    unit = names.units.get(payload.get("unit_id"))
    if unit is None:
        return None
    month = payload["month"]
    if reader.role in (Role.CNO, Role.DEPUTY_CNO):
        return Link("unit_roster", month, unit.pk)
    if reader.role == Role.UNIT_MANAGER and unit.manager_id == reader.pk:
        return Link("roster", month)
    if note.event == Event.ROSTER_APPROVED and reader.role in (Role.STAFF_NURSE, Role.UNIT_MANAGER):
        return Link("my_roster", month)
    return None  # A manager who has since lost the unit: its pages are no longer theirs.


def names_for(notes: list[Notification]) -> _Names:
    return _Names(notes)
