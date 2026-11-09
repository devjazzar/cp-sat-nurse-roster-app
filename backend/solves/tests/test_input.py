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
from requesting.models import Preference, PreferenceKind, PreferenceState, RequestWindow
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


def preference(unit, hospital_id, day, kind=PreferenceKind.DAY_OFF, state=PreferenceState.MADE) -> Preference:
    """Made in a window of the unit for the day's month, as `requesting` makes one: the assembler reads only the rows."""
    month = day.replace(day=1)
    window = RequestWindow.objects.filter(unit=unit, month=month).first() or RequestWindow.objects.create(
        unit=unit, month=month, opens_on=dt.date(2026, 5, 15), closes_on=dt.date(2026, 5, 25), state="closed",
        created_by=unit.manager or NurseProfile.objects.first().user)
    ended = None if state == PreferenceState.MADE else dt.datetime(2026, 5, 20, tzinfo=dt.UTC)
    return Preference.objects.create(window=window, nurse=NurseProfile.objects.get(user__username=hospital_id), date=day,
                                     kind=kind, state=state, ended_at=ended)


def leave_on(nurse, *days, by):
    kind = LeaveType.objects.get(name="Sick")
    for day in days:
        Leave.objects.create(nurse=nurse, date=day, leave_type=kind, recorded_by=by)


def test_the_solvers_own_sample_as_this_app_holds_it_comes_out_as_the_sample(er, make_user):
    """The sample is the solver's, so it is a truth this code did not write."""
    badr = NurseProfile.objects.get(user__username="Badr")
    leave_on(badr, *next(row for row in SAMPLE["nurses"] if row["id"] == "Badr")["leave"], by=badr.user)
    dana = next(row for row in SAMPLE["nurses"] if row["id"] == "Dana")
    for day in dana["undesired_days"]:
        preference(er, "Dana", dt.date.fromisoformat(day))
    for day in dana["desired_days"]:
        preference(er, "Dana", dt.date.fromisoformat(day), PreferenceKind.WORKING_DAY)

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
        # No month before has a roster, so the carry-over is the opening values with no history (ticket 21).
        row["previous"] = []
        # No pin is made here; Dana's two preferences are (ticket 29).
        row.pop("pinned", None)
        # The chain carries the count of preferences not kept (ticket 28): 0, since none were ever priced.
        row["preferences_not_kept"] = 0
    assert solve_input["nurses"] == expected["nurses"]
    assert (solve_input["version"], solve_input["month"], solve_input["ramadan_days"]) == (2, MONTH, [])
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


def carried_from_may(unit, hospital_id, preferences_not_kept) -> None:
    """As if May had closed with her preferences not kept: a closed carry-over of May, the January test's pattern."""
    from closes.models import CarryOver, CarrySource, MonthClose
    may = dt.date(2026, 5, 1)
    close = MonthClose.objects.filter(unit=unit, month=may).first() or MonthClose.objects.create(
        unit=unit, month=may, version=1, input={}, result={})
    values = {"ytd_overtime": 0, "hours_balance": 0, "night_balance": 0.0, "friday_balance": 0.0, "previous": [],
              "last_shift_kind": None, "rest_owed": 0, "preferences_not_kept": preferences_not_kept}
    CarryOver.objects.create(nurse=NurseProfile.objects.get(user__username=hospital_id), unit=unit, month=may,
                             source=CarrySource.CLOSED, close=close, values=values)


