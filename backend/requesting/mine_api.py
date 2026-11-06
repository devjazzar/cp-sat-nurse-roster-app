"""A staff nurse's own requests for a month: the window, the cap, making and withdrawing them, and every outcome with the
manager's reasons. Nothing here takes a nurse, so nobody reads a colleague's requests, which no other page shows either."""
from __future__ import annotations

import datetime as dt
from typing import Literal
from uuid import UUID

from django.db import transaction
from django.http import HttpRequest
from ninja import Field, Query, Router, Schema, Status

from accounts.authz import SignedIn
from accounts.models import Role
from hospital.api import StrictSchema
from hospital.catalogue_api import IsoDate
from hospital.models import Shift
from nurses import membership
from nurses.models import NurseProfile
from requesting import making
from requesting.api import RequestStateText, StepRow, step_rows, with_steps
from requesting.models import Request, WindowState
from requesting.windows import state_today
from solves.api import MonthFilter, chosen_month

router = Router(tags=["requests"])
nurse_only = SignedIn(Role.STAFF_NURSE)


class MyWindow(Schema):
    unit: str
    opens_on: dt.date
    closes_on: dt.date = Field(description="The last day requests can be made.")
    state: Literal["scheduled", "open", "closed"] = Field(description="As the dates say today.")
    closed_early: bool


class RequestableShift(Schema):
    code: str
    display_name: str


class MyRequestRow(Schema):
    id: UUID
    date: dt.date
    shift: str = Field(description="What you asked for: a shift's code, empty for a day off.")
    state: RequestStateText
    promised: str | None = Field(description="While accepted, what is promised, which your manager may have changed.")
    steps: list[StepRow]


class MyRequests(Schema):
    month: str = Field(description="YYYY-MM.")
    window: MyWindow | None = Field(description="The latest window for this month of the unit it falls under for you.")
    request_cap: int | None = Field(description="Requests a nurse may have pending or accepted this month.")
    counted: int = Field(description="Yours pending or accepted this month, which count against the cap.")
    refusal: str | None = Field(description="Why you cannot make a request for this month now.")
    shifts: list[RequestableShift] = Field(description="The shifts you may ask for.")
    first_day: dt.date | None = Field(description="The first day of the month you may ask about, within your dates.")
    last_day: dt.date | None
    requests: list[MyRequestRow] = Field(description="Yours for this month, every state, by date.")


def my_rows(requests) -> list[MyRequestRow]:
    return [MyRequestRow(id=row.pk, date=row.date, shift=row.code, state=row.state, promised=row.pin.code if row.pin else None,
                         steps=step_rows(list(row.steps.all()))) for row in requests]


def _shifts(nurse: NurseProfile, month: dt.date, unit) -> list[RequestableShift]:
    allowed = membership.placement_in(nurse, month).allowed_shifts
    shifts = Shift.objects.filter(active=True, code__in=unit.rules.get("shifts", [])).order_by("start_time", "code")
    return [RequestableShift(code=shift.code, display_name=shift.display_name) for shift in shifts
            if allowed is None or shift.code in allowed]


@router.get("/mine", response=MyRequests, auth=nurse_only, operation_id="getMyRequests")
def my_requests(request: HttpRequest, filters: Query[MonthFilter]) -> MyRequests:
    month = chosen_month(filters.month)
    nurse = NurseProfile.objects.select_related("user").filter(user=request.user).first()
    rows = my_rows(with_steps(Request.objects.filter(nurse=nurse, date__year=month.year, date__month=month.month)))
    window = making.window_for(nurse, month) if nurse else None
    answer = MyRequests(month=month.strftime("%Y-%m"), window=None, request_cap=None, counted=0, shifts=[], first_day=None,
                        last_day=None, requests=rows, refusal=f"No request window is open for {month:%B %Y}.")
    if window is None:
        return answer
    state = state_today(window)
    answer.window = MyWindow(unit=window.unit.name, opens_on=window.opens_on, closes_on=window.closes_on, state=state,
                             closed_early=window.closed_by_id is not None)
    answer.request_cap, answer.counted = window.unit.request_cap, making.live_in(nurse, month).count()
    first, last = max(month, nurse.start_date), min(membership.last_day_of(month), nurse.end_date or dt.date.max)
    if first <= last:
        answer.first_day, answer.last_day = first, last
    answer.shifts = _shifts(nurse, month, window.unit)
    if state != WindowState.OPEN:
        return answer
    if first > last:
        answer.refusal = f"You have no days on the {window.unit.name} roster in {month:%B %Y}."
    elif answer.counted >= answer.request_cap:
        answer.refusal = (f"You have {answer.counted} requests for {month:%B %Y}, the most this unit allows. Withdraw a pending "
                          "one to make another.")
    else:
        answer.refusal = None
    return answer


class NewRequestBody(StrictSchema):
    date: IsoDate
    shift: str | None = Field(max_length=8, description="The shift's code, or null for a day off.")
    reason: str = Field("", max_length=500, description="Optional. Only you and your manager read it.")


@router.post("/mine", response={201: MyRequestRow}, auth=nurse_only, operation_id="makeRequest")
def make_request(request: HttpRequest, body: NewRequestBody) -> Status:
    """Within an open window of the unit the date's month falls under for you, up to the unit's cap of requests pending or
    accepted, one a date. The audit log says that you made one, never what or why."""
    with transaction.atomic():
        made = making.make(request.user, body.date, body.shift or None, body.reason.strip(), request)
    return Status(201, my_rows(with_steps(Request.objects.filter(pk=made.pk)))[0])


@router.post("/mine/{request_id}/withdraw", response=MyRequestRow, auth=nurse_only, operation_id="withdrawRequest")
def withdraw_request(request: HttpRequest, request_id: UUID) -> MyRequestRow:
    """A pending one, while its window is open. Another nurse's is the same 404 as none."""
    with transaction.atomic():
        making.withdraw(request.user, request_id, request)
    return my_rows(with_steps(Request.objects.filter(pk=request_id)))[0]
