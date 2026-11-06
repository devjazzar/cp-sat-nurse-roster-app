import datetime as dt

from django.utils import timezone

from notifications.models import Notification
from ops.queue import daily

KEPT = dt.timedelta(days=365)


@daily(at_hour_utc=22, at_minute=20)
def remove_old_notifications(timestamp: int) -> None:
    """A notification is kept for a year, read or not (ticket 22). A day missed is caught up by the next."""
    Notification.objects.filter(created_at__lt=timezone.now() - KEPT).delete()
