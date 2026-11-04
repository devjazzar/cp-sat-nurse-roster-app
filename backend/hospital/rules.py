"""The hospital rules: the solver's `general` block, kept in the solver's own field names so a solve
input can carry them as they are. `shift_hours` is not among them: it comes from the shift catalogue."""
from __future__ import annotations

# Until ticket 05's shift catalogue exists to ask. Forbidden successions may only name these.
SHIFT_CODES = ("D", "N", "A", "B", "C")

# The reviewed set the solver was shaped on. hospital/tests/test_rules.py holds it to the solver's own.
DEFAULT_RULES = {
    "hours_per_day": 8,
    "ramadan_hours_per_day": 6,
    "breastfeeding_reduction": 1,
    "weekend_weekdays": [4],
    "forbidden_successions": [["D", "C"], ["N", "D"], ["N", "A"], ["N", "B"], ["A", "B"],
                              ["A", "C"], ["B", "D"], ["C", "D"], ["C", "A"], ["C", "B"]],
    "forbidden_successions_enabled": True,
    "hours_rule_enabled": True,
    "overtime_caps_enabled": True,
    "overtime_month_cap": 40,
    "overtime_year_cap": 720,
    "dept_overtime_cap": 400,
    "weights": {
        "night_rest": 5,
        "dept_overtime": 1,
        "nurse_overtime": 1,
        "nurse_shortfall": 1,
        "avoidable_shortfall": 1000,
        "fair_day": 1,
        "fair_night": 1,
        "fair_weekend": 1,
        "score_deficit": 2,
        "score_spread": 1,
        "excess_weekend": 6,
        "shift_switch": 8,
        "undesired_day": 2,
        "desired_day": 1,
        "change": 3,
    },
}


def general_block(settings, *, shift_hours: dict[str, int]) -> dict:
    """The `general` block of a solve input."""
    return settings.rules | {"shift_hours": shift_hours}


def changes(before: dict, after: dict) -> tuple[dict, dict]:
    """Only what differs, with each weight as `weights.<name>`, so the audit log reads field by field."""
    def flat(rules: dict) -> dict:
        return {key: value for key, value in rules.items() if key != "weights"} | {
            f"weights.{key}": value for key, value in rules["weights"].items()}

    old, new = flat(before), flat(after)
    differing = [key for key in old if old[key] != new[key]]
    return {key: old[key] for key in differing}, {key: new[key] for key in differing}
