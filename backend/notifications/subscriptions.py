"""Push subscriptions: a device turned on for one user, and every way one ends (GLOSSARY, ADR 0012). The audit log holds who
turned pushes on or off and when, and nothing of the device: not its address, its keys or the IP it called from."""
from __future__ import annotations

from collections.abc import Iterable

from django.db import transaction
from django.utils import timezone

from accounts.models import User
from audit.log import record
from notifications.models import PushSubscription


def devices(user: User) -> int:
    return PushSubscription.objects.filter(user=user).count()


def holds(user: User, endpoint: str | None) -> bool:
    return bool(endpoint) and PushSubscription.objects.filter(user=user, endpoint=endpoint).exists()


def _audit(action: str, user: User) -> None:
    record(action, actor=user, target=user.username)


def turn_on(user: User, *, endpoint: str, p256dh: str, auth: str, replaces: str | None = None) -> None:
    """Idempotent for the same user and address. An address another user holds moves to this one, since it belongs to whoever
    last subscribed it. With `replaces`, one of this user's addresses the browser renewed or a rotation retired: it is gone
    afterwards, and that renewal writes no entry."""
    keys = {"p256dh": p256dh, "auth": auth}
    with transaction.atomic():
        # One user's calls one at a time: a double tap must not make two rows or two entries.
        User.objects.select_for_update(no_key=True).filter(pk=user.pk).first()
        old = PushSubscription.objects.filter(user=user, endpoint=replaces).first() if replaces and replaces != endpoint else None
        held = PushSubscription.objects.select_for_update().filter(endpoint=endpoint).first()
        if held is not None and held.user_id == user.pk:
            PushSubscription.objects.filter(pk=held.pk).update(**keys)
            if old is not None:
                old.delete()
            return
        if held is not None:  # another user's: theirs no more
            PushSubscription.objects.filter(pk=held.pk).update(
                user=user, turned_on_at=timezone.now(), failures_in_a_row=0, last_success_at=None, **keys)
            if old is not None:
                old.delete()
            else:
                _audit("push.turned_on", user)
            return
        if old is not None:
            PushSubscription.objects.filter(pk=old.pk).update(
                endpoint=endpoint, failures_in_a_row=0, last_success_at=None, **keys)
            return
        PushSubscription.objects.create(user=user, endpoint=endpoint, **keys)
        _audit("push.turned_on", user)


def turn_off(user: User, endpoint: str) -> None:
    """This device. Answers the same whether or not the address was this user's, so nobody learns whose an address is; an
    entry is written only when something was turned off."""
    with transaction.atomic():
        deleted, _ = PushSubscription.objects.filter(user=user, endpoint=endpoint).delete()
        if deleted:
            _audit("push.turned_off", user)


def turn_off_everywhere(user: User) -> None:
    """For a lost phone: every device of the user, from any of them. One entry, when there was something to turn off."""
    with transaction.atomic():
        deleted, _ = PushSubscription.objects.filter(user=user).delete()
        if deleted:
            _audit("push.turned_off", user)


def end_for(user_ids: Iterable) -> None:
    """A deactivation's: every device of these users, beside their sessions. Not the user's own act, so no entry of its own;
    the deactivation's says enough."""
    PushSubscription.objects.filter(user_id__in=list(user_ids)).delete()
