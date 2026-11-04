"""Score a given roster against a solve input, with no search."""
from __future__ import annotations

from nurse_roster.explain import explain
from nurse_roster.request import load_request
from nurse_roster.rules import HARD, soft_ids


def _parse_roster(solve_input: object, roster: object) -> list[list[int]]:
    """The roster as the package's assignment matrix. A roster has the shape of the solve
    input's `published` block, so the package's own loader checks it: every nurse, every date,
    only known shifts. This parse is thrown away after that: a solve input's real `published`
    block prices the `change` rule, and must stay what it is."""
    if not isinstance(roster, dict):
        raise ValueError("roster: must be an object {nurse id: {date: shift or \"\"}}")
    try:
        parsed = load_request({**solve_input, "published": roster, "replan_from": None})
    except ValueError as e:
        raise ValueError(str(e).replace("request: published", "roster")) from None
    return parsed.problem.published_matrix()


def validate_grid(solve_input: object, roster: object) -> dict:
    """Hard violations, cost, penalties and the per-rule explanation. The violation, cost and
    penalty fields read exactly as the same fields of a result (see nurse_roster/result.py)."""
    req = load_request(solve_input)
    matrix = _parse_roster(solve_input, roster)
    analysis = explain(req.problem, matrix)
    month = req.month

    def date_of(day: int | None) -> str | None:
        return month.iso(day) if day is not None and 0 <= day < month.days else None

    violations, elapsed_violations, rules = [], [], []
    for rule in analysis.rules.values():
        rules.append({
            "id": rule.id, "level": rule.level, "weight": rule.weight, "unit": rule.unit,
            "raw": rule.raw, "weighted": rule.weighted,
            "matches": [{"nurse": m.nurse, "date": date_of(m.day), "amount": m.amount,
                         "text": m.text, "elapsed": m.elapsed} for m in rule.matches],
        })
        if rule.level == HARD:
            for m in rule.matches:
                item = {"rule": rule.id, "nurse": m.nurse, "date": date_of(m.day), "text": m.text}
                (elapsed_violations if m.elapsed else violations).append(item)
    return {
        "ok": not violations,
        "violations": violations,
        "elapsed_violations": elapsed_violations,
        "cost": analysis.total,
        "penalties": {rid: analysis.rules[rid].weighted for rid in soft_ids()},
        "department_cost": analysis.nurses.get("", 0),
        "nurses": {nid: cost for nid, cost in analysis.nurses.items() if nid},
        "rules": rules,
    }
