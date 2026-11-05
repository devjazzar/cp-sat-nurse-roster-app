from django.conf import settings
from django.db import models
from django.db.models.functions import UUID7


class Gender(models.TextChoices):
    # The solver's own two values: see `gender` in solver/nurse_roster/problem.py.
    FEMALE = "F", "Female"
    MALE = "M", "Male"


class NurseProfile(models.Model):
    """A user's roster identity. The hospital ID is the user's username, so there is one place for it and
    usernames already keep it unique in any case. The unit is not here: see `Placement`."""

    id = models.UUIDField(primary_key=True, db_default=UUID7(), editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="nurse_profile")
    gender = models.CharField(max_length=1, choices=Gender)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)


class Placement(models.Model):
    """From this month on, until a later placement of the same nurse, the nurse belongs to this unit. A transfer
    takes effect from a chosen month, so a coming one has to wait here: see `nurses.membership`."""

    id = models.UUIDField(primary_key=True, db_default=UUID7(), editable=False)
    nurse = models.ForeignKey(NurseProfile, on_delete=models.PROTECT, related_name="placements")
    unit = models.ForeignKey("units.Unit", on_delete=models.PROTECT, related_name="placements")
    from_month = models.DateField(help_text="The first day of the month.")

    class Meta:
        ordering = ["from_month"]
        constraints = [
            models.UniqueConstraint(fields=["nurse", "from_month"], name="nurses_one_placement_a_month"),
            models.CheckConstraint(condition=models.Q(from_month__day=1), name="nurses_placement_starts_a_month"),
        ]
