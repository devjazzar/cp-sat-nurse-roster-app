"""Reading a stored result: the one place that says what its fields mean to this application."""
from __future__ import annotations

import datetime as dt
import re

from nurse_roster.rules import SOFT
from solver_service.grid import validate_grid

# Below this many, every occurrence is in view; a long tail of the same thing says nothing more. The solver's own report's size.
LARGEST = 5
_DAY = re.compile(r"(?<![/\w])day (-?\d+)\b")  # Not "changes night/day 6 times", the one place a day's number follows otherwise.


def has_a_roster_to_keep(result: dict | None) -> bool:
    """A result can hold no roster, or one the validator says breaks a hard rule, which `ok` false reports. Neither becomes
    a draft."""
    return bool(result and result.get("ok") and result.get("roster"))


def in_dates(text: str, month: dt.date) -> str:
    """The solver's words count a month's days from 0 ("day 4" is the 5th), and from below 0 for the days before it, which
    next to a date in the same line reads as a mistake."""
    return _DAY.sub(lambda found: (month + dt.timedelta(days=int(found[1]))).isoformat(), text)


def explanation(solve_input: dict, result: dict | None) -> dict[str, dict] | None:
    """Each soft rule that costs something: its own largest occurrences, by rule name. A stored result holds only the totals,
    so this asks the solver's own code to score what is stored, here and with no search, which needs no solver running.
    None if the solver's code no longer reads what it was given."""
    if not (result and result.get("roster")):
        return {}
    try:
        answer = validate_grid(solve_input, result["roster"])
    except ValueError:
        return None
    return {rule["id"]: rule | {"matches": sorted(rule["matches"], key=lambda match: -match["amount"])}
            for rule in answer["rules"] if rule["level"] == SOFT and rule["weighted"]}
