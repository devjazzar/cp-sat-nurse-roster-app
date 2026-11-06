"""`/metrics` for a Prometheus on the internal network (docs/ARCHITECTURE.md section 8): what the health page reads, as gauges
worked out at each scrape, in the text format by hand. Nothing here counts requests, which would need state shared across
gunicorn's workers and a library for it.

It answers with no sign-in, as a scraper cannot log in, so it must never be reached from outside: Caddy refuses the path
(deploy/Caddyfile), and this refuses whatever Caddy passed on all the same, since Caddy always adds `X-Forwarded-For`."""
from __future__ import annotations

from django.db.models import Count
from django.http import Http404, HttpRequest, HttpResponse
from django.views.decorators.http import require_GET

from ops import backups
from ops.solver_client import SolverUnreachable, solver_health
from ops.status import database_reachable, database_size_bytes, disk_usage, queue_state
from solves.models import Solve, SolveState


def _solver_up() -> bool:
    try:
        solver_health()
    except SolverUnreachable:
        return False
    return True


class _Exposition:
    def __init__(self):
        self.lines: list[str] = []

    def gauge(self, name: str, help_text: str, samples: dict[str, float] | float) -> None:
        self.lines += [f"# HELP nurse_roster_{name} {help_text}", f"# TYPE nurse_roster_{name} gauge"]
        for labels, value in (samples.items() if isinstance(samples, dict) else [("", samples)]):
            self.lines.append(f"nurse_roster_{name}{labels} {value!r}")

    def text(self) -> str:
        return "\n".join(self.lines) + "\n"


def _exposition() -> str:
    out = _Exposition()
    out.gauge("database_up", "Whether the application reaches its database.", int(database_reachable()))
    out.gauge("solver_up", "Whether the application reaches the solver service.", int(_solver_up()))
    queue = queue_state()
    out.gauge("queue_jobs", "Jobs on the queue by status: waiting, running, and failed and still kept.",
              {'{status="waiting"}': queue.waiting, '{status="running"}': queue.running, '{status="failed"}': queue.failed})
    out.gauge("queue_workers", "Queue workers that beat within the last 30 seconds.", queue.workers)
    solves = dict(Solve.objects.order_by().values_list("state").annotate(Count("id")))
    out.gauge("solves", "Solves kept, by state.", {f'{{state="{state}"}}': solves.get(state, 0) for state in SolveState.values})
    out.gauge("database_size_bytes", "The size of the application's database.", database_size_bytes())
    disk = disk_usage()
    if disk is not None:
        out.gauge("disk_free_bytes", "Free space on the disk the backups are written to.", disk.free_bytes)
        out.gauge("disk_size_bytes", "The size of the disk the backups are written to.", disk.total_bytes)
    kept = backups.list_backups()
    out.gauge("backups", "Backups kept.", len(kept))
    out.gauge("backups_size_bytes", "The size of every backup kept, together.", sum(backup.size_bytes for backup in kept))
    if kept:
        out.gauge("last_backup_timestamp_seconds", "When the newest backup was taken, in seconds since the epoch.",
                  kept[0].taken_at.timestamp())
    return out.text()


@require_GET
def metrics(request: HttpRequest) -> HttpResponse:
    if "HTTP_X_FORWARDED_FOR" in request.META:
        raise Http404()
    response = HttpResponse(_exposition(), content_type="text/plain; version=0.0.4; charset=utf-8")
    response["Cache-Control"] = "no-store"
    return response
