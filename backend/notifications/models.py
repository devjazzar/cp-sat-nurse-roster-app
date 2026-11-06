from django.conf import settings
from django.db import models
from django.db.models.functions import UUID7


class Event(models.TextChoices):
    """What a notification is about. A later ticket adds its own here and its words in `notifications.reading`."""
    ROSTER_SUBMITTED = "roster_submitted"
    ROSTER_APPROVED = "roster_approved"
    ROSTER_REJECTED = "roster_rejected"
    ROSTER_CHANGED = "roster_changed"
    SOLVE_ENDED = "solve_ended"
    WINDOW_OPENED = "window_opened"
    WINDOW_CLOSED_EARLY = "window_closed_early"
    WINDOW_CLOSED = "window_closed"
    REQUEST_DECIDED = "request_decided"
    SWAP_STEP = "swap_step"
    MONTH_CLOSED = "month_closed"


class SolveOutcome(models.TextChoices):
    """How a solve ended, as the manager is told: a solve's payload keeps it, since the solve's row cannot change after."""
    DRAFT = "draft"
    STOPPED_DRAFT = "stopped_draft"
    NO_ROSTER = "no_roster"
    FROZEN = "frozen"
    FAILED = "failed"
    # A re-plan's own ends. Its failure and a search that kept no roster are FAILED and NO_ROSTER, with `replan` in the payload.
    REPLANNED = "replanned"
    STOPPED_REPLANNED = "stopped_replanned"
    REPLAN_UNCHANGED = "replan_unchanged"
    REPLAN_OUTDATED = "replan_outdated"
    REPLAN_MONTH_OVER = "replan_month_over"


class Notification(models.Model):
    """One thing one user is told. `payload` holds identifiers only (a unit, a month, a solve, who did it): the words are
    worked out when the notification is read, from what those name then, so a rename or a correction leaves nothing stale and
    nothing about a person is kept here. Never a rejection's comment, a leave or a nurse."""

    id = models.UUIDField(primary_key=True, db_default=UUID7(), editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="notifications")
    event = models.CharField(max_length=32, choices=Event)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["user", "-created_at"], name="notifications_newest_a_user")]
