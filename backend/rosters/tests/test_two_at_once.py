"""A decision racing another write, on the real PostgreSQL, as `nurses/tests/test_two_at_once.py` does it: one transaction stays
open with its change made, the other is seen waiting for a lock before the first commits, so the order is forced, not hoped for."""
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import transaction

from nurses.tests.test_two_at_once import alongside
from rosters.models import RosterState, RosterVersion, Submission
from rosters.tests.test_review import (BADR_OFF, BADR_WORKS, approve, carla, dina, record_leave, reject, roster, solved,  # noqa: F401
                                       submit, submitted)
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
