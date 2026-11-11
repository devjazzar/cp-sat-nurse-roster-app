# 63: The throttle on failed logins from one address

**What to build:** Fifty failed logins from one client address in a fifteen-minute window throttle that address for the rest of the window. A throttled login is refused at once with 429, the time it may try again and a `Retry-After` header, before its username's login-attempts row is touched or any password is checked, whatever username and password it carries. A wrong password, a refusal while the name is locked, and a wrong current password on Change password each count one failure; a success counts nothing and clears nothing. Change password is refused the same way while its address is throttled, before the current password is checked. IPv6 addresses count by their /64; a request with no address is never throttled. The audit log gets one `auth.login_throttled` entry (no actor, no target, the address, the window's end) when an address reaches the limit, and nothing for the requests refused during it. The login page and Change password show "Too many failed logins from this network" and the time on the hospital's clock. The lockout per username is unchanged. Spec: `.scratch/nurse-rostering-v2/specs/hardening.md` (The throttle); ADR 0015; the words: `GLOSSARY.md` (Throttle, Lockout).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] A model in `accounts`, beside `LoginAttempts`, holding an address key's window start and failure count; the constants (fifty, fifteen minutes) beside `MAX_FAILURES` and `LOCK_DURATION`, not in the technical settings
- [x] `attempt_login` asks whether the address is throttled before it takes the name's row lock; a throttled login calls neither `authenticate` nor the hasher, touches no `LoginAttempts` row and writes nothing (a test counting hasher calls, as the audit's harness did)
- [x] Each refusal `attempt_login` makes, wrong credentials or locked, records one failure for the address; the address's row is not held across the hash
- [x] The failure that brings a window to fifty writes the one `auth.login_throttled` entry; a failure in a window older than fifteen minutes starts a new one counting one
- [x] `POST /api/auth/login` and `POST /api/auth/change-password` answer 429 with the detail, the time and `Retry-After`; a wrong current password counts one failure; the OpenAPI schema and the generated client follow
- [x] Two IPv6 addresses in one /64 share a budget, two /64s do not; a different address is not affected; the window's end lifts the throttle
- [x] The existing lockout tests pass unchanged; the public allow-list walk of the authorization tests still passes
- [x] The login page and Change password show the throttle's words and time on a 429 (the frontend's app-level suite)
- [x] `docs/ARCHITECTURE.md` section 8: the throttle beside the lockout, and the audit rule as the user changed it: every login the server checked, failed or not, is in the log, and so is each throttle; a request refused by a throttle is not
- [x] `docs/security/2026-11-11-security-audit.md`: lead 1 marked fixed, with this ticket's commits, and lead 2's per-address bound noted
- [x] Tests at the agreed seams: the backend API suite and the frontend's app-level suite; the usual full suites and both workflows

## Comments

