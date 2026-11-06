# 22: Operations: backups, metrics and scripts

**What to build:** The worker takes a nightly backup at the configured time and keeps the configured number of days; the System Admin sees the backups on the health page with the last backup time and downloads one. A documented restore script and an admin password reset script run on the server. Every container logs JSON to standard output and the web application exposes a Prometheus metrics endpoint on the internal network only.

**Blocked by:** 11 Run a solve

**Status:** ready-for-agent

- [x] Backup job with retention; health page lists backups with sizes and dates; download
- [x] Restore script stops the app, restores, starts it; admin reset script; both documented in the install guide
- [x] JSON logging for web, worker and solver; metrics endpoint unreachable through Caddy
- [x] API tests cover the backup list and download authorization; a compose-level test runs backup and restore

## Comments

**Decisions from the user (2026-11-05).**

- **Trim the public `/api/health`** so it no longer shows the solver's version and thread count, keeping what the compose health check needs. `deploy/compose.yaml` needs only a 200 from it, and the README's install check reads `"solver": {"reachable": true, ...}`, so change that line if the answer changes. The System Admin's page reads `/api/ops/health`, behind a role.
- **Measure the 500-row import against the timeout on the real server at first install.** Ticket 08 measured 62.5 s on 8 cores on a development machine, against gunicorn's `--timeout 300`, and no real hospital server's hash speed. Say this in the install guide.
- **Prove Let's Encrypt at first real install.** Ticket 01's criterion stays unticked until then, because it needs a real domain whose DNS points at the server. Say this in the install guide too.

**From ticket 11 (2026-11-05): queue rows pile up.** Every run of a job leaves a row in `procrastinate_jobs` and its events, and nothing removes them. `recover_lost_jobs` runs every five minutes, so that is 288 rows a day beside the solves. Solves do not need theirs once ended, since the `Solve` row is the record and `queue_ahead` counts only active ones. Add retention here, with the worker's `delete_jobs` option or a job of its own. The health page's `waiting`, `running` and `failed` are unaffected by either.

**From the scheduled-jobs design (2026-11-06, ADR 0009).** The worker runs at concurrency 4 and every job takes a lock. The backup can run for minutes, so it takes a lock of its own (`lock="backup"`), which `ops.queue._periodic` gives every periodic job under its name from ticket 21 on. It then holds one slot at most and never runs beside itself.

**Decided by the user (2026-11-06), for this ticket.** From the review of tickets 01–20.

- **The admin reset script also lifts a login lock** (`deploy/reset-admin-password.sh`, not built yet). Anyone can lock any account for 15 minutes with five wrong passwords, the System Admin's included, and the user kept that (ticket 02). So the script that resets the System Admin's password from the server also clears that account's failed-login count, as `accounts.provisioning.reset_password` already does for the accounts a person resets (`LoginAttempts` rows by username).
- **Remove notifications older than a year**, in a scheduled job. Nothing deletes them today (ticket 15).
- **Clear expired sessions daily** (Django's `clearsessions`, or the same in a job). Nothing clears them today (ticket 02).
- **Why a solve failed, for the System Admin, in a few fixed words naming no one.** Today the history shows only `SolveFailure` (`solver`: crashed or unreachable; `refused`: the rules), and the worker's own words can name a nurse and a date, so they stay out (ticket 12). Add a few fixed kinds, such as the solver unreachable, the solver restarted and lost the job, the time limit overrun, a refused input, each with a sentence that holds no name, date or rule value.
- **An install-notes line on the worker's log:** it can hold names and dates (a solver error, a refusal's words), so it is personal data, to be kept and rotated as such.
- **Scheduled jobs and the worker's slot:** settled by ADR 0009 and the comment above; the jobs above are periodic jobs under its rules (a run lock under each job's own name).

**The install checklist: what only the hospital's people can check, at first install.**

- [ ] The roster's Excel file opened in Excel on Windows with a `;` list separator (a European locale), not only the default `,`.
- [ ] The ward print page printed on a real printer: A4 landscape, a 31-day month on one page, the header row repeated.
- [ ] One pass of the main pages with the keyboard alone and with a screen reader.
- [ ] Caddy in a browser at the hospital's own address: the certificate (Let's Encrypt with `DOMAIN`, or the self-signed one), and the app through it.
- [ ] Time a solve, a draft's read and a re-plan's comparison on a 60-nurse unit on the real server.
- [ ] Time the audit log filtered by user on the real database.

