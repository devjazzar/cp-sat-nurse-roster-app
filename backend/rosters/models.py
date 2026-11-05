from django.db import models
from django.db.models.functions import UUID7


class RosterState(models.TextChoices):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"


class Roster(models.Model):
    """A unit's plan for one month. `grid` is the one in use and follows a shift's rename, unlike the stored result it came from.
    Roster versions begin at the first approval (ticket 14): until then each solve replaces the grid, and the solve history
    keeps what it replaced."""

    id = models.UUIDField(primary_key=True, db_default=UUID7(), editable=False)
    unit = models.ForeignKey("units.Unit", on_delete=models.PROTECT, related_name="rosters")
    month = models.DateField(help_text="The first day of the month.")
    state = models.CharField(max_length=9, choices=RosterState, default=RosterState.DRAFT)
    grid = models.JSONField(help_text='{hospital ID: {date: shift code or ""}}, the shape of a result\'s roster.')
    solve = models.ForeignKey("solves.Solve", on_delete=models.PROTECT, related_name="+",
                              help_text="The solve that produced this grid.")
    restored_at = models.DateTimeField(null=True, blank=True, help_text="When the manager last restored `solve`'s result as "
                                                                        "this grid. A solve replacing it clears this.")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["unit", "month"], name="rosters_one_roster_a_unit_month"),
            models.CheckConstraint(condition=models.Q(month__day=1), name="rosters_roster_month_starts_a_month"),
        ]
