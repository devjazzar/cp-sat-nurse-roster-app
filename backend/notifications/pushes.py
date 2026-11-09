"""The push job's work (ADR 0012): for each notification of a kind with a deadline, to each subscription of its reader, the kind
code alone, but only while the thing still waits and the reader still has a page for it. What each push service answers moves the
subscription: a success resets its failures, a gone address ends it, and a push that does not reach it counts one failure, the
tenth ending it. An attempt that could not reach the service is tried again for that subscription alone (`RETRY_IN`)."""
from __future__ import annotations

import datetime as dt

from django.db.models import F
from django.utils import timezone

from accounts.models import User
from notifications import push_keys, pushing, reading, subscriptions
from notifications.kinds import PushKind, kind_of
from notifications.models import Notification, PushAttempt, PushOutcome, PushSubscription
from requesting.models import RequestState, RequestWindow, WindowState
from requesting.windows import state_today
from rosters.models import Roster, RosterState
from swaps.expiring import state_now
from swaps.models import Answer, Swap, SwapParticipant, SwapState

RETRY_IN = (60, 180, 360)
"""Seconds before each try again of a subscription the push service could not be reached at: three, over about ten minutes."""
FAILURES_THAT_END = 10

Pairs = list[list[str]]
"""[notification id, subscription id] of the sends still to make, carried from one try to the next."""


def _month(payload: dict) -> dt.date:
    return dt.date.fromisoformat(f"{payload['month']}-01")


def still_waits(kind: PushKind, note: Notification) -> bool:
    """Read as the pages read it, from the dates as well as the stored state, so a swap past its first date or a window past
    its close date is no longer waiting, whether or not the hourly job has stored it."""
    payload = note.payload
    match kind:
        case PushKind.SWAP_TO_ANSWER | PushKind.SWAP_TO_DECIDE:
            swap = Swap.objects.prefetch_related("cells").filter(pk=payload.get("swap_id")).first()
            if swap is None:
                return False
            if kind == PushKind.SWAP_TO_DECIDE:
                return state_now(swap) == SwapState.AWAITING_MANAGER
            # Answered on another device: nothing to tell.
            return state_now(swap) == SwapState.PENDING and SwapParticipant.objects.filter(
                swap=swap, nurse__user_id=note.user_id, answer=Answer.PENDING).exists()
        case PushKind.REQUESTS_OPEN | PushKind.REQUESTS_TO_DECIDE:
            window = RequestWindow.objects.filter(pk=payload.get("window_id")).first()
            if window is None:
                return False
            if kind == PushKind.REQUESTS_OPEN:
                return state_today(window) == WindowState.OPEN
            return state_today(window) == WindowState.CLOSED and window.requests.filter(state=RequestState.PENDING).exists()
        case PushKind.ROSTER_TO_APPROVE | PushKind.ROSTER_SENT_BACK:
            roster = Roster.objects.filter(unit_id=payload.get("unit_id"), month=_month(payload)).first()
            if roster is None:
                return False
            if kind == PushKind.ROSTER_TO_APPROVE:
                return roster.state == RosterState.SUBMITTED
            return roster.state == RosterState.DRAFT and not roster.submissions.filter(
                submitted_at__gt=note.created_at).exists()
    return False


def has_page(note: Notification) -> bool:
    """The Notifications page's own rule: a reader it would give no link to (a manager taken off the unit, say) gets no push."""
    reader = User.objects.filter(pk=note.user_id, is_active=True).first()
    return reader is not None and reading.link_of(note, reader, reading.Names([note])) is not None


def _failed(subscription_id) -> None:
    PushSubscription.objects.filter(pk=subscription_id).update(failures_in_a_row=F("failures_in_a_row") + 1)
    PushSubscription.objects.filter(pk=subscription_id, failures_in_a_row__gte=FAILURES_THAT_END).delete()


def deliver(notification_ids: list[str], *, attempt: int = 0, remaining: Pairs | None = None) -> Pairs:
    """One try. `remaining`, on a try again, holds the sends the last one could not make; the first try makes one to each
    subscription the reader holds now. Returns the sends to try again."""
    retry: Pairs = []
    last_try = attempt >= len(RETRY_IN)
    key = None
    for note in Notification.objects.filter(pk__in=notification_ids).order_by("pk"):
        kind = kind_of(note.event, note.payload)
        if kind is None or not still_waits(kind, note) or not has_page(note):
            continue
        # The reader's own: an address moved to another user since is not sent this one.
        held = PushSubscription.objects.filter(user_id=note.user_id).order_by("pk")
        if remaining is not None:
            held = held.filter(pk__in=[sub for of, sub in remaining if of == str(note.pk)])
        for subscription in held:
            if not subscriptions.allowed(subscription.endpoint):
                PushSubscription.objects.filter(pk=subscription.pk).delete()
                continue
            key = key or push_keys.private_key()
            outcome = pushing.send(endpoint=subscription.endpoint, p256dh=subscription.p256dh, auth=subscription.auth,
                                   kind=kind, private_key=key)
            PushAttempt.objects.create(outcome=outcome)
            match outcome:
                case PushOutcome.SENT:
                    PushSubscription.objects.filter(pk=subscription.pk).update(failures_in_a_row=0,
                                                                                last_success_at=timezone.now())
                case PushOutcome.GONE:
                    PushSubscription.objects.filter(pk=subscription.pk).delete()
                case PushOutcome.UNREACHABLE if not last_try:
                    retry.append([str(note.pk), str(subscription.pk)])
                case _:  # refused, or unreachable at the last try: this push did not reach it
                    _failed(subscription.pk)
    return retry