**From ticket 21 (2026-11-06).** The worker runs at `--concurrency 4` and every periodic job takes a lock under its own name (`ops.queue._periodic`). The backup is a job that can run longer than a minute: give it a lock of its own (`ops.queue.under_its_own_lock` for an on-demand job, or `_periodic` for the cron). `solves.tests.conftest.run_the_queue(concurrency=4)` runs the real queue at that concurrency for its test. Procrastinate's job rows now include `project_carry_over`, one after each roster version and each close: their retention is yours with the rest.

**Implemented on 2026-11-06,** on branch `claude/ticket-22-operations-8d72b7`. The backend ran under pytest on a throwaway PostgreSQL 18 container of my own (2307 passed), the solver's suite in full (447 passed: 442 and 5 new), the frontend under Vitest (539 passed) and `npm run build`. `makemigrations --check` is clean; `frontend/openapi.json` matches the export. The compose-level test, `deploy/tests/operations.sh`, passed all 31 of its checks on a stack built from the branch (scratch project `nr-t22-ops`) and removed everything it made.

What was built:
- **Backups (`ops.backups`, `ops.tasks.backup`):**
  - A `pg_dump` of the whole database in its custom format, written to the `backups` volume under a name nothing lists. It gets its own name once whole: `nurse-roster-<UTC time>.dump`, readable by the app user only (`0600`). A name taken in the same second is never overwritten.
  - The files are the record. The list, the last backup and what is kept are read from the directory, never from a table, so a restored database cannot disagree with the disk.
  - The job is `_periodic` every five minutes under its own lock, `backup`. It takes a backup once the System Admin's backup time has passed on the hospital's clock and none was taken since, then removes those past the days kept, never the newest. It also removes a half-written file a killed backup left, a day on.
  - The image carries PostgreSQL's own `postgresql-client-18` (from the PGDG repository), since Debian's client is 17 and `pg_dump` refuses a newer server.
  - `manage.py backup` takes one at once (`deploy/restore.sh` runs it first).
- **The health page:**
  - `GET /api/ops/health` adds `backups` (name, size, time, newest first), `last_backup` and `backup_schedule`.
  - The Backups card shows the last backup, the schedule with a link to Technical settings, a warning that a backup holds every account and every nurse's leave, and a table of backups with a Download link for each.
  - `GET /api/ops/backups/{name}` (System Admin only) answers the file as an attachment with `no-store`. It serves only a finished backup by its exact name. Each download writes `backup.downloaded` with the name and nothing else.
- **Scripts in `deploy/`:**
  - `restore.sh <name or file>` checks the backup, asks for `RESTORE` (`--yes` skips), stops `web` and `worker` and takes a backup of the database as it stands. It restores into `nurse_roster_restoring`, renames the old database aside, renames the restored one in, drops the old one last, and starts `web` and `worker`. A failure or a stop before the swap ends puts everything back.
  - `reset-admin-password.sh [--username …]` runs `manage.py reset_admin_password` through `exec`, or `run` when `web` is down. It refuses an account that is not a System Admin or is deactivated, and prints a generated password once with a forced change. Through `accounts.provisioning.reset_from_the_server`, the same transaction as `reset_password`, it clears `LoginAttempts` by username and ends the account's sessions (new hash). It is audited as `user.password_reset` with no actor and `"from": "the server"`.
