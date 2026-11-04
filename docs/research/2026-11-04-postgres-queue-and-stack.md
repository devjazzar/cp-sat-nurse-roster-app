# PostgreSQL job queue and stack versions — research notes

Date of research: 2026-11-04. Pure web research against primary sources (PyPI JSON API, GitHub REST API, official docs and release notes). Every fact below carries the date of the release or document it was read from. "Last 6 months" means 2026-05-04 to 2026-11-04. GitHub `open_issues_count` includes pull requests; the "issues only" numbers come from the GitHub search API.

Settled context (not researched): single-hospital Django + React SPA, PostgreSQL only, docker compose on one VPS, a separate CPU-heavy OR-Tools CP-SAT solver container with no DB and no internet, reachable from the web container over an internal HTTP API. The web side needs a durable PostgreSQL job queue (no Redis/RabbitMQ) so a worker process can run "solve" jobs (20 s to minutes, one at a time), call the solver over HTTP, record progress, store results, support cancellation, and run a nightly backup job.

---

## 1. PostgreSQL-backed task queues usable from Django

### Summary table

| Candidate | Latest version (date) | Python / Django | Storage and wake-up | Separate worker process | Periodic tasks | Cancellation | Django integration | Maintenance signal |
|---|---|---|---|---|---|---|---|---|
| Procrastinate | 3.10.0 (2026-09-23) | Py >=3.10, CI 3.10–3.14 with PG 14–18; `django>=2.2` extra, "tested with the latest Django supported by that Python" | Own tables (`procrastinate_jobs`, `_events`, `_periodic_defers`, `_workers`); LISTEN/NOTIFY trigger + polling fallback; `FOR UPDATE SKIP LOCKED` | Yes: `./manage.py procrastinate worker` (uses Django `DATABASES`) or `procrastinate --app=... worker` with a psycopg conninfo | Yes, `@app.periodic(cron=...)`, DB-deduplicated across workers | Yes: `cancel_job_by_id(id, abort=True)`; running job checks `context.should_abort()` / `JobAborted`; NOTIFY on abort | Mature: `procrastinate.contrib.django` app, migrations, models, admin, mgmt command | 2 active maintainers, README says "looking for additional maintainers"; 70 open issues, 18 opened / 8 closed in 6 months |
| Django core `django.tasks` + `django-tasks-db` | Django 6.1.3 (2026-11-03); django-tasks-db 0.13.0 (2026-08-28) | django-tasks-db: Py 3.10–3.14 (3.15 formalised on master 2026-10-16), `django>=5.2`, classifiers 5.2/6.0 | ORM model `DBTaskResult` (UUID pk, status, priority, run_after, worker_ids...); polling only (`--interval`, default 1 s); claims via `select_for_update(skip_locked=True)` | Yes: `./manage.py db_worker` | No cron (only `run_after`); DEP 14 puts cron out of scope; third-party `django-crontask` 2.2.0 | No API in core or backend | Core API is official; backend is third party (Jake Howard, the DEP 14 author) | 1 main maintainer; 12 open issues, 8 closed in 6 months; 22 commits in 6 months |
| Django-Q2 | 1.11.1 (2026-08-26) | Py 3.10–3.14, `django>=5.2`, tested 5.2/6.0/6.1 | ORM broker table `django_q_ormq` (`key`, `payload`, `lock`); polling every `poll` = 0.2 s; results in `django_q_task`; schedules in `django_q_schedule` | Yes: `python manage.py qcluster` (multiprocessing cluster) | Yes: `Schedule` model (ONCE, MINUTES, HOURLY, DAILY, ..., CRON via croniter), editable in admin | No cancel/abort API; only `timeout` kills a worker process | Native Django app (admin pages for queue, tasks, schedules) | Essentially 1 maintainer (GDay); 81 open issues, 13 opened / 8 closed in 6 months; 17 commits in 6 months |
| Celery + SQL broker | Celery 5.6.3 (2026-03-26); Kombu 5.7.0 (2026-11-03) | Celery Py >=3.9 | Kombu SQLAlchemy transport (not listed as a Celery broker at all); new Kombu 5.7.0 `pgmq://` transport needs the PGMQ Postgres extension | Yes (`celery worker`) | celery beat | `revoke(terminate=True)` (not verified here) | celery itself is Django-friendly | SQLAlchemy transport not in Celery's broker table (stable: RabbitMQ, Redis, SQS); historically "experimental" |
| pgqueuer | 1.6.0 (2026-10-11) | Py 3.10–3.15; asyncio-first; asyncpg/psycopg | Own tables; LISTEN/NOTIFY + polling; `FOR UPDATE SKIP LOCKED`; heartbeats | Yes: `pgq run myapp:main` | Yes: `@schedule` cron decorator (5/6 fields) | Yes: `queries.mark_job_as_cancelled(ids)` + `with ctx.cancellation:`; "best-effort" | None (integrations: FastAPI, Flask, MCP, PostgREST, Prometheus) | 1 maintainer (janbjorge, 844 of ~870 contributions); 11 open issues, 84 closed in 6 months |
| Chancy | 0.26.0 (2026-10-14) | Py >=3.11; `django>=4.0` extra; PG 14–18 (PyPI badge) | Own tables (`chancy_` prefix); dashboard; retries, cron, workflows plugins | Yes: `chancy --app ... worker start` (worker.py calls `django.setup()`) | Yes, Cron plugin (admin-editable with `chancy.plugins.cron.django`) | Yes ("cancellation" listed as a job feature) | `chancy.contrib.django` (models + admin) and an **experimental** `django.tasks` backend `chancy.contrib.django.backend.ChancyBackend` (Django 6.0+) | 1 maintainer (TkTech, 547 of ~556 contributions); 293 stars; pushed 2026-11-04 |
| django-pgqueue | 0.9.3 (2019-12-17) | Py 3.5–3.7, Django 2.0–2.2 | — | — | — | — | — | Dead: no release since 2019 |

