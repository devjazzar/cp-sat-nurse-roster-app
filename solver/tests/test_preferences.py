"""Preferences after an unkept month (ADR 0013): a nurse whose preferences the month before were not all kept carries
`preferences_not_kept` above zero, and every day she asked off or asked to work then costs twice its weight, in the model's
objective and in the validator's explanation alike; the result's carry-over counts, from the month's own facts, the days of
hers not kept for next month. Expected numbers are worked out by hand on tiny months."""
from __future__ import annotations

import pytest

from nurse_roster.explain import explain, report
from nurse_roster.model import build_model, solve
from nurse_roster.problem import Headcount, Nurse, Weights
from nurse_roster.request import load_request
from nurse_roster.result import nurse_accounting
from nurse_roster.validate import validate
from solver_service.grid import nurses_of
from tests.er_fixture import request_of
from tests.test_audit import mini

D, OFF = 0, -1


def prices(undesired: int = 2, desired: int = 1) -> Weights:
    return Weights(**{**{f: 0 for f in Weights.__slots__}, "undesired_day": undesired, "desired_day": desired})


def two_nurses(**weights):
    """Three days, one shift. Both nurses asked day 0 off and day 1 to work; only `a`'s were not kept last month."""
    return mini(3, ["D"], [Nurse("a", undesired_days=[0], desired_days=[1], preferences_not_kept=1),
                           Nurse("b", undesired_days=[0], desired_days=[1])], weights=prices(**weights))


BOTH_BROKEN = [[D, OFF, OFF], [D, OFF, OFF]]          # each works the day she asked off, is off the day she asked to work


# ---- the price -----------------------------------------------------------------------------------
def test_a_nurse_with_an_unkept_month_pays_twice_the_weight_and_another_once():
    p = two_nurses(undesired=2, desired=1)

    errors, by_rule, total = validate(p, BOTH_BROKEN)

    # a: 2 x 2 (day 0 worked) + 2 x 1 (day 1 off) = 6;  b: 2 + 1 = 3
    assert errors == [] and by_rule["undesired_day"] == 4 + 2 and by_rule["desired_day"] == 2 + 1 and total == 9
    an = explain(p, BOTH_BROKEN)
    assert an.nurses == {"a": 6, "b": 3, "": 0} and an.total == 9


def test_any_count_above_zero_doubles_and_never_more():
    p = two_nurses()
    p.nurses[0].preferences_not_kept = 7
    assert explain(p, BOTH_BROKEN).nurses["a"] == 6
    p.nurses[0].preferences_not_kept = 0
    assert explain(p, BOTH_BROKEN).nurses["a"] == 3


def test_a_solves_cost_and_a_validation_of_the_same_grid_agree():
    p = two_nurses(undesired=2, desired=1)

    forced = _solve_grid(p, BOTH_BROKEN)
    assert forced.assignment == BOTH_BROKEN
    assert forced.solver_objective == forced.objective == 9 == validate(p, BOTH_BROKEN)[2]


def _solve_grid(p, grid):
    """The model with every cell fixed to `grid` (no history, so month day d is horizon index d)."""
    rm = build_model(p)
    for n, row in enumerate(grid):
        for d, v in enumerate(row):
            rm.model.add(rm.off[n][d] == 1) if v < 0 else rm.model.add(rm.x[n][d][v] == 1)
    return solve(rm, p, time_limit=10, workers=4)


def test_the_solver_keeps_the_doubled_nurses_wish_when_only_one_can_have_it():
    """One nurse a day on the only shift: someone works day 0, which both asked off. Keeping `a`'s saves twice the
    weight, so the optimum gives day 0 to `b`."""
    p = mini(2, ["D"], [Nurse("a", undesired_days=[0], preferences_not_kept=1), Nurse("b", undesired_days=[0])],
             weights=prices(undesired=1, desired=0), headcounts=[Headcount("D", 1, 1, 1, 1)], headcount_enabled=True)

    sol = solve(build_model(p), p, time_limit=10, workers=4)

    assert sol.status == "OPTIMAL" and sol.assignment[0][0] == OFF and sol.assignment[1][0] == D
    assert sol.objective == sol.solver_objective == 1


