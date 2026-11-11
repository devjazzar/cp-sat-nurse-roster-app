# 71: Gunicorn runs threaded workers

**What to build:** Each web worker serves several requests at once, so one hash, one import or one slow request holds a quarter of one worker and not a third of the pool. Gunicorn runs `--worker-class gthread --threads 4 --workers 3`, with `--timeout` at gunicorn's default, which under `gthread` is only how long a worker's main loop may go silent: a 500-row import is never killed at 300 seconds. Caddy's idle time on its connections to `web` is shorter than gunicorn's keep-alive, so Caddy never reuses a connection gunicorn has just closed. Spec: `.scratch/nurse-rostering-v2/specs/hardening.md` (Caddy and gunicorn, Keep-alive).

**Blocked by:** 70 Caddy holds the body (the Caddyfile's `reverse_proxy` block and the same checks in `operations.sh`)

**Status:** ready-for-agent

- [ ] The web command runs `gthread`, 3 workers of 4 threads, with `--timeout` at its default; the comment above it, which sized 300 s for the import, is rewritten
- [ ] Caddy's idle keep-alive to `web` is shorter than gunicorn's `--keep-alive`; the ticket comment says how it was checked
- [ ] A search of the application for mutable module-level state a thread could race on, with what it found and what was done about it, in the ticket comment
- [ ] `docs/ARCHITECTURE.md`: section 2 (web's command) and ADR 0009's connection count in the architecture (web at most 12, beside the worker's 9)
- [ ] `deploy/INSTALL.md`: the 500-row import is still timed at the first real install, with no limit to stay under
- [ ] `docs/security/2026-11-11-security-audit.md`: lead 3's worker half marked fixed, with this ticket's commits
- [ ] Tests at the agreed seams: `deploy/tests/operations.sh` (gunicorn running threaded); the browser checks pass on the threaded server; both workflows

## Comments

**From ticket 69 (2026-11-11).** gunicorn's access line now takes `remote` from `X-Client-IP`, the header Caddy always sets,
else the peer (`solver/solver_service/logs.py`). `audit.log.client_ip` keeps no state, so threads change nothing there.

**From ticket 70 (2026-11-11).**
- `deploy/Caddyfile`'s `reverse_proxy web:8000` block now holds `header_up X-Client-IP {client_ip}` and `request_buffers 2MiB`.
  Caddy's idle time to `web` goes in a `transport http { keepalive … }` there (check its name with `caddy adapt` on
  `caddy:2.11`, as ticket 70 did).
- `deploy/tests/compose.one-worker.yaml` replaces web's whole `command` for `operations.sh`'s held-body check:
  `--workers 1 --threads 1`, no `--worker-class`, no `--timeout`. Once compose.yaml says `gthread`, mirror it there
  (`--worker-class gthread --threads 1`) so the check still runs one request at a time on the same kind of worker. The check
  also counts gunicorn processes in `web` (master plus one), which stays true under `gthread`.
- That check now asserts a withheld login never reaches `web` at all, read from web's access lines (`/api/auth/login`).
  Django reads no chunked body, so under sync workers a chunked login passed on is answered at once. Under `gthread` with
  keep-alive, gunicorn may try to read the rest of such a body before the connection's next request; Caddy no longer passes
  one on, which is why `request_buffers` is larger than the 2 MB cap.
- Caddy's minimum body rate runs from the body's start: 1 minute, plus a tenth of a millisecond for each byte received. A
  2 MB body therefore has at most 260 s to arrive. Once it is in, nothing bounds the request: confirmations of 140 rows took
  99 s (HTTP/1.1) and 94 s (HTTP/2) through Caddy on a scratch stack with `web` held to one CPU (`docker update --cpus 1`),
  and both finished. That is the setup for timing the 500-row import without the 300-second limit.
