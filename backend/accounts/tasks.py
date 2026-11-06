from django.contrib.sessions.backends.db import SessionStore

from ops.queue import daily


@daily(at_hour_utc=22, at_minute=40)
def clear_expired_sessions(timestamp: int) -> None:
    """What Django's `clearsessions` does: a session past its twelve idle hours is no use to anyone (ticket 22)."""
    SessionStore.clear_expired()
