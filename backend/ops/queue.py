"""The one module that knows the queue's library (docs/ARCHITECTURE.md section 7), so it can be replaced without
touching what the jobs do. Procrastinate finds a job by the module's name: put it in an app's `tasks.py`."""
from __future__ import annotations

from collections.abc import Callable

from procrastinate.contrib.django import app


def hourly(*, at_minute: int) -> Callable:
    """A job that takes the time it was due, as `timestamp`, and at most one of which waits at a time."""
    def schedule(job: Callable) -> Callable:
        return app.periodic(cron=f"{at_minute} * * * *")(app.task(queueing_lock=job.__name__)(job))
    return schedule
