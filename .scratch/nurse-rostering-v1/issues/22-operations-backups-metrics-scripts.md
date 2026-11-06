# 22: Operations: backups, metrics and scripts

**What to build:** The worker takes a nightly backup at the configured time and keeps the configured number of days; the System Admin sees the backups on the health page with the last backup time and downloads one. A documented restore script and an admin password reset script run on the server. Every container logs JSON to standard output and the web application exposes a Prometheus metrics endpoint on the internal network only.

**Blocked by:** 11 Run a solve

**Status:** ready-for-agent

- [ ] Backup job with retention; health page lists backups with sizes and dates; download
- [ ] Restore script stops the app, restores, starts it; admin reset script; both documented in the install guide
- [ ] JSON logging for web, worker and solver; metrics endpoint unreachable through Caddy
- [ ] API tests cover the backup list and download authorization; a compose-level test runs backup and restore

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
