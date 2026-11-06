"""The one way to tell users something. Call `notify` inside the transaction that makes the change, after its audit entry, so a
change rolled back tells nobody. The recipients of each event that exists are worked out here, next to each other."""
from __future__ import annotations

import datetime as dt
from collections.abc import Iterable
from typing import TYPE_CHECKING
from uuid import UUID

from django.db.models import QuerySet, TextChoices

from accounts.models import Role, User
from notifications.models import Event, Notification, SolveOutcome
from nurses import membership
from units.models import Unit

if TYPE_CHECKING:
    from requesting.models import Request, RequestWindow
    from swaps.models import Swap


def notify(users: Iterable[User | None], event: Event, **payload) -> int:
    """Each active user once, whatever the list repeats: a manager with a nurse profile is a nurse of the month too. A
    deactivated user is told nothing, as they can read nothing. Payload values are identifiers and numbers only."""
    seen, rows = set(), []
    for user in users:
        if user is None or not user.is_active or user.pk in seen:
            continue
        seen.add(user.pk)
        rows.append(Notification(user=user, event=event, payload=payload))
    Notification.objects.bulk_create(rows)
    return len(rows)


def _about(unit: Unit, month: dt.date) -> dict:
    return {"unit_id": str(unit.pk), "month": month.strftime("%Y-%m")}


def roster_submitted(unit: Unit, month: dt.date, by: User) -> None:
    """To the CNO and the Deputy CNO, who decide."""
    notify(User.objects.filter(role__in=(Role.CNO, Role.DEPUTY_CNO)), Event.ROSTER_SUBMITTED, **_about(unit, month),
           by=str(by.pk))


def roster_approved(unit: Unit, month: dt.date, by: User) -> None:
    """To the unit's manager and every nurse of the unit's month, a nurse due to join included (`membership.placed_in`). No
    version number: a later one would make it untrue, and the page says which is in force."""
    nurses = User.objects.filter(nurse_profile__in=membership.placed_in(unit, month))
    notify([unit.manager, *nurses], Event.ROSTER_APPROVED, **_about(unit, month), by=str(by.pk))


def roster_changed(unit: Unit, month: dt.date, by: User) -> None:
    """To every nurse of the unit's month, as an approval is, but not to whoever made the change, who knows. Never the reason,
    the cells or whose they are, since a cell taken off can be leave and a colleague must not learn that: each nurse reads their
    own row on My roster. No version number, which a later version would make untrue."""
    nurses = User.objects.filter(nurse_profile__in=membership.placed_in(unit, month)).exclude(pk=by.pk)
    notify(nurses, Event.ROSTER_CHANGED, **_about(unit, month), by=str(by.pk))


def roster_rejected(unit: Unit, month: dt.date, by: User) -> None:
    """To the unit's manager only. The comment stays on the roster: it can name a nurse and their leave."""
    notify([unit.manager], Event.ROSTER_REJECTED, **_about(unit, month), by=str(by.pk))


def solve_ended(unit_id: UUID, month: dt.date, solve_id: UUID, outcome: SolveOutcome, *, replan: bool = False) -> None:
    """To whoever manages the unit when the solve ends, read again then: a manager taken off it since starting the solve no
    longer reads its pages, and the one who holds it now has the draft. Nobody when the unit has none. A re-plan says so, so
    that its failure is told as a re-plan's."""
    unit = Unit.objects.select_related("manager").get(pk=unit_id)
    notify([unit.manager], Event.SOLVE_ENDED, **_about(unit, month), solve_id=str(solve_id), outcome=outcome,
           **({"replan": True} if replan else {}))


def _window_nurses(window: "RequestWindow") -> QuerySet[User]:
    """The staff nurses of the unit's target month, a nurse due to join included, as an approval's are. A manager with a nurse
    profile makes no requests."""
    return User.objects.filter(role=Role.STAFF_NURSE, nurse_profile__in=membership.placed_in(window.unit, window.month))


def window_opened(window: "RequestWindow") -> None:
    """When its open date comes, which may be the day it is made. The words read the window's dates when shown."""
    notify(_window_nurses(window), Event.WINDOW_OPENED, **_about(window.unit, window.month), window_id=str(window.pk),
           by=str(window.created_by_id))


def window_closed_early(window: "RequestWindow", by: User) -> None:
    """To the nurses told it opened, who expected it open until its close date."""
    notify(_window_nurses(window), Event.WINDOW_CLOSED_EARLY, **_about(window.unit, window.month), window_id=str(window.pk),
           by=str(by.pk))


def window_closed(window: "RequestWindow") -> None:
    """To the unit's manager, once, when its close date has passed with requests waiting for a decision: one notification a
    window rather than one a request. How many still wait is worked out when it is read."""
    notify([window.unit.manager], Event.WINDOW_CLOSED, **_about(window.unit, window.month), window_id=str(window.pk))


def request_decided(request: "Request", step: str, by: User | None) -> None:
    """To the nurse who made it, and nobody else. Never its date, shift or either reason: the words read them from the request
    when shown, and only she reads them. `by` is None when the month's close ended it (`expired`)."""
    notify([request.nurse.user], Event.REQUEST_DECIDED, **_about(request.window.unit, request.window.month),
           request_id=str(request.pk), step=str(step), **({"by": str(by.pk)} if by is not None else {}))


def month_closed(unit: Unit, month: dt.date, close_id: UUID) -> None:
    """To the unit's manager, when the schedule closes its month: how many hard rules the recorded facts broke is read from the
    close when shown, never kept here, since a broken rule can be a nurse's leave. A manager who closes it again sees it there and
    then, so is not told."""
    notify([unit.manager], Event.MONTH_CLOSED, **_about(unit, month), close_id=str(close_id))


class SwapStep(TextChoices):
    """A step a swap took, as its people are told: a payload's `step`, so no migration."""
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    AWAITING = "awaiting"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    APPROVED = "approved"


def swap_step(swap: "Swap", step: SwapStep, by: User | None, *, awaiting: bool = False) -> None:
    """Everyone involved, at each step (ticket 20): its colleagues when it is proposed; its proposer at each acceptance; the
    unit's manager when all have accepted, which awaits them. At a rejection, a withdrawal, an expiry and an approval, the
    proposer and every colleague in it, and the manager too for a withdrawal or an expiry of one that was `awaiting` them. Never
    whoever took the step, who knows. The payload holds identifiers and the step only: the words read the swap when shown, and
    never say why one expired, since a cell a version changed can be a colleague's leave. `by` is None for an expiry."""
    colleagues = [row.nurse.user for row in swap.participants.select_related("nurse__user")]
    proposer = swap.proposer.user
    match step:
        case SwapStep.PROPOSED:
            users = colleagues
        case SwapStep.ACCEPTED:
            users = [proposer]
        case SwapStep.AWAITING:
            users = [swap.unit.manager]
        case _:
            users = [proposer, *colleagues, *([swap.unit.manager] if awaiting else [])]
    users = [user for user in users if user is not None and (by is None or user.pk != by.pk)]
    notify(users, Event.SWAP_STEP, **_about(swap.unit, swap.roster.month), swap_id=str(swap.pk), step=str(step),
           **({"by": str(by.pk)} if by is not None else {}))
