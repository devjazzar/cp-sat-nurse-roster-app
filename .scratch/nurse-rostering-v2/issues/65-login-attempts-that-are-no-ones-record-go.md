# 65: Login attempts that are no one's record go

**What to build:** A username's count of failed logins is forgotten a day after its last failure, unless the name is locked now, and an address's throttle window is removed once it is over. A daily retention job, beside the others and caught up by the next day when one is missed, removes both. The audit entries of failed logins stay. Spec: `.scratch/nurse-rostering-v2/specs/hardening.md` (Housekeeping); ADR 0009 (every job under a lock).

**Blocked by:** 64 A failed login names only a real account (both change the login's failure path and its tests), after 63

**Status:** ready-for-agent

- [x] `LoginAttempts` gains the time of its last failure, set at every failure it counts; rows written before have none
- [x] A daily job at a fixed UTC time after the other retention jobs, under its own lock, removes every login-attempts row not locked now whose last failure is more than 24 hours old or unknown, and every address row whose window ended
- [x] It keeps a locked row, a fresh one and the current window; it deletes no audit entry
- [x] A name whose count was removed starts again from none at its next failure
- [x] `docs/ARCHITECTURE.md` section 7's retention list and section 9's "no one's record" list name both
- [x] `docs/security/2026-11-11-security-audit.md`: lead 2 marked fixed, with this ticket's commits
- [x] Tests at the agreed seams: the backend suite (prior art: the retention jobs' tests of tickets 22 and 42) and the retention check in `deploy/tests/operations.sh` if it fits there; the usual full suites and both workflows

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

**From ticket 64's review (2026-11-11):** the user chose to change the login lockout's 423 message here. It now says "Too many failed logins. This account is locked for now." even for a name no account has; it becomes "Too many failed logins. Try again after {time}.", with the time on the hospital's clock as the login page already shows it (`backend/accounts/api.py`, `frontend/src/routes/login.tsx`).

**Implemented on 2026-11-11,** on branch `claude/ticket-65-login-attempts-retention-7354d9` (`2172be9`, `70b25c5`,
`fc3a2de`, `31ae007`, with `main` merged in at `eac788f`, and this comment after them), from `main` at `472f71f`. Draft pull
request [devjazzar/cp-sat-nurse-roster-app#13](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/13).

The suites ran locally under the heavy-run lock, on `31ae007`:
- the backend, on a throwaway PostgreSQL 18 container of my own: 3185 passed, plus 1 error. The error was
  `nurses/tests/test_files.py::test_no_password_reaches_the_logs`, caused by my own `-p no:logging`, which removes `caplog`.
  Run again with the normal plugins, it passed: 3186 in all;
- the frontend: `npm test`, 771 passed, and `npm run build` succeeded;
- `makemigrations --check`: "No changes detected" once `0004_login_attempts_last_failure` was added;
- the OpenAPI document and the client, exported and generated again: no difference. Only the 423's `detail` text changed,
  and the schema does not carry it;
- no Playwright file changed;
- GitHub's two workflows were green on `31ae007` on the first attempt: CI (backend, frontend, image, solver), and the
  browser checks with `operations.sh`, which now runs the new job and the restore of a backup from before the new column.

**What the dev stack needs:** a **rebuild** (`docker compose up -d --build`). It brings **one migration**
(`accounts.0004_login_attempts_last_failure`, a nullable column, which `web` applies at start) and the new periodic job
the worker registers. No change to `deploy/Caddyfile`, compose or the `Dockerfile`, and no new dependency.

**What was built, criterion by criterion.**
- **The time of the last failure.** `LoginAttempts.last_failure_at`, nullable, is set on the wrong-credentials path in
  `attempt_login`, in the same `attempts.save()`. A refusal while the name is locked still saves nothing. Rows written
  before the column existed have none.
- **The daily job.**
  - `accounts.tasks.remove_old_login_failures` runs at 22:50 UTC, under its own lock and queueing lock (`@daily`, ADR
    0009). It calls `accounts.login.remove_old_failures`, which sits beside `FAILURES_KEPT` (24 hours) and
    `THROTTLE_WINDOW`.
  - It removes every `LoginAttempts` row that is not locked now (`exclude(locked_until__gt=now)`) and whose last failure
    is more than 24 hours old (strictly: a row exactly a day old is kept until the next run) or unknown. It removes every
    `AddressFailures` row with `window_start + THROTTLE_WINDOW <= now`.
  - It is a cut-off from now, not a day's slice, so a day missed is caught up by the next run, as tickets 22 and 42 do.
- **What it keeps.** A locked row, a fresh row, the current window, and every audit entry. Tests are in
  `accounts/tests/test_login_retention.py`, through the login with the server's clock moved (a local `clock` fixture, as
  in `test_throttle.py`):
  - a count a day and a minute old goes and one two minutes old stays;
  - the day counts from the last failure;
  - exactly 24 hours stays (this test fails with `<=`);
  - a name locked for longer than a day stays and still answers 423;
  - a lock that ran out goes with its day;
  - a row from before the column goes;
  - an ended window goes and the current one stays;
  - no audit entry goes;
  - the job's lock.
- **Starting again from none.** After the job, four failures at that name answer 401 and the fifth 423
  (`test_a_name_whose_count_went_starts_again_from_none`). On the stack, `nobody-here`'s next failure made a new row
  with one failure and no lock.
- **The lockout's words.**
  - The 423's `detail` is now `"Too many failed logins."` (`LOCKED_OUT`, beside the throttle's `THROTTLED` in
    `accounts/api.py`).
  - The page carries the user-visible sentence, built from `locked_until` on the hospital's clock: "Too many failed
    logins. Try again after 10:15." Without a time, it reads "Too many failed logins. Try again later."
  - Neither side says "account" any more (glossary: _Avoid_ "account lock").
  - Tests: `test_the_lock_says_too_many_failed_logins_and_names_no_account` (an unknown name), and two app-level tests in
    `app.test.tsx`: with a `+05:45` time (the whole sentence, and no "account"), and without one.
- **Docs.**
  - `docs/ARCHITECTURE.md` section 7's retention list names the job, its time, both tables and what it keeps.
  - Section 9's "no one's record" list names a username's count and an address's window.
- **The audit record.**
  - `docs/security/2026-11-11-security-audit.md` marks lead 2 fixed in `2172be9` and `fc3a2de`, in the table and in "What
    the user decided".
  - It says that the typed name ticket 64 left in `LoginAttempts` now stays there, and in backups, for under two days after
    its last failure, and longer only while the name is locked or the worker is down.
  - The audit entries stay, bounded per address by the throttle (ADR 0007).
- **`deploy/tests/operations.sh`.** The retention check fits there, so it has one:
  - It inserts a count 25 hours old, a fresh one, one locked for two days and one from before the column, plus an ended and
    a current window.
  - It runs the job with the other four and reads back only its own rows: `fresh locked` and `192.0.2.2`. Then it removes
    what it left.
  - The pre-63 restore check now also drops `last_failure_at` and deletes the `0004` migration row, as ticket 66's note asked
    of any later `accounts` migration.

**What was driven, and how.** I used my own scratch stack, `e2e/stack.sh up nr-t65 --empty` (ports 18650 and 18651), on 11
November 2026.
- **From a scratch Python client through Caddy's HTTPS:**
  - Five wrong logins at `nobody-here`: the fifth answered 423 with `{"detail": "Too many failed logins.", "locked_until":
    "2026-11-11T14:37:21.301+03:00"}`.
  - Two at `old-name`: 401.
  - The rows held `last_failure_at`, and the address `172.26.0.1` had a window of 7.
- **In the browser pane (Chromium), at 375 px, over the stack's HTTP origin:** the login at `nobody-here` read "Too many
  failed logins. Try again after 14:37." in the red `role="alert"` under the password field. The page fit (`scrollWidth`
  375).
