import copy
import dataclasses
import json
from pathlib import Path

import pytest
from django.core.management import call_command
from nurse_roster.problem import GeneralRules, Weights
from nurse_roster.request import load_request

from accounts.models import Role
from audit.models import AuditEntry
from hospital.models import HospitalSettings
from hospital.rules import DEFAULT_RULES, general_block

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("catalogue")]

RULES = "/api/hospital/rules"
ER_REQUEST = Path(__file__).parents[3] / "solver/tests/fixtures/er_request_2026-03.json"


def body(**changes) -> dict:
    return copy.deepcopy(DEFAULT_RULES) | changes


def weights(**changes) -> dict:
    return body(weights=DEFAULT_RULES["weights"] | changes)


def put(client, rules):
    return client.put(RULES, rules, content_type="application/json")


def refused_fields(response) -> set[tuple]:
    assert response.status_code == 422, response.content
    return {tuple(error["loc"][2:]) for error in response.json()["detail"]}


def er_request() -> dict:
    return json.loads(ER_REQUEST.read_text())


# ---- the solver's contract ------------------------------------------------------------------------
def test_the_rules_are_every_field_of_the_solvers_block_but_the_shift_catalogues():
    fields = {field.name for field in dataclasses.fields(GeneralRules)}

    assert set(DEFAULT_RULES) == fields - {"shift_hours"}
    assert set(DEFAULT_RULES["weights"]) == {field.name for field in dataclasses.fields(Weights)}


def test_the_defaults_are_the_reviewed_set_the_solver_was_shaped_on():
    reviewed = er_request()["general"]
    del reviewed["shift_hours"]

    assert DEFAULT_RULES == reviewed


def test_what_the_cno_saved_is_what_a_solve_input_receives(signed_in):
    saved = weights(change=9) | {"hours_per_day": 7}
    assert put(signed_in(Role.CNO), saved).status_code == 200
    shift_hours = er_request()["general"]["shift_hours"]

    general = general_block(HospitalSettings.load(), shift_hours=shift_hours)

    assert general == saved | {"shift_hours": shift_hours}
    problem = load_request(er_request() | {"general": general}).problem
    assert problem.general.hours_per_day == 7 and problem.general.weights.change == 9


# ---- defaults -------------------------------------------------------------------------------------
def test_first_start_seeds_the_defaults_flagged_for_review(monkeypatch):
    monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", "one-time-password")

    call_command("bootstrap")

    row = HospitalSettings.objects.get()
    assert row.rules == DEFAULT_RULES and row.rules_need_review


def test_an_installation_older_than_the_rules_gets_them_on_its_next_start(make_user):
    make_user("admin", Role.SYSTEM_ADMIN)

    call_command("bootstrap")

    assert HospitalSettings.objects.get().rules_need_review


def test_later_starts_leave_saved_rules_alone(monkeypatch, signed_in):
    monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", "one-time-password")
    call_command("bootstrap")
    assert put(signed_in(Role.CNO), body(hours_per_day=7)).status_code == 200

    call_command("bootstrap")

    row = HospitalSettings.objects.get()
    assert row.rules["hours_per_day"] == 7 and not row.rules_need_review


def test_the_cno_reads_the_defaults_and_the_flag(signed_in):
    answer = signed_in(Role.CNO).get(RULES).json()

    assert answer["rules"] == DEFAULT_RULES and answer["needs_review"] is True
    assert answer["shift_codes"] == ["D", "N", "A", "B", "C"]


# ---- saving ---------------------------------------------------------------------------------------
def test_saving_stores_the_rules_and_clears_the_flag(signed_in):
    client = signed_in(Role.CNO)
    saved = body(hours_per_day=7, weekend_weekdays=[4, 5], forbidden_successions=[["N", "D"]],
                 hours_rule_enabled=False)

    response = put(client, saved)

    assert response.status_code == 200
    assert response.json()["rules"] == saved and response.json()["needs_review"] is False
    assert client.get(RULES).json() == response.json()


def test_a_zero_weight_is_allowed_because_it_switches_the_rule_off(signed_in):
    response = put(signed_in(Role.CNO), weights(fair_day=0))

    assert response.status_code == 200 and response.json()["rules"]["weights"]["fair_day"] == 0


def test_weekend_days_are_stored_in_order_however_they_were_sent(signed_in):
    response = put(signed_in(Role.CNO), body(weekend_weekdays=[5, 4]))

    assert response.json()["rules"]["weekend_weekdays"] == [4, 5]


def test_no_weekend_and_no_forbidden_succession_are_both_possible(signed_in):
    response = put(signed_in(Role.CNO), body(weekend_weekdays=[], forbidden_successions=[]))

    assert response.status_code == 200


def test_saving_audits_who_changed_what_from_what_to_what(signed_in):
    client = signed_in(Role.CNO, username="the-cno")
    AuditEntry.objects.all().delete()

    put(client, weights(change=9) | {"hours_per_day": 7})

    entry = AuditEntry.objects.get()
    assert entry.action == "hospital_rules.changed" and entry.actor.username == "the-cno"
    assert entry.target == "hospital rules" and entry.ip
    assert entry.before == {"needs_review": True, "hours_per_day": 8, "weights.change": 3}
    assert entry.after == {"needs_review": False, "hours_per_day": 7, "weights.change": 9}


def test_saving_the_defaults_unchanged_is_a_review_so_it_clears_the_flag_and_is_audited(signed_in):
    client = signed_in(Role.CNO)
    AuditEntry.objects.all().delete()

    response = put(client, body())

    assert response.json()["needs_review"] is False
    entry = AuditEntry.objects.get()
    assert entry.before == {"needs_review": True} and entry.after == {"needs_review": False}


