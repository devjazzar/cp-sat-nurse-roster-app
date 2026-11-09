"""A nurse's skills: the CNO records, renews and takes them off; her unit manager (and the manager of a unit she is due to join)
and the Deputy CNO read them on the rows they already read (`nurses.api.NurseRow`, `nurses.attributes_api.NurseAttributesRow`);
she reads her own here. The System Admin reads the audit log, so an entry says only whose skills changed and by whom: never
which skill or date, since a skill's lapse says something about a person.

The skills are on the profile, not a placement, so they follow her across a transfer and stay when she is deactivated or ends.
Every write takes the catalogue's lock before the nurse's, as `hospital.catalogue_api.update_skill` and a transfer take them,
so a record and a change of the skill's `expires` or `active` cannot pass each other."""
from __future__ import annotations

import datetime as dt
from uuid import UUID

from django.db import transaction
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Field, Router, Status
from ninja.errors import HttpError

from accounts.authz import SignedIn
from accounts.models import Role, User
from audit.log import record
from hospital.api import refuse
from hospital.catalogue_api import IsoDate
from hospital.models import HospitalSettings, Skill
from nurses.api import Body
from nurses.models import NurseProfile, NurseSkill
from nurses.skills import NurseSkillRow, as_rows, skills_of

router = Router(tags=["nurses"])
cno = SignedIn(Role.CNO)


class NewNurseSkillBody(Body):
    skill_id: UUID
    expiry: IsoDate | None = Field(description="Required when the skill expires; empty when it does not.")


class NurseSkillChangeBody(Body):
    expiry: IsoDate | None


def _locked_nurse(nurse_id: UUID) -> NurseProfile:
    return get_object_or_404(NurseProfile.objects.select_for_update(of=("self", "user"), no_key=True).select_related("user"),
                             pk=nurse_id)


def _refuse_expiry(skill: Skill, expiry: dt.date | None) -> None:
    if skill.expires and expiry is None:
        refuse((("expiry",), f"{skill.name} expires. Enter the last day it counts."))
    if not skill.expires and expiry is not None:
        refuse((("expiry",), f"{skill.name} does not expire, so it takes no expiry."))


def _held(nurse: NurseProfile, skill_id: UUID) -> NurseSkill:
    """A 409, as for leave changed since the page opened: acting on it could undo someone's correction."""
    row = NurseSkill.objects.current().filter(nurse=nurse, skill_id=skill_id).select_related("skill").first()
    if row is None:
        raise HttpError(409, f"{nurse.user.full_name} does not hold this skill now. Reload the page to see their skills as they are.")
    return row


def _end(row: NurseSkill, user: User) -> None:
    row.removed_at, row.removed_by = timezone.now(), user
    row.save(update_fields=["removed_at", "removed_by"])


def _changed(request: HttpRequest, nurse: NurseProfile) -> None:
    record("nurse.skills_changed", actor=request.user, target=nurse.user.username, request=request)


@router.post("/{nurse_id}/skills", response={201: list[NurseSkillRow]}, auth=cno, operation_id="recordNurseSkill")
def record_skill(request: HttpRequest, nurse_id: UUID, body: NewNurseSkillBody) -> Status:
    """Any nurse's, a manager with a nurse profile's too, deactivated or not: a returning nurse has her record. Answers with all
    her skills as they now are."""
    with transaction.atomic():
        HospitalSettings.load(for_update=True)
        nurse = _locked_nurse(nurse_id)
        skill = Skill.objects.filter(pk=body.skill_id).first()
        if skill is None:
            refuse((("skill_id",), "Choose a skill from the list."))
        if not skill.active:
            refuse((("skill_id",), f"{skill.name} is retired, so it can no longer be recorded."))
        if NurseSkill.objects.current().filter(nurse=nurse, skill=skill).exists():
            refuse((("skill_id",), f"{nurse.user.full_name} already holds {skill.name}. Change or take off the one recorded."))
        _refuse_expiry(skill, body.expiry)
        NurseSkill.objects.create(nurse=nurse, skill=skill, expiry=body.expiry, recorded_by=request.user)
        _changed(request, nurse)
        return Status(201, skills_of(nurse))


@router.put("/{nurse_id}/skills/{skill_id}", response=list[NurseSkillRow], auth=cno, operation_id="renewNurseSkill")
def renew_skill(request: HttpRequest, nurse_id: UUID, skill_id: UUID, body: NurseSkillChangeBody) -> list[NurseSkillRow]:
    """A renewal or a correction of the expiry: the row ends and another begins, as leave's does. Saving it as it reads (for a
    kind that no longer expires, with no date, whatever is kept) changes nothing."""
    with transaction.atomic():
        HospitalSettings.load(for_update=True)
        nurse = _locked_nurse(nurse_id)
        row = _held(nurse, skill_id)
        skill = row.skill
        if body.expiry == (row.expiry if skill.expires else None):
            return skills_of(nurse)
        if not skill.active:
            refuse((("expiry",), f"{skill.name} is retired, so it can no longer be renewed."))
        _refuse_expiry(skill, body.expiry)
        _end(row, request.user)
        NurseSkill.objects.create(nurse=nurse, skill=skill, expiry=body.expiry, recorded_by=request.user)
        _changed(request, nurse)
        return skills_of(nurse)


@router.post("/{nurse_id}/skills/{skill_id}/remove", response=list[NurseSkillRow], auth=cno, operation_id="removeNurseSkill")
def remove_skill(request: HttpRequest, nurse_id: UUID, skill_id: UUID) -> list[NurseSkillRow]:
    """A retired skill's too: a record made in error comes off. The row ends, and stays as the record of what was there."""
    with transaction.atomic():
        HospitalSettings.load(for_update=True)
        nurse = _locked_nurse(nurse_id)
        _end(_held(nurse, skill_id), request.user)
        _changed(request, nurse)
        return skills_of(nurse)


@router.get("/my-skills", response=list[NurseSkillRow], auth=SignedIn(Role.STAFF_NURSE, Role.UNIT_MANAGER),
            operation_id="getMySkills")
def my_skills(request: HttpRequest) -> list[NurseSkillRow]:
    """Takes no nurse, so it cannot answer for a colleague. A manager is here because a manager with a nurse profile is a nurse
    too; one with no profile simply has none."""
    return as_rows(NurseSkill.objects.current().filter(nurse__user=request.user).select_related("skill"))

