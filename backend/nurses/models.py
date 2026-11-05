import datetime as dt

from django.conf import settings
from django.db import models
from django.db.models.functions import UUID7


class Gender(models.TextChoices):
    # The solver's own two values: see `gender` in solver/nurse_roster/problem.py.
    FEMALE = "F", "Female"
    MALE = "M", "Male"


class NurseProfile(models.Model):
    """A user's roster identity. The hospital ID is the user's username, so there is one place for it and
    usernames already keep it unique in any case. The unit is not here: see `Placement`. Nor are the allowed shifts,
    which only mean something in a unit. The rest of the rostering attributes and the opening values keep the solver's
    field names and its defaults, and no value of theirs may reach `audit.log.record`: the System Admin reads the log."""

    id = models.UUIDField(primary_key=True, db_default=UUID7(), editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="nurse_profile")
    gender = models.CharField(max_length=1, choices=Gender)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    team_leader = models.BooleanField(default=False)
    score = models.FloatField(default=0.8)
    ramadan_reduced = models.BooleanField(default=False)
    breastfeeding = models.BooleanField(default=False)
    ytd_overtime = models.IntegerField(default=0, help_text="Overtime hours this year, as of the day they were added.")
    hours_balance = models.IntegerField(default=0, help_text="Hours still owed (+) or worked ahead (-).")
    night_balance = models.FloatField(default=0.0, help_text="Night shifts above (+) or below (-) their fair share.")
    friday_balance = models.FloatField(default=0.0, help_text="Weekend days above (+) or below (-) their fair share.")
    attributes_saved = models.BooleanField(
        default=False, help_text="A manager has saved these attributes at least once, so a score at the default was looked at.")


class Placement(models.Model):
    """From this month on, until a later placement of the same nurse, the nurse belongs to this unit. A transfer
    takes effect from a chosen month, so a coming one has to wait here: see `nurses.membership`."""

    id = models.UUIDField(primary_key=True, db_default=UUID7(), editable=False)
    nurse = models.ForeignKey(NurseProfile, on_delete=models.PROTECT, related_name="placements")
    unit = models.ForeignKey("units.Unit", on_delete=models.PROTECT, related_name="placements")
    from_month = models.DateField(help_text="The first day of the month.")
    # On the placement because a list only means something in a unit, and two units can each roster their own months
    # of a nurse at once: see `membership.transfer`. Empty means any shift this unit works; never an empty list.
    allowed_shifts = models.JSONField(null=True, blank=True)
    allowed_shifts_to_check = models.BooleanField(
        default=False, help_text="A transfer found none of the list's shifts in this unit, so the list was emptied.")

    class Meta:
        ordering = ["from_month"]
        constraints = [
            models.UniqueConstraint(fields=["nurse", "from_month"], name="nurses_one_placement_a_month"),
            models.CheckConstraint(condition=models.Q(from_month__day=1), name="nurses_placement_starts_a_month"),
        ]


class LeaveQuerySet(models.QuerySet):
    def current(self) -> "LeaveQuerySet":
        return self.filter(removed_at__isnull=True)

    def in_month(self, month: dt.date) -> "LeaveQuerySet":
        return self.filter(date__year=month.year, date__month=month.month)


class Leave(models.Model):
    """One date a nurse is off for a recorded reason. A correction or a removal ends the row rather than rewriting or
    deleting it, because the audit log may hold neither the date nor the type (the System Admin reads it), so this is
    the only record of what was there. Only `current()` rows mean anything to anyone. The unit is not here: the manager
    of a date is whoever runs its month, which a placement says (`nurses.membership.placement_in`)."""

    id = models.UUIDField(primary_key=True, db_default=UUID7(), editable=False)
    nurse = models.ForeignKey(NurseProfile, on_delete=models.PROTECT, related_name="leave")
    date = models.DateField()
    leave_type = models.ForeignKey("hospital.LeaveType", on_delete=models.PROTECT, related_name="+")
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    recorded_at = models.DateTimeField(auto_now_add=True)
    removed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    removed_at = models.DateTimeField(null=True, blank=True)

    objects = LeaveQuerySet.as_manager()

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=["nurse", "date"], condition=models.Q(removed_at__isnull=True),
                                    name="nurses_one_leave_a_day"),
        ]
