# 68: The public health answer kept five seconds

**What to build:** `GET /api/health`, which anyone may call, keeps its answer for five seconds in each web process, so a client polling it cannot make the application call the solver on every request. The compose health check reads it as before. The System Admin's health page is not cached. Spec: `.scratch/nurse-rostering-v2/specs/hardening.md` (The public health answer).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Within five seconds a second public health request does not call the solver or the database again and gives the same answer; after five seconds it does
- [ ] The System Admin's `/api/ops/health` and `/metrics` are not cached
- [ ] The web service's compose health check still turns healthy at start and unhealthy when the database is gone, within its retries
- [ ] `docs/ARCHITECTURE.md` section 8's Observability says the public answer is kept five seconds
- [ ] `docs/security/2026-11-11-security-audit.md`: the health hardening note marked fixed, with this ticket's commits
- [ ] Tests at the agreed seams: the backend API suite; the usual full suites and both workflows

## Comments
