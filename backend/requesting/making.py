"""Opening and closing a request window, and a nurse making and withdrawing a request: each refusal, then the write, the audit
entry and whoever is told. Call each inside a transaction. The audit log says that a window or a request moved and whose: never
what a request asked for, its date or a reason, since a reason can be about someone's health and a date is part of a roster."""
from __future__ import annotations

import datetime as dt
from uuid import UUID

from django.db.models import QuerySet
from django.http import Http404, HttpRequest
from django.utils import timezone
from ninja.errors import HttpError

from accounts.models import User
from audit.log import record
from hospital.api import refuse
from hospital.models import Shift
from notifications import sending
from nurses import membership
from nurses.models import NurseProfile
from requesting.models import LIVE, Request, RequestState, RequestStep, RequestWindow, Step, WindowState
from requesting.windows import catch_up, not_closed, state_today
from rosters.drafts import current_code
from rosters.pins import Judge, long_date
from units.models import Unit

NO_CAP = ("This unit's request cap is 0, so its nurses could make no requests. Raise it on the Unit rules page to open a "
          "window.")


def month_name(month: dt.date) -> str:
    return f"{month:%B %Y}"


def at_the_cap(count: int, month: dt.date) -> str:
    return (f"You have {count} requests for {month_name(month)}, the most this unit allows. Withdraw a pending one to make "
            "another.")


def open_window(unit: Unit, month: dt.date, opens_on: dt.date, closes_on: dt.date, by: User,
                request: HttpRequest) -> RequestWindow:
    """Hold the unit's lock. A window whose open date is today opens now, and its nurses are told at once; a later one opens,
    and tells them, when the hourly job or the next write finds its date has come."""
    today = membership.today()
    if unit.request_cap == 0:
        raise HttpError(409, NO_CAP)
    if month <= membership.this_month():
        refuse((("month",), "Choose a coming month: requests are for a month not yet begun."))
    if opens_on < today:
        refuse((("opens_on",), f"Choose today, {long_date(today)}, or a later day."))
    if closes_on < opens_on:
        refuse((("closes_on",), "The close date cannot be before the open date."))
    if closes_on >= month:
        last = month - dt.timedelta(days=1)
        refuse((("closes_on",), f"Requests have to close before {month_name(month)} begins, so that its roster can be made: "
                                f"choose {long_date(last)} or earlier."))
    waiting = next(iter(catch_up(not_closed(unit.pk))), None)
    if waiting is not None and waiting.state != WindowState.CLOSED:
        when = (f"opens on {long_date(waiting.opens_on)}" if waiting.state == WindowState.SCHEDULED
                else f"is open until {long_date(waiting.closes_on)}")
        raise HttpError(409, f"The request window for {month_name(waiting.month)} {when}. A unit has one window at a time: "
                             "close it first.")
    window = RequestWindow.objects.create(unit=unit, month=month, opens_on=opens_on, closes_on=closes_on, created_by=by)
    record("request_window.opened", actor=by, target=window.audit_target, request=request,
           after={"opens_on": opens_on.isoformat(), "closes_on": closes_on.isoformat()})
    return catch_up(RequestWindow.objects.filter(pk=window.pk))[0]


def close_window(unit: Unit, window_id: UUID, by: User, request: HttpRequest) -> RequestWindow:
    """Early, by its manager, under the unit's lock. Nurses told it opened are told it closed; nobody, if it never opened."""
    window = next(iter(catch_up(RequestWindow.objects.filter(unit=unit, pk=window_id))), None)
    if window is None:
        raise Http404("There is no such request window.")
    if window.state == WindowState.CLOSED:
        raise HttpError(409, "This window has closed already.")
    was_open = window.state == WindowState.OPEN
    window.state, window.closed_by = WindowState.CLOSED, by
    window.closed_at = window.closed_at or timezone.now()
    window.save(update_fields=["state", "closed_at", "closed_by"])
    record("request_window.closed", actor=by, target=window.audit_target, request=request)
    if was_open:
        sending.window_closed_early(window, by)
    return window


def locked_nurse(user: User) -> NurseProfile:
    """`FOR NO KEY UPDATE`, as every lock on a nurse's row is taken (docs/ARCHITECTURE.md section 5): it serialises a nurse's
    requests, so two made at once cannot both pass the cap, and orders them with leave and the manager's decisions."""
    nurse = (NurseProfile.objects.select_for_update(of=("self", "user"), no_key=True).select_related("user")
             .filter(user=user).first())
    if nurse is None:
        raise HttpError(403, "Only a nurse makes requests.")
    return nurse


