"""A decision racing another write, on the real PostgreSQL, as `nurses/tests/test_two_at_once.py` does it: one transaction stays
open with its change made, the other is seen waiting for a lock before the first commits, so the order is forced, not hoped for."""
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import transaction

from conftest import post
from hospital.models import LeaveType
from nurses.models import NurseProfile
from nurses.tests.test_two_at_once import alongside
from rosters.drafts import in_current_codes
from rosters.models import RosterState, RosterVersion, Submission
from rosters.tests.test_pins import change_shift, off, pin
from rosters.tests.test_review import (BADR_OFF, BADR_WORKS, approve, approved, carla, dina, record_leave,  # noqa: F401
                                       reject, roster, solved, submit, submitted)
from rosters.tests.test_versions import change
from solves.tests.conftest import empty_queue, start_solve  # noqa: F401

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def _scene(before_june, solver, empty_queue):
    pass


@pytest.fixture
def pool():
    with ThreadPoolExecutor(max_workers=1) as executor:
        yield executor


def test_of_two_approvers_the_second_waits_and_is_told_the_first_decided(mona, carla, dina, er, solver, pool):
    submitted(mona, er, solver)

    with transaction.atomic():
        assert approve(carla, er).status_code == 200
        second = alongside(pool, lambda: approve(dina, er))
        assert not second.done()

    answer = second.result()
    assert (answer.status_code, answer.json()["detail"]) == (409, "This roster has been approved already by Carla CNO.")
    assert RosterVersion.objects.count() == 1


def test_an_approval_waiting_on_a_rejection_finds_nothing_to_approve(mona, carla, dina, er, solver, pool):
    submitted(mona, er, solver)

    with transaction.atomic():
        assert reject(dina, er).status_code == 200
        second = alongside(pool, lambda: approve(carla, er))
        assert not second.done()

    assert second.result().json()["detail"] == "This month has no roster waiting for a decision."
    assert roster(er).state == RosterState.DRAFT and not RosterVersion.objects.exists()


def test_an_approval_waits_for_leave_being_recorded_and_then_checks_it(mona, carla, er, solver, pool):
    """Without the nurses' lock it would check the grid before the leave committed, and approve a roster that breaks a rule."""
    submitted(mona, er, solver)

    with transaction.atomic():
        assert record_leave(mona, er, "Badr", BADR_WORKS).status_code == 201
        approval = alongside(pool, lambda: approve(carla, er))
        assert not approval.done()

    answer = approval.result()
    assert answer.status_code == 409 and "breaks 1 hard rule" in answer.json()["detail"]
    assert roster(er).state == RosterState.SUBMITTED


def test_leave_waits_for_an_approval_and_is_then_recorded(mona, carla, er, solver, pool):
    submitted(mona, er, solver)

    with transaction.atomic():
        assert approve(carla, er).status_code == 200
        leave = alongside(pool, lambda: record_leave(mona, er, "Badr", BADR_OFF))
        assert not leave.done()

    assert leave.result().status_code == 201
    assert roster(er).state == RosterState.APPROVED


def test_a_submit_waiting_on_a_solve_starting_is_refused(mona, er, solver, pool):
    solved(mona, er, solver)

    with transaction.atomic():
        assert start_solve(mona, er).status_code == 201
        second = alongside(pool, lambda: submit(mona, er))
        assert not second.done()

    assert second.result().json()["detail"].startswith("A solve of this month is queued or running")
    assert not Submission.objects.exists()


def test_of_two_changes_to_an_approved_roster_the_second_waits_and_is_the_next_version(mona, carla, er, solver, pool):
    approved(mona, carla, er, solver)

    with transaction.atomic():
        assert change(mona, er, pin("Amal", 9, "N")).status_code == 200
        second = alongside(pool, lambda: change(mona, er, off("Badr", 2), reason="Badr asked."))
        assert not second.done()

    assert second.result().status_code == 200
    versions = list(roster(er).versions.order_by("number").values_list("number", "reason"))
    assert [number for number, _ in versions] == [1, 2, 3] and versions[2][1] == "Badr asked."
    latest = roster(er).versions.first().grid
    assert latest["Amal"]["2026-06-09"] == "N" and latest["Badr"]["2026-06-02"] == "", "the second built on the first"
    assert roster(er).grid == latest


def test_leave_taking_a_shift_off_waits_for_a_change_to_the_same_nurse_and_comes_after_it(mona, carla, er, solver, pool):
    """The change holds the nurse's lock, which a leave write takes first; the leave then takes the roster's after it."""
    approved(mona, carla, er, solver)

    with transaction.atomic():
        assert change(mona, er, pin("Badr", BADR_OFF, "D")).status_code == 200
        leave = alongside(pool, lambda: record_leave(mona, er, "Badr", BADR_WORKS))
        assert not leave.done()

    answer = leave.result()
    assert answer.status_code == 201, answer.content
    assert [row["version"] for row in answer.json()["shifts_taken_off"]] == [3]
    latest = roster(er).versions.first()
    assert latest.number == 3 and latest.grid["Badr"][f"2026-06-{BADR_OFF:02d}"] == "D"
    assert latest.grid["Badr"][f"2026-06-{BADR_WORKS:02d}"] == ""
    assert roster(er).grid == latest.grid


def test_a_change_waits_for_leave_on_another_nurse_and_keeps_the_shift_it_took_off(mona, carla, er, solver, pool):
    """Different nurses' locks do not meet, so the roster's row lock is what orders them."""
    approved(mona, carla, er, solver)

    with transaction.atomic():
        assert record_leave(mona, er, "Badr", BADR_WORKS).status_code == 201
        edit = alongside(pool, lambda: change(mona, er, pin("Amal", 9, "N")))
        assert not edit.done()

    assert edit.result().status_code == 200
    latest = roster(er).versions.first()
    assert latest.number == 3
    assert latest.grid["Badr"][f"2026-06-{BADR_WORKS:02d}"] == "" and latest.grid["Amal"]["2026-06-09"] == "N"


def test_a_rename_waits_for_leave_taking_shifts_off_two_approved_months_and_then_follows_both(mona, carla, er, solver, pool):
    """Leave over the end of a month locks June's roster, then July's. A rename locks every roster by month, then unit, so it
    waits on June and never holds July while waiting on June. Dana works 30 June and 1 July in the sound rosters."""
    approved(mona, carla, er, solver)
    approved(mona, carla, er, solver, month="2026-07")

    with transaction.atomic():
        answer = post(mona, f"/api/units/{er.pk}/leave", {
            "nurse_id": str(NurseProfile.objects.get(user__username="Dana").pk),
            "leave_type_id": str(LeaveType.objects.get(name="Sick").pk), "first": "2026-06-30", "last": "2026-07-01"})
        assert [row["date"] for row in answer.json()["shifts_taken_off"]] == ["2026-06-30", "2026-07-01"]
        rename = alongside(pool, lambda: change_shift(carla, "N", code="NT"))
        assert not rename.done()

    assert rename.result().status_code == 200
    for month in ("2026-06", "2026-07"):
        held = roster(er, month).grid
        assert "N" not in {code for row in held.values() for code in row.values()}
        assert roster(er, month).grid == in_current_codes(roster(er, month).versions.first().grid)
