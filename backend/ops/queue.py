"""The one module that knows the queue's library (docs/ARCHITECTURE.md section 7), so it can be replaced without
touching what the jobs do. Procrastinate finds a job by the module's name: put it in an app's `tasks.py`."""
from __future__ import annotations

from collections.abc import Callable

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from procrastinate.contrib.django import app
from procrastinate.contrib.django.models import ProcrastinateJob, ProcrastinateWorker
from procrastinate.exceptions import AlreadyEnqueued

from ops.status import WORKER_SILENCE

# Jobs sharing a lock run one at a time, lowest job id first, whichever worker fetches them. A job kept waiting by the lock
# takes no place from one without it, so the crons still run between solves.
_HOSPITAL_WIDE_SOLVE = "solve"


def _periodic(cron: str) -> Callable:
    """A job that takes the time it was due, as `timestamp`. At most one of it waits at a time (its queueing lock), and it never
    runs beside its own previous run (its lock), both under its own name (ADR 0009): at the worker's concurrency of 4, a periodic
    job runs beside a solve, but never beside itself."""
    def schedule(job: Callable) -> Callable:
        return app.periodic(cron=cron)(app.task(queueing_lock=job.__name__, lock=job.__name__)(job))
    return schedule


def hourly(*, at_minute: int) -> Callable:
    return _periodic(f"{at_minute} * * * *")


every_five_minutes = _periodic("*/5 * * * *")


def one_at_a_time_across_the_hospital(job: Callable) -> Callable:
    return app.task(lock=_HOSPITAL_WIDE_SOLVE)(job)


def under_its_own_lock(job: Callable) -> Callable:
    """A job run on demand that may not run beside itself (ADR 0009's rule 1)."""
    return app.task(lock=job.__name__)(job)


def enqueue_once(job: Callable, key: str, **arguments) -> int | None:
    """As `enqueue`, but no second copy waits while one with this key does: None then. In a savepoint of its own, so the copy
    already waiting fails only this and not the caller's transaction."""
    try:
        with transaction.atomic():
            return job.configure(queueing_lock=key).defer(**arguments)
    except AlreadyEnqueued:
        return None


def enqueue(job: Callable, **arguments) -> int:
    """Puts a job on the queue in the caller's transaction, so neither it nor what it is about exists without the other."""
    return job.defer(**arguments)


def requeue_stalled() -> list[int]:
    """Jobs whose worker died with them, which would otherwise hold their lock for good. A job is `doing` until then, however
    long it has run: a worker that lives keeps beating. The library's own call for this is async only, and this is the same
    query, so it holds to what `select_stalled_jobs_by_heartbeat` means."""
    silent = ProcrastinateWorker.objects.filter(last_heartbeat__lt=timezone.now() - WORKER_SILENCE)
    stalled = list(ProcrastinateJob.objects.filter(Q(worker__isnull=True) | Q(worker__in=silent), status="doing")
                   .values_list("id", flat=True))
    for job_id in stalled:
        app.job_manager.retry_job_by_id(job_id, timezone.now())
    return stalled


def still_on_the_queue(job_ids: list[int]) -> set[int]:
    """Those of these jobs that a worker will yet run or is running."""
    return set(ProcrastinateJob.objects.filter(id__in=job_ids, status__in=("todo", "doing")).values_list("id", flat=True))