def nurse_refusal(judge: Judge, nurse: NurseProfile, day: dt.date, asked: str | None,
                  shift: Shift | None) -> tuple[str, str] | None:
    """`Judge`'s answer, the one a manager's acceptance gets, said to the nurse, with the field it is about: a request that
    could never be accepted is refused here."""
    match judge.day_why(nurse.pk, day):
        case "not_in_month":
            return "date", f"You have no days on the {judge.unit.name} roster in {month_name(judge.month)}."
        case "outside_dates":
            return "date", f"{long_date(day)} is outside your dates on the roster."
        case "leave":
            return "date", f"You are on leave on {long_date(day)}, so there is nothing to request that day."
    if asked is None:
        return None
    match judge.shift_why(nurse.pk, shift) if shift else "shift_not_worked":
        case "shift_not_worked":
            return "shift", f"{asked} is not one of the {judge.unit.name} unit's shifts."
        case "shift_not_allowed":
            return "shift", f"{asked} is not one of the shifts you work."
    return None


def window_for(nurse: NurseProfile, month: dt.date) -> RequestWindow | None:
    """The latest window of the unit this month falls under for the nurse, which may be one they are due to join."""
    placement = membership.placement_in(nurse, month)
    if placement is None:
        return None
    return RequestWindow.objects.filter(unit_id=placement.unit_id, month=month).select_related("unit").first()


def live_in(nurse: NurseProfile, month: dt.date, unit: Unit) -> QuerySet[Request]:
    """Those that count against this unit's cap: one left behind in another unit by a transfer is that unit's to decide."""
    return Request.objects.filter(nurse=nurse, window__unit=unit, date__year=month.year, date__month=month.month,
                                  state__in=LIVE)


def make(user: User, day: dt.date, asked: str | None, reason: str, request: HttpRequest) -> Request:
    nurse = locked_nurse(user)
    month = day.replace(day=1)
    latest = window_for(nurse, month)
    window = catch_up(RequestWindow.objects.filter(pk=latest.pk))[0] if latest else None
    if window is None or window.state != WindowState.OPEN:
        raise HttpError(409, f"No request window is open for {month_name(month)}.")
    unit = Unit.objects.get(pk=window.unit_id)
    code = current_code(asked) if asked else None
    shift = Shift.objects.filter(code=code, active=True).first() if code else None
    refusal = nurse_refusal(Judge(unit, month), nurse, day, code, shift)
    if refusal:
        refuse(((refusal[0],), refusal[1]))
    live = list(live_in(nurse, month, unit))
    # Any unit's: a request a transfer left behind still holds its date until its manager decides it.
    if Request.objects.filter(nurse=nurse, date=day, state__in=LIVE).exists():
        refuse((("date",), f"You already have a request on {long_date(day)}. Withdraw it to ask for something else."))
    if len(live) >= unit.request_cap:
        raise HttpError(409, at_the_cap(len(live), month))
    made = Request.objects.create(window=window, nurse=nurse, date=day, shift=shift)
    RequestStep.objects.create(request=made, step=Step.MADE, by=user, reason=reason)
    record("request.made", actor=user, target=user.username, request=request)
    return made


def withdraw(user: User, request_id: UUID, request: HttpRequest) -> Request:
    nurse = locked_nurse(user)
    mine = Request.objects.select_for_update(of=("self",)).filter(pk=request_id, nurse=nurse).first()
    if mine is None:
        raise Http404("You have no such request.")
    if mine.state != RequestState.PENDING:
        raise HttpError(409, f"This request is {mine.state_words}, so it cannot be withdrawn.")
    window = catch_up(RequestWindow.objects.filter(pk=mine.window_id))[0]
    if state_today(window) != WindowState.OPEN:
        raise HttpError(409, "The request window has closed, so this request waits for your manager's decision.")
    mine.state = RequestState.WITHDRAWN
    mine.save(update_fields=["state"])
    RequestStep.objects.create(request=mine, step=Step.WITHDRAWN, by=user)
    record("request.withdrawn", actor=user, target=user.username, request=request)
    return mine
