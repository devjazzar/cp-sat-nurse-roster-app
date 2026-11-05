"""Creating users, deactivating them and resetting their passwords: every change is audited here,
in one transaction with the change itself. Who may do it is the caller's business (accounts.api
for the management roles; ticket 07 for nurses)."""
from __future__ import annotations

import secrets

from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.models import Session
from django.db import IntegrityError, transaction
from django.http import HttpRequest
from django.utils import timezone

from accounts.models import ONE_OF_A_KIND_CONSTRAINTS, LoginAttempts, User
from audit.log import record
from units.assignment import release_managed_unit

# Read aloud or copied from a note at times, so nothing that looks like something else.
_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def generate_password() -> str:
    """Four groups of four: about 79 bits, and it passes the password policy."""
    return "-".join("".join(secrets.choice(_ALPHABET) for _ in range(4)) for _ in range(4))


class UsernameTaken(Exception):
    pass


class RoleTaken(Exception):
    """An active user already holds this one-of-a-kind role."""

    def __init__(self, role: str):
        super().__init__(role)
        self.holder = User.objects.get(role=role, is_active=True)


def _refusal(error: IntegrityError, role: str) -> Exception:
    constraint = getattr(getattr(error.__cause__, "diag", None), "constraint_name", None)
    return RoleTaken(role) if constraint in ONE_OF_A_KIND_CONSTRAINTS else UsernameTaken()


def create_user(request: HttpRequest, *, username: str, full_name: str, role: str) -> tuple[User, str]:
    """The user and their generated password, which is shown once and kept nowhere. The database's
    constraints decide refusals, so two people creating a CNO at the same moment get one CNO."""
    password = generate_password()
    try:
        with transaction.atomic():
            user = User.objects.create_user(username, password, role, full_name=full_name, must_change_password=True)
            record("user.created", actor=request.user, target=username, request=request,
                   after={"username": username, "full_name": full_name, "role": role, "must_change_password": True})
    except IntegrityError as error:
        raise _refusal(error, role) from error
    return user, password


def deactivate(request: HttpRequest, user_id) -> User:
    """Ends the user's sessions too, so reactivating cannot bring an old browser back in, and takes a manager
    off their unit, which reactivating does not undo."""
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user_id)
        if user.is_active:
            user.is_active = False
            user.save(update_fields=["is_active"])
            _end_sessions(user)
            record("user.deactivated", actor=request.user, target=user.username, request=request,
                   before={"is_active": True}, after={"is_active": False})
            release_managed_unit(request, user)
    return user


def reactivate(request: HttpRequest, user_id) -> User:
    try:
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user_id)
            if not user.is_active:
                user.is_active = True
                user.save(update_fields=["is_active"])
                record("user.reactivated", actor=request.user, target=user.username, request=request,
                       before={"is_active": False}, after={"is_active": True})
    except IntegrityError as error:
        raise _refusal(error, User.objects.get(pk=user_id).role) from error
    return user


def reset_password(request: HttpRequest, user_id) -> tuple[User, str]:
    """A new generated password, shown once, with a forced change at the next login. The new hash
    ends the user's sessions, and a lock from failed logins goes, or they would stay locked out."""
    password = generate_password()
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user_id)
        user.set_password(password)
        user.must_change_password = True
        user.save(update_fields=["password", "must_change_password"])
        LoginAttempts.objects.filter(username=user.username).delete()
        record("user.password_reset", actor=request.user, target=user.username, request=request,
               after={"must_change_password": True})
    return user, password


def _end_sessions(user: User) -> None:
    """Sessions are not indexed by user, so this reads them all. It is a rare action on a table of
    one hospital's sessions."""
    for session in Session.objects.filter(expire_date__gt=timezone.now()).iterator():
        if session.get_decoded().get(SESSION_KEY) == str(user.pk):
            session.delete()
