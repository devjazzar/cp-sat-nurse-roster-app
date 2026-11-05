"""Reading a stored result: the one place that says what its fields mean to this application."""
from __future__ import annotations


def has_a_roster_to_keep(result: dict | None) -> bool:
    """A result can hold no roster, or one the validator says breaks a hard rule, which `ok` false reports. Neither becomes
    a draft."""
    return bool(result and result.get("ok") and result.get("roster"))