**Implemented on 2026-11-11,** on branch `claude/ticket-63-login-throttle-901d2d` (`52db6f8`, `a9dcfa6`, `0f8cbab`,
`0cc1940`, this comment in `7c744ba`, then `Retry-After` declared in the schema and this comment corrected), from `main` at `5230b55`. Draft pull request
[devjazzar/cp-sat-nurse-roster-app#8](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/8).

The suites ran locally under the heavy-run lock:
- the backend on `0cc1940`, on a throwaway PostgreSQL 18 container of my own: 3143 passed, 1 error. The error was
  `nurses/tests/test_files.py::test_no_password_reaches_the_logs`, and it was my command's fault: I had passed
  `-p no:logging`, which takes away `caplog`. That file run again without the flag: 108 passed;
- the frontend: `npm test` on `0cc1940`, 769 passed, and `npm run build` succeeded;
- `makemigrations --check`: "No changes detected". The one new migration is `accounts/0003_address_failures`;
- the OpenAPI document was regenerated with the generated client, and they match the export. They hold the login's and
  Change password's new 429 answer, `ThrottleRefusal`;
- no Playwright file changed;
- GitHub's two workflows were green on `0cc1940`: backend, frontend, image, solver and browser checks.

**What the dev stack needs:** a **rebuild** (`docker compose up -d --build`), which runs the new migration. There is no change
to `deploy/Caddyfile`, compose or the `Dockerfile`, and no new dependency.

**What was built, criterion by criterion.**
- **The model.**
  - `accounts.models.AddressFailures` sits beside `LoginAttempts`. It has `address` (the key), `window_start` and
    `failures`.
  - The key is an IPv4 address as itself, and an IPv6 address as its /64 network (`2001:db8:1:2::/64`).
  - `MAX_ADDRESS_FAILURES = 50` and `THROTTLE_WINDOW = 15 minutes` sit beside `MAX_FAILURES` and `LOCK_DURATION` in
    `backend/accounts/login.py`. They are not technical settings.
- **The check comes first.** `attempt_login` calls `check_throttle` before it takes the name's row lock.
  - `check_throttle` only reads: one `SELECT` of the address's row.
  - A throttled login calls neither `authenticate` nor the hasher, touches no `LoginAttempts` row, and writes nothing.
  - `test_a_throttled_login_hashes_nothing_and_touches_no_name` counts the MD5 hasher's `verify` and `encode` calls, as the
    audit's harness did. It first asserts that an unthrottled refusal does hash, so the zero it then asserts can fail. It
    also checks a known name's row stays at `failures=2` and an untried name gets no row.
- **Each refusal counts one.** A wrong password and a refusal while the name is locked each call `record_address_failure`.
  The call comes after the name's transaction has committed, in a short transaction of its own (`select_for_update` on the
  address's row). So that row is never held across the hash.
- **The audit entry.**
  - The failure that makes the count exactly 50 writes `auth.login_throttled`: no actor, no target, the request's address,
    and `after: {"until": <the window's end on the hospital's clock, to the second>}`.
  - A parallel failure that lands past 50 writes nothing more.
  - A failure in a window older than fifteen minutes starts a new window, counting one.
- **The API.**
  - `POST /api/auth/login` and `POST /api/auth/change-password` answer 429 with `{detail: "Too many failed logins from this
    network.", throttled_until}` and `Retry-After` in whole seconds, rounded up.
  - `throttled_until` is sent with the hospital's offset (`timezone.localtime`).
  - Change password checks the throttle before `check_password`. A wrong current password records one failure; a right
    one records nothing.
  - The OpenAPI document and the client follow. Both routes declare the 429 in full through `openapi_extra`, with its
    `Retry-After` header (an integer, in seconds). Ninja's `openapi_extra` replaces the answer it names, so the body's
    schema is declared there too. The generated client did not change.
- **IPv6 and other addresses.** Two addresses in one /64 share a budget, two /64s do not, and a different address is not
  affected. The window's end lifts the throttle; the tests move the server's clock by monkeypatching `timezone.now`. A
  request with no address (`REMOTE_ADDR` empty and no forwarded header) is never throttled: 60 failures, then 200.
- **The lockout and the allow-list.** `test_login.py` is unchanged and passes. `test_authorization.py`'s public allow-list
  walk passes; the login's route did not change its auth.
- **The pages.**
  - The login page and Change password show "Too many failed logins from this network. Try again at 10:15." in a
    `role="alert"`. The time is read off the answer's ISO string (`hospitalClock`, beside `hospitalTime` in
    `lib/utils.ts`), so it is the hospital's clock whatever the browser's.
  - The app-level tests use a `+05:45` offset, so they cannot pass on the browser's clock.
  - A 429 with no time (not the application's) reads "…Try again later.".
- **The audit log page.** It names the new action "Logins throttled", by "Unknown", as a failed login is shown.
- **Docs.**
  - `docs/ARCHITECTURE.md` section 8: the throttle beside the lockout, and the audit rule as the user changed it: every
    login the server checked, failed or not, is logged, and so is each throttle, once; a request a throttle refused is not.
  - The audit record: lead 1 is marked fixed with `52db6f8` and `a9dcfa6`. Lead 2 is noted as bounded per address and
    left open for ticket 65.
  - Notes left on tickets 64, 65, 66 and 69.

**What was driven, and how.** I used my own scratch stack, `e2e/stack.sh up nr-t63` (ports 18630 and 18631), on 11 November
2026, through Caddy's HTTPS. I drove it with a scratch Python client and with headless Chromium through Playwright 1.64.1.
- **The limit:**
  - Carla signed in first (200).
  - Fifty logins with fifty made-up names and a wrong password were each 401, in 29 s.
  - The fifty-first, Carla with her right password, was 429 with `Retry-After: 872` and
    `throttled_until: 2026-11-11T09:46:22.597+03:00`.
- **Change password while throttled:** with a session of Carla's made inside `web` (a login through Caddy was throttled by
  then), Change password with her right current password was 429 with `Retry-After: 857`.