- **The job.**
  - `stack.sh clock` moves only the hospital's date, not `timezone.now()`, so the first try changed nothing. I put it back
    and aged the rows in the database instead, which is the same thing to the job: `nobody-here` and `old-name` by 25 hours
    (`nobody-here`'s lock with them), and the window by 16 minutes. I also added a fresh failure at `fresh-name`.
  - `stack.sh fire nr-t65 accounts.tasks.remove_old_login_failures` succeeded, under the lock `remove_old_login_failures`.
    Left after it: `fresh-name` only and no window. The audit count was 12 before and after.
  - Then `nobody-here` answered 401, with a new row of one failure.
  - A name locked now (`locked-now`, five failures) whose last failure I aged by 25 hours was kept by a second run.
- **Held by hand against `better-interface`, `better-writing` and `better-accessibility`:**
  - The only change on screen is the sentence in the `role="alert"` it already had, the same place, colour and size.
  - It is shorter, says what to do and when, and no longer claims an account where none may exist.
  - "Try again after" (the user's words) sits beside the throttle's "Try again at"; see **Worth your review**.

The stack is down, with its volumes, image and `e2e/.stack/nr-t65.*` gone. My PostgreSQL container is removed. The heavy-run
lock was released.

**What was found, and fixed.** Nothing beyond the ticket.

**Findings for you, not fixed.**
- **`e2e/stack.sh clock` does not move `timezone.now()`**, only the hospital's date (`nurses.membership`). A browser check
  of anything timed in hours (the lockout, the throttle, this job) cannot use it. Ageing rows in the database does the job
  here.
- **`operations.sh`'s `done_ok`** passes on any succeeded run of a task, not the one it just queued. That only matters on a
  long-lived stack, and it predates this ticket (raised by the review).

**What was NOT checked.**
- The six parallel frontend runs and the whole browser suite were GitHub's. Both passed there.
- The job at its real 22:50 UTC: it was fired now, as `stack.sh fire` does.
- A browser in a time zone other than the hospital's on the stack: the pane was in Riyadh. The app-level test covers it
  with `+05:45`.
- **A short window in `operations.sh`'s pre-63 restore check** during which the live database has no `last_failure_at`. A
  worker run of this job landing exactly there would fail once. CI's stack never reaches 22:50 UTC inside it in practice.

**Decisions taken here.**
- **The job is named `remove_old_login_failures`,** in `accounts/tasks.py`. Its query is `accounts.login.remove_old_failures`,
  beside the constants it reads.
- **"More than 24 hours" is strict** (`<`), as the spec says. The window's end is `<=`, as ticket 63 defined it.
- **The 24 hours is `FAILURES_KEPT`,** in code beside `MAX_FAILURES`, not a technical setting, as the spec put the
  throttle's constants.

**Worth your review.**
- **The time, 22:50 UTC: last of the retention jobs** (22:10, 22:20, 22:30, 22:40), and ten minutes before a nightly backup
  at 02:00 in Riyadh (23:00 UTC). So that night's backup holds the fewest names. For another time zone the backup time
  moves and this does not.
- **The retention check is in `operations.sh` as well as the backend suite.** It fit, and it proves the job is registered
  and runs in the real worker on the real tables, and that a pre-63 backup restores with the new column.
- **The page carries the sentence and the API's `detail` is "Too many failed logins.".** This follows the throttle's
  pattern: `detail` is fixed words, the time is a field, and the page joins them on the hospital's clock. So the API's own
  text never says "Try again after". Making `detail` the whole sentence would put a formatted time in it, on the server's
  clock format.
- **"Try again after 10:15" for the lockout beside "Try again at 10:15" for the throttle.** "After" is your sentence. The
  two now differ by one word.
- **How long a typed name stays:** under two days after its last failure (a day, then up to a day until the job's next
  run), not "at most a day plus the lock". A lock is 15 minutes and is set at the last counted failure, so it ends inside
  the day anyway. Running the job hourly would bring this near one day; the spec said daily.

**Review.** `code-review` against `472f71f`:
- **Standards:** no hard violation.
  - Taken: the 423's words are a named constant beside `THROTTLED` (`31ae007`).
  - Kept: the copied `clock`, `login` and `fail` helpers in the new test file. The `clock` fixtures across the suite mean
    different things (`nurses/tests/test_clock.py`'s is the file clock), so one in `conftest.py` would need a new name.
  - Kept: the test that locks a name for two days, and the one creating a pre-column row, reach the table directly.
    No client can make either state, and the prior-art retention tests of tickets 22 and 42 do the same.
  - Kept: no `lockedWords` helper beside `throttledWords`. It is one sentence on one page, as ticket 64 decided.
  - Kept: the task delegates to `accounts.login`, so the 24 hours and the window stay in the module that owns them.
- **Spec:** nothing missing.
  - Taken: lead 2 cites `fc3a2de` too.
  - The NULL handling, the boundaries and the concurrency with a login holding the row lock were checked and are right:
    one `DELETE`, which re-reads a row a login committed meanwhile.
  - The `operations.sh` SQL and its scoping were checked as well.
  - The optional 423 body on the page is defensive, matching the throttle's.
- **The advisor** (before the full runs) caught three things, all fixed in `fc3a2de`: the `operations.sh` asserts read the
  whole tables and left rows behind, the boundary was `<=`, and the "about a day" claim was wrong.

**Things later tickets should know.**
- **A later `accounts` migration:** `operations.sh`'s pre-63 restore check now undoes `0003` and `0004` (it drops the
  table and the column, and deletes both migration rows). A new migration joins that list.
- **Ticket 70** also edits `operations.sh`. This ticket's change sits in the retention block (after the backup checks) and
  the pre-63 restore line.

**After ticket 70 landed (2026-11-11):** `origin/main` (ticket 70, up to `28d7ec4`) was merged in at `7e735f3`.
- `deploy/tests/operations.sh` merged cleanly: this ticket's retention rows and the pre-63 line sit beside ticket 70's
  checks.
- The audit document's three conflicts were resolved keeping both: lead 2 fixed in ticket 65, lead 3 fixed at Caddy in
  ticket 70.
- Both GitHub workflows were green on `7e735f3` (CI, and the browser checks with `operations.sh`). That head, with this note
  after it, is what reached `main`.

**Reviewed by the user (2026-11-11):** all five points kept as built.
- The job runs at 22:50 UTC, the last retention job, ten minutes before a 02:00 Riyadh backup.
- It is checked in `deploy/tests/operations.sh` as well as the backend suite, with a restore from before the new column.
- The page builds the sentence from the API's short text and `locked_until`, as the throttle's does.
- The lockout's "Try again after" beside the throttle's "Try again at".
- A typed name stays up to about two days after its last failure, the job running once a day.
