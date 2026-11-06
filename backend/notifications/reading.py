"""A notification's words and where it leads, worked out as it is read from the identifiers it keeps, so they follow a rename and
a corrected name. They say only what the reader could read on the page it leads to, and nothing about any nurse: no leave, no
comment, no colleague. The link is the reader's own page for that month, by their role and what they hold now."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from accounts.models import Role, User
from notifications.models import Event, Notification, SolveOutcome
from requesting.models import Request, RequestState, RequestWindow, Step
from rosters.pins import long_date
from units.models import Unit

WINDOW_EVENTS = (Event.WINDOW_OPENED, Event.WINDOW_CLOSED_EARLY, Event.REQUEST_DECIDED)


@dataclass(frozen=True)
class Link:
    page: Literal["roster", "my_roster", "unit_roster", "my_month", "requests"]
    month: str
    unit_id: UUID | None = None


class Names:
    """The units and users a page of notifications names, read in two queries."""

    def __init__(self, notes: list[Notification]):
        unit_ids = {note.payload.get("unit_id") for note in notes} - {None}
        user_ids = {note.payload.get("by") for note in notes} - {None}
        self.units = {str(unit.pk): unit for unit in Unit.objects.filter(pk__in=unit_ids)}
        self.users = {str(user.pk): user.full_name or user.username for user in User.objects.filter(pk__in=user_ids)}
        window_ids = {note.payload.get("window_id") for note in notes} - {None}
        request_ids = {note.payload.get("request_id") for note in notes} - {None}
        self.windows = {str(window.pk): window for window in RequestWindow.objects.filter(pk__in=window_ids)}
        self.requests = {str(row.pk): row for row in Request.objects.filter(pk__in=request_ids).select_related("shift")}


def _month_name(month: str) -> str:
    return dt.date.fromisoformat(f"{month}-01").strftime("%B %Y")


def _replan_words(payload: dict, roster: str) -> str:
    stays = "so the roster in force stays as it was."
    match payload.get("outcome"):
        case SolveOutcome.REPLANNED:
            return (f"The re-plan of the {roster} has finished, and its roster is now in force as a new version. The unit's "
                    "nurses are told the roster has changed.")
        case SolveOutcome.STOPPED_REPLANNED:
            return (f"The re-plan of the {roster} was stopped, and the best roster it found is now in force as a new version. "
                    "The unit's nurses are told the roster has changed.")
        case SolveOutcome.REPLAN_UNCHANGED:
            return f"The re-plan of the {roster} has finished without changing a cell, {stays}"
        case SolveOutcome.REPLAN_OUTDATED:
            return (f"The re-plan of the {roster} has ended, but the roster in force or the month changed while it ran, so it "
                    "stays as it was. Re-plan again to take that in.")
        case SolveOutcome.REPLAN_MONTH_OVER:
            return f"The re-plan of the {roster} has ended after the month did, {stays}"
        case SolveOutcome.FAILED:
            return f"The re-plan of the {roster} failed, {stays} Its result says why."
        case SolveOutcome.NO_ROSTER:
            return f"The re-plan of the {roster} has ended with no roster to keep, {stays} Its result says why."
    return f"The re-plan of the {roster} has ended."


def _solve_words(payload: dict, roster: str) -> str:
    if payload.get("replan"):
        return _replan_words(payload, roster)
    match payload.get("outcome"):
        case SolveOutcome.DRAFT:
            return f"The solve of the {roster} has finished, and its roster is now the draft."
        case SolveOutcome.STOPPED_DRAFT:
            return f"The solve of the {roster} was stopped, and the best roster it found is now the draft."
        case SolveOutcome.FROZEN:
            return f"The solve of the {roster} has ended. The roster had been submitted or approved meanwhile, so it stays as it was."
        case SolveOutcome.FAILED:
            return f"The solve of the {roster} failed. Its result says why."
        case SolveOutcome.NO_ROSTER:
            return f"The solve of the {roster} has ended with no roster to keep. Its result says why."
    return f"The solve of the {roster} has ended."


def _window_words(note: Notification, names: Names, roster: str, by: str) -> str:
    window = names.windows.get(note.payload.get("window_id"))
    match note.event:
        case Event.WINDOW_OPENED:
            until = f", until {long_date(window.closes_on)}" if window else ""
            return f"{by} opened requests for the {roster}{until}."
        case Event.WINDOW_CLOSED_EARLY:
            return (f"{by} closed the request window for the {roster} early. Any request you made in it waits for a "
                    "decision.")
    waiting = window.requests.filter(state=RequestState.PENDING).count() if window else 0
    if waiting == 0:
        return f"The request window for the {roster} has closed. Every request made in it has been decided."
    many = f"{waiting} requests wait" if waiting > 1 else "1 request waits"
    return f"The request window for the {roster} has closed, and {many} for your decision."


def _decision_words(note: Notification, names: Names, by: str) -> str:
    """Only the nurse who made the request is told, so it may say what she asked for, read from the request now. Never a
    reason: those are on her page."""
    row = names.requests.get(note.payload.get("request_id"))
    if row is None:
        return "One of your requests has moved."
    what = f"{row.shift.display_name} ({row.shift.code})" if row.shift else "a day off"
    on = long_date(row.date)
    match note.payload.get("step"):
        case Step.ACCEPTED:
            return f"{by} accepted your request for {what} on {on}."
        case Step.REJECTED:
            return f"{by} rejected your request for {what} on {on}. The reason is on My month."
        case Step.EDITED:
            return f"{by} changed what your accepted request on {on} promises. My month says what it is now."
        case Step.CANCELLED:
            return f"{by} cancelled your accepted request for {what} on {on}. The reason is on My month."
        case Step.REPLACED_BY_LEAVE:
            return f"Leave recorded on {on} replaced your accepted request for {what}, as leave wins."
    return f"Your request for {what} on {on} has moved."


def text_of(note: Notification, names: Names) -> str:
    payload = note.payload
    unit = names.units.get(payload.get("unit_id"))
    roster = f"{unit.name if unit else 'a unit'} roster for {_month_name(payload['month'])}"
    by = names.users.get(payload.get("by"), "Someone")
    match note.event:
        case Event.ROSTER_SUBMITTED:
            return f"{by} submitted the {roster}."
        case Event.ROSTER_APPROVED:
            return f"{by} approved the {roster}."
        case Event.ROSTER_CHANGED:
            return f"{by} changed the {roster}."
        case Event.ROSTER_REJECTED:
            return f"{by} rejected the {roster}. The comment is with the draft."
        case Event.SOLVE_ENDED:
            return _solve_words(payload, roster)
        case Event.WINDOW_OPENED | Event.WINDOW_CLOSED_EARLY | Event.WINDOW_CLOSED:
            return _window_words(note, names, roster, by)
        case Event.REQUEST_DECIDED:
            return _decision_words(note, names, by)
    return "Something has changed."


def link_of(note: Notification, reader: User, names: Names) -> Link | None:
    payload = note.payload
    unit = names.units.get(payload.get("unit_id"))
    if unit is None:
        return None
    month = payload["month"]
    if note.event in WINDOW_EVENTS:
        return Link("my_month", month) if reader.role == Role.STAFF_NURSE else None
    if note.event == Event.WINDOW_CLOSED:
        return Link("requests", month) if unit.manager_id == reader.pk else None
    if reader.role in (Role.CNO, Role.DEPUTY_CNO):
        return Link("unit_roster", month, unit.pk)
    if reader.role == Role.UNIT_MANAGER and unit.manager_id == reader.pk:
        return Link("roster", month)
    if note.event in (Event.ROSTER_APPROVED, Event.ROSTER_CHANGED) and reader.role in (Role.STAFF_NURSE, Role.UNIT_MANAGER):
        return Link("my_roster", month)
    return None  # A manager who has since lost the unit: its pages are no longer theirs.
