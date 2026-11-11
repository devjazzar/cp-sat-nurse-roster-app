# 64: A failed login names only a real account

**What to build:** An `auth.login_failed` entry names the typed username as its target only when an account has that username; otherwise its target is empty, and its address and reason stay. A password typed into the username box is then never kept where the System Admin reads it, and a 600-byte made-up name no longer makes a 600-byte audit row. The login-attempts row is still keyed by the name typed, so an unknown name still locks exactly like a real one and the answer to a login still never says which names exist. Spec: `.scratch/nurse-rostering-v2/specs/hardening.md` (The throttle, "The failed login's target").

**Blocked by:** 63 The throttle on failed logins from one address (both change the login's failure path and its tests)

**Status:** ready-for-agent

- [ ] A failed login at an unknown name, wrong credentials or locked, writes `auth.login_failed` with an empty target, no actor, its reason and its address
- [ ] A failed login at a real account's name writes that name as its target and the account as its actor, as today
- [ ] The answer to the login is the same in both cases (status, words, `locked_until`), and an unknown name still locks after five failures
- [ ] The System Admin's audit log page shows such an entry without a target and does not fail on it
- [ ] The `AuditEntry` docstring and `docs/ARCHITECTURE.md` section 8 say that a failed login's target is the username only when an account has it
- [ ] `docs/security/2026-11-11-security-audit.md`: the hardening note on the typed username marked fixed, with this ticket's commits
- [ ] Tests at the agreed seams: the backend API suite (`accounts/tests/test_login.py` and the audit log's API); the usual full suites and both workflows

## Comments
