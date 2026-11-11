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

**From ticket 63 (2026-11-11).** The address rows are `accounts.models.AddressFailures`: `address` (the key, an IPv4 address
or an IPv6 /64 such as `2001:db8:1:2::/64`), `window_start` and `failures`. A window has ended when
`window_start + THROTTLE_WINDOW <= now`; `THROTTLE_WINDOW` and `MAX_ADDRESS_FAILURES` sit beside `MAX_FAILURES` and
`LOCK_DURATION` in `backend/accounts/login.py`. `record_address_failure` there already starts a new window when the old one
has ended, so a removed row loses nothing. The tests move the clock by monkeypatching `django.utils.timezone.now` (the
`clock` fixture in `test_throttle.py`).

**From ticket 64 (2026-11-11).** `_record_failure` in `backend/accounts/login.py` now looks the typed name up once
(`User.objects.filter(username=...)`) and writes `auth.login_failed` with that account as actor and the name as target, or
with neither when no account has it. `LoginAttempts` is still keyed by the typed name, for a real name and an unknown one
alike, so the rows this ticket removes are unchanged. Where `attempt_login` sets the time of the last failure, it is the
same `attempts.save()` on the wrong-credentials path; a refusal while locked saves nothing today. The 423's `locked_until`
is now sent with the hospital's offset (`timezone.localtime` in `accounts/api.py`).
