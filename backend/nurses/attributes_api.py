"""The rostering attributes and opening values of a unit's nurses: its manager sets them, the CNO and the Deputy CNO read
them, and nobody else does. Gender aside, which the CNO sets (`nurses.api`). The System Admin reads the audit log and may
see no attribute, so an entry here says only whose changed. A field's name would say too much: a change to `breastfeeding`
on a nurse who was at the default can mean only one thing. Her probation is the exception (ticket 54): its length, extension
and end are logged with their values, as the user decided on 2026-11-11."""
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
from closes.chain import has_closed
from hospital.api import StrictSchema, differing, refuse
from hospital.models import HospitalSettings
from nurses import membership, probation
from nurses.api import Probation, probation_of, with_units
from nurses.models import Gender, NurseProfile
from nurses.skills import NurseSkillRow, skills_of
from rosters.pins import outside_allowed, words_for
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
    opening_values_locked: bool = Field(description="Their first month has closed: the opening values (`ytd_overtime`, "
                                                    "`hours_balance`, `night_balance`, `friday_balance`) can no longer change, "
                                                    "as the carry-over comes from the closes now.")
    skills: list[NurseSkillRow] = Field(description="Their current skills, to read: the CNO sets them on the Nurses page.")
    probation: Probation | None = Field(description="Empty when she is not on probation, or it is over. Her unit manager sets "
                                                    "its length, extends it and ends it; the CNO ticks it.")


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
        allowed_shifts=here.allowed_shifts, allowed_shifts_to_check=here.allowed_shifts_to_check,
        opening_values_locked=has_closed(nurse), skills=skills_of(nurse), probation=probation_of(nurse))


OPENING_VALUES = ("ytd_overtime", "hours_balance", "night_balance", "friday_balance")


def _refuse_opening_values(nurse: NurseProfile, changing: dict) -> None:
    """Editable until her first month closes (ticket 21). They travel in one body with the attributes, so a save that leaves them
    as they are goes through, and only a field that changes is refused."""
    locked = [name for name in OPENING_VALUES if name in changing]
    if locked and has_closed(nurse):
        refuse(*[((name,), f"{nurse.user.full_name}'s first month has closed, so their opening values can no longer change: "
                           "each month now starts from the carry-over of the one before.") for name in locked])


def _row_as_saved(nurse_id: UUID, unit: Unit) -> NurseAttributesRow:
    return _row(with_units(NurseProfile.objects).get(pk=nurse_id), unit)


def _nurse_to_change(user: User, unit_id: UUID, nurse_id: UUID) -> tuple[Unit, NurseProfile]:
    """The same 403 whether another unit's nurse exists or not. The nurse's lock comes before the check, because a transfer
    and an end date change who is on this list under it, and the account's with it, as they take them."""
    unit = unit_in_scope(user, unit_id)
    NurseProfile.objects.select_for_update(of=("self", "user"), no_key=True).select_related("user").filter(pk=nurse_id).first()
    if not membership.on_the_list_of(unit).filter(pk=nurse_id).exists():
        raise HttpError(403, "This nurse is not in your unit.")
    return unit, with_units(NurseProfile.objects).get(pk=nurse_id)


def _refuse_shifts_outside(unit: Unit, nurse: NurseProfile, allowed: list[str] | None) -> None:
    refused = [(("allowed_shifts", index), f"{code} is not one of this unit's shifts.")
               for index, code in enumerate(allowed or []) if code not in unit.rules["shifts"]]
    if refused:
        refuse(*refused)
    if allowed == [unit.rules.get("night_shift")] and probation.running(nurse):
        refuse((("allowed_shifts",), f"{nurse.user.full_name} is on probation, and a nurse on probation does not work "
                                     f"{allowed[0]}, the night shift, so it alone would leave her no shift."))
    pinned = outside_allowed(nurse, unit, allowed)
    if pinned:
        refuse((("allowed_shifts",), f"A pin holds a shift this leaves out: {words_for(pinned)}. "
                                     "Clear it on the Roster page first."))


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
    Deputy CNO can read the values, and the log shows whose hand changed them. The opening values are refused, on their fields
    alone, once the nurse's first month has closed."""
    with transaction.atomic():
        HospitalSettings.load(for_update=True)
        unit, nurse = _nurse_to_change(request.user, unit_id, nurse_id)
        if membership.unit_id_now(nurse) != unit.pk:
            raise HttpError(403, "Until this nurse joins, their current unit's manager sets everything but their shifts here.")
        _refuse_shifts_outside(unit, nurse, body.allowed_shifts)
        fields = body.model_dump(exclude={"allowed_shifts"})
        _, changing = differing({name: getattr(nurse, name) for name in fields}, fields)
        _refuse_opening_values(nurse, changing)
        for name, value in changing.items():
            setattr(nurse, name, value)
        nurse.attributes_saved = True  # A save that changes nothing still says someone looked: see ticket 11.
        nurse.save(update_fields=[*changing, "attributes_saved"])
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
        _refuse_shifts_outside(unit, nurse, body.allowed_shifts)
        if membership.set_allowed_shifts(nurse, unit, body.allowed_shifts):
            record("nurse.attributes_changed", actor=request.user, target=nurse.user.username, request=request)
    return _row_as_saved(nurse_id, unit)


