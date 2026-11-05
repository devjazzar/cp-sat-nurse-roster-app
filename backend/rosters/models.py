import datetime as dt

from django.conf import settings
from django.db import models
from django.db.models.functions import UUID7


class RosterState(models.TextChoices):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"


class PinOrigin(models.TextChoices):
    MANAGER = "manager"
    REQUEST = "request"
    SWAP = "swap"


class PinEnded(models.TextChoices):
    CLEARED = "cleared"
    REPLACED = "replaced", "Another pin took its place."
    LEAVE = "leave", "Leave recorded on its date, which wins over a pin."


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
    updated_at = models.DateTimeField(auto_now=True, help_text="When a solve or a restore last replaced the grid. A hand edit "
                                                               "does not move it, so a failed solve before one is still news.")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["unit", "month"], name="rosters_one_roster_a_unit_month"),
            models.CheckConstraint(condition=models.Q(month__day=1), name="rosters_roster_month_starts_a_month"),
        ]


class PinnedCellQuerySet(models.QuerySet):
    def current(self) -> "PinnedCellQuerySet":
        return self.filter(removed_at__isnull=True)

    def in_month(self, month: dt.date) -> "PinnedCellQuerySet":
        return self.filter(date__year=month.year, date__month=month.month)


class PinnedCell(models.Model):
    """A nurse's shift, or day off when `shift` is null, on one date, fixed by a unit's manager or by an accepted request or
    swap: the solver may not change it. The shift is a key, so a rename needs nothing here. The row belongs to the unit whose
    month it is, so a nurse transferred out does not take it along. Nothing is hard-deleted: a pin that ends keeps its row, since
    the audit log may say nothing of what it held (`rosters.pins`)."""

    id = models.UUIDField(primary_key=True, db_default=UUID7(), editable=False)
    unit = models.ForeignKey("units.Unit", on_delete=models.PROTECT, related_name="pins")
    nurse = models.ForeignKey("nurses.NurseProfile", on_delete=models.PROTECT, related_name="pins")
    date = models.DateField()
    shift = models.ForeignKey("hospital.Shift", on_delete=models.PROTECT, null=True, blank=True, related_name="pins")
    origin = models.CharField(max_length=7, choices=PinOrigin, default=PinOrigin.MANAGER)
    pinned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    pinned_at = models.DateTimeField(auto_now_add=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    removed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    removed_why = models.CharField(max_length=8, choices=PinEnded, blank=True)

    objects = PinnedCellQuerySet.as_manager()

    class Meta:
        ordering = ["date", "id"]
        constraints = [
            models.UniqueConstraint(fields=["nurse", "date"], condition=models.Q(removed_at__isnull=True),
                                    name="rosters_one_current_pin_a_nurse_date"),
        ]

    @property
    def code(self) -> str:
        return self.shift.code if self.shift else ""
