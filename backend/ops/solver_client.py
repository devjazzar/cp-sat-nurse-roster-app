"""The application's only way to the solver service (docs/ARCHITECTURE.md section 6)."""
from __future__ import annotations

import httpx
from django.conf import settings


class SolverUnreachable(Exception):
    """The solver service did not give a usable answer."""


def solver_health(timeout: float = 2.0) -> dict:
    try:
        r = httpx.get(f"{settings.SOLVER_URL}/health", timeout=timeout,
                      headers={"Authorization": f"Bearer {settings.SOLVER_TOKEN}"})
        r.raise_for_status()
        return r.json()
    except (httpx.HTTPError, ValueError) as e:
        raise SolverUnreachable(str(e)) from e