# ---- her probation: the unit manager's -----------------------------------------------------------------------------------
class LengthBody(StrictSchema):
    months: int = Field(ge=probation.FIRST_LENGTHS[0], le=probation.FIRST_LENGTHS[-1],
                        description="1, 2 or 3, while it stands at 3 or less. Beyond, it is extended a month at a time.")


def _probation_to_change(request, unit_id: UUID, nurse_id: UUID) -> tuple[Unit, NurseProfile]:
    """Her current unit's manager's, as her other attributes are: not a unit she is due to join."""
    unit, nurse = _nurse_to_change(request.user, unit_id, nurse_id)
    if membership.unit_id_now(nurse) != unit.pk:
        raise HttpError(403, "Until this nurse joins, their current unit's manager sets her probation.")
    name = nurse.user.full_name
    if not probation.running(nurse):
        refuse((("probation",), f"{name} is not on probation."))
    if probation.ended_early(nurse):
        refuse((("probation",), f"{name}'s probation was ended early, on {probation.last_day(nurse):%-d %B %Y}, "
                                "so it can no longer change."))
    return unit, nurse


def _save_probation(request, nurse: NurseProfile, action: str, was: dict) -> None:
    nurse.save(update_fields=["probation_months", "probation_ended_in"])
    record(action, actor=request.user, target=nurse.user.username, request=request, before=was,
           after=probation.describe(nurse))


@router.put("/{unit_id}/nurses/{nurse_id}/probation/length", response=NurseAttributesRow, auth=manager,
            operation_id="setProbationLength")
def set_probation_length(request, unit_id: UUID, nurse_id: UUID, body: LengthBody) -> NurseAttributesRow:
    """Refused once extended beyond 3, and for a length that would have ended it before this month: End does that."""
    with transaction.atomic():
        unit, nurse = _probation_to_change(request, unit_id, nurse_id)
        name = nurse.user.full_name
        if nurse.probation_months > probation.FIRST_LENGTHS[-1]:
            refuse((("months",), f"{name}'s probation is extended to {nurse.probation_months} months. Extend it again or "
                                 "end it."))
        last = probation.last_day_after(nurse.start_date, body.months)
        if last < membership.this_month():
            refuse((("months",), f"{body.months} month{'' if body.months == 1 else 's'} would have ended {name}'s probation on "
                                 f"{last:%-d %B %Y}, before this month. End it instead, at the end of this month."))
        if body.months != nurse.probation_months:
            was = probation.describe(nurse)
            nurse.probation_months = body.months
            _save_probation(request, nurse, "nurse.probation_length_set", was)
    return _row_as_saved(nurse_id, unit)


@router.post("/{unit_id}/nurses/{nurse_id}/probation/extend", response=NurseAttributesRow, auth=manager,
             operation_id="extendProbation")
def extend_probation(request, unit_id: UUID, nurse_id: UUID) -> NurseAttributesRow:
    """One month at a time, to 6 at most."""
    with transaction.atomic():
        unit, nurse = _probation_to_change(request, unit_id, nurse_id)
        if nurse.probation_months >= probation.LONGEST:
            refuse((("probation",), f"{nurse.user.full_name}'s probation is {probation.LONGEST} months, the longest it can be."))
        was = probation.describe(nurse)
        nurse.probation_months += 1
        _save_probation(request, nurse, "nurse.probation_extended", was)
    return _row_as_saved(nurse_id, unit)


@router.post("/{unit_id}/nurses/{nurse_id}/probation/end", response=NurseAttributesRow, auth=manager,
             operation_id="endProbation")
def end_probation(request, unit_id: UUID, nurse_id: UUID) -> NurseAttributesRow:
    """Its last day becomes the last day of the month under way on the hospital's clock, so that month keeps its roster. Refused
    before the month she starts in, when there is no month of it under way: the CNO unticks it."""
    with transaction.atomic():
        unit, nurse = _probation_to_change(request, unit_id, nurse_id)
        month = membership.this_month()
        if month < nurse.start_date.replace(day=1):
            refuse((("probation",), f"{nurse.user.full_name}'s probation begins on her start date, "
                                    f"{nurse.start_date:%-d %B %Y}. If she is not to be on probation, the CNO unticks it."))
        was = probation.describe(nurse)
        nurse.probation_ended_in = month
        _save_probation(request, nurse, "nurse.probation_ended", was)
    return _row_as_saved(nurse_id, unit)
