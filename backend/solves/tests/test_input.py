"""The assembler: what the solver receives for a unit's month."""
import copy
import datetime as dt
import json

import pytest
from nurse_roster.request import load_request

from accounts.models import Role
from hospital.models import FixedRamadanMonth, HospitalSettings, LeaveType, PublicHoliday, Shift
from nurses.models import Leave, NurseProfile, Placement
from nurses.tests.conftest import make_unit
from solves.input import assemble, changes_since, solver_refusal
from solves.tests.conftest import MONTH, SAMPLE, nurse_in

pytestmark = pytest.mark.django_db
JUNE = dt.date(2026, 6, 1)


@pytest.fixture(autouse=True)
def _before_june(before_june):
    pass


def built(unit, **options):
    return assemble(unit, JUNE, time_limit=options.get("time_limit", 20))


def block(assembled, hospital_id):
    return next(row for row in assembled.input["nurses"] if row["id"] == hospital_id)


def leave_on(nurse, *days, by):
    kind = LeaveType.objects.get(name="Sick")
    for day in days:
        Leave.objects.create(nurse=nurse, date=day, leave_type=kind, recorded_by=by)


def test_the_solvers_own_sample_as_this_app_holds_it_comes_out_as_the_sample(er, make_user):
    """The sample is the solver's, so it is a truth this code did not write."""
    badr = NurseProfile.objects.get(user__username="Badr")
    leave_on(badr, *next(row for row in SAMPLE["nurses"] if row["id"] == "Badr")["leave"], by=badr.user)

    solve_input = built(er, time_limit=SAMPLE["solver"]["time_limit_seconds"]).input

    expected = copy.deepcopy(SAMPLE)
    expected["department"]["name"] = "ER"
    assert solve_input["department"] == expected["department"]
    assert {key: value for key, value in solve_input["general"].items() if key != "shift_hours"} == {
        key: value for key, value in expected["general"].items() if key != "shift_hours"}
    assert solve_input["general"]["shift_hours"] == {shift.code: shift.hours for shift in Shift.objects.all()}
    assert expected["general"]["shift_hours"].items() <= solve_input["general"]["shift_hours"].items()
    for row in expected["nurses"]:
        row.setdefault("leave", [])
        row.setdefault("allowed_shifts", None)
        # Nothing in this app holds these yet: pins arrive with ticket 13, and there are no soft preferences in v1.
        for absent in ("undesired_days", "desired_days", "pinned", "previous"):
            row.pop(absent, None)
    assert solve_input["nurses"] == expected["nurses"]
    assert (solve_input["version"], solve_input["month"], solve_input["ramadan_days"]) == (1, MONTH, [])
    assert solve_input["solver"] == SAMPLE["solver"]
    assert [row.id for row in load_request(solve_input).problem.nurses] == ["Amal", "Badr", "Dana", "Emad"]


def test_opening_values_reach_the_solver(er, make_user):
    nurse_in(er, make_user, "Omar", gender="M", ytd_overtime=12, hours_balance=-8, night_balance=1.5, friday_balance=-0.5)

    row = block(built(er), "Omar")

    assert (row["ytd_overtime"], row["hours_balance"], row["night_balance"], row["friday_balance"]) == (12, -8, 1.5, -0.5)


def test_days_outside_the_dates_are_credited_like_leave_and_listed_once(er, make_user):
    """A date recorded and then left outside the dates by a correction must not reach the solver twice."""
    nurse = nurse_in(er, make_user, "Omar", gender="M", start=dt.date(2026, 6, 3), end=dt.date(2026, 6, 28))
    leave_on(nurse, dt.date(2026, 6, 2), dt.date(2026, 6, 10), by=nurse.user)

    assembled = built(er)

    assert block(assembled, "Omar")["leave"] == ["2026-06-01", "2026-06-02", "2026-06-10", "2026-06-29", "2026-06-30"]
    assert assembled.leave_days == 1
    assert assembled.outside_days == {"Omar": ["2026-06-01", "2026-06-02", "2026-06-29", "2026-06-30"]}
    load_request(assembled.input)


def test_a_nurse_never_present_stays_out(er, make_user):
    nurse_in(er, make_user, "Omar", gender="M", start=dt.date(2026, 7, 1))
    nurse_in(er, make_user, "Zaid", gender="M", start=dt.date(2026, 6, 20), end=dt.date(2026, 5, 1))

    assert {row["id"] for row in built(er).input["nurses"]} == {"Amal", "Badr", "Dana", "Emad"}


def test_allowed_shifts_are_those_of_the_months_placement(er, make_user):
    icu = make_unit("ICU")
    nurse = nurse_in(er, make_user, "Omar", gender="M")
    Placement.objects.filter(nurse=nurse).update(allowed_shifts=["N"])
    Placement.objects.create(nurse=nurse, unit=icu, from_month=dt.date(2026, 7, 1), allowed_shifts=["D"])

    assert block(built(er), "Omar")["allowed_shifts"] == ["N"]
    assert block(assemble(icu, dt.date(2026, 7, 1), time_limit=20), "Omar")["allowed_shifts"] == ["D"]


