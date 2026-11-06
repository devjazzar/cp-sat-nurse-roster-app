"""Notifications are kept for a year (ticket 22), read or not: nothing else removes them."""
import datetime as dt

import pytest
from django.utils import timezone

from accounts.models import Role
from notifications.models import Event, Notification
from notifications.tasks import remove_old_notifications

pytestmark = pytest.mark.django_db


def test_those_older_than_a_year_go_read_or_not(make_user):
    user = make_user("mona", Role.UNIT_MANAGER)
    now = timezone.now()

    def made(days_ago, read=False):
        notification = Notification.objects.create(user=user, event=Event.ROSTER_CHANGED, payload={})
        Notification.objects.filter(pk=notification.pk).update(created_at=now - dt.timedelta(days=days_ago),
                                                               read_at=now if read else None)
        return notification.pk

    gone = {made(366), made(400, read=True)}
    kept = {made(364), made(1, read=True)}

    remove_old_notifications(timestamp=int(now.timestamp()))

    assert set(Notification.objects.values_list("pk", flat=True)) == kept
    assert not Notification.objects.filter(pk__in=gone).exists()


def test_the_job_runs_daily_under_a_lock_of_its_own():
    assert (remove_old_notifications.lock, remove_old_notifications.queueing_lock) == ("remove_old_notifications",) * 2
