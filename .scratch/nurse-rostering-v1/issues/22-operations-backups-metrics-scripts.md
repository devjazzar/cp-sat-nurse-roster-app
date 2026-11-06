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
