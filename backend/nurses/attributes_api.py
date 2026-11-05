"""The rostering attributes and opening values of a unit's nurses: its manager sets them, the CNO and the Deputy CNO read
them, and nobody else does. Gender aside, which the CNO sets (`nurses.api`). The System Admin reads the audit log and may
see no attribute, so an entry here says only whose changed. A field's name would say too much: a change to `breastfeeding`
on a nurse who was at the default can mean only one thing."""
from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from django.db import transaction
from ninja import Router, Schema
from ninja.errors import HttpError
from nurse_roster.problem import MAX_HOURS, MAX_PARAM
from pydantic import AfterValidator, Field

from accounts.authz import SignedIn
from accounts.models import Role, User
from audit.log import record
from hospital.api import StrictSchema, differing, refuse
from hospital.models import HospitalSettings
from nurses import membership
from nurses.api import with_units
from nurses.models import Gender, NurseProfile
from units.models import Unit
from units.rules import distinct_shifts
from units.scope import unit_in_scope

router = Router(tags=["nurses"])
manager = SignedIn(Role.UNIT_MANAGER)

Balance = Annotated[float, Field(ge=-MAX_PARAM, le=MAX_PARAM, allow_inf_nan=False)]


AllowedShifts = Annotated[list[str], Field(min_length=1), AfterValidator(distinct_shifts)] | None


class AllowedShiftsBody(StrictSchema):
    allowed_shifts: AllowedShifts = Field(description="Empty for any shift the unit works, now or later.")


class AttributesBody(AllowedShiftsBody):
    team_leader: bool
    score: float = Field(ge=0, le=1, allow_inf_nan=False)
    ramadan_reduced: bool
    breastfeeding: bool
    ytd_overtime: int = Field(ge=0, le=MAX_HOURS, description="Overtime hours this year.")
    hours_balance: int = Field(ge=-MAX_HOURS, le=MAX_HOURS, description="Hours still owed (+) or worked ahead (-).")
    night_balance: Balance = Field(description="Night shifts above (+) or below (-) their fair share.")
    friday_balance: Balance = Field(description="Weekend days above (+) or below (-) their fair share.")


class NurseAttributesRow(Schema):
    id: UUID
    hospital_id: str
    full_name: str
    is_active: bool
    gender: Literal[Gender.FEMALE, Gender.MALE] = Field(description="The CNO's to set: it is here to read.")
    joins_from: str | None = Field(description="YYYY-MM, for a nurse due to join. Until then only their allowed shifts "
                                               "here are this unit's to set.")
    leaves_from: str | None = Field(description="YYYY-MM, for a nurse due to leave. Names no other unit.")
    team_leader: bool
    score: float
    ramadan_reduced: bool
    breastfeeding: bool
    ytd_overtime: int
    hours_balance: int
    night_balance: float
    friday_balance: float
    allowed_shifts: list[str] | None = Field(description="In this unit. Empty for any shift it works.")
    allowed_shifts_to_check: bool = Field(description="A transfer emptied the list, as none of its shifts are worked here.")


def _row(nurse: NurseProfile, unit: Unit) -> NurseAttributesRow:
    current, *coming = membership.from_now_on(nurse)
    here = membership.here_from_now_on(nurse, unit)[0]
    joins = here.from_month if current.unit_id != unit.pk else None
    leaves = next((placement.from_month for placement in coming if placement.unit_id != unit.pk), None) if not joins else None
    user = nurse.user
    return NurseAttributesRow(
        id=nurse.pk, hospital_id=user.username, full_name=user.full_name, is_active=user.is_active, gender=nurse.gender,
        joins_from=joins.strftime("%Y-%m") if joins else None, leaves_from=leaves.strftime("%Y-%m") if leaves else None,
        team_leader=nurse.team_leader, score=nurse.score, ramadan_reduced=nurse.ramadan_reduced,
        breastfeeding=nurse.breastfeeding, ytd_overtime=nurse.ytd_overtime, hours_balance=nurse.hours_balance,
        night_balance=nurse.night_balance, friday_balance=nurse.friday_balance,
        allowed_shifts=here.allowed_shifts, allowed_shifts_to_check=here.allowed_shifts_to_check)