- **Logs:**
  - One formatter, `solver_service.logs` (in the solver package because the backend already imports it and the solver cannot import the backend), used by Django's `LOGGING`, by gunicorn's own and access lines (`config/gunicorn.py`; each request's method, path, query, status, time, bytes and the forwarded address) and by the solver's uvicorn (`solver_service/logging.json`).
  - `web` starts with `manage.py prepare` (migrations and `bootstrap`, their output logged).
  - The worker runs `manage.py queue worker --concurrency 4`: Procrastinate's own command, with what it prints to standard error logged instead. The health check uses the same command.
  - `deploy/compose.yaml` rotates every container's log at 10 MB × 5 (`x-logging`).
- **Metrics (`ops.metrics`):**
  - `/metrics` on `web`, in Prometheus's text format, worked out at each scrape: database and solver up, queue jobs by status and workers, solves by state, database size, disk, backups with their total size and the last one's time.
  - It needs no sign-in. Caddy answers 404 to `/metrics` and `/metrics/*`, and `web` refuses anything carrying `X-Forwarded-For`, which Caddy always adds. `web` is now in `ALLOWED_HOSTS` for a scraper on the internal network.
- **Retention**, each `daily` under a lock of its own name:
  - `ops.tasks.remove_ended_jobs` (22:10 UTC): Procrastinate's own `delete_old_jobs` query. It removes rows and events of jobs that ended well or were stopped more than 7 days ago, and of failed jobs more than 30 days ago. That covers `recover_lost_jobs`, `project_carry_over`, ended solves and every periodic run.
  - `notifications.tasks.remove_old_notifications` (22:20 UTC): older than 365 days, read or not.
  - `accounts.tasks.clear_expired_sessions` (22:40 UTC): Django's `clear_expired`.
- **Failure kinds:**
  - `SolveFailure` (migration `solves.0003`) is `refused`, `unreachable`, `lost`, `overrun`, `solver_error`, `stuck`, `worker_lost`, `unexpected`, and `solver` for rows from before.
  - `solves.running` decides the kind from what was raised on the last attempt, never from its words.
  - The System Admin's solve history has a "Why it failed" column in fixed sentences. The manager's pages are unchanged ("Rules to review" or "Failed").
- **The public `/api/health`** is `{"status", "database", "solver": {"reachable"}}`. The compose health check needs only its 200; the README's install-check line now quotes the whole answer.
- **`deploy/INSTALL.md`**, the install guide, which the README points to:
  - install and upgrade, Let's Encrypt to prove at the first real install, and the 500-row import to time against gunicorn's 300 s (backup, import, restore);
  - the install checklist, with two lines added (that import, and a real restore);
  - backups and off-site copies, restore and what to do with a `nurse_roster_replaced` left behind, the reset;
  - logs as personal data ("the worker's log can hold names and dates … treat these logs as personal data … keep them only as long as you need") and their rotation;
  - metrics and how a Prometheus joins the `frontend` network, and what the queue keeps.

Seams, test first:
- `ops/tests/test_backups.py` (24):
  - due-ness on the hospital's clock, the System Admin's time, a catch-up once, the first backup at once;
  - a file whole or not at all, `0600`, no overwrite;
  - retention, including never the newest, a stale half-written file and files that are not backups;
  - the list on the health page, and the download: content, headers, audit, every other role 403, signed out 401, five refused names including traversal;
  - the job's lock and `manage.py backup`.
- `ops/tests/test_retention.py` (4) and `test_recovery.py` (3). On real job rows: what goes and what stays, the health page's counts unchanged, and a dead run whose next run waits.
- `ops/tests/test_metrics.py` (8), `ops/tests/test_logs.py` (4, each a real process: settings, `prepare`, a real gunicorn and `queue`), `solver/service_tests/test_logs.py` (5, a real uvicorn under `logging.json`).
- `accounts/tests/test_reset_admin_password.py` (8), `test_sessions_cleared.py` (2), `notifications/tests/test_retention.py` (2).
- `solves/tests/test_flow.py`: each failure kind from its cause.
- `app.test.tsx`: the Backups card twice, the "Why it failed" column, and each kind's words (9).
- `deploy/tests/operations.sh`: the compose-level test.
- No raised timeouts, no fake timers, no wait that proves something did not happen. The compose test's waits are for a job to run or a service to answer.

The checklist the session gave, answered one by one:
- **Backup at the configured time, keeping the configured days:** yes; at most five minutes late (below).
- **Its own lock at concurrency 4:** `lock = backup`, asserted in the test and read from the job row on the stack.
- **Health page list, sizes, dates, last backup, download:** yes.
- **API tests on the list and who may download:** yes, beside the authorization walk, which now includes the endpoint.
- **Where backups live, and only to the System Admin:** the `backups` volume. `worker` mounts it read-write and `web` read-only; no other service mounts it. The files are `0600`, and download is the System Admin's alone.
- **Restore that stops, restores and starts; reset that lifts the lock; both in the install guide; a compose test of backup and restore:** yes.
- **JSON logs from web, worker and solver:** yes, every line on the stack.
- **`/metrics` internal only, proved through Caddy:** yes.
- **The install note on the worker's log:** yes.
- **Retention of queue rows, notifications and sessions:** yes, each periodic under its own lock.
- **Fixed failure kinds with sentences naming no one:** yes.
- **Trim the public `/api/health`, keep the compose check, fix the README:** yes.
- **The guide on the 500-row import, Let's Encrypt and the checklist:** yes.

**Driven in the built-in browser,** on scratch project `nr-t22-ops`: the production compose file with the test override (Caddy on `127.0.0.1:18443`) and its own image (`nr-t22-ops-app:test`), secrets and volumes. The built-in browser refuses Caddy's self-signed certificate, so for the pages `web` was also published on `127.0.0.1:18022` under `DJANGO_DEBUG` from an override in my scratchpad, as ticket 21 did.
- **A backup by the job:** deferred from the worker's CLI and also due at start; it ran with `lock = backup`.
- **The System Admin's first login** used the password `reset-admin-password.sh` printed, and was sent to change it.
- **The health page** listed two backups, 303 KB and 302 KB, with the last one's time. The download (fetched from the page with the admin's cookies, not saved to disk) answered 200, `application/octet-stream`, the attachment's name, `no-store`, 310,549 bytes beginning `PGDMP`. The audit log showed "Downloaded a backup" with the name only, and the two server resets as "System … from: the server".
- **As a CNO** created on the Users page, the same address answered 403 "Your role may not do this." and `/health` sent them home.
- **At 320 px** the page does not scroll sideways. The Backups table scrolls inside its named region, with the Download column at the edge. The download link has a visible 2 px focus ring.
- **Through the compose test (twice, from fresh builds):**
  - the public health answer, and `/metrics` and `/metrics/` 404 through Caddy but answered from Caddy's container to `web:8000`;
  - every line of `web`, `worker` and `solver` parsed as JSON;
  - the backup `0600 app` and read by `pg_restore`;
  - the three retention jobs succeeded;
  - a file that is no backup, given as a relative path from another directory, refused with the database as it was and nothing left over;
  - a real restore that took back a table written after the backup and kept a backup of the database first;
  - `recover_lost_jobs` succeeding after it;
  - five wrong passwords locking `admin`, the reset lifting it, and the old password refused.
