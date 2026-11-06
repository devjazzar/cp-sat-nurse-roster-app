"""The unit manager's decisions on a request: accept, reject, edit and cancel an accepted one, and leave replacing one. An accepted
request is a pinned cell of origin `request` (ADR 0005), refused where a pin would be, in the same words (`rosters.pins.Judge`),
and put on the roster as a pin is: on a draft's cell at once, since a draft never disagrees with a pin, and on an approved roster
of a month not over as a new version with origin `request`, when it changes a cell. A submitted roster is frozen, so a decision
that would move a pin waits for its decision. Call each inside a transaction under `locked_for_decision`."""
from __future__ import annotations

import copy
import datetime as dt
from dataclasses import dataclass
from typing import Iterable

from django.http import Http404
from ninja.errors import HttpError

from accounts.models import User
from audit.log import record
from hospital.models import HospitalSettings, Shift
from notifications import sending
from nurses import membership
from nurses.models import NurseProfile
from requesting.models import Request, RequestState, RequestStep, Step
from rosters.drafts import FROZEN, current_code
from rosters.models import PinEnded, PinnedCell, PinOrigin, Roster, RosterState, RosterVersion, VersionOrigin
from rosters.pins import Judge, end, long_date, pin_cell
from rosters.versions import make_version
from units.models import Unit
from units.scope import unit_in_scope

MONTH_OVER = "This month is over, so its pins cannot change."


@dataclass
class Locked:
    unit: Unit
    nurse: NurseProfile
    request: Request
    roster: Roster | None

    @property
    def month(self) -> dt.date:
        return self.request.window.month

    @property
    def name(self) -> str:
        return self.nurse.user.full_name or self.nurse.user.username


def locked_for_decision(user: User, unit_id, request_id) -> Locked:
    """The locks a save of pins takes, in its order (`rosters.api._locked_for_edits`): the catalogue's, the nurse's `FOR NO KEY
    UPDATE` (which a leave write holds), the unit's and the month's roster, then the request's, so two clicks on Accept cannot
    both find it pending. The same 404 for another unit's request as for none."""
    HospitalSettings.load(for_update=True)
    found = Request.objects.filter(pk=request_id).values_list("nurse_id", flat=True).first()
    if found is not None:
        list(NurseProfile.objects.select_for_update(of=("self", "user"), no_key=True).select_related("user").filter(pk=found))
    unit = unit_in_scope(user, unit_id, for_update=True)
    nurse_request = (Request.objects.select_for_update(of=("self",)).select_related("window", "shift", "nurse__user", "pin__shift")
                     .filter(pk=request_id, window__unit=unit).first())
    if nurse_request is None:
        raise Http404("There is no such request in your unit.")
    roster = (Roster.objects.select_for_update(of=("self",)).select_related("solve", "unit")
              .filter(unit=unit, month=nurse_request.window.month).first())
    return Locked(unit, nurse_request.nurse, nurse_request, roster)


def _what(shift: Shift | None) -> str:
    return f"{shift.display_name} ({shift.code})" if shift else "a day off"


def _state_words(state: str) -> str:
    return RequestState(state).label.lower().replace("_", " ")


def why_the_pin_cannot_move(locked: Locked) -> str | None:
    """A month that is over and a submitted roster take no pin, and an accepted swap's pin is the swap's to change."""
    if locked.month < membership.this_month():
        return MONTH_OVER
    if locked.roster is not None and locked.roster.state == RosterState.SUBMITTED:
        return FROZEN[RosterState.SUBMITTED]
    return None


def refusal_to_pin(locked: Locked, shift: Shift | None, asked: str | None, judge: Judge | None = None) -> str | None:
    """Why the request's date could not hold this pin now, in a save's words; None when it could."""
    moving = why_the_pin_cannot_move(locked)
    if moving:
        return moving
    held = PinnedCell.objects.current().filter(nurse=locked.nurse, date=locked.request.date, unit=locked.unit).first()
    if held is not None and held.origin == PinOrigin.SWAP:
        return f"An accepted swap holds this cell on {long_date(locked.request.date)}, so change it there."
    judge = judge or Judge(locked.unit, locked.month)
    return judge.refusal(locked.nurse.pk, locked.name, locked.request.date, asked, shift)


def _onto_roster(locked: Locked, code: str, by: User, reason: str) -> RosterVersion | None:
    """The pin's cell on the month's roster. A draft takes it in place; an approved roster takes it as a new version, which tells
    its nurses, only when a cell changes. A nurse with no row joined after the solve: the next solve takes their pin."""
    roster, hospital_id, day = locked.roster, locked.nurse.user.username, locked.request.date.isoformat()
    row = roster.grid.get(hospital_id) if roster else None
    if roster is None or row is None or day not in row or row[day] == code:
        return None
    grid = copy.deepcopy(roster.grid)
    grid[hospital_id][day] = code
    if roster.state == RosterState.DRAFT:
        roster.grid = grid
        roster.save(update_fields=["grid"])  # `updated_at` stays, as for a hand edit.
        return None
    return make_version(roster, grid, VersionOrigin.REQUEST, by, reason)


