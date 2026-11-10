import datetime as dt

from django.utils import timezone

from notifications import pushes
from notifications.models import Notification, PushAttempt
from ops.queue import daily, enqueue_later, under_its_own_lock

KEPT = dt.timedelta(days=365)


@daily(at_hour_utc=22, at_minute=20)
def remove_old_notifications(timestamp: int) -> None:
    """A notification is kept for a year, read or not (ticket 22). A day missed is caught up by the next."""
    Notification.objects.filter(created_at__lt=timezone.now() - KEPT).delete()


ATTEMPTS_KEPT = dt.timedelta(days=7)
"""Long enough to look back over a week of pushes that failed; the health page reads the last 24 hours only."""


@daily(at_hour_utc=22, at_minute=30)
def remove_old_push_attempts(timestamp: int) -> None:
    """A push attempt is no one's record: kept seven days, whatever came of it (ticket 42). A day missed is caught up by the
    next."""
    PushAttempt.objects.filter(at__lt=timezone.now() - ATTEMPTS_KEPT).delete()


TRY_AGAIN_PRIORITY = -1
"""A try again waits minutes for its time, holding the lock `push` meanwhile against any job of its priority deferred after it.
Below the first tries' priority, it holds back no new push; a new push waiting holds it back only until that runs."""


@under_its_own_lock
def push(notification_ids: list[str], attempt: int = 0, remaining: list[list[str]] | None = None) -> None:
    """Deferred by `notifications.sending.notify` in the transaction that writes the notifications, so it exists only if they
    do (ADR 0006); one job a call, however many it tells. Under the lock `push`, one push job at a time (ADR 0009)."""
    retry = pushes.deliver(notification_ids, attempt=attempt, remaining=remaining)
    if retry:
        enqueue_later(push, seconds=pushes.RETRY_IN[attempt], priority=TRY_AGAIN_PRIORITY,
                      notification_ids=notification_ids, attempt=attempt + 1, remaining=retry)