- **Found by driving, fixed with tests:**
  - A restore brings back the backup job that was running as that backup was taken, as `doing` under a worker long gone, while the next run of `backup` already waits. `recover_lost_jobs` tried to put the dead one back, hit the waiting one's queueing lock and failed every five minutes, and the waiting one never ran behind the dead one's lock. The same holds for any periodic job whose worker dies mid-run once its next run is queued.
  - `ops.queue.requeue_stalled` now ends such a run as failed and puts back the rest. Seen live: the dead run failed, `recover_lost_jobs` succeeded, the waiting backup ran.

What was NOT checked:
- **The backup firing on its own at 02:00 in a real worker.** It ran at start and when deferred; the time logic is a unit test.
- **The daily retention jobs firing on their own at 22:10, 22:20 and 22:40 UTC.** They ran when deferred.
- **A failed solve's kind on the real stack.** Vitest and the API tests only (ticket 24 can stop the solver mid-solve).
- **A restore stopped in the middle of its swap** (Ctrl-C, or the server going down between the two renames). The trap's way back was read, not exercised; a failure before the swap was tested.
- **`reset-admin-password.sh` with `web` down** (the `run` path). Only `exec` ran.
- **`docker compose cp worker:/backups …`** for off-site copies, as the guide suggests.
- **A real Prometheus scraping the stack.** The exposition was read by the tests and by `wget`, not by Prometheus's own parser.
- **The log rotation** reaching 10 MB.
- **Dark mode** (the app renders light under a dark preference), 200% zoom, a screen reader, and browsers other than the built-in one.
- **The image's build reaching `apt.postgresql.org`** from a hospital's network. It needs that host at build time, which a hospital that pulls the image from the registry does not.

