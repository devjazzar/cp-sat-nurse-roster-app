"""How a nurse's current skills read, wherever someone may read them: see `nurses.skills_api`."""
from __future__ import annotations

import datetime as dt
from uuid import UUID

from django.db.models import Prefetch
from django.utils import timezone
from ninja import Field, Schema

from nurses.models import NurseSkill


class NurseSkillRow(Schema):
    skill_id: UUID
    name: str
    expires: bool = Field(description="The catalogue's: whether the kind has an expiry.")
    required_to_work: bool = Field(description="The catalogue's: from the day after its expiry, she works no shift.")
    active: bool = Field(description="False once the CNO has retired the skill. Her record of it stays.")
    expiry: dt.date | None = Field(description="The last day it counts. Null for a kind that does not expire, even when a date "
                                               "recorded while it did is kept.")


def counted_expiry(row: NurseSkill) -> dt.date | None:
    """Her record's expiry as it counts: none for a kind that does not expire, whatever date is kept from when it did."""
    return row.expiry if row.skill.expires else None


def as_rows(rows) -> list[NurseSkillRow]:
    """`rows`: her current `NurseSkill`s with their skills."""
    return [NurseSkillRow(skill_id=row.skill.pk, name=row.skill.name, expires=row.skill.expires,
                          required_to_work=row.skill.required_to_work, active=row.skill.active,
                          expiry=counted_expiry(row))
            for row in sorted(rows, key=lambda row: (row.skill.name.lower(), row.skill.pk))]


def current_skills():
    """A prefetch for a list of nurses: `nurse.current_skills` is then each one's current rows, with their skills."""
    return Prefetch("skills", queryset=NurseSkill.objects.current().select_related("skill"), to_attr="current_skills")


def skills_of(nurse) -> list[NurseSkillRow]:
    """Her current skills: from `current_skills()` when the list prefetched them, or read here."""
    rows = getattr(nurse, "current_skills", None)
    if rows is None:
        rows = NurseSkill.objects.current().filter(nurse=nurse).select_related("skill")
    return as_rows(rows)


def end_record(row: NurseSkill, user) -> None:
    """A renewal or a removal ends her record of a skill rather than rewriting or deleting it (`NurseSkill`)."""
    row.removed_at, row.removed_by = timezone.now(), user
    row.save(update_fields=["removed_at", "removed_by"])
