"""Logging in, with the lockout (docs/ARCHITECTURE.md section 8)."""
from __future__ import annotations

from datetime import datetime, timedelta

from django.contrib.auth import authenticate, login
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from accounts.models import LoginAttempts, User
from audit.log import record

MAX_FAILURES = 5
LOCK_DURATION = timedelta(minutes=15)


class LoginRefused(Exception):
    """Wrong credentials, or locked when `locked_until` is set."""

    def __init__(self, locked_until: datetime | None = None):
        super().__init__("login refused")
        self.locked_until = locked_until


def attempt_login(request: HttpRequest, username: str, password: str) -> User:
    """Logs the request in or raises LoginRefused. The row lock is held across the password check,
    so a burst of parallel guesses at one username gets no more than five checks. While locked the
    password is not looked at, so even the right one is refused."""
    refused = None
    with transaction.atomic():
        attempts, _ = LoginAttempts.objects.select_for_update().get_or_create(username=username)
        now = timezone.now()
        if attempts.locked_until and attempts.locked_until > now:
            refused = LoginRefused(attempts.locked_until)
            _record_failure(request, username, reason="locked")
        else:
            if attempts.locked_until:  # the lock has run out: a fresh count
                attempts.failures, attempts.locked_until = 0, None
            user = authenticate(request, username=username, password=password)
            if user is not None:
                attempts.delete()
                login(request, user)
                record("auth.login", actor=user, target=username, request=request)
                return user
            attempts.failures += 1
            if attempts.failures >= MAX_FAILURES:
                attempts.locked_until = now + LOCK_DURATION
            attempts.save()
            refused = LoginRefused(attempts.locked_until)
            _record_failure(request, username, reason="wrong_credentials", failures=attempts.failures)
    raise refused


def _record_failure(request: HttpRequest, username: str, **details) -> None:
    record("auth.login_failed", actor=User.objects.filter(username=username).first(), target=username,
           after=details, request=request)
