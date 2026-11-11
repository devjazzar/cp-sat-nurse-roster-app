"""The public `GET /api/health` answer, kept five seconds in each web process (ticket 68), so a client polling it cannot make
the application call the solver and the database on every request. Only that route keeps it: the System Admin's health page
and `/metrics` ask afresh each time.

Gunicorn's threads in one process share the kept answer, and one lock is held while it is worked out, so a burst of requests
as it runs out makes one call to the solver, not one a thread; the others wait for it, at most the solver's 2-second timeout.
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Generic, TypeVar

KEPT_SECONDS = 5.0

# Read at each request, so a test can move it (`ops/tests/test_health.py`).
clock: Callable[[], float] = time.monotonic

T = TypeVar("T")


class Kept(Generic[T]):
    """An answer worked out by `work`, given again until `seconds` have passed on `clock` since it was worked out."""

    def __init__(self, work: Callable[[], T], seconds: float = KEPT_SECONDS):
        self._work, self._seconds = work, seconds
        self._lock = threading.Lock()
        self._answer: T | None = None
        self._until = 0.0

    def __call__(self) -> T:
        with self._lock:
            if self._answer is None or clock() >= self._until:
                self._answer = self._work()
                self._until = clock() + self._seconds
            return self._answer

    def forget(self) -> None:
        """For the tests' own start: each test begins with nothing kept."""
        with self._lock:
            self._answer, self._until = None, 0.0
