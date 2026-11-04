"""The application's only way to write to the audit log."""
from __future__ import annotations

import ipaddress

from django.http import HttpRequest

from audit.models import AuditEntry


def client_ip(request: HttpRequest) -> str | None:
    """Caddy replaces any X-Forwarded-For a client sends, and `web` publishes no port, so the
    header can only say what Caddy saw. Without Caddy (development) the peer is the client."""
    forwarded = request.headers.get("X-Forwarded-For", "").rsplit(",", 1)[-1].strip()
    for candidate in (forwarded, request.META.get("REMOTE_ADDR", "")):
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            continue
    return None


def record(action: str, *, actor=None, target: str = "", before: dict | None = None, after: dict | None = None,
           request: HttpRequest | None = None) -> AuditEntry:
    return AuditEntry.objects.create(action=action, actor=actor, target=target, before=before, after=after,
                                     ip=client_ip(request) if request else None)