def _row_as_saved(nurse_id: UUID, unit: Unit) -> NurseAttributesRow:
    return _row(with_units(NurseProfile.objects).get(pk=nurse_id), unit)


def _nurse_to_change(user: User, unit_id: UUID, nurse_id: UUID) -> tuple[Unit, NurseProfile]:
    """The same 403 whether another unit's nurse exists or not. The nurse's lock comes before the check, because a transfer
    and an end date change who is on this list under it, and the account's with it, as they take them."""
    unit = unit_in_scope(user, unit_id)
    NurseProfile.objects.select_for_update(of=("self", "user")).select_related("user").filter(pk=nurse_id).first()
    if not membership.on_the_list_of(unit).filter(pk=nurse_id).exists():
        raise HttpError(403, "This nurse is not in your unit.")
    return unit, with_units(NurseProfile.objects).get(pk=nurse_id)


def _refuse_shifts_outside(unit: Unit, allowed: list[str] | None) -> None:
    refused = [(("allowed_shifts", index), f"{code} is not one of this unit's shifts.")
               for index, code in enumerate(allowed or []) if code not in unit.rules["shifts"]]
    if refused:
        refuse(*refused)


@router.get("/{unit_id}/nurses", response=list[NurseAttributesRow], auth=SignedIn(Role.UNIT_MANAGER, Role.CNO, Role.DEPUTY_CNO),
            operation_id="listNurseAttributes")
def list_nurse_attributes(request, unit_id: UUID) -> list[NurseAttributesRow]:
    """Those placed here now or due to join, deactivated or not, as on the manager's list of nurses."""
    unit = unit_in_scope(request.user, unit_id)
    return [_row(nurse, unit) for nurse in with_units(membership.on_the_list_of(unit))]


@router.put("/{unit_id}/nurses/{nurse_id}/attributes", response=NurseAttributesRow, auth=manager,
            operation_id="updateNurseAttributes")
def update_nurse_attributes(request, unit_id: UUID, nurse_id: UUID, body: AttributesBody) -> NurseAttributesRow:
    """A manager with a nurse profile sets their own, because nobody else may and a nurse has to have them. The CNO and the
    Deputy CNO can read the values, and the log shows whose hand changed them. Ticket 21 refuses the opening values here
    once the nurse's first month has closed."""
    with transaction.atomic():
        HospitalSettings.load(for_update=True)
        unit, nurse = _nurse_to_change(request.user, unit_id, nurse_id)
        if membership.unit_id_now(nurse) != unit.pk:
            raise HttpError(403, "Until this nurse joins, their current unit's manager sets everything but their shifts here.")
        _refuse_shifts_outside(unit, body.allowed_shifts)
        fields = body.model_dump(exclude={"allowed_shifts"})
        _, changing = differing({name: getattr(nurse, name) for name in fields}, fields)
        for name, value in changing.items():
            setattr(nurse, name, value)
        if changing:
            nurse.save(update_fields=list(changing))
        shifts_changed = membership.set_allowed_shifts(nurse, unit, body.allowed_shifts)
        if changing or shifts_changed:
            record("nurse.attributes_changed", actor=request.user, target=nurse.user.username, request=request)
    return _row_as_saved(nurse_id, unit)


@router.put("/{unit_id}/nurses/{nurse_id}/allowed-shifts", response=NurseAttributesRow, auth=manager,
            operation_id="updateNurseAllowedShifts")
def update_nurse_allowed_shifts(request, unit_id: UUID, nurse_id: UUID, body: AllowedShiftsBody) -> NurseAttributesRow:
    """All a manager can change of a nurse due to join: a unit may roster a month ahead of their arrival, and this list is
    about this unit's shifts, whereas the rest is about the nurse and stays with the manager of the unit they are in."""
    with transaction.atomic():
        HospitalSettings.load(for_update=True)
        unit, nurse = _nurse_to_change(request.user, unit_id, nurse_id)
        _refuse_shifts_outside(unit, body.allowed_shifts)
        if membership.set_allowed_shifts(nurse, unit, body.allowed_shifts):
            record("nurse.attributes_changed", actor=request.user, target=nurse.user.username, request=request)
    return _row_as_saved(nurse_id, unit)
