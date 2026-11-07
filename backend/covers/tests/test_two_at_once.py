"""Covers and other writes at once, on real connections: a cover refers to its unit, whose foreign key is checked at commit, so
opening one takes the unit's lock before the roster's, as an edit does. A rename holds every unit while it waits on the
rosters; it waits for the opening instead of deadlocking with it. Leave's own two-at-once tests are in `rosters/tests`."""
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import transaction

from covers.models import Cover
from covers.tests.conftest import opened
from nurses.tests.test_two_at_once import alongside
from rosters.tests.test_pins import change_shift
from solves.tests.conftest import empty_queue  # noqa: F401

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def _scene(before_june, solver, empty_queue):
    pass


@pytest.fixture
def pool():
    with ThreadPoolExecutor(max_workers=1) as executor:
        yield executor


def test_a_rename_waits_for_a_cover_opened_by_hand_and_then_renames_its_shift(in_force, mona, carla, pool):
    with transaction.atomic():
        opened(mona, in_force, 9, "N")
        rename = alongside(pool, lambda: change_shift(carla, "N", code="NT"))
        assert not rename.done()

    assert rename.result().status_code == 200
    assert Cover.objects.get().shift.code == "NT"