**Decisions taken here:**
- **Worth your review: the backup is a five-minute catch-up, not a 02:00 cron.** Procrastinate's cron is fixed at import and in UTC, so like `close_month` it asks and decides itself. A backup comes at most five minutes after its time, and a worker that was down takes the missed one once. With none at all, one is taken at once, so a new installation has a backup from its first five minutes rather than waiting for the night.
- **Worth your review: the files are the record,** named by UTC time, and the newest is always kept whatever the days allow, so a backup that keeps failing never leaves none.
- **Worth your review: each download is audited** (`backup.downloaded`, the name only), as the staff list and a roster file are.
- **Worth your review: the restore takes a backup first, restores beside and swaps,** and asks to type `RESTORE`. It refuses to run while a `nurse_roster_replaced` is left from one that did not finish, and the guide says what to do with it.
- **Worth your review: queue rows that ended well go after 7 days, failed ones after 30.** The ticket's note says the health page's failed count is unaffected by retention; that held only while failed rows stayed for good. A backup failing every five minutes would add 288 a day for ever, so they go after a month, and the page says "Jobs failed, last 30 days".
- **Worth your review: `recover_lost_jobs` ends a dead periodic run as failed when its next run already waits,** instead of putting it back (above). It is a change to ticket 11's recovery, forced by the restore.
- **Worth your review: the failure kinds and their words** (in `solve-words.ts`, mirrored as the model's labels), with `unexpected` for an error in the worker's own code and `stuck` for an earlier job the solver would not stop. Old rows keep `solver` rather than being guessed from their words.
- **Worth your review: the metrics are a handful of gauges written by hand,** with no `prometheus_client` and so no request counters or latencies, which would need state shared across gunicorn's workers. They add solves by state to what the health page reads.
- **Worth your review: a Prometheus joins the `frontend` network** (Caddy's and `web`'s) in the hospital's own override, rather than a network of its own in `compose.yaml`.
- **Worth your review: Docker's log rotation at 10 MB × 5 a container,** set in `compose.yaml`, so "rotated as personal data" is true out of the box.
- **The reset script** refuses accounts that are not a System Admin's and deactivated ones, and takes `--username` for a second System Admin.
- **The formatter lives in the solver package,** and the worker's command is `manage.py queue worker` so that what Procrastinate prints is logged.
- **Two lines added to the install checklist:** the timed 500-row import and a real restore.
- **The retention jobs run at fixed UTC times,** since their hour does not matter; a day missed is caught up by the next.

`docs/ARCHITECTURE.md` sections 2, 4, 7, 8, 9 and 10 moved, and `README.md`. The glossary gained **Failure kind**, **Backup** and **Restore**.

**Review.** The `code-review` skill's two axes against `53cecd6`.
- **Spec found:**
  - The restore's swap dropped the old database before renaming the new one in, so a failure or a stop between the two statements left no database: fixed (aside, in, drop last), and the compose test now runs a failing restore.
  - Failed queue rows kept for good: fixed (30 days).
  - A relative file path read against `deploy/`: fixed.
  - Half-written backup files never removed: fixed.
  - The guide not saying the reset needs `db`, and "every container logs JSON" while PostgreSQL does not: both now said.
  - It listed the choices beyond the ticket, all recorded above.
- **Standards found:**
  - "dump" for a backup and "ward" against the glossary, and section 9's "nothing is hard-deleted" not naming housekeeping: fixed.
  - Backend and frontend failure words that had drifted: made one, each pointing at the other.
  - Duplicates fixed: the solver's state, the newest backup, the file's OpenAPI response (which had carried two `200` keys).
  - The worker's health check on the old command name, an unused parameter, and three names: fixed.
  - Left as judgement calls: the raw job-row helper in two test files, and the gauge's pre-formatted labels.

`better-interface` and its domain skills, held by hand on the Backups card and the "Why it failed" column:
- **Accessibility:** the table is a named, focusable scroll region with row headers, and each Download has an accessible name that starts with its visible text and names the time. The Refresh status region is unchanged.
- **Layout:** the card spans both columns. At 320 px the Download column is reached by the region's scroll, with the scrollbar and the column's edge as the cue (`LOW`, the project's pattern, kept).
- **Writing:** the copy uses the glossary's words. The System Admin's history now says the unit's manager can run a failed solve again and that the server's logs say more.
- **Typography:** times and sizes are tabular. No new colour, type or motion.

`interface-review` is yours to invoke.

**Things later tickets should know:**
- **PWA (23):** never cache `/api/ops/backups/*` or `/api/ops/health` (comment left there).
- **Browser journeys (24):** the System Admin's health page and the refusal, `deploy/tests/operations.sh` as a ready compose-level test, and `ignoreHTTPSErrors` through Caddy (comment left there).
- **The dev stack was not touched.** When this branch reaches `main` it needs a **rebuild**, not a restart (`docker compose -f compose.yaml -f compose.dev.yaml up -d --build`):
  - The `Dockerfile` changed: `postgresql-client-18` from the PGDG repository.
  - `deploy/compose.yaml` changed: `web` runs `prepare` and gunicorn with `-c config/gunicorn.py`, and mounts `backups` read-only; the worker runs `manage.py queue worker` and checks its health the same way; the solver takes `--log-config`; every service has `logging`.
  - `deploy/compose.dev.yaml`'s `web` and `solver` commands changed.
  - The solver package changed: `solver_service/logs.py` and `logging.json`.
  - Migration `solves.0003` runs at `web`'s start.
  - On its first run the worker takes a backup within five minutes, since the dev stack has none.
  - **No new Python or npm dependency.**

**Reviewed by the user (2026-11-06):** all ten points marked **Worth your review** are kept as built: the backup as a five-minute catch-up; the newest backup always kept; each download audited; the restore's backup-first, restore-beside-and-swap with `RESTORE` typed; ended queue rows kept 7 days and failed ones 30; `recover_lost_jobs` ending a dead periodic run as failed when its next run waits; the failure kinds and their words; hand-written gauges with no `prometheus_client`; Prometheus on the `frontend` network; Docker log rotation at 10 MB × 5.