def _told(locked: Locked, step: str, by: User, version: RosterVersion | None, request) -> None:
    """After the change: its audit entry, which says the request moved and whose, never what or why, then whoever is told."""
    record(f"request.{step}", actor=by, target=locked.nurse.user.username, request=request)
    if version is not None:
        sending.roster_changed(locked.unit, locked.month, by)
    sending.request_decided(locked.request, step, by)


def _pinned(locked: Locked, shift: Shift | None, step: str, by: User, reason: str, version_reason: str,
            request) -> RosterVersion | None:
    pin = pin_cell(locked.unit, locked.nurse, locked.request.date, shift, PinOrigin.REQUEST, by)
    version = _onto_roster(locked, shift.code if shift else "", by, version_reason)
    nurse_request = locked.request
    nurse_request.state, nurse_request.pin = RequestState.ACCEPTED, pin
    nurse_request.save(update_fields=["state", "pin"])
    RequestStep.objects.create(request=nurse_request, step=step, by=by, reason=reason, pin=pin)
    _told(locked, step, by, version, request)
    return version


def accept(locked: Locked, by: User, reason: str, request) -> RosterVersion | None:
    """What she asked for becomes a pin. One the manager pinned on that cell ends as replaced, as their next pin there would:
    the page says so before they accept."""
    nurse_request = locked.request
    if nurse_request.state != RequestState.PENDING:
        raise HttpError(409, f"This request is {_state_words(nurse_request.state)} already.")
    refusal = refusal_to_pin(locked, nurse_request.shift, nurse_request.shift.code if nurse_request.shift else None)
    if refusal:
        raise HttpError(409, refusal)
    what = _what(nurse_request.shift)
    return _pinned(locked, nurse_request.shift, Step.ACCEPTED, by, reason, f"{locked.name}'s request for {what} on "
                   f"{long_date(nurse_request.date)} accepted.", request)


def edit(locked: Locked, asked: str | None, by: User, reason: str, request) -> RosterVersion | None:
    """An accepted request now promises a different shift, or a day off, on its date. The request keeps what she asked for; its
    new pin holds what is promised."""
    nurse_request = locked.request
    if nurse_request.state != RequestState.ACCEPTED:
        raise HttpError(409, f"Only an accepted request can be changed, and this one is {_state_words(nurse_request.state)}.")
    code = current_code(asked) if asked else None
    shift = Shift.objects.filter(code=code, active=True).first() if code else None
    if (code is None and nurse_request.pin.shift_id is None) or (shift is not None and shift.pk == nurse_request.pin.shift_id):
        raise HttpError(409, f"The request already promises {_what(shift)}. Choose something else, or leave it as it is.")
    refusal = refusal_to_pin(locked, shift, code)
    if refusal:
        raise HttpError(409, refusal)
    return _pinned(locked, shift, Step.EDITED, by, reason, f"{locked.name}'s accepted request changed to {_what(shift)} on "
                   f"{long_date(nurse_request.date)}.", request)


def reject(locked: Locked, by: User, reason: str, request) -> None:
    nurse_request = locked.request
    if nurse_request.state != RequestState.PENDING:
        raise HttpError(409, f"This request is {_state_words(nurse_request.state)} already.")
    nurse_request.state = RequestState.REJECTED
    nurse_request.save(update_fields=["state"])
    RequestStep.objects.create(request=nurse_request, step=Step.REJECTED, by=by, reason=reason)
    _told(locked, Step.REJECTED, by, None, request)


def cancel(locked: Locked, by: User, reason: str, request) -> None:
    """Its pin ends, and no cell changes: the next solve or a hand edit is free to change it. So no version is made and the
    unit's nurses are told nothing."""
    nurse_request = locked.request
    if nurse_request.state != RequestState.ACCEPTED:
        raise HttpError(409, f"Only an accepted request can be cancelled, and this one is {_state_words(nurse_request.state)}.")
    moving = why_the_pin_cannot_move(locked)
    if moving:
        raise HttpError(409, moving)
    end([nurse_request.pin], PinEnded.CLEARED, by)
    nurse_request.state, nurse_request.pin = RequestState.CANCELLED, None
    nurse_request.save(update_fields=["state", "pin"])
    RequestStep.objects.create(request=nurse_request, step=Step.CANCELLED, by=by, reason=reason)
    _told(locked, Step.CANCELLED, by, None, request)


def replaced_by_leave(ended: Iterable[PinnedCell], by: User) -> list[Request]:
    """Leave wins over a pin, so an accepted request whose pin leave ended takes a final state of its own and stays on record.
    Call it where leave ends pins, under the nurse's lock, and tell the nurse after the leave's audit entry. No audit entry of
    its own: one beside the leave's would date that leave for the System Admin."""
    rows = list(Request.objects.select_for_update(of=("self",)).select_related("window__unit", "nurse__user")
                .filter(pin__in=[pin.pk for pin in ended], state=RequestState.ACCEPTED))
    for nurse_request in rows:
        nurse_request.state, nurse_request.pin = RequestState.REPLACED_BY_LEAVE, None
        nurse_request.save(update_fields=["state", "pin"])
        RequestStep.objects.create(request=nurse_request, step=Step.REPLACED_BY_LEAVE, by=by)
    return rows
