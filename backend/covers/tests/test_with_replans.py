"""Covers and re-plans, mid-June: a re-plan's version that puts one more nurse on a cover's shift-day fills it, as any version
does."""
import pytest

from covers.models import Cover, CoverState
from covers.tests.conftest import opened
from rosters.models import VersionOrigin
from rosters.tests.test_replan import answered, in_force, mid_june, moved, replanned  # noqa: F401
from solves.models import ReplanOutcome

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _scene(before_june, solver):
    pass


def test_a_re_plans_version_putting_a_nurse_on_its_shift_day_fills_it(mona, er, solver, in_force):
    """From the 12th: Dana works the only Night on the 15th, and the scripted re-plan puts Amal on it beside her."""
    opened(mona, er, 15, "N")

    solve = replanned(mona, er, solver, answered(moved(Amal_15="N")))

    assert solve.replan_outcome == ReplanOutcome.VERSION
    assert er.rosters.get().versions.first().origin == VersionOrigin.REPLAN
    assert Cover.objects.get().state == CoverState.FILLED
