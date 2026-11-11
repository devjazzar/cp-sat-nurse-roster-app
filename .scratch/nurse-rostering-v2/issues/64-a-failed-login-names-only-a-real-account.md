# 64: A failed login names only a real account

**What to build:** An `auth.login_failed` entry names the typed username as its target only when an account has that username; otherwise its target is empty, and its address and reason stay. A password typed into the username box is then never kept where the System Admin reads it, and a 600-byte made-up name no longer makes a 600-byte audit row. The login-attempts row is still keyed by the name typed, so an unknown name still locks exactly like a real one and the answer to a login still never says which names exist. Spec: `.scratch/nurse-rostering-v2/specs/hardening.md` (The throttle, "The failed login's target").

**Blocked by:** 63 The throttle on failed logins from one address (both change the login's failure path and its tests)

**Status:** ready-for-agent

- [x] A failed login at an unknown name, wrong credentials or locked, writes `auth.login_failed` with an empty target, no actor, its reason and its address
- [x] A failed login at a real account's name writes that name as its target and the account as its actor, as today
- [x] The answer to the login is the same in both cases (status, words, `locked_until`), and an unknown name still locks after five failures
- [x] The System Admin's audit log page shows such an entry without a target and does not fail on it
- [x] The `AuditEntry` docstring and `docs/ARCHITECTURE.md` section 8 say that a failed login's target is the username only when an account has it
- [x] `docs/security/2026-11-11-security-audit.md`: the hardening note on the typed username marked fixed, with this ticket's commits
- [x] Tests at the agreed seams: the backend API suite (`accounts/tests/test_login.py` and the audit log's API); the usual full suites and both workflows

## Comments

**From ticket 63 (2026-11-11).** The failed login's audit entry is still written by `_record_failure` in
`backend/accounts/login.py`, with the typed name as its target. Ticket 63's tests (`accounts/tests/test_throttle.py`) count
`auth.login_failed` entries and do not read their target, so the change here should not break them. The throttle's own
entry, `auth.login_throttled`, already has an empty target.

**From the user's review of ticket 63 (2026-11-11):** this ticket also shows the lockout's time ("locked until") on the
hospital's clock, as the throttle's "Try again at HH:MM" is (`frontend/src/lib/utils.ts`'s `hospitalClock`), on the login
page and Change password, instead of the browser's clock. About two lines, with the app-level test beside the throttle's.

**Implemented on 2026-11-11,** on branch `claude/ticket-64-failed-login-target-8e499b` (`d2043f0`, `a68466e`, `cb57fd1`,
`812e387`, this comment after them), from `main` at `e2ae502`. Draft pull request
[devjazzar/cp-sat-nurse-roster-app#10](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/10).

The suites ran locally under the heavy-run lock, on `cb57fd1`:
- the backend, on a throwaway PostgreSQL 18 container of my own: 3171 passed;
- the frontend: `npm test`, 770 passed, and `npm run build` succeeded. `812e387` changed one test after that run; that
  test file's test was run again on its own (passed);
- `makemigrations --check`: "No changes detected". There is no migration;
- the OpenAPI document and the client, exported and generated again: no difference. `locked_until` was a date-time
  already; only its offset changed;
- no Playwright file changed.

**What the dev stack needs:** a **rebuild** (`docker compose up -d --build`) for the new code. No migration, no change to
`deploy/Caddyfile`, compose or the `Dockerfile`, and no new dependency.

**What was built, criterion by criterion.**
- **An unknown name, wrong credentials or locked.** `_record_failure` in `backend/accounts/login.py` looks the typed name up
  once. With no account, `auth.login_failed` has no actor and an empty target. Its `after` (`reason`, and `failures` on a
  wrong password) and its address stay. Tests: `test_a_failure_with_an_unknown_username_keeps_nothing_that_was_typed`
  (types a password-like name and checks it is in no field) and
  `test_a_refusal_while_an_unknown_username_is_locked_names_nothing_either`.
- **A real name.** That account is the actor and its name the target, as before. This holds for a wrong password, a refusal
  while locked, and a deactivated account, which still has its name. "Has the name" is the exact match `authenticate` uses,
  so `SomeOne` is not `someone`'s (tested).
- **The same answer.** `test_a_real_name_and_an_unknown_one_get_the_same_answers` compares all six answers, with the
  server's clock held. The answers are four 401s, then a 423, then a second 423 with the same `locked_until`, and they are
  equal in status, words and time. `test_an_unknown_username_locks_the_same_so_names_cannot_be_probed` is unchanged and
  passes. `LoginAttempts` is still keyed by the name typed.
- **The audit log page.** `test_a_failed_login_at_an_unknown_name_has_no_target_and_keeps_its_address` in
  `audit/tests/test_api.py` runs real logins through the API and reads them back: target `""`, actor `null`, the reason and
  the address. On the page, an app-level test reads the row: "Unknown", "Failed login", an empty "On" cell, the reason and
  the address. It passed the first time it ran: the throttle's row of ticket 63 already rendered an empty target. The
  earlier test's failed-login fixture now has the shape the API sends (`target: ""`).
- **Docs.**
  - The `AuditEntry` docstring and `docs/ARCHITECTURE.md` section 8 say a failed login's target is the username only when
    an account has it.
  - Section 8's lockout sentence now also says it applies whether or not an account has the name, and that the login page
    shows its end on the hospital's clock.
- **The audit record.** `docs/security/2026-11-11-security-audit.md` has the typed-username note (`REPORT.md` section 5)
  marked fixed in `d2043f0`, and the lockout's clock in `a68466e`. `REPORT.md` is the run's record, left as written, as
  tickets 67 and 68 did.
- **The lockout's clock (the user's review of 63).**
  - `POST /api/auth/login`'s 423 now sends `locked_until` with the hospital's offset (`timezone.localtime`, as the 429
    does). `test_the_lock_is_sent_on_the_hospitals_clock` asserts `+03:00`, as `test_throttle.py` does.
  - The login page reads it with `hospitalClock`. The app-level test sits beside the throttle's, with a `+05:45` offset, and
    asserts the whole sentence with 10:15.
  - Both halves are needed: `hospitalClock` only slices the string, so without the backend change the page would show UTC.

**What was driven, and how.** I used my own scratch stack, `e2e/stack.sh up nr-t64` (ports 18640 and 18641), on
11 November 2026, through Caddy's HTTPS.
- **The logins, from a scratch Python client:**
  - Carla with a wrong password: 401.
  - `MySecret#Pass2026` typed as a username: 401, the same words.
  - Five logins at `nobody-here`: the fifth was 423 with `locked_until: 2026-11-11T11:24:01.559+03:00`.
  - Five at Hala: the fifth was 423 with the same words and the same offset.
  - A sixth at `nobody-here`: 423, with the same time.
- **As the System Admin, through `/api/audit/entries`:**
  - Carla's and Hala's entries name them as actor and target.
  - Every entry at `nobody-here` and at the password-like name has actor `null`, target `''`, its reason and
    `172.27.0.1`.
  - In the database, no audit row's target or `after` holds `MySecret`.
- **In headless Chromium (Playwright 1.64.1), on a London clock:**
  - At 375 px, Hala's login read "Too many failed logins. This account is locked until 11:24. Try again then." The
    browser's own clock read 08:09. The page fit (`scrollWidth` 375).
  - The admin's audit log page, filtered to failed logins, showed the unknown name's rows as "Unknown" with an empty "On"
    cell, between Hala's rows, and nothing failed.
- **Held by hand against `better-interface`, `better-writing` and `better-accessibility`:** the only change on screen is
  the time inside a sentence that was already there, in the `role="alert"` it already had. It now reads the hospital's
  clock, as the throttle's sentence beside it does. The empty "On" cell is the throttle's row's convention.

The stack is down, with its volumes, image and `e2e/.stack/nr-t64.*` gone. My PostgreSQL container is removed.

**What was found, and fixed.** Nothing beyond the ticket.

**Findings for you, not fixed.**
- **The typed name is still kept in `accounts_loginattempts`.** It is the lockout's key, by the spec. On the stack, the
  row `MySecret#Pass2026` was there. The System Admin's pages do not show it, but the database and every backup hold it
  until ticket 65's housekeeping removes it after a day.
- **Entries written before this ticket keep what was typed.** The log is append-only (ADR 0007), so I scrubbed nothing.

**What was NOT checked.**
- The whole browser suite and `operations.sh`, and the six parallel frontend runs: GitHub's.
- A real server's address. As ticket 63 found, every request through compose on Docker Desktop has `172.27.0.1`. Ticket 69
  works out the address.

**Decisions taken here.**
- "An account has the name" is an exact, case-sensitive match. It is the lookup the default `ModelBackend` makes, so the
  audit's actor and the login's own check cannot disagree.
- A deactivated account still has its name, so its failed logins name it. It is a real account the System Admin
  manages.
- I did not pull the 423's words into a shared module beside `throttle-words.ts`: it is one sentence in one page.

**Worth your review.**
- **Change password has no lockout, so only the login page changed.** Its endpoint answers 400 or 429, never 423, and its
  429 already goes through `hospitalClock`. The user's note named both pages.
- **The audit log page shows an empty "On" cell for a failed login at an unknown name,** as for a throttle. It shows no
  placeholder such as "—" or "(no account)". The spec left this open.
- **The "User" filter no longer finds failed logins at a name no account has,** since their target is empty. Filtering
  by a real user still finds theirs. A spray of made-up names is now found by the action filter and the address, not by
  name.
- **The 423 still reads "This account is locked",** also for a name no account has. That keeps the answer the same for
  both, which is the point, but the glossary's Lockout entry lists "account lock" under _Avoid_. The sentence predates this
  ticket; only its time changed.

**Review.** `code-review` against `e2ae502`:
- **Standards:** no hard violation.
  - Taken: the audit page test read cells by position; it now reads the whole row, as its neighbours do (`812e387`).
  - Kept: the held clock in `test_login.py` repeats `test_throttle.py`'s `clock` fixture in two lines; moving the fixture
    to `conftest.py` belongs to the next ticket that needs it.
  - Kept: the two audit-row asserts in `TestAudit` are clearer written out.
  - The "account locked" wording: above, under **Worth your review**.
- **Spec:** nothing missing or wrong.
  - The backend change to the 423's offset goes beyond "about two lines", but the page cannot be right without it.
  - `+03:00` depends on `TIME_ZONE`'s default, as the throttle's test already does.

**Things later tickets should know.**
- **Ticket 65** changes the same failure path next; there is a note on it. `_record_failure` makes one `User` lookup,
  and `LoginAttempts` is keyed as before.
- **Ticket 69:** the new tests set the address with `REMOTE_ADDR`, as their neighbours in `TestAudit` and
  `audit/tests/test_api.py` do. A change to `audit.log.client_ip` should move them together.