def test_a_leave_day_is_ignored_for_a_doubled_nurse_too():
    p = mini(3, ["D"], [Nurse("a", unavailable=[0, 1], undesired_days=[0], desired_days=[1], preferences_not_kept=1)],
             weights=prices())
    assert validate(p, [[OFF, OFF, OFF]])[2] == 0


# ---- the words -----------------------------------------------------------------------------------
def test_the_explanation_says_a_doubled_preference_counted_double():
    an = explain(two_nurses(), BOTH_BROKEN)

    off = {m.nurse: m for m in an.rules["undesired_day"].matches}
    on = {m.nurse: m for m in an.rules["desired_day"].matches}
    assert (off["a"].amount, on["a"].amount, off["b"].amount, on["b"].amount) == (2, 2, 1, 1)
    assert "counts double" in off["a"].text and "counts double" in on["a"].text
    assert "double" not in off["b"].text and "double" not in on["b"].text
    assert off["a"].text == "a: works day 0 (asked off; counts double, a preference was not kept last month)"
    assert on["a"].text == "a: off on day 1 (asked to work; counts double, a preference was not kept last month)"
    assert "counts double" in report(an)


# ---- the carry-over -------------------------------------------------------------------------------
def _june(nurses):
    """A June 2026 request (30 days from a Monday) with every rule off and both prices at 0: the count is a fact of the
    month, whatever the weights."""
    return request_of(mini(30, ["D"], nurses, weights=prices(0, 0)), "2026-06")


def _grid(rows: dict[str, set[int]]) -> list[list[int]]:
    """One row per nurse, D on the given days, off elsewhere."""
    return [[D if d in on else OFF for d in range(30)] for on in rows.values()]


def test_the_carry_over_counts_the_days_not_kept_with_leave_left_out():
    # a asked days 0, 1, 4 off and days 2, 3 to work; day 3 became leave. She works 0 and 4 (2 not kept), is off 2
    # (1 not kept) and 3 (leave: neither way); day 1 is kept. Already doubled, she still carries days, not the price.
    raw = _june([Nurse("a", undesired_days=[0, 1, 4], desired_days=[2, 3], unavailable=[3], preferences_not_kept=1),
                 Nurse("b", undesired_days=[5], desired_days=[6]),
                 Nurse("c")])
    p = load_request(raw).problem
    grid = _grid({"a": {0, 4}, "b": {6}, "c": {0, 1, 2}})

    carried = {nid: row["carry_over"]["preferences_not_kept"] for nid, row in nurse_accounting(p, grid).items()}

    assert carried == {"a": 3, "b": 0, "c": 0}


def test_a_shift_the_roster_in_force_holds_on_a_leave_day_counts_neither_way():
    """The service's reading of a month: leave wins over the roster in force, and a preference on a leave day is not
    counted, whichever way the roster went."""
    raw = _june([Nurse("a", undesired_days=[9], desired_days=[10], unavailable=[9, 10])])
    roster = {"a": {f"2026-06-{d + 1:02d}": ("D" if d in (9, 12) else "") for d in range(30)}}

    assert nurses_of(raw, roster)["a"]["carry_over"]["preferences_not_kept"] == 0


def test_the_count_carried_out_loads_as_next_months_input():
    raw = _june([Nurse("a", undesired_days=[0, 1])])
    p = load_request(raw).problem
    out = nurse_accounting(p, _grid({"a": {0, 1}}))["a"]["carry_over"]
    assert out["preferences_not_kept"] == 2

    nxt = dict(raw, month="2026-07")
    nxt["nurses"] = [dict(n, **out, undesired_days=[]) for n in raw["nurses"]]
    assert load_request(nxt).problem.nurses[0].preferences_not_kept == 2


@pytest.mark.parametrize("count", [0, 1, 31])
def test_the_count_loads_from_the_request(count):
    raw = _june([Nurse("a", preferences_not_kept=count)])
    assert load_request(raw).problem.nurses[0].preferences_not_kept == count


def test_an_absent_count_is_zero_so_every_stored_input_still_loads():
    raw = _june([Nurse("a")])
    del raw["nurses"][0]["preferences_not_kept"]
    assert load_request(raw).problem.nurses[0].preferences_not_kept == 0
