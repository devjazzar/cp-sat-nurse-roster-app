from django.conf import settings
from django.db import models
from django.db.models.functions import UUID7


class SolveState(models.TextChoices):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


ACTIVE_STATES = (SolveState.QUEUED, SolveState.RUNNING)


class SolveFailure(models.TextChoices):
    SOLVER = "solver", "The solver crashed or could not be reached."
    REFUSED = "refused", "The solver refused the solve input, which is a matter of the rules and not of the solver."


class ReplanOutcome(models.TextChoices):
    """What a re-plan's end did to the roster in force. Blank until it ends, and for a re-plan that kept no roster: no roster
    found, one breaking a hard rule, a failure, or a stop before any was found."""
    VERSION = "version", "Its roster became a new version in force."
    UNCHANGED = "unchanged", "Its roster changed no cell, so no version was made."
    OUTDATED = "outdated", "The roster in force or the month's facts changed while it waited or ran, so it was not applied."
    MONTH_OVER = "month_over", "The month ended while it waited or ran, so it was not applied."


class Solve(models.Model):
    """One run of the solver on one solve input, kept for good. `input` and `result` are what the solver was given and
    what it answered, and nothing rewrites them, not even a shift's rename: the grid in use is on `rosters.Roster`.

    `succeeded` means the solver ran to its end, which may have found no roster: `result` then says why. `cancelled` may
    still hold the best roster found. Only `failed` means the solver gave no answer, and `failure` says how."""

    id = models.UUIDField(primary_key=True, db_default=UUID7(), editable=False)
    unit = models.ForeignKey("units.Unit", on_delete=models.PROTECT, related_name="solves")
    month = models.DateField(help_text="The first day of the month.")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    requested_at = models.DateTimeField(auto_now_add=True)
    time_limit_seconds = models.PositiveIntegerField()
    state = models.CharField(max_length=9, choices=SolveState, default=SolveState.QUEUED)
    # The queue's own id, which is the order solves run in: see `queue_ahead`.
    job_id = models.BigIntegerField(null=True, blank=True)
    solver_job_id = models.CharField(max_length=64, blank=True, help_text="Only while the solver holds the job in memory.")
    attempts = models.PositiveSmallIntegerField(default=0, help_text="How many times the solver was given this solve.")
    stop_requested = models.BooleanField(default=False)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    elapsed_seconds = models.FloatField(default=0)
    best_cost = models.BigIntegerField(null=True, blank=True)
    improvements = models.PositiveIntegerField(default=0)
    input = models.JSONField(help_text="The complete solve input, as the solver receives it.")
    outside_days = models.JSONField(
        default=dict, help_text="{hospital ID: [dates]}: which of a nurse's credited days were outside their dates, which the "
                                "input does not say, as it lists them with leave. No dates of leave, and no type.")
    result = models.JSONField(null=True, blank=True, help_text="The solver's result, as it answered.")
    failure = models.CharField(max_length=7, choices=SolveFailure, blank=True)
    error = models.TextField(blank=True, help_text="Why the last attempt failed, also when a retry then worked.")
    # A re-plan of an approved month: days before `replan_from` are facts, and its roster becomes a new version.
    replan_from = models.DateField(null=True, blank=True, help_text="Set only on a re-plan: the first date it plans again.")
    replan_of = models.PositiveIntegerField(null=True, blank=True, help_text="The version in force when the re-plan started, "
                                                                             "which its input holds as `published`.")
    replan_reason = models.TextField(blank=True, help_text="The manager's reason, for the version it makes. Read by the unit's "
                                                           "manager and the approvers only, as a version's reason is.")
    replan_outcome = models.CharField(max_length=10, choices=ReplanOutcome, blank=True)

    class Meta:
        ordering = ["-requested_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(month__day=1), name="solves_solve_month_starts_a_month"),
            # A second one would only replace the first one's grid when it ends.
            models.UniqueConstraint(fields=["unit", "month"], condition=models.Q(state__in=ACTIVE_STATES),
                                    name="solves_one_active_solve_a_unit_month"),
        ]

    @property
    def audit_target(self) -> str:
        return f"{self.unit.name}, {self.month:%Y-%m}"

    @property
    def queue_ahead(self) -> int | None:
        """How many solves of any unit go first. Worked out when asked rather than written by the worker, so it cannot be
        out of date when one ahead is stopped. None once this one has started."""
        if self.state != SolveState.QUEUED:
            return None
        return Solve.objects.filter(state__in=ACTIVE_STATES, job_id__lt=self.job_id).count()
