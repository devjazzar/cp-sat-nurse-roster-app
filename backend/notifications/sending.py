"""The one way to tell users something. Call `notify` inside the transaction that makes the change, after its audit entry, so a
change rolled back tells nobody. The recipients of each event that exists are worked out here, next to each other."""
from __future__ import annotations

import datetime as dt
from collections.abc import Iterable
from uuid import UUID

from accounts.models import Role, User
from notifications.models import Event, Notification, SolveOutcome
from nurses import membership
from units.models import Unit


def notify(users: Iterable[User | None], event: Event, **payload) -> int:
    """Each active user once, whatever the list repeats: a manager with a nurse profile is a nurse of the month too. A
    deactivated user is told nothing, as they can read nothing. Payload values are identifiers and numbers only."""
    seen, rows = set(), []
    for user in users:
        if user is None or not user.is_active or user.pk in seen:
            continue
        seen.add(user.pk)
        rows.append(Notification(user=user, event=event, payload=payload))
    Notification.objects.bulk_create(rows)
    return len(rows)


def _about(unit: Unit, month: dt.date) -> dict:
    return {"unit_id": str(unit.pk), "month": month.strftime("%Y-%m")}


def roster_submitted(unit: Unit, month: dt.date, by: User) -> None:
    """To the CNO and the Deputy CNO, who decide."""
    notify(User.objects.filter(role__in=(Role.CNO, Role.DEPUTY_CNO)), Event.ROSTER_SUBMITTED, **_about(unit, month),
           by=str(by.pk))


def roster_approved(unit: Unit, month: dt.date, by: User) -> None:
    """To the unit's manager and every nurse of the unit's month, a nurse due to join included (`membership.placed_in`). No
    version number: a later one would make it untrue, and the page says which is in force."""
    nurses = User.objects.filter(nurse_profile__in=membership.placed_in(unit, month))
    notify([unit.manager, *nurses], Event.ROSTER_APPROVED, **_about(unit, month), by=str(by.pk))


def roster_changed(unit: Unit, month: dt.date, by: User) -> None:
    """To every nurse of the unit's month, as an approval is, but not to whoever made the change, who knows. Never the reason,
    the cells or whose they are, since a cell taken off can be leave and a colleague must not learn that: each nurse reads their
    own row on My roster. No version number, which a later version would make untrue."""
    nurses = User.objects.filter(nurse_profile__in=membership.placed_in(unit, month)).exclude(pk=by.pk)
    notify(nurses, Event.ROSTER_CHANGED, **_about(unit, month), by=str(by.pk))


def roster_rejected(unit: Unit, month: dt.date, by: User) -> None:
    """To the unit's manager only. The comment stays on the roster: it can name a nurse and their leave."""
    notify([unit.manager], Event.ROSTER_REJECTED, **_about(unit, month), by=str(by.pk))


def solve_ended(unit_id: UUID, month: dt.date, solve_id: UUID, outcome: SolveOutcome) -> None:
    """To whoever manages the unit when the solve ends, read again then: a manager taken off it since starting the solve no
    longer reads its pages, and the one who holds it now has the draft. Nobody when the unit has none."""
    unit = Unit.objects.select_related("manager").get(pk=unit_id)
    notify([unit.manager], Event.SOLVE_ENDED, **_about(unit, month), solve_id=str(solve_id), outcome=outcome)
