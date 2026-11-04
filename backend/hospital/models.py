import copy

from django.db import models

from hospital.rules import DEFAULT_RULES


def default_rules() -> dict:
    return copy.deepcopy(DEFAULT_RULES)


class HospitalSettings(models.Model):
    """One row, reached only through `load`. `rules` is written only through the API's schema."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    rules = models.JSONField(default=default_rules)
    rules_need_review = models.BooleanField(default=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name="hospital_settings_one_row")]

    @classmethod
    def load(cls, *, for_update: bool = False) -> "HospitalSettings":
        objects = cls.objects.select_for_update() if for_update else cls.objects
        return objects.get_or_create(pk=1)[0]
