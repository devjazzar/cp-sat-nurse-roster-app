"""Who may call what. An endpoint or router names its roles here:

    Router(auth=SignedIn(Role.SYSTEM_ADMIN))

A signed-in user who has not yet changed a forced password may call nothing else until they do.
"""
from __future__ import annotations

from django.http import HttpRequest
from ninja.errors import HttpError
from ninja.security import SessionAuth


class SignedIn(SessionAuth):
    """401 when not signed in, 403 for the wrong role, and CSRF on every unsafe method."""

    def __init__(self, *roles: str, during_forced_change: bool = False):
        super().__init__()
        self.roles = roles
        self.during_forced_change = during_forced_change

    def authenticate(self, request: HttpRequest, key: str | None):
        user = request.user
        if not user.is_authenticated:
            return None
        if user.must_change_password and not self.during_forced_change:
            raise HttpError(403, "Change your password first.")
        if self.roles and user.role not in self.roles:
            raise HttpError(403, "Your role may not do this.")
        return user