class TestTheCountCarriedIn:
    """Each nurse's count of preferences not kept the month before reaches the solver (ticket 30), and above 0 her preferences
    cost twice the weight: priced here by the solver package's own validator on SOUND's June, with no search."""

    def test_it_reaches_the_solver_and_doubles_her_price_alone(self, er):
        from solver_service.grid import validate_grid
        from rosters.tests.test_review import SOUND
        carried_from_may(er, "Dana", 1)
        carried_from_may(er, "Amal", 0)
        preference(er, "Dana", dt.date(2026, 6, 5))   # Dana works Night on the 5th of SOUND's June,
        preference(er, "Amal", dt.date(2026, 6, 2))   # and so does Amal on the 2nd.

        solve_input = built(er).input

        assert (block_of(solve_input, "Dana")["preferences_not_kept"], block_of(solve_input, "Amal")["preferences_not_kept"]) == (1, 0)
        [rule] = [rule for rule in validate_grid(solve_input, SOUND[MONTH]["roster"])["rules"] if rule["id"] == "undesired_day"]
        weight = HospitalSettings.load().rules["weights"]["undesired_day"]
        assert {match["nurse"]: match["amount"] for match in rule["matches"]} == {"Amal": 1, "Dana": 2}
        assert rule["weighted"] == 3 * weight
        dana = next(match for match in rule["matches"] if match["nurse"] == "Dana")
        assert dana["text"].endswith("counts double, a preference was not kept last month)")


def block_of(solve_input, hospital_id):
    return next(row for row in solve_input["nurses"] if row["id"] == hospital_id)


def full_runs_capped(unit, cap: int, weight: int) -> None:
    unit.rules |= {"max_full_runs": cap}
    unit.save()
    settings = HospitalSettings.load()
    settings.rules["weights"]["excess_full_run"] = weight
    settings.save()


class TestFullRuns:
    """The unit's most full runs in a month and the hospital's price of each one above it reach every new input (ticket 48);
    one stored without them is read as no cap. Priced by the solver package's own validator, with no search."""

    @staticmethod
    def amal_in_six_full_runs() -> dict:
        """SOUND's June, but Amal works Day on four days in a row, off on the fifth, all month: six full runs of the
        sample's longest run, 4, the last ended by the 30th off."""
        from rosters.tests.test_review import SOUND
        roster = copy.deepcopy(SOUND[MONTH]["roster"])
        roster["Amal"] = {f"2026-06-{day:02d}": "" if day % 5 == 0 else "D" for day in range(1, 31)}
        return roster

    def test_a_solve_input_carries_the_units_cap_and_the_hospitals_weight(self, er):
        full_runs_capped(er, 2, 20)

        problem = load_request(built(er).input).problem

        assert (problem.department.max_full_runs, problem.general.weights.excess_full_run) == (2, 20)

    def test_each_full_run_above_the_cap_costs_the_weight_in_the_solvers_words(self, er):
        from solver_service.grid import validate_grid
        full_runs_capped(er, 3, 4)

        [rule] = [rule for rule in validate_grid(built(er).input, self.amal_in_six_full_runs())["rules"]
                  if rule["id"] == "excess_full_run"]

        amal = next(match for match in rule["matches"] if match["nurse"] == "Amal")
        assert (amal["amount"], amal["text"]) == (3, "Amal: 6 full runs of 4 shifts, max 3")
        assert rule["weight"] == 4

    def test_an_input_stored_before_full_runs_is_read_as_no_cap_and_prices_the_rest_as_before(self, er):
        from solver_service.grid import validate_grid
        full_runs_capped(er, 3, 4)
        now = built(er).input
        stored = copy.deepcopy(now)
        del stored["department"]["max_full_runs"]
        del stored["general"]["weights"]["excess_full_run"]
        roster = self.amal_in_six_full_runs()

        before, after = validate_grid(stored, roster), validate_grid(now, roster)

        assert load_request(stored).problem.department.max_full_runs is None
        assert before["penalties"]["excess_full_run"] == 0 and after["penalties"]["excess_full_run"] >= 3 * 4
        assert before["penalties"] == after["penalties"] | {"excess_full_run": 0}
        assert before["cost"] == after["cost"] - after["penalties"]["excess_full_run"]


