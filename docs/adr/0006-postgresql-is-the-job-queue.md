---
status: accepted
date: 2026-11-04
---
# PostgreSQL is the job queue, through Procrastinate; no Redis or message broker

Solves run for minutes and must survive a restart, report progress, be cancellable and be
serialised (one at a time, since CP-SAT uses every core). The obvious stack, Celery with Redis
or RabbitMQ, would add a second stateful service to an installation whose whole point is one
image and one `docker compose up`. Procrastinate keeps the queue in our PostgreSQL database
(LISTEN/NOTIFY plus polling, `FOR UPDATE SKIP LOCKED`), has retries, cron-style periodic jobs
for the nightly backup and the month close, job locks, cooperative cancellation and a Django
integration with migrations and admin. The `worker` container runs it from the same image as
`web`. The worker, not the solver, talks to the queue: the solver container never holds a
database credential.

Risk accepted: Procrastinate has two active maintainers. The queue is therefore wrapped in one
module of ours (enqueue a solve, report progress, cancel, schedule), so a replacement would not
touch the API, the solver client or the solver.

## Considered options

- Django's built-in tasks framework (6.x): no database worker backend in core yet, no
  cancellation, no scheduling.
- django-tasks-db, Django-Q2: polling only, no cancellation API, no cron (or single maintainer).
- Celery: no supported SQL broker; needs Redis or RabbitMQ.
