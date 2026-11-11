# 63: The throttle on failed logins from one address

**What to build:** Fifty failed logins from one client address in a fifteen-minute window throttle that address for the rest of the window. A throttled login is refused at once with 429, the time it may try again and a `Retry-After` header, before its username's login-attempts row is touched or any password is checked, whatever username and password it carries. A wrong password, a refusal while the name is locked, and a wrong current password on Change password each count one failure; a success counts nothing and clears nothing. Change password is refused the same way while its address is throttled, before the current password is checked. IPv6 addresses count by their /64; a request with no address is never throttled. The audit log gets one `auth.login_throttled` entry (no actor, no target, the address, the window's end) when an address reaches the limit, and nothing for the requests refused during it. The login page and Change password show "Too many failed logins from this network" and the time on the hospital's clock. The lockout per username is unchanged. Spec: `.scratch/nurse-rostering-v2/specs/hardening.md` (The throttle); ADR 0015; the words: `GLOSSARY.md` (Throttle, Lockout).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] A model in `accounts`, beside `LoginAttempts`, holding an address key's window start and failure count; the constants (fifty, fifteen minutes) beside `MAX_FAILURES` and `LOCK_DURATION`, not in the technical settings
- [ ] `attempt_login` asks whether the address is throttled before it takes the name's row lock; a throttled login calls neither `authenticate` nor the hasher, touches no `LoginAttempts` row and writes nothing (a test counting hasher calls, as the audit's harness did)
- [ ] Each refusal `attempt_login` makes, wrong credentials or locked, records one failure for the address; the address's row is not held across the hash
- [ ] The failure that brings a window to fifty writes the one `auth.login_throttled` entry; a failure in a window older than fifteen minutes starts a new one counting one
- [ ] `POST /api/auth/login` and `POST /api/auth/change-password` answer 429 with the detail, the time and `Retry-After`; a wrong current password counts one failure; the OpenAPI schema and the generated client follow
- [ ] Two IPv6 addresses in one /64 share a budget, two /64s do not; a different address is not affected; the window's end lifts the throttle
- [ ] The existing lockout tests pass unchanged; the public allow-list walk of the authorization tests still passes
- [ ] The login page and Change password show the throttle's words and time on a 429 (the frontend's app-level suite)
- [ ] `docs/ARCHITECTURE.md` section 8: the throttle beside the lockout, and the audit rule as the user changed it: every login the server checked, failed or not, is in the log, and so is each throttle; a request refused by a throttle is not
- [ ] `docs/security/2026-11-11-security-audit.md`: lead 1 marked fixed, with this ticket's commits, and lead 2's per-address bound noted
- [ ] Tests at the agreed seams: the backend API suite and the frontend's app-level suite; the usual full suites and both workflows

## Comments