def test_saving_again_with_no_change_writes_no_entry(signed_in):
    client = signed_in(Role.CNO)
    put(client, body())
    AuditEntry.objects.all().delete()

    assert put(client, body()).status_code == 200

    assert not AuditEntry.objects.exists()


def test_a_later_change_does_not_bring_the_flag_back(signed_in):
    client = signed_in(Role.CNO)
    put(client, body())

    assert put(client, body(hours_per_day=7)).json()["needs_review"] is False


# ---- validation -----------------------------------------------------------------------------------
@pytest.mark.parametrize("rules, field", [
    (body(hours_per_day=25), ("hours_per_day",)),
    (body(hours_per_day=-1), ("hours_per_day",)),
    (body(hours_per_day="8"), ("hours_per_day",)),
    (body(hours_per_day=8.5), ("hours_per_day",)),
    (body(hours_per_day=True), ("hours_per_day",)),
    (body(ramadan_hours_per_day=9), ("ramadan_hours_per_day",)),
    (body(breastfeeding_reduction=7), ("breastfeeding_reduction",)),
    (body(weekend_weekdays=[7]), ("weekend_weekdays", 0)),
    (body(weekend_weekdays=[4, 4]), ("weekend_weekdays",)),
    (body(forbidden_successions=[["N", "X"]]), ("forbidden_successions", 0, 1)),
    (body(forbidden_successions=[["N"]]), ("forbidden_successions", 0)),
    (body(forbidden_successions=[["N", "D", "A"]]), ("forbidden_successions", 0)),
    (body(forbidden_successions=[["N", "D"], ["N", "D"]]), ("forbidden_successions",)),
    (body(forbidden_successions_enabled="yes"), ("forbidden_successions_enabled",)),
    (body(hours_rule_enabled=1), ("hours_rule_enabled",)),
    (body(overtime_caps_enabled=None), ("overtime_caps_enabled",)),
    (body(overtime_month_cap=-1), ("overtime_month_cap",)),
    (body(overtime_year_cap=10 ** 6 + 1), ("overtime_year_cap",)),
    (body(dept_overtime_cap=1.5), ("dept_overtime_cap",)),
    (weights(night_rest=-1), ("weights", "night_rest")),
    (weights(change=10 ** 6 + 1), ("weights", "change")),
    (weights(fair_day="1"), ("weights", "fair_day")),
])
def test_a_refusal_names_the_field(signed_in, rules, field):
    assert refused_fields(put(signed_in(Role.CNO), rules)) == {field}


def test_a_refusal_names_every_bad_field_at_once(signed_in):
    rules = weights(change=-1) | {"hours_per_day": 25, "overtime_month_cap": -1}

    assert refused_fields(put(signed_in(Role.CNO), rules)) == {
        ("hours_per_day",), ("overtime_month_cap",), ("weights", "change")}


def test_a_missing_field_is_named(signed_in):
    rules = body()
    del rules["hours_per_day"]
    del rules["weights"]["change"]

    assert refused_fields(put(signed_in(Role.CNO), rules)) == {("hours_per_day",), ("weights", "change")}


@pytest.mark.parametrize("rules, field", [
    (body(shift_hours={"D": 12}), ("shift_hours",)),
    (weights(extra=1), ("weights", "extra")),
])
def test_an_unknown_field_is_refused_rather_than_dropped(signed_in, rules, field):
    assert refused_fields(put(signed_in(Role.CNO), rules)) == {field}


def test_a_refused_save_changes_nothing(signed_in):
    client = signed_in(Role.CNO)
    AuditEntry.objects.all().delete()

    put(client, body(hours_per_day=25))

    row = HospitalSettings.load()
    assert row.rules == DEFAULT_RULES and row.rules_need_review and not AuditEntry.objects.exists()


@pytest.mark.parametrize("rules", [
    body(hours_per_day=0, ramadan_hours_per_day=0, breastfeeding_reduction=0),
    body(hours_per_day=24, ramadan_hours_per_day=24, breastfeeding_reduction=24),
    body(overtime_month_cap=10 ** 6, overtime_year_cap=0, dept_overtime_cap=0),
    body(forbidden_successions=[["D", "D"]]),
    body(weekend_weekdays=list(range(7))),
    weights(**dict.fromkeys(DEFAULT_RULES["weights"], 10 ** 6)),
    weights(**dict.fromkeys(DEFAULT_RULES["weights"], 0)),
])
def test_what_this_api_accepts_the_solver_accepts_too(signed_in, rules):
    response = put(signed_in(Role.CNO), rules)
    assert response.status_code == 200, response.content

    general = general_block(HospitalSettings.load(), shift_hours=er_request()["general"]["shift_hours"])

    assert load_request(er_request() | {"general": general}).problem.general.hours_per_day == rules["hours_per_day"]


# ---- authorization --------------------------------------------------------------------------------
def test_the_deputy_cno_reads_but_cannot_change(signed_in):
    client = signed_in(Role.DEPUTY_CNO)
    AuditEntry.objects.all().delete()

    assert client.get(RULES).json()["rules"] == DEFAULT_RULES
    assert put(client, body(hours_per_day=7)).status_code == 403
    assert HospitalSettings.load().rules == DEFAULT_RULES and not AuditEntry.objects.exists()


@pytest.mark.parametrize("role", [Role.SYSTEM_ADMIN, Role.UNIT_MANAGER, Role.STAFF_NURSE])
def test_every_other_role_can_neither_read_nor_change(signed_in, role):
    client = signed_in(role)

    assert client.get(RULES).status_code == 403
    assert put(client, body(hours_per_day=7)).status_code == 403
