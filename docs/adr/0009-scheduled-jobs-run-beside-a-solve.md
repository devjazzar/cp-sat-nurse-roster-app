---
status: accepted
date: 2026-11-06
---
# Scheduled jobs run beside a solve: one worker, every job under a lock, and only `run_solve` calls the solver's search

A solve holds the hospital-wide lock for up to the time-limit cap (300 s), and the worker ran one
job at a time, so every scheduled job waited behind a running solve. The month close cannot wait.
The `worker` container therefore runs Procrastinate at concurrency 4, and three rules keep that
safe:

1. **Every job takes a lock.** Solves share the hospital-wide one; each periodic job takes one
   under its own name, beside its queueing lock. Procrastinate never fetches a job whose lock a
   running job holds, so a waiting job takes no slot, no kind of job can hold more than one, and a
   periodic job never runs beside its own previous run. A new job that can run longer than about a
   minute (ticket 22's backup) takes a lock of its own for the same reason.
2. **`run_solve` is the only caller of the solver's `POST /solve`.** The solver service runs one
   job and answers `409` to a second, and `run_solve` cancels a job it finds there that no solve is
   watching. Anything else that submitted a search would be refused during a solve or cancelled by
   the next one.
3. **The close and the projection compute carry-over with no search, in the worker's own
   process.** The per-nurse carry-over block is one function of the vendored package, taking a
   problem and a complete grid, used by the solver's own result and exposed beside `validate_grid`
   in `solver_service.grid`. A close and a solve cannot work it out differently, and the close
   needs neither the solver container nor its one job.

The close itself is an hourly catch-up job at minute 30, like the other hourly jobs: it closes
every unit's month whose close time has passed on the hospital's clock and is not closed.
Procrastinate's cron is fixed at import and runs in UTC, so it could neither read a configured time
nor follow the hospital's time zone; a worker that was down catches up on its next run. A close does
not wait for or stop a solve of a later month: that solve ends as usual and its draft is warned of
as older than the close, as for a correction to leave, and is validated again before submit.

## Considered options

- **A `solves` queue and a second worker service** for everything else: a hard reservation that
  needs no rule about locks, but a sixth container from the same image, two heartbeats to watch,
  and a change to ADR 0001's set of services, for an installation whose only long job is the solve.
  If a second kind of long job ever cannot be given a lock, this is the way back.
- **Two processes in the worker container:** against ADR 0001's one process per container.
- **The close as a solve with every day recorded,** through `POST /solve`: it is the same
  computation, but it would queue behind the solver's one job, which is the delay this removes.

## Consequences

- Database connections: the worker holds a pool of 4, one listener and one per running job, at
  most 9, beside `web`'s three, against PostgreSQL's default limit of 100.
- `recover_lost_jobs` now runs during a solve rather than between solves. It holds: it requeues
  only the jobs of a worker silent for 30 s, and fails a solve only when its queue job is neither
  waiting nor running; a solve's row is ended before its job is.
- Ticket 11's "the worker's concurrency stays 1" is superseded.