def test_no_leave_type_is_in_a_solve_input(er, make_user):
    nurse = nurse_in(er, make_user, "Omar", gender="M")
    leave_on(nurse, dt.date(2026, 6, 9), by=nurse.user)

    assert "Sick" not in json.dumps(built(er).input)


def test_a_deactivated_manager_with_no_end_date_is_left_out_and_named(er, make_user):
    nurse = nurse_in(er, make_user, "Sara", role=Role.UNIT_MANAGER)
    nurse.user.is_active = False
    nurse.user.save()

    assembled = built(er)

    assert "Sara" not in {row["id"] for row in assembled.input["nurses"]}
    assert [left.user.username for left in assembled.left_out] == ["Sara"]


def test_a_deactivated_nurse_whose_end_date_has_come_keeps_the_days_they_worked(er, make_user, monkeypatch):
    from nurses import membership
    monkeypatch.setattr(membership, "today", lambda: dt.date(2026, 6, 20))
    nurse = nurse_in(er, make_user, "Omar", gender="M", end=dt.date(2026, 6, 20))
    nurse.user.is_active = False
    nurse.user.save()

    assembled = built(er)

    assert block(assembled, "Omar")["leave"] == [f"2026-06-{day}" for day in range(21, 31)]
    assert assembled.left_out == []


def test_a_list_a_transfer_emptied_is_named(er, make_user):
    nurse = nurse_in(er, make_user, "Omar", gender="M")
    Placement.objects.filter(nurse=nurse).update(allowed_shifts_to_check=True)

    assert [checked.user.username for checked in built(er).to_check] == ["Omar"]


def test_fixed_and_derived_ramadan_and_only_this_months_holidays(er):
    PublicHoliday.objects.create(date=dt.date(2026, 6, 15), name="In")
    PublicHoliday.objects.create(date=dt.date(2026, 7, 15), name="Out")
    FixedRamadanMonth.objects.filter(month=MONTH).update(dates=[dt.date(2026, 6, 1), dt.date(2026, 6, 2)])

    solve_input = built(er).input

    assert solve_input["public_holidays"] == ["2026-06-15"]
    assert solve_input["ramadan_days"] == ["2026-06-01", "2026-06-02"]


def test_what_the_solver_refuses_is_said_in_its_words(er):
    er.rules["night_shift"] = ""
    er.save()

    assert "night_shift" in solver_refusal(built(er).input)


def test_a_raised_weight_can_leave_a_one_shift_unit_for_the_solver_to_refuse(er, make_user):
    """Saved while `shift_switch` and `night_rest` were 0, as ticket 09 allows: the CNO then raises one."""
    settings = HospitalSettings.load()
    settings.rules["weights"] |= {"shift_switch": 0, "night_rest": 0}
    settings.save()
    er.rules |= {"shifts": ["D"], "fair_shifts": ["D"], "night_shift": "N", "day_shift": "D", "no_mixed_blocks": False,
                 "night_rest_hard": False, "carry_fairness": False, "headcounts": er.rules["headcounts"][:1]}
    er.save()
    Placement.objects.filter(unit=er).update(allowed_shifts=None)
    assert solver_refusal(built(er).input) is None

    settings.rules["weights"]["shift_switch"] = 8
    settings.save()

    assert solver_refusal(built(er).input) is not None


class TestChangesSince:
    def test_nothing_changed(self, er):
        assert changes_since(built(er).input, er, JUNE) == []

    def test_gender_leave_and_who_is_in_the_month(self, er, make_user):
        solved = built(er).input
        amal = NurseProfile.objects.get(user__username="Amal")
        amal.gender = "M"
        amal.save()
        badr = NurseProfile.objects.get(user__username="Badr")
        leave_on(badr, dt.date(2026, 6, 9), by=badr.user)
        dana = NurseProfile.objects.get(user__username="Dana")
        dana.start_date = dt.date(2026, 7, 1)
        dana.save()
        nurse_in(er, make_user, "Omar", gender="M")

        assert changes_since(solved, er, JUNE) == [
            {"hospital_id": "Amal", "what": "gender"}, {"hospital_id": "Badr", "what": "leave"},
            {"hospital_id": "Dana", "what": "left"}, {"hospital_id": "Omar", "what": "joined"}]

    def test_a_start_date_counts_only_when_it_moves_days_of_this_month(self, er):
        solved = built(er).input
        amal = NurseProfile.objects.get(user__username="Amal")
        amal.start_date = dt.date(2026, 2, 1)
        amal.save()
        assert changes_since(solved, er, JUNE) == []

        amal.start_date = dt.date(2026, 6, 5)
        amal.save()
        assert changes_since(solved, er, JUNE) == [{"hospital_id": "Amal", "what": "leave"}]
