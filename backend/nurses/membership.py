"""Which unit a nurse belongs to, and when. A nurse's placements answer it month by month: the one in force is
the latest that has begun, and any after it are transfers still to come. Every question about that goes here."""
from __future__ import annotations

import datetime as dt
from uuid import UUID

from django.db.models import Exists, OuterRef, Q, QuerySet, Subquery
from django.utils import timezone

from accounts.models import User
from nurses.models import NurseProfile, Placement
from units.models import Unit


def today() -> dt.date:
    return timezone.localdate()


def this_month() -> dt.date:
    return today().replace(day=1)


def place_new_nurse(nurse: NurseProfile, unit: Unit) -> None:
    """A nurse starting later belongs to the unit from now, so their unit's manager can prepare and they can see
    it at first login. Days before the start date are the solve input's concern: see docs/ARCHITECTURE.md section 5."""
    Placement.objects.create(nurse=nurse, unit=unit, from_month=min(nurse.start_date.replace(day=1), this_month()))


def reach_back_to_start_date(nurse: NurseProfile) -> tuple[Placement, dt.date] | None:
    """A start date corrected to before the first placement would leave months with no unit, so that placement
    begins earlier. It and the month it began are returned, so the caller can say so. Those months had no unit, so
    none is rewritten. It only ever moves back: a placement before the start date means nothing, as `place_new_nurse`
    shows, and moving it forward could leave a nurse with none in force."""
    first = nurse.placements.select_related("unit").first()
    month = nurse.start_date.replace(day=1)
    if month >= first.from_month:
        return None
    began = first.from_month
    first.from_month = month
    first.save(update_fields=["from_month"])
    return first, began


def from_now_on(nurse: NurseProfile) -> list[Placement]:
    """The placement in force, then any still to come."""
    month = this_month()
    placements = list(nurse.placements.all())
    return [p for p in placements if p.from_month <= month][-1:] + [p for p in placements if p.from_month > month]


def unit_in(nurse: NurseProfile, month: dt.date) -> Unit:
    """The unit a nurse belongs to in a month, this one or a later one."""
    return [p.unit for p in nurse.placements.all() if p.from_month <= month][-1]


def transfer(nurse: NurseProfile, unit: Unit, month: dt.date) -> bool:
    """From this month on the nurse belongs to this unit, whatever was waiting for then or later: a transfer waiting
    is a plan, and the audit log keeps what it said. False when that changes nothing."""
    if unit_in(nurse, month).pk == unit.pk and not nurse.placements.filter(from_month__gt=month).exists():
        return False
    nurse.placements.filter(from_month__gte=month).delete()
    before = nurse.placements.order_by("-from_month").first()
    if before is None or before.unit_id != unit.pk:
        Placement.objects.create(nurse=nurse, unit=unit, from_month=month)
    return True


def _unit_in_force(placements: QuerySet[Placement]) -> Subquery:
    return Subquery(placements.filter(from_month__lte=this_month()).order_by("-from_month").values("unit")[:1])


def on_the_list_of(unit: Unit) -> QuerySet[NurseProfile]:
    """Who the unit's manager sees: placed there now, or due to join, deactivated or not."""
    return (NurseProfile.objects
            .annotate(placed_now=_unit_in_force(Placement.objects.filter(nurse=OuterRef("pk"))))
            .filter(Q(placed_now=unit.pk)
                    | Exists(Placement.objects.filter(nurse=OuterRef("pk"), unit=unit, from_month__gt=this_month()))))


def unit_of_nurse(user: User) -> QuerySet[Unit]:
    return Unit.objects.filter(pk=_unit_in_force(Placement.objects.filter(nurse__user=user)))


def unit_id_now(nurse: NurseProfile) -> UUID:
    return from_now_on(nurse)[0].unit_id


def placed_outside(user: User, unit_id: UUID | None) -> Unit | None:
    """The unit a manager's profile would be outside of, were they to hold this one: a manager reaches only the
    unit they hold, so a roster of another's would be one they could not see. Any profile counts, an ended one
    too, because clearing its end date would otherwise bring it back elsewhere."""
    nurse = NurseProfile.objects.filter(user=user).first()
    if nurse is None:
        return None
    return next((p.unit for p in from_now_on(nurse) if p.unit_id != unit_id), None)


def belonging_to(unit: Unit) -> QuerySet[NurseProfile]:
    """The nurses who stop a unit being archived: placed there now or due to join, and not ended. A deactivated
    nurse does not count, because nurses are never deleted and the refusal's advice would otherwise be false."""
    return (on_the_list_of(unit)
            .filter(user__is_active=True)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=today())))


def archived_unit_in_the_way(user: User) -> Unit | None:
    """The archived unit this user would land in by coming back into service, if any. Takes the lock on every unit
    they are placed in, as archiving does, so the unit cannot be archived between this answer and the change. A
    profile whose end date has passed does not count: its nurse is coming back to no unit, whatever the account does."""
    nurse = NurseProfile.objects.filter(user=user).first()
    if nurse is None or (nurse.end_date is not None and nurse.end_date < today()):
        return None
    ids = [placement.unit_id for placement in from_now_on(nurse)]
    return next((unit for unit in Unit.objects.select_for_update().filter(pk__in=ids).order_by("pk") if unit.archived),
                None)


def end_date_fits(start: dt.date, end: dt.date) -> bool:
    """On or after the start date, or today or earlier for a nurse who has not started: one added by mistake has to
    be able to end now. Ticket 11 treats that nurse as never present."""
    return end >= start or (start > today() and end <= today())


def start_date_fits(was: dt.date, start: dt.date, end: dt.date) -> bool:
    """On or before the end date, or still to come for a nurse who has not started. The exception needs both dates:
    a nurse who really worked must not be corrected into one who was never present, whose days ticket 11 drops."""
    return start <= end or (was > today() and end_date_fits(start, end))


def cancel_transfers_after(nurse: NurseProfile, day: dt.date) -> list[Placement]:
    """Those a nurse's end date has overtaken. Never the placement in force, since a nurse always has one."""
    cancelled = list(nurse.placements.select_related("unit").filter(from_month__gt=max(day, this_month())))
    nurse.placements.filter(pk__in=[placement.pk for placement in cancelled]).delete()
    return cancelled