### 1.1 Procrastinate

- Latest release 3.10.0, PyPI upload 2026-09-23; `requires_python >=3.10`; core deps `psycopg[pool]`, `croniter`, `asgiref`; extras `django` (`django>=2.2`), `sqlalchemy`, `aiopg`, `psycopg2`. Development status classifier: 5 Production/Stable.
- Release cadence 2026: 3.7.0 (2026-01-17, dropped Py 3.9, added 3.14), 3.7.1/3.7.2 (Jan), 3.7.3 (2026-03-28), 3.8.0 (2026-04-06, external-connection atomic defer), 3.8.1 (Apr), 3.9.0 (2026-06-20: task and worker middleware, automatic closing of Django DB connections around each task), 3.10.0 (2026-09-23: external connection support for cancellation/status, worker shutdown fix, heartbeats compared against DB clock).
- CI matrix: Python 3.10/3.11/3.12/3.13/3.14 paired with PostgreSQL 14/15/16/17/18. README states "Python 3.10+" and "PostgreSQL 13+". Django docs say "Procrastinate is tested with the latest Django version supported by that Python version"; no explicit Django version list.
- Storage: `procrastinate_jobs` (bigserial id, queue_name, task_name, priority, lock, queueing_lock, jsonb args, status enum `todo/doing/succeeded/failed/cancelled/aborted`, scheduled_at, attempts, abort_requested, worker_id), `procrastinate_events`, `procrastinate_periodic_defers` (unique on task_name, periodic_id, defer_timestamp), `procrastinate_workers` (heartbeat). Trigger `procrastinate_jobs_notify_queue_job_inserted_v1` sends NOTIFY on `procrastinate_queue_v1#<queue>` and `procrastinate_any_queue_v1`; a second trigger notifies on `abort_requested`. Fetch function `procrastinate_fetch_job_v2` uses `FOR UPDATE ... SKIP LOCKED`.
- Worker: LISTEN/NOTIFY by default plus polling (`fetch_job_polling_interval` 5 s, `abort_job_polling_interval` 5 s), `concurrency` default 1 (each worker takes one job at a time; raise for async I/O-bound jobs), `update_heartbeat_interval` 10 s, `stalled_worker_timeout` 30 s, `shutdown_graceful_timeout`, `install_signal_handlers`. Stalled jobs are not retried automatically: the docs show a `@app.periodic(cron="*/10 * * * *")` task that calls `job_manager.get_stalled_jobs()` and `job_manager.retry_job(job)`.
- Retries: `@app.task(retry=5 | True | RetryStrategy(max_attempts, wait | linear_wait | exponential_wait, retry_exceptions))`, or subclass `BaseRetryStrategy.get_retry_decision()`.
- Periodic: `@app.periodic(cron="*/5 * * * *")` above `@app.task`; the decorated task receives a `timestamp` argument; the database guarantees a single defer per period even with several workers; missed runs older than 10 minutes are skipped (configurable). Scheduling only happens while a worker is running.
- Cancellation: `app.job_manager.cancel_job_by_id(job_id, abort=False, delete_job=False)` (and `_async`). Queued jobs are cancelled directly; with `abort=True` a running job is "marked for abortion", workers get a NOTIFY (or poll); sync tasks declared with `pass_context=True` must call `context.should_abort()` and raise `JobAborted`; async tasks receive `asyncio.CancelledError`. An aborted-then-failed job is not retried.
- Django integration: `pip install 'procrastinate[django]'`, add `"procrastinate.contrib.django"` to `INSTALLED_APPS`, run Django migrations (provided), define tasks with `from procrastinate.contrib.django import app; @app.task`, defer with `mytask.defer(...)` / `await mytask.defer_async(...)`, run `./manage.py procrastinate worker` which "connects using the `DATABASES` settings" (requires psycopg 3 or aiopg). Models `ProcrastinateJob`, `ProcrastinateEvent`, `ProcrastinatePeriodicDefer`, `ProcrastinateWorker` with admin pages; a how-to for FK relations from your models to `ProcrastinateJob`. A worker can also run without Django via `procrastinate --app=dotted.path worker` with a `PsycopgConnector` conninfo.
- Maintenance: repo created 2019-02; 1,442 stars; pushed 2026-11-02; MIT. Contributors: ewjoachim 1,085, medihack 209 (both active in 2026: ewjoachim 19+ commits since 2026-08-22, medihack 25+ since 2026-06-13); bots (renovate, pre-commit-ci, dependabot) author most commits. Issues only: 70 open, 18 opened and 8 closed in the last 6 months. README: "Procrastinate is looking for additional maintainers!" (discussion #748).

### 1.2 Django's Tasks framework (DEP 14, `django.tasks`) and `django-tasks-db`

- DEP 14 "Background workers" (status Accepted, type Feature, author Jake Howard, shepherd Carlton Gibson, created 2024-02-07) proposed three core backends (Immediate, Database, Dummy), put cron scheduling and automatic retries out of scope for the first pass, and does not provide a worker ("the responsibility of the underlying implementation").
- What shipped: Django 6.0 (released 2025-12-03) added `django.tasks` with only `django.tasks.backends.immediate.ImmediateBackend` and `django.tasks.backends.dummy.DummyBackend`; the release notes say "The two built-in backends included in this release are primarily intended for development and testing" and "Django ... does not provide a worker mechanism to run tasks." The 6.1 reference docs repeat that core backends are "for development and testing only" and point to the Community Ecosystem page and the Django Packages "task-framework" grid for production backends. Django 6.1 (2026-08-05) only added `task(**kwargs)` forwarding and pickling of `Task`/`TaskResult`. The 6.2 draft release notes (read 2026-11-04) have an empty "Tasks" placeholder. So: **no database backend in core in 6.0, 6.1, or the 6.2 draft.** The DatabaseBackend from the DEP lives in the third-party `django-tasks-db`.
- Core API: `@task(priority=, queue_name=, takes_context=)`, `.enqueue()`, `.using(run_after=...)`, `TaskResultStatus` = READY / RUNNING / FAILED / SUCCESSFUL, `result.errors`, `context.attempt`. No cancellation API, no periodic API.
- `django-tasks` (the backport, 0.12.0, 2026-02-06) is only needed on Django < 6.0; since 0.12.0 the DB and RQ backends are separate packages. Repo last pushed 2026-05-22 (2 commits in 6 months) — it is in maintenance because the API now lives in Django.
- `django-tasks-db` 0.13.0 (2026-08-28): `requires_python >=3.10`, `django>=5.2`, classifiers Django 5.2 and 6.0, Python 3.10–3.14 (3.15 formalised on master 2026-10-16). 0.13.0 removed the dependency on `django-tasks`, added MySQL/MariaDB support and better SQLite/MySQL claiming locks. Storage: `DBTaskResult` (UUID4 pk by default, custom `id_function` such as `uuid.uuid7` or a DB expression on Django 6.0+; status, priority, run_after, worker_ids, return_value, exception path + traceback; partial index on READY ordering). Claiming: `ready().get_locked()` = `select_for_update(skip_locked=True).first()` inside a transaction. Worker: `./manage.py db_worker --queue-name --exclude-queues --interval (1 s) --batch --max-tasks --worker-id --backend --no-startup-delay --reload`; SIGINT/SIGTERM finish the current task then exit, second signal aborts. Polling only (no LISTEN/NOTIFY). No retry policy (the backport README: attempts "will currently only ever be 0 or 1"), no cancellation, no cron. `prune_db_task_results` command for retention. Repo: 126 stars, created 2026-02-03, pushed 2026-10-16, 22 commits in 6 months (14 by RealOrangeOne), 12 open issues, 8 closed in 6 months.
- Periodic tasks for `django.tasks` need another package, e.g. `django-crontask` 2.2.0 (2026-10-10, `requires_python >=3.14`, `django>=6.0`, APScheduler-based, `python manage.py crontask` process, optional Redis lock to avoid duplicate schedulers).
- Other `django.tasks` backends seen on the Django Packages grid (2026-11-04, not evaluated in depth): `dj-queue` 0.15.0 (2026-10-31, `django>=6.0,<6.2`, Solid-Queue-inspired, recurring tasks, LISTEN/NOTIFY on top of polling, no automatic retries, no cancel; 13 stars, created 2026-04-06, one owner), `django-task-psql` 0.2.1 (2026-08-27, `django>=6.1`, SKIP LOCKED + LISTEN/NOTIFY + retry with backoff; 0 stars, created 2026-08-26, 4 releases), `django-ox` 1.9.1, `threadmill` 0.10.0, `Steady Queue` 0.3.0, `huey` 3.5.4 (2026-11-01; description: "support for redis (or valkey/redict), postgres, sqlite, file-system, or in-memory storage" and "django integration (native or via django.tasks)").

### 1.3 Django-Q2

- 1.11.1 on PyPI 2026-08-26 (`requires_python <4,>=3.10`, `django>=5.2`, tested with Django 5.2/6.0/6.1, Python 3.10–3.14). Releases: 1.8.0 (2025-04-25), 1.9.0 (2025-12-04, Django 6.0), 1.10.0 (2026-05-01), 1.11.0 (2026-08-14: Py 3.13/3.14, Django 6.1, croniter extra, moved to uv), 1.11.1 (2026-08-26).
- ORM broker: queue rows in `django_q_ormq` (`key` cluster name, `payload` signed pickle, `lock` datetime); results in `django_q_task` (id, func, args/kwargs/result as pickled fields, started/stopped, success, attempt_count); schedules in `django_q_schedule` (`schedule_type` O/I/H/D/W/BW/M/BM/Q/Y/C with `cron`, `repeats`, `next_run`, `catch_up`). Broker docs: ORM broker "supports delivery receipts and bulk dequeuing", needs Django's cache framework for monitoring, "isn't a good first choice for high-traffic setups" unless given a dedicated DB, "suits medium message rates and scheduled tasks best". Polling: `poll` default 0.2 s.
- Long tasks: `timeout` default None; `retry` default 60 s "must be greater than timeout and the duration of your longest task" or the broker re-delivers the task (docs show a sleep(22)/retry 5 task running five times); `max_attempts` 0 = infinite; `ack_failures`.
- Cancellation: none. The tasks docs expose only `delete_group`/`group_delete` (deleting stored Task rows) and `timeout`. No revoke/abort API for a queued or running task.
- Worker: `python manage.py qcluster` (multiprocessing: sentinel, pusher, workers, monitor, scheduler); "run only one qcluster process per environment".
- Maintenance: fork of Koed00/django-q (2022-09-03); 632 stars; pushed 2026-10-31; 17 commits in 6 months (10 by GDay, 7 single-commit contributors); contributors GDay 113 (Koed00's 1,101 are inherited history). Issues only: 81 open, 13 opened and 8 closed in the last 6 months.

### 1.4 Celery with a SQL broker

- Celery stable 5.6.3 (PyPI 2026-03-26, `requires_python >=3.9`, `kombu>=5.6.0`); 5.7.0rc1 on GitHub 2026-10-18. Kombu 5.7.0 released 2026-11-03.
- Celery's "Backends and Brokers" page lists stable brokers RabbitMQ, Redis, Amazon SQS and experimental Zookeeper, Kafka, GC PubSub ("Experimental brokers may be functional but they don't have dedicated maintainers"). SQLAlchemy appears only as a **result backend**: "SQLAlchemy is a backend ... the way Celery can use a SQL DB as a result backend." No SQL broker and no Django-ORM broker is documented for Celery 5.x. The old Celery 3.1 "SQLAlchemy broker" page carried an "Experimental Status" warning (unstable, no remote control/events, duplicate execution with more than a few workers). Kombu still ships `kombu.transport.sqlalchemy` (virtual transport; direct/topic yes, fanout/priority/TTL no; 5.7.0 changelog only contains fixes) but it is not a supported Celery broker.
- New: Kombu 5.7.0a1 "Add PGMQ transport for PostgreSQL message queues (#2559)"; `pgmq://user:pass@host:5432/db`, extra `kombu[pgmq]` pins `pgmq==1.1.4`, requires the PGMQ extension in PostgreSQL (`init_extension` can create it), long polling with NOTIFY/LISTEN wake-ups, no TTL. Too new (days old) and needs an extension the official `postgres` image does not ship.
- Conclusion: running Celery on PostgreSQL remains unsupported/experimental; it would also require a results backend and Celery beat, adding operational weight for one job at a time.

### 1.5 pgqueuer

- 1.6.0 on PyPI 2026-10-11 (`requires_python >=3.10`, classifiers 3.10–3.15; deps anyio, croniter, pydantic, typer, uvloop; extras asyncpg, psycopg, fastapi, mcp, web). 1.6.0 requires `pgq upgrade` (new indexes), drops PG 13. Rapid releases: 1.3.0 (2026-07-27), 1.4.0 (2026-09-14), 1.5.0 (2026-10-04), 1.6.0 (2026-10-11).
- Jobs in the same PostgreSQL DB, claimed with `FOR UPDATE SKIP LOCKED`, LISTEN/NOTIFY with polling fallback, heartbeats to re-queue stalled jobs, `DatabaseRetryEntrypointExecutor` for DB-level retries with backoff, `on_failure="hold"`, `@schedule` cron (5 or 6 fields, no separate beat), `pgq install` / `pgq run myapp:main` / `pgq dashboard`.
- Cancellation: `await queries.mark_job_as_cancelled(job_ids)`; queued jobs are removed immediately, a picked job's handler gets a NOTIFY and should wrap work in `with ctx.cancellation:`; "Cancellations are best-effort and may not halt a job already underway."
- Django: no integration (docs/integrations contains mcp-server, postgrest, prometheus, tracing, web-dashboard). asyncio-first design; you would write your own bridge to Django models.
- Maintenance: 1,548 stars; created 2024-04-19; pushed 2026-10-29; contributors janbjorge 844, ericdelorefice 12; issues 11 open, 84 closed in 6 months. Single-maintainer project.

### 1.6 Chancy

- 0.26.0 on PyPI 2026-10-14 (`requires_python >=3.11`, `psycopg[pool]`, extras `cli`, `cron` (croniter), `django` (`django>=4.0`), `web`). Features: retries, cancellation, cron plugin, workflows, built-in dashboard; "Used in production environments to process millions of jobs per day."
- Django: `pip install chancy[cli,django]`; `"chancy.contrib.django"` in `INSTALLED_APPS` exposes Jobs/Queues/Workers models and admin (new in 0.22.0; tables must live in Django's `default` DB); cron jobs can be created in admin with `chancy.plugins.cron.django`; a `django.tasks` backend `chancy.contrib.django.backend.ChancyBackend` is labelled **experimental** (Django 6.0+). Workers are started with the `chancy` CLI from a `worker.py` that calls `django.setup()` (`chancy --app my_application.worker.chancy_app misc migrate` / `worker start`).
- Maintenance: 293 stars; created 2024-05-16; pushed 2026-11-04; contributors TkTech 547 of ~556 (single maintainer); 25 open issues+PRs.

### Recommendation (section 1)

Use **Procrastinate 3.10.x** with its `procrastinate.contrib.django` app. It is the only candidate that satisfies every requirement natively and from a Django management command: durable jobs in PostgreSQL with LISTEN/NOTIFY and `SKIP LOCKED`, retries with strategies, cron-style periodic tasks deduplicated through the database (nightly backup), job locks (`lock="roster-solver"` to serialise solves), priorities, and cooperative abort (`cancel_job_by_id(..., abort=True)` + `context.should_abort()` inside the loop that polls the solver's HTTP API; on abort, call the solver's cancel endpoint and raise `JobAborted`). Progress goes into your own Django model related to `ProcrastinateJob` (documented how-to). The worker is `./manage.py procrastinate worker --concurrency=1` in a second container built from the web image and only needs the same `DATABASES`/`DATABASE_URL` as the web app. Add the documented periodic "retry stalled jobs" task (heartbeats detect a crashed worker). Risks: two active maintainers and an open call for more; mitigations are its 5-year history, MIT licence, plain SQL schema, and that the job table can be read with the ORM. Second choice is `django.tasks` + `django-tasks-db` if you want the core API: it is polling-only (1 s), has no retries, no cancellation and no cron (you would add `django-crontask` and hand-roll abort flags), so it covers less of the brief today. Django-Q2 would work for the backup schedule but has no cancellation at all and a re-delivery `retry` timer that must exceed the longest solve. Celery on PostgreSQL is not a supported configuration. pgqueuer and Chancy are capable but asyncio/CLI-first with no (pgqueuer) or experimental (Chancy) Django integration and a single maintainer each.

---

## 2. Django release status

- Current stable: **Django 6.1.3** (PyPI 2026-11-03; `requires_python >=3.12`; classifiers 3.12/3.13/3.14/3.15). 6.1.0 was released 2026-08-05 (headline: field fetch modes, DB-level `on_delete` options, dictionary-based email settings, new `UUID4`/`UUID7` database functions). Support (djangoproject.com/download): mainstream until April 2027, extended until December 2027.
- Previous feature release: Django 6.0 (released 2025-12-03, latest 6.0.10): mainstream support ended 2026-08-04, extended support until April 2027. Python 3.12–3.14.
- Current LTS: **Django 5.2 LTS** (released 2025-04-02, latest 5.2.19): extended support until **April 2028**; Python 3.10–3.14 (5.2.x is the last series supporting 3.10/3.11).
- Next LTS: **Django 6.2 LTS**, scheduled 2027-04-06 (alpha/feature freeze 2027-01-19, beta 2027-02-23, RC1 2027-03-23); extended support until April 2030; Python 3.12–3.15; drops PostgreSQL 15 (supports 16+). 6.2 is the last release under the current policy; from 2028 Django moves to annual `YYYY` releases every January with 3-year support for every release.
- Tasks framework in core: 6.0 and 6.1 ship only `ImmediateBackend` and `DummyBackend` ("primarily intended for development and testing"); no worker, no database backend, no cancellation, no periodic API. The 6.2 draft notes list no Tasks changes yet.

### Recommendation (section 2)

Start on **Django 6.1.x** (currently 6.1.3). Reasons: it is the current stable, supports Python 3.12–3.15, includes `UUID7()` for `db_default`, and the migration path to 6.2 LTS (April 2027) is a single feature step with no breaking jump; 5.2 LTS would mean skipping two feature releases later and lacks `UUID7`. Plan the upgrade to 6.2 LTS in Q2 2027 (6.1 extended support ends December 2027). Use `django.tasks` only if you pick a third-party backend knowingly; the core provides no production backend in any released version.

---

## 3. Django Ninja

- Latest: **django-ninja 1.7.3**, PyPI 2026-10-29 (hotfix after 1.7.2 the same day; 1.7.1 on 2026-09-19; 1.7.0 on 2026-08-30 confirmed Django 6.1 support, dropped the Django upper bound, Python 3.14 fixes, `Retry-After` on throttling). A parallel 1.6.x line also received hotfixes (1.6.4/1.6.5 on 2026-10-29).
- Constraints: `requires_python >=3.7`, `Django>=3.1`, `pydantic>=2.0,<3.0.0`; classifiers Django 3.1–6.1, Python 3.7–3.14. Pydantic latest is 2.14.2 (2026-10-29); the 1.7.2 notes mention a test-only fix for pydantic 2.14.
- Maintenance: 9,232 stars; pushed 2026-11-04; contributors vitalik 938 (16 of 21 recent commits), next stephenrauch 55 — effectively a single maintainer with drive-by contributors. Issues only: 88 open; 65 closed in the last 6 months.
- Django 6: no open issue specific to Django 6.0/6.1 was found (a search for "Django 6" among open issues returns generic bugs such as #1767 `transaction.non_atomic_requests` ignored on Ninja routes, #1704 `ATOMIC_REQUESTS` rollback). Python 3.15: issue #1833 (opened 2026-11-01, closed 2026-11-03) reports the full test suite passing on 3.15.2 with Django 6.1.x and Pydantic 2.14.2 with no code changes; only the CI matrix/classifiers needed updating, so 3.15 is not yet in the published 1.7.3 classifiers.
- DRF for comparison: djangorestframework 3.18.3 (2026-10-06; `django>=5.2`, Python >=3.10, Django 5.2/6.0/6.1); the release notes describe it "As REST Framework is considered feature-complete", so releases are mostly minor compatibility fixes.

### Recommendation (section 3)

Django Ninja 1.7.3 is a sound choice for the SPA API on Django 6.1 + Pydantic 2.14: actively released (four releases in Oct 2026), Django 6.1 officially supported, 3.15 verified upstream. Pin `pydantic<3` as the package does. Accept the bus-factor-of-one risk (same as DRF's feature-complete status) — both are stable; Ninja gives typed schemas and OpenAPI with less code.

---

## 4. UUID primary keys

- PostgreSQL 18 (released **2025-09-25**) adds `uuidv7()` ("This UUID value is temporally sortable") and the alias `uuidv4()` (release notes E.6.3.4). Current minor 18.6 (2026-08-13).
- Python: `uuid.uuid7()` "Added in version 3.14" (also `uuid6()` and `uuid8()`); RFC 9562; 48-bit ms timestamp plus a 42-bit counter for monotonicity within a millisecond.
- Django: `Field.db_default` was added in **Django 5.0** (2023-12-04): "a literal value or a database function, such as Now()"; "more complex expressions ... made from literals and database functions"; it cannot reference other fields; unsaved instances expose a `DatabaseDefault` placeholder until saved. Django **6.1** added `django.db.models.functions.UUID4` and `UUID7` (ticket #36735, "Added UUID4 and UUID7 database functions"); `UUID7` is "Available on PostgreSQL version 18 or later, MariaDB 11.7+, and SQLite on Python 3.14+", with an optional `shift` timedelta on PostgreSQL. So `models.UUIDField(primary_key=True, db_default=UUID7())` works on Django 6.1 + PostgreSQL 18 and yields `uuid DEFAULT (uuidv7()) NOT NULL PRIMARY KEY`; on Django 5.x/6.0 the equivalent is a two-line `Func` subclass (`function = "uuidv7"`, `output_field = UUIDField()`), as shown by Paolo Melchiorre (2025-11-14) and his DjangoCon US 2026 talk.
- Best-practice consensus (secondary sources, 2025–2026): UUIDv7 removes UUIDv4's random-insert penalty — credativ's PG18 benchmark (2025-12-05, 50M rows) measured inserts ~11× faster into an empty table and ~28× faster into a 50M-row table, index ~24 % smaller, leaf density ~90 % vs ~71 %; it does not benchmark bigint. Guides comparing bigint identity vs UUIDv7 report UUIDv7 within ~2 % to ~12 % of bigint throughput with a larger index (16 vs 8 bytes in every PK, FK and index), and recommend bigint identity when only one database generates IDs, UUIDv7 when IDs must be generated client-side/before insert or must not be guessable by counting; several suggest bigint PK + UUIDv7 public id as a hybrid. Caveat: UUIDv7 leaks creation time, so avoid exposing it where that matters.

### Recommendation (section 4)

For a single-database hospital app either works; prefer **UUIDv7 primary keys via `UUIDField(primary_key=True, db_default=UUID7())`** (Django 6.1, PostgreSQL 18) for tables exposed through the API or referenced by the solver payload (rosters, solve jobs, assignments) because IDs are then safe to show in URLs and can be created before the DB round-trip, with index locality close to bigint; keep Django's default `BigAutoField` for high-volume internal/audit rows where 8-byte keys matter. Do not use UUIDv4 for new PKs.

---

## 5. Versions to target

- Python: latest stable is **3.15.2** (2026-10-25; 3.15.0 released 2026-10-09, bugfix until 2031-10). 3.14 (released 2025-10-07, bugfix until 2030-10, current 3.14.10 in Docker). 3.13 and 3.12 are security-only. 3.10 reached end of life 2026-10-01.
- `ortools`: latest **9.15.6755** (PyPI 2026-01-14; GitHub tag v9.15, 2026-01-12; `requires_python >=3.9`). Wheels (34, no sdist): CPython 3.9, 3.10, 3.11, 3.12, 3.13, 3.14 for `manylinux_2_27_x86_64.manylinux_2_28_x86_64`, `manylinux_2_26_aarch64.manylinux_2_28_aarch64`, macOS x86_64/arm64, win_amd64; free-threaded `cp313t` and `cp314t` for Linux x86_64/aarch64. **No cp315 wheels**; no OR-Tools issue about 3.15 wheels was found (only #5527 about missing `.pyi` files in the 3.14 manylinux wheels, closed 2026-10-22). Runtime deps: `absl-py>=2.0.0`, `numpy>=2.0.2`, `pandas>=2.0.0`, `protobuf>=6.33.1,<6.34`, `immutabledict`, `typing-extensions`.
- PostgreSQL: latest major **18** (18.6, 2026-08-13; supported until 2030-11-14). PostgreSQL 19 is at RC1 (2026-10-15); the roadmap says GA "October 2026" but it had not shipped as of 2026-11-04. Next minor releases 2026-11-12, 2027-02-11. Docker official image tags: `18.6`, `18`, `latest`, `18.6-trixie`, `18-trixie`, `18.6-bookworm`, `18-bookworm`, `18.6-alpine3.24`, `18-alpine`, `18-alpine3.23` (plus `19rc1` tags); amd64 and arm64v8 among supported architectures. Note the 18+ layout change: `PGDATA=/var/lib/postgresql/18/docker` and the volume must be mounted at `/var/lib/postgresql` (not `/var/lib/postgresql/data`), which enables `pg_upgrade --link` across majors.
- Caddy: latest **v2.11.8** (GitHub release 2026-11-04). Docker official tags `2.11.8`, `2.11`, `2`, `latest`, `*-alpine`, `*-builder`; architectures amd64, arm64v8 and others; mount `/data` persistently (certificates and keys) and `/config`; config dir `/etc/caddy`; publish 80, 443 and 443/udp. Automatic HTTPS: public DNS names get publicly trusted certificates from an ACME CA (Let's Encrypt/ZeroSSL) when the name is not localhost (including `.localhost`, `.local`, `.internal`, `.home.arpa` TLDs) and not an IP; IPs and local/internal hostnames get self-signed certificates from Caddy's own CA, "trusted only where the CA's root certificate is installed". The Caddyfile directive is `tls internal` ("use Caddy's internal, locally-trusted CA to produce certificates for this site"), long form `tls { issuer internal { ca local; lifetime 12h } }`; example `example.com { tls internal }`.

### Recommendation (section 5)

Solver container: **Python 3.14** (`python:3.14-slim-trixie`) with `ortools==9.15.6755`, because OR-Tools has no 3.15 wheels and building from source with Bazel is not worth it; the manylinux_2_28 x86_64 and aarch64 wheels cover Intel and ARM VPSes. Web/worker container: also Python 3.14 for one toolchain (Django 6.1.3 and Procrastinate both test 3.14); revisit 3.15 once ortools ships cp315. Database: `postgres:18` (`18.6`) with the `/var/lib/postgresql` mount. Reverse proxy: `caddy:2.11` with `tls internal` for a non-public hostname/IP and the default automatic HTTPS once a real domain points at the VPS.

---

## 6. Docker images and uv

- Official `python` image tags exist for both candidate versions (Docker Hub, read 2026-11-04): `3.14.10`, `3.14`, `3.14-slim`, `3.14-slim-trixie`, `3.14-slim-bookworm`, `3.14-alpine`; and `3.15.2`, `3.15`, `3.15-slim`, `3.15-slim-trixie`, `3.15-bookworm`, `3.15-alpine`; architectures include amd64 and arm64v8.
- uv: latest **0.13.7** (PyPI 2026-11-03). Official Docker guide (docs.astral.sh/uv/guides/integration/docker): distroless images `ghcr.io/astral-sh/uv:latest` / `ghcr.io/astral-sh/uv:0.13.7` for copying the binary (`COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /bin/`, pin a version or SHA256), and derived images `ghcr.io/astral-sh/uv:python3.x-trixie(-slim)` with uv preinstalled. Recommended project install: two-stage layer caching
  ```dockerfile
  RUN --mount=type=cache,target=/root/.cache/uv \
      --mount=type=bind,source=uv.lock,target=uv.lock \
      uv sync --frozen --no-install-project
  COPY . /app
  RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked
  ```
  with `ENV UV_COMPILE_BYTECODE=1`, `ENV UV_LINK_MODE=copy`, `ENV UV_NO_DEV=1` (skip dev deps), `.venv` in `.dockerignore`, and either `ENV PATH="/app/.venv/bin:$PATH"` or `uv run`; `UV_PROJECT_ENVIRONMENT` can target the system interpreter. `--locked` asserts the lockfile is current; `--frozen` installs from the lockfile without checking it (required in the dependency-only layer and in workspaces).

### Recommendation (section 6)

Base both images on `python:3.14-slim-trixie`, copy uv from `ghcr.io/astral-sh/uv:0.13.7`, and use the two-layer `uv sync --frozen --no-install-project` then `uv sync --locked` pattern with `UV_COMPILE_BYTECODE=1`, `UV_LINK_MODE=copy`, `UV_NO_DEV=1`. Keep separate `uv.lock`s (or dependency groups) for the solver and web projects so the solver image contains only `ortools` and the HTTP server.

---

## Sources

Task queues
- Procrastinate PyPI 3.10.0: https://pypi.org/pypi/procrastinate/3.10.0/json
- Procrastinate GitHub releases: https://github.com/procrastinate-org/procrastinate/releases
- Procrastinate repo / contributors / commits (GitHub API): https://api.github.com/repos/procrastinate-org/procrastinate
- Procrastinate README (maintainers call, discussion #748): https://github.com/procrastinate-org/procrastinate/blob/main/README.md
- Procrastinate schema.sql: https://github.com/procrastinate-org/procrastinate/blob/main/procrastinate/sql/schema.sql
- Procrastinate CI matrix: https://github.com/procrastinate-org/procrastinate/blob/main/.github/workflows/ci.yml
- Procrastinate docs: Django configuration https://procrastinate.readthedocs.io/en/stable/howto/django/configuration.html ; Django basic usage https://procrastinate.readthedocs.io/en/stable/howto/django/basic_usage.html ; cancellation https://procrastinate.readthedocs.io/en/stable/howto/advanced/cancellation.html ; cron https://procrastinate.readthedocs.io/en/stable/howto/advanced/cron.html ; retry https://procrastinate.readthedocs.io/en/stable/howto/advanced/retry.html ; stalled jobs https://procrastinate.readthedocs.io/en/stable/howto/production/retry_stalled_jobs.html ; concurrency https://procrastinate.readthedocs.io/en/stable/howto/production/concurrency.html ; discussions https://procrastinate.readthedocs.io/en/stable/discussions.html ; API reference https://procrastinate.readthedocs.io/en/stable/reference.html ; CLI https://procrastinate.readthedocs.io/en/stable/howto/basics/command_line.html
- DEP 14 (final): https://github.com/django/deps/blob/main/final/0014-background-workers.rst
- Django 6.0 release notes: https://docs.djangoproject.com/en/6.1/releases/6.0/
- Django 6.1 release notes: https://docs.djangoproject.com/en/6.1/releases/6.1/
- Django 6.2 draft release notes: https://docs.djangoproject.com/en/dev/releases/6.2/
- Django tasks reference: https://docs.djangoproject.com/en/6.1/ref/tasks/ ; topic guide: https://docs.djangoproject.com/en/6.1/topics/tasks/
- Django ecosystem page (Background Tasks): https://www.djangoproject.com/community/ecosystem/
- Django Packages task-framework grid: https://djangopackages.org/grids/g/task-framework/
- django-tasks PyPI: https://pypi.org/pypi/django-tasks/json ; releases https://github.com/RealOrangeOne/django-tasks/releases ; repo API https://api.github.com/repos/RealOrangeOne/django-tasks
- django-tasks-db PyPI: https://pypi.org/pypi/django-tasks-db/json ; releases https://github.com/RealOrangeOne/django-tasks-db/releases ; README https://github.com/RealOrangeOne/django-tasks-db/blob/master/README.md ; db_worker source https://github.com/RealOrangeOne/django-tasks-db/blob/master/django_tasks_db/management/commands/db_worker.py ; models https://github.com/RealOrangeOne/django-tasks-db/blob/master/django_tasks_db/models.py
- django-crontask PyPI: https://pypi.org/pypi/django-crontask/json
- Django-Q2 PyPI: https://pypi.org/pypi/django-q2/json ; releases https://github.com/django-q2/django-q2/releases ; models https://github.com/django-q2/django-q2/blob/master/django_q/models.py ; docs brokers https://django-q2.readthedocs.io/en/master/brokers.html ; configure https://django-q2.readthedocs.io/en/master/configure.html ; schedules https://django-q2.readthedocs.io/en/master/schedules.html ; tasks https://django-q2.readthedocs.io/en/master/tasks.html ; cluster https://django-q2.readthedocs.io/en/master/cluster.html
- Celery brokers overview: https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/index.html ; Celery 5.6.3 PyPI https://pypi.org/pypi/celery/5.6.3/json ; Celery 3.1 SQLAlchemy broker (experimental warning) https://docs.celeryq.dev/en/3.1/getting-started/brokers/sqlalchemy.html
- Kombu 5.7.0 PyPI: https://pypi.org/pypi/kombu/5.7.0/json ; changelog https://docs.celeryq.dev/projects/kombu/en/stable/changelog.html ; SQLAlchemy transport https://docs.celeryq.dev/projects/kombu/en/stable/reference/kombu.transport.sqlalchemy.html ; PGMQ transport https://docs.celeryq.dev/projects/kombu/en/stable/reference/kombu.transport.pgmq.html
- pgqueuer PyPI 1.6.0: https://pypi.org/pypi/pgqueuer/1.6.0/json ; releases https://github.com/janbjorge/pgqueuer/releases ; docs https://janbjorge.github.io/pgqueuer/ ; cancellation guide https://janbjorge.github.io/pgqueuer/guides/job-cancellation
- Chancy PyPI: https://pypi.org/pypi/chancy/json ; docs https://tkte.ch/chancy/ ; Django how-to https://tkte.ch/chancy/howto/django.html ; repo API https://api.github.com/repos/tktech/chancy
- dj-queue PyPI: https://pypi.org/pypi/dj-queue/json ; django-task-psql PyPI: https://pypi.org/pypi/django-task-psql/json ; huey 3.5.4 PyPI: https://pypi.org/pypi/huey/3.5.4/json ; django-pgqueue PyPI: https://pypi.org/pypi/django-pgqueue/json

Django, Ninja, DRF
- Django download/support table: https://www.djangoproject.com/download/
- Django 6.2 roadmap: https://www.djangoproject.com/download/6.2/roadmap/
- Django 6.1 release announcement: https://www.djangoproject.com/weblog/2026/aug/05/django-61-released/
- Django 6.1.3 PyPI: https://pypi.org/pypi/Django/6.1.3/json
- Django 5.2 release notes: https://docs.djangoproject.com/en/6.1/releases/5.2/
- Django 5.0 release notes (db_default): https://docs.djangoproject.com/en/6.1/releases/5.0/
- Django db_default reference: https://docs.djangoproject.com/en/6.1/ref/models/fields/#db-default
- Django database functions (UUID4/UUID7): https://docs.djangoproject.com/en/6.1/ref/models/database-functions/
- Django ticket #36735: https://code.djangoproject.com/ticket/36735
- django-ninja 1.7.3 PyPI: https://pypi.org/pypi/django-ninja/1.7.3/json ; releases https://github.com/vitalik/django-ninja/releases ; repo API https://api.github.com/repos/vitalik/django-ninja ; issue #1833 https://github.com/vitalik/django-ninja/issues/1833
- Pydantic latest release: https://github.com/pydantic/pydantic/releases/latest
- djangorestframework 3.18.3 PyPI: https://pypi.org/pypi/djangorestframework/3.18.3/json ; DRF release notes https://www.django-rest-framework.org/community/release-notes/

UUID
- PostgreSQL 18 release notes: https://www.postgresql.org/docs/18/release-18.html
- Python uuid docs: https://docs.python.org/3/library/uuid.html
- Paolo Melchiorre, "How to use UUIDv7 in Python, Django and PostgreSQL" (2025-11-14): https://www.paulox.net/2025/11/14/how-to-use-uuidv7-in-python-django-and-postgresql/
- "The Django UUID Story", DjangoCon US 2026: https://speakerdeck.com/pauloxnet/the-django-uuid-story-djangocon-us-2026
- credativ, UUIDv4 vs UUIDv7 in PostgreSQL 18 (2025-12-05): https://www.credativ.de/en/blog/postgresql-en/a-deeper-look-at-old-uuidv4-vs-new-uuidv7-in-postgresql-18/
- Secondary comparisons: https://dev.to/fabwaseem/uuidv7-in-postgresql-18-uuidv7-vs-uuidv4-vs-bigint-primary-keys-benchmarked-1lae ; https://monpg.app/blog/postgresql-uuid-vs-bigint-primary-keys ; https://www.dbgorilla.com/learn/postgres/are-uuid-primary-keys-still-bad-uuidv7/

Versions and Docker
- Python downloads: https://www.python.org/downloads/ ; 3.15.0 https://www.python.org/downloads/release/python-3150/ ; 3.15.2 https://www.python.org/downloads/release/python-3152/
- ortools 9.15.6755 PyPI: https://pypi.org/pypi/ortools/9.15.6755/json ; OR-Tools releases https://github.com/google/or-tools/releases
- PostgreSQL versioning policy: https://www.postgresql.org/support/versioning/ ; 18.6 release notes https://www.postgresql.org/docs/release/18.6/ ; roadmap https://www.postgresql.org/developer/roadmap/ ; home page (19 RC1) https://www.postgresql.org/
- Docker Hub postgres: https://hub.docker.com/_/postgres ; python https://hub.docker.com/_/python ; caddy https://hub.docker.com/_/caddy
- Caddy latest release: https://api.github.com/repos/caddyserver/caddy/releases/latest ; automatic HTTPS https://caddyserver.com/docs/automatic-https ; tls directive https://caddyserver.com/docs/caddyfile/directives/tls
- uv 0.13.7 PyPI: https://pypi.org/pypi/uv/0.13.7/json ; uv Docker guide https://docs.astral.sh/uv/guides/integration/docker/
