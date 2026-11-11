# 65: Login attempts that are no one's record go

**What to build:** A username's count of failed logins is forgotten a day after its last failure, unless the name is locked now, and an address's throttle window is removed once it is over. A daily retention job, beside the others and caught up by the next day when one is missed, removes both. The audit entries of failed logins stay. Spec: `.scratch/nurse-rostering-v2/specs/hardening.md` (Housekeeping); ADR 0009 (every job under a lock).

**Blocked by:** 64 A failed login names only a real account (both change the login's failure path and its tests), after 63

**Status:** ready-for-agent

- [ ] `LoginAttempts` gains the time of its last failure, set at every failure it counts; rows written before have none
- [ ] A daily job at a fixed UTC time after the other retention jobs, under its own lock, removes every login-attempts row not locked now whose last failure is more than 24 hours old or unknown, and every address row whose window ended
- [ ] It keeps a locked row, a fresh one and the current window; it deletes no audit entry
- [ ] A name whose count was removed starts again from none at its next failure
- [ ] `docs/ARCHITECTURE.md` section 7's retention list and section 9's "no one's record" list name both
- [ ] `docs/security/2026-11-11-security-audit.md`: lead 2 marked fixed, with this ticket's commits
- [ ] Tests at the agreed seams: the backend suite (prior art: the retention jobs' tests of tickets 22 and 42) and the retention check in `deploy/tests/operations.sh` if it fits there; the usual full suites and both workflows

## Comments
