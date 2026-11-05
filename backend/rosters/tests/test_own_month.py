"""A nurse's own month: their hours and shift counts from the version in force, worked out on the month as it stands. Nothing
of a colleague. The numbers below are worked by hand from `fixtures/sound_rosters.json`: in June 2026, Amal works 6 Day and 11
Night shifts of 12 hours, and owes 8 hours on each of the 26 days that are not a Friday."""
import copy
import datetime as dt

import pytest

from accounts.models import Role, User
from nurses.models import NurseProfile, Placement
from rosters.models import Roster, RosterVersion, VersionOrigin
from rosters.tests.test_review import (_scene, approve, carla, ok, record_leave, solved, submit,  # noqa: F401
                                       url)
from notifications.tests.test_events import as_user, joining

pytestmark = pytest.mark.django_db

AMAL_SHIFTS = [{"code": "D", "display_name": "Day", "count": 6}, {"code": "N", "display_name": "Night", "count": 11}]


def month(client, chosen="2026-06") -> dict:
    return ok(client.get("/api/rosters/mine/month", {"month": chosen}))


def approved_june(mona, er, solver, carla):
    solved(mona, er, solver)
    ok(submit(mona, er))
    ok(approve(carla, er))


def shifts_of(hours) -> dict[str, int]:
    return {row["code"]: row["count"] for row in hours["shifts"]}


def shifts(answer) -> list[dict]:
    return [{key: row[key] for key in ("code", "display_name", "count")} for row in answer["roster"]["hours"]["shifts"]]


class TestFromTheVersionInForce:
    def test_nothing_before_approval(self, mona, er, solver):
        solved(mona, er, solver)

        answer = month(as_user("Amal"))

        assert answer["unit"] == "ER" and answer["roster"] is None

    def test_hours_and_shift_counts(self, mona, er, solver, carla):
        approved_june(mona, er, solver, carla)

        answer = month(as_user("Amal"))

        assert answer["roster"]["version"] == 1
        hours = answer["roster"]["hours"]
        assert {key: hours[key] for key in ("worked", "leave_credit", "owed", "overtime", "carried")} == {
            "worked": 204, "leave_credit": 0, "owed": 208, "overtime": 0, "carried": 4}
        assert shifts(answer) == AMAL_SHIFTS

    def test_leave_recorded_since_counts(self, mona, er, solver, carla):
        """Wednesday 10 June is a day off for Amal: as leave it is 8 hours credited, so 200 are owed and 4 are overtime."""
        approved_june(mona, er, solver, carla)
        assert record_leave(mona, er, "Amal", 10).status_code == 201

        hours = month(as_user("Amal"))["roster"]["hours"]

        assert (hours["leave_credit"], hours["owed"], hours["overtime"], hours["carried"]) == (8, 200, 4, 0)

    def test_a_later_version_is_the_one_read(self, mona, er, solver, carla):
        """Ticket 16 makes versions after the first. Wednesday 10 June as a Night makes 216 hours worked, 8 of them overtime."""
        approved_june(mona, er, solver, carla)
        roster = Roster.objects.get(unit=er)
        grid = copy.deepcopy(roster.grid)
        grid["Amal"]["2026-06-10"] = "N"
        RosterVersion.objects.create(roster=roster, number=2, grid=grid, origin=VersionOrigin.EDIT, created_by=roster.solve.requested_by)

        answer = month(as_user("Amal"))

        assert answer["roster"]["version"] == 2
        assert (answer["roster"]["hours"]["worked"], answer["roster"]["hours"]["overtime"]) == (216, 8)

    def test_leave_on_a_day_the_version_still_works_counts_once(self, mona, er, solver, carla):
        """Leave wins over a shift. Amal works Night on Tuesday 2 June: as leave it is 8 hours credited and 12 not worked, so
        192 worked against 200 owed, and 8 owed into July."""
        approved_june(mona, er, solver, carla)
        assert record_leave(mona, er, "Amal", 2).status_code == 201

        hours = month(as_user("Amal"))["roster"]["hours"]

        assert (hours["worked"], hours["leave_credit"], hours["owed"], hours["overtime"], hours["carried"]) == (192, 8, 200, 0, 8)
        assert shifts_of(hours) == {"D": 6, "N": 10}

    def test_a_manager_with_a_nurse_profile_reads_their_own(self, mona, er, solver, carla):
        """Their profile starts in July, so June's solve has no row of theirs: they read the roster without hours."""
        nurse = NurseProfile.objects.create(user=User.objects.get(username="mona"), gender="F", start_date=dt.date(2026, 7, 1))
        Placement.objects.create(nurse=nurse, unit=er, from_month=dt.date(2026, 1, 1))
        approved_june(mona, er, solver, carla)

        answer = month(mona)

        assert answer["unit"] == "ER" and answer["roster"]["version"] == 1 and answer["roster"]["hours"] is None

class TestNothingOfAColleague:
    def test_a_colleagues_leave_changes_nothing_in_the_answer(self, mona, er, solver, carla):
        approved_june(mona, er, solver, carla)
        amal = as_user("Amal")
        before = month(amal)

        assert record_leave(mona, er, "Badr", 3).status_code == 201

        assert month(amal) == before

    def test_no_colleague_is_named(self, mona, er, solver, carla):
        approved_june(mona, er, solver, carla)

        text = as_user("Amal").get("/api/rosters/mine/month", {"month": "2026-06"}).content.decode()

        assert not any(name in text for name in ("Badr", "Dana", "Emad"))


class TestWhichMonths:
    def test_a_month_already_over_shows_no_hours(self, mona, er, solver, carla, monkeypatch):
        approved_june(mona, er, solver, carla)
        from nurses import membership
        monkeypatch.setattr(membership, "today", lambda: __import__("datetime").date(2026, 7, 2))

        answer = month(as_user("Amal"))

        assert answer["first_month"] == "2026-07" and answer["roster"] is None

    def test_a_nurse_due_to_join_sees_the_roster_without_hours(self, mona, er, solver, carla, make_user):
        joining(er, make_user, "Faris")
        approved_june(mona, er, solver, carla)

        answer = month(as_user("Faris"))

        assert answer["roster"]["version"] == 1 and answer["roster"]["hours"] is None

    def test_a_manager_with_no_nurse_profile_has_no_unit(self, mona, er, solver, carla):
        approved_june(mona, er, solver, carla)

        assert month(mona) == {"month": "2026-06", "first_month": "2026-05", "unit": None, "roster": None}

    @pytest.mark.parametrize("role", [Role.CNO, Role.DEPUTY_CNO, Role.SYSTEM_ADMIN])
    def test_other_roles_are_refused(self, role, client_of):
        assert client_of("someone", role).get("/api/rosters/mine/month").status_code == 403
