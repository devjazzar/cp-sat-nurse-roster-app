from django.conf import settings
from django.db import models
from django.db.models.functions import UUID7, Lower


class Unit(models.Model):
    """A nursing unit. Never deleted, only archived, and an archived unit has no manager, so a manager's
    unit is always a live one. `rules` is the solver's `department` block but for its name: see `units.rules`."""

    id = models.UUIDField(primary_key=True, db_default=UUID7(), editable=False)
    name = models.CharField(max_length=100)
    archived = models.BooleanField(default=False)
    # At most one each way. A unit waits with none until the CNO assigns one: see docs/ARCHITECTURE.md section 3.
    manager = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
                                   related_name="managed_unit")
    rules = models.JSONField()
    rules_need_review = models.BooleanField(default=True)

    class Meta:
        ordering = ["archived", Lower("name")]
        constraints = [
            # A hospital can close a unit and open another under its name; two live ones would be confused.
            models.UniqueConstraint(Lower("name"), condition=models.Q(archived=False),
                                    name="units_live_unit_name_any_case"),
            models.CheckConstraint(condition=models.Q(archived=False) | models.Q(manager__isnull=True),
                                   name="units_archived_unit_has_no_manager"),
        ]

    def nurse_count(self) -> int:
        """How many nurses belong to this unit, which is what stops it being archived."""
        from nurses.membership import belonging_to  # That module's models point here.
        return belonging_to(self).count()