class TestPreferences:
    """A nurse's live preferences are the days she asked off (`undesired_days`) and to work (`desired_days`), each in date
    order (ADR 0013)."""

    def test_her_live_ones_of_the_month_fill_the_two_lists_and_nothing_else_does(self, er, make_user):
        for day in (9, 3):
            preference(er, "Amal", dt.date(2026, 6, day))
        preference(er, "Amal", dt.date(2026, 6, 20), PreferenceKind.WORKING_DAY)
        preference(er, "Amal", dt.date(2026, 6, 4), state=PreferenceState.WITHDRAWN)
        preference(er, "Amal", dt.date(2026, 6, 5), PreferenceKind.WORKING_DAY, state=PreferenceState.ASKED_INSTEAD)
        preference(er, "Amal", dt.date(2026, 7, 2))
        preference(er, "Badr", dt.date(2026, 6, 4), PreferenceKind.WORKING_DAY)

        assembled = built(er)

        amal, badr, emad = (block(assembled, hospital_id) for hospital_id in ("Amal", "Badr", "Emad"))
        assert (amal["undesired_days"], amal["desired_days"]) == (["2026-06-03", "2026-06-09"], ["2026-06-20"])
        assert (badr.get("undesired_days"), badr["desired_days"]) == (None, ["2026-06-04"])
        assert "undesired_days" not in emad and "desired_days" not in emad
        assert solver_refusal(assembled.input) is None

    def test_one_on_leave_or_outside_her_dates_is_left_in_for_the_solver_to_ignore(self, er):
        amal = NurseProfile.objects.get(user__username="Amal")
        amal.end_date = dt.date(2026, 6, 20)
        amal.save()
        leave_on(amal, dt.date(2026, 6, 3), by=amal.user)
        preference(er, "Amal", dt.date(2026, 6, 3))
        preference(er, "Amal", dt.date(2026, 6, 25), PreferenceKind.WORKING_DAY)

        assembled = built(er)

        row = block(assembled, "Amal")
        assert (row["undesired_days"], row["desired_days"]) == (["2026-06-03"], ["2026-06-25"])
        assert {"2026-06-03", "2026-06-25"} <= set(row["leave"])
        assert solver_refusal(assembled.input) is None

    def test_one_left_on_another_units_record_reaches_neither_unit(self, er, make_user):
        icu = make_unit("ICU")
        Unit = type(er)
        Unit.objects.filter(pk=icu.pk).update(rules=er.rules)
        icu.refresh_from_db()
        preference(er, "Amal", dt.date(2026, 6, 3))
        Placement.objects.create(nurse=NurseProfile.objects.get(user__username="Amal"), unit=icu,
                                 from_month=dt.date(2026, 6, 1))

        assert "Amal" not in {row["id"] for row in built(er).input["nurses"]}
        assert "undesired_days" not in block(assemble(icu, JUNE), "Amal")


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

    def test_a_preference_made_withdrawn_or_asked_instead_is_a_change_to_her_preferences(self, er):
        made = preference(er, "Amal", dt.date(2026, 6, 3))
        preference(er, "Badr", dt.date(2026, 6, 4), PreferenceKind.WORKING_DAY)
        solved = built(er).input
        assert changes_since(solved, er, JUNE) == []

        Preference.objects.filter(pk=made.pk).update(state=PreferenceState.WITHDRAWN, ended_at=dt.datetime.now(dt.UTC))
        preference(er, "Dana", dt.date(2026, 6, 6))

        assert changes_since(solved, er, JUNE) == [
            {"hospital_id": "Amal", "what": "preferences"}, {"hospital_id": "Dana", "what": "preferences"}]

    def test_an_input_stored_before_preferences_existed_changes_only_where_one_is_made(self, er):
        solved = built(er).input
        for row in solved["nurses"]:
            row.pop("undesired_days", None)
            row.pop("desired_days", None)
        assert changes_since(solved, er, JUNE) == []

        preference(er, "Emad", dt.date(2026, 6, 8), PreferenceKind.WORKING_DAY)

        assert changes_since(solved, er, JUNE) == [{"hospital_id": "Emad", "what": "preferences"}]