- **The database afterwards:**
  - `audit_auditentry` held one `auth.login`, 50 `auth.login_failed` and one `auth.login_throttled`, with
    `{"until": "2026-11-11T09:46:22+03:00"}`. The 429s wrote nothing.
  - `accounts_addressfailures` held one row: `172.27.0.1`, 50 failures.
  - There were 50 `made-up-*` login-attempt rows, as before this ticket (ticket 65's).
- **The pages, in Chromium on a London clock:**
  - The login page showed "Too many failed logins from this network. Try again at 09:46.", the hospital's time and not
    London's 06:46.
  - At 375 px it fit (`scrollWidth` 375).
  - Change password, after filling all three fields, showed the same words.
- **Held by hand against `better-interface`, `better-writing` and `better-accessibility`:**
  - The words say what happened and when to try again, in the voice of the lockout's message beside it.
  - The words avoid the glossary's "blocked" and "rate limit".
  - The refusal is a `role="alert"` paragraph in the place a wrong password's already takes, so it is read out on arrival.

The stack is down; its volumes, image and `e2e/.stack/nr-t63.*` are gone, and my PostgreSQL container is removed.
`npx playwright install chromium` removed an unused WebKit build from the shared Playwright cache
(`~/Library/Caches/ms-playwright/webkit-2182`). A run that needs it downloads it again.

**What was found, and fixed.**
- A 429 that carried no time would have thrown in the page. It now reads "…Try again later.", with a test (`0cc1940`, from
  the review).

**Findings for you, not fixed.**
- **The lockout's time is on the browser's clock; the throttle's is on the hospital's.** `login.tsx` shows `locked_until`
  through `toLocaleTimeString`, which is the browser's time zone, and the backend sends it in UTC. On a phone set to
  another zone, the two refusals on one page read different clocks. The spec says the throttle shows its time "as it shows
  a lockout's", but the lockout was never on the hospital's clock. The fix is two lines: `timezone.localtime` on the 423's
  time and `hospitalClock` in the page. The ticket says the lockout is unchanged, so I left it.
- **Through compose on Docker Desktop, the client address the app saw was the bridge gateway (`172.27.0.1`), not my
  machine's.** So on a stack run on Docker Desktop, the dev stack included, every client shares one address: fifty failed
  logins from anyone throttle everyone's logins for the rest of the window. Ticket 69 is where the address is worked out.

**What was NOT checked.**
- The whole browser suite and `operations.sh`: GitHub's, green on `0cc1940`.
- The six parallel frontend runs: GitHub's.
- The window's end lifting the throttle on the stack (fifteen minutes of waiting): the backend suite checks it with a moved
  clock.
- A burst of parallel failures past 50 against the real pool: the code writes the entry only at exactly 50, and the
  overshoot is bounded by the pool, as the spec accepts. No load was sent.
- IPv6 through Caddy: the scratch stack is IPv4 only. The backend suite covers the /64 rule.
- Which address the app sees on a Linux server, where Docker's networking differs from Docker Desktop's: not run.
- Where focus goes after the 429: I read the text of the alert and did not look at focus.

**Decisions taken here.**
- **`record_address_failure` runs after the name's transaction, not inside it.** The spec says the address's row is not
  held across the hash, and inside the name's transaction it would be held until that commits. The cost is that a failed
  login whose address count then fails to write answers 500, after its own entry is committed.
- **The entry is written at exactly 50, not at 50 or more.** A parallel failure that overshoots writes no second entry and
  does not move the window.
- **An IPv4 address written as IPv6 (`::ffff:a.b.c.d`) counts as that IPv4 address.** Otherwise every such client would
  share one /64. The spec does not say; there is a test.
- **The audit entry's `until` is to the second, with the hospital's offset,** as the audit log shows other times.
- **The frontend does not read `Retry-After`;** it shows `throttled_until`. The header is for other clients, and it is
  tested and declared in the schema.
- **The frontend writes its own words** for the 429, as it does for the 401 and the 423, rather than showing `detail`.

**Worth your review.**
- **The words: "Too many failed logins from this network. Try again at 10:15."** The spec fixed only the first sentence. I
  chose "Try again at" over the lockout's "…locked until 10:15. Try again then." because there is no account to name, and
  "network" because the address is shared by everyone behind it (glossary, Throttle).
- **How the time is shown: hours and minutes on the hospital's clock, with no date.** A window is at most fifteen minutes, so
  the date is always today's or, just before midnight, tomorrow's.
- **The audit log names the action "Logins throttled", by "Unknown",** and shows the window's end in its details.
- **The lockout's browser-clock time** (Findings above): fix it with the throttle's helper, or leave it.

**Review.** `code-review` against `5230b55`, both axes in fresh sub-agents.
- Standards: no hard violations. Fixed in `0cc1940`:
  - the slicing of the time now lives in `hospitalClock` beside `hospitalTime`;
  - the audit log's "Unknown" actions are one `ANONYMOUS_ACTIONS` set;
  - the `Retry-After` test now uses a fixed bound (890 to 900 s) instead of the code's own sum;
  - `HERE` is renamed `ADDRESS`.

  Kept:
  - the words in both the backend's `detail` and the frontend: the frontend owns its words, as for the 401 and 423;
  - per-file test helpers, as the repo does;
  - `check_throttle` and `record_address_failure` called in two places: they are apart so the address's row is never held
    across the hash.
- Spec: nothing missing or wrong.
  - Fixed: the 429 without a time; `Retry-After` is now declared in the schema (after the review).
  - Kept: the IPv4-mapped rule and the audit-log name (both small and tested).

**Things later tickets should know.**
- **64:** `_record_failure` in `accounts/login.py` still writes the typed name as the target. `test_throttle.py` counts
  `auth.login_failed` entries and does not read their target.
- **65:**
  - Remove an address row when `window_start + THROTTLE_WINDOW <= now`.
  - `record_address_failure` already restarts an ended window, so a removed row loses nothing.
  - The tests' `clock` fixture in `test_throttle.py` moves `timezone.now`.
- **66:** `accounts_addressfailures` is a second login-attempts table; whether a restore empties it is that ticket's to say.
- **69:** the throttle reads the address only through `audit.log.client_ip`, inside `_address_key`. `test_throttle.py`
  sends the address as `REMOTE_ADDR` through one helper, `login()`.
- From 62, still true: a file route takes `for_a_file(...)`, and tests needing two active solves need two units.
