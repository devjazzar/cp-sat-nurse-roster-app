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
