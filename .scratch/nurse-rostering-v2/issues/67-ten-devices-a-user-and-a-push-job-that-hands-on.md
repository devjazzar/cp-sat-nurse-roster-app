# 67: Ten devices a user, and a push job that hands on after 30 seconds

**What to build:** A user holds at most ten push subscriptions: turning pushes on for an eleventh device ends the user's earliest turned on, with no audit entry of its own, while a browser's renewal adds and ends none and an address moving from another user counts. A push job starts no new send once it has run 30 seconds and hands the sends it has not made to a new push job at the normal priority, with the same try number, behind any push already waiting; nothing is dropped, and tries again work as today. A push `auth` key longer than the model's column is refused with 422 at turn-on, and `pushing.send` never raises: an exception the library raises that is not already sorted is a refusal. Spec: `.scratch/nurse-rostering-v2/specs/hardening.md` (Push subscriptions and the push job); ADR 0012, ADR 0009; the words: `GLOSSARY.md` (Push subscription, Push).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] `subscriptions.turn_on`, under the user's row lock, ends the earliest subscriptions by `turned_on_at` until the user holds ten, after a new address or one moving from another user; a renewal (`replaces`) ends none; no audit entry for the ended one
- [x] `pushes.deliver` takes the job's start and a 30-second budget on a clock the tests can move, and returns the sends it did not make beside those to try again
- [x] The push job defers the sends handed on as a new push job at normal priority and the same try number; a try again stays at priority −1
- [x] A test: a job past its budget makes no more sends; the next job makes them as first tries, after a push already waiting; every send is made once
- [x] The API's `auth` key limit matches the column; a longer key is 422, not a database error
- [x] A library exception of an unforeseen kind in `pushing.send` is `refused`, and the job goes on to the next send
- [x] `docs/ARCHITECTURE.md` section 7's `push` paragraph gains the cap and the budget; ADR 0012 gains a consequence line for the eleventh device
- [x] `docs/security/2026-11-11-security-audit.md`: lead 4 and the push hardening notes marked fixed, with this ticket's commits
- [x] Tests at the agreed seams: the backend API suite (`notifications/tests/test_pushes.py` with its scripted push service); the usual full suites and both workflows

## Comments

**Implemented on 2026-11-11,** on branch `claude/ticket-67-push-limits-bfc983` (`756f5c5`, `68308ef`, `ba67a89`, a merge of
`main` with ticket 68 in `2cb4e42`, then this comment), from `main` at `5230b55`. Draft pull request
[devjazzar/cp-sat-nurse-roster-app#9](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/9).

The suites ran locally under the heavy-run lock, on `ba67a89`, the backend on a throwaway PostgreSQL 18 container of my own:
- the backend: 3141 passed;
- the frontend: `npm test` 765 passed; `npm run build` succeeded;
- `makemigrations --check`: "No changes detected";
- the OpenAPI document was regenerated: `SubscriptionKeys.auth` now has `maxLength` 100 (was 200), and the generated client
  and zod schema changed to match. The browser's `auth` secret is 16 bytes (22 characters), so no device is refused;
- no Playwright file changed. Both GitHub workflows were green on `ba67a89`.

**What the dev stack needs:** a **rebuild** (`docker compose up -d --build`) for the backend code. There is no migration, no
new dependency, and no change to compose, the `Dockerfile`, the Caddyfile or the solver.

**What was built, criterion by criterion.**
- **The cap:**
  - `notifications.subscriptions.turn_on` keeps the user's ten latest (`SUBSCRIPTIONS_A_USER`) after it stores a new address,
    or moves an address from another user to this one. It deletes the rest, earliest `turned_on_at` first, with the pk
    (UUIDv7) to break a tie. This happens in the transaction that holds the user's row lock.
  - A renewal (`replaces`), and turning the same address on again, end none.
  - No entry is written for one ended; the new device's `push.turned_on` is the only one.
  - A user holding more than ten from before is brought down to ten at their next turn-on.
- **The budget:**
  - `pushes.deliver(..., started=, budget=30)` reads `pushes.clock` (`time.monotonic`, which the tests replace) before each
    send. Once 30 seconds have passed it starts no new send.
  - It returns `Delivered(retry, handed_on)`. The sends handed on are the rest of the current reader's and every later
    notification's, filtered by `remaining` as a try again is. So a try-again job hands on only what it held.
  - A notification reached after the budget is handed on without its checks: the next job reads again whether the thing
    still waits, whether the reader has a page, and whose the subscription is.
- **The job:** `notifications.tasks.push` reads its own start. It defers the sends handed on with `enqueue`: priority 0, no
  delay, the same `attempt`. So they queue behind any push already waiting and stay first tries if they were. It defers the
  tries again as before, at priority −1. A job may defer both.
- **The tests** (`notifications/tests/test_pushes.py`, `TestTheBudget`, with a moved `Clock` and the scripted push service):
  - a job past its budget, then the approvers' job already waiting, then the handed-on sends: the order of the sends and
    each one made once;
  - a job within its budget makes every send, in one job;
  - a send handed on from a try again keeps its try number. Each phone that is down is still sent four times and counts one
    failure. The test fails when the hand-on is changed to try 0;
  - a handed-on send to a thing that no longer waits is not made.
- **The `auth` key:** `push_api`'s two key types take `max_length` from `PushSubscription`'s columns (p256dh 200, auth 100).
  A 101-character `auth` is 422 on `auth`, and nothing is kept; keys as long as their columns are kept. Before the fix the
  101-character key was a 500 `DataError`.
- **`pushing.send`:** a last `except Exception` returns `refused`. Tested with an exception class the library never raises:
  that phone counts one failure, and the laptop after it in the same job is still sent.
- **Docs:**
  - `docs/ARCHITECTURE.md` section 7's `push`: the budget, the hand-on and the cap. Section 8's subscription paragraph: the
    eleventh device and the renewal.
  - ADR 0012: a consequence line for the eleventh device.
  - The audit record: lead 4 and `REPORT.md` section 5's push note marked fixed with `756f5c5`. The merge with ticket 68's
    note kept both.
- **Tests at the agreed seams:** `test_push.py` (the subscription tests beside it; `TestTenDevices`, eight tests, and the two
  key tests) and `test_pushes.py` (five tests), through the API, the real queue and the scripted push service.

**What was driven, and how.** I used my own scratch stack, `e2e/stack.sh up nr-t67` (ports 18670 and 18671), on 11 November
2026. I drove it through Caddy's HTTPS with a scratch Python client, as the seed's people.
- **The cap, as Amal:**
  - ten devices on: `devices` 10;
  - the eleventh: 200, `devices` 10, the first no longer held, the second still held;
  - a renewal of the sixth: `devices` 10, the second still held;
  - Badr's device turned on by Amal: `devices` 10, Amal's second ended, Badr's `devices` 0.
- **The audit log** held 12 `push.turned_on` for Amal from this, and none for any subscription ended.
- **The key:** a 101-character `auth` was 422 with "String should have at most 100 characters" on `keys.auth`.
- **The hand-on, on the real worker:**
  - Inside my stack's worker only, five made-up names under `push.services.mozilla.com` were mapped in `/etc/hosts` to
    `10.255.255.1`. Through Docker Desktop that connects and never answers, so one send took about 10.9 s to its read
    timeout (`unreachable`). Nothing was sent to a real push service.
  - Amal turned pushes on for four such devices, and Emad proposed the seed's sound swap to her.
  - The queue showed push job 9 run from 09:55:56 to 09:56:27. It made three sends, at 09:56:06, :16 and :27, then
    deferred job 10 (priority 0, try 0, one send, no delay) and job 11 (priority −1, try 1, the three sends, at +60 s).
  - Job 10 made the fourth first try at 09:56:42 and deferred its own try again, job 12 at −1.
  - Jobs 11 and 12 ran at 09:57:27 and 09:57:42 and deferred the third tries for 10:00:57 and 10:01:12. I stopped
    watching there.

The stack is down, its volumes and `e2e/.stack/nr-t67.*` are gone, and my PostgreSQL container is removed.

**What was found, and fixed.** Nothing beyond the ticket.

**Findings for you, not fixed.**
- **A user already holding more than ten keeps them until their next turn-on.** The spec asks only for the turn-on. The
  owner's read-only count of the largest number one account holds (`NEEDS-VALIDATION.md`, lead 4) says whether a one-off
  trim matters on the installation.

**What was NOT checked.**
- The full course of tries again on the stack (the last ones due about ten minutes on): the suite's tests cover them, and
  the first two rounds were watched.
- A real push service that is slow: the slowness was a blackholed address in my worker. How long a send to a made-up
  address takes on the hospital's network is still not measured; the budget bounds a job whatever it is.
- The whole browser suite and `operations.sh`: GitHub's. No push journey changed.
- The six parallel frontend runs: GitHub's.

**Decisions taken here.**
- **The clock is `pushes.clock`, a module attribute.** The job reads its start from it and the tests replace it with one
  they move inside a scripted answer. The job's start is never a job argument, so each job handed on gets 30 seconds of its
  own.
- **A notification reached after the budget is handed on unchecked,** rather than checked and then handed on. The job
  ends sooner, and the next job checks it anyway. The cost: a notification that no longer waits can cause one job that
  sends nothing.
- **The key limits come from the model's fields,** so the API and the column cannot drift again; `p256dh` keeps 200.
- **The architecture's section 8** also gains the cap, beside section 7 as the spec asked, since that paragraph lists every
  way a subscription ends.

**Worth your review.**
- **The ordering "behind a push already waiting" rests on Procrastinate's fetch order** (priority, then id) and the `push`
  lock. A job handed on gets a later id than any job already waiting at priority 0. The test asserts the order of the
  sends, so a change in the library would fail it. Recommendation: keep.
- **A send handed on from a try again runs at priority 0, not −1.** That is what the spec says ("a new push job at the
  normal priority, with the same try number"). It means a try again that ran out of time competes with new pushes for its
  rest. Recommendation: keep; it is due now, unlike a try again waiting for its time.
- **The word "budget"** is the spec's and the ticket's, but the glossary lists it as a word to avoid under **Time limit**
  (the solver's). It is now in the code for the push job (`BUDGET_SECONDS`, `TestTheBudget`). Recommendation: keep it, or
  add a line under **Push**; your call.
- **Two tests set state through the database rather than the API:** twelve subscriptions "from before" the cap (which no
  API call can make now), and a request window deleted mid-job to show the next job checks again.

**Review.** `code-review` against `5230b55` ran its two axes in parallel.
- **Spec.** Nothing missing or wrong. Kept: section 8's extra sentence (above), and the unchecked hand-on (above).
- **Standards.** No hard breach. Fixed in `ba67a89`: the cap renamed `SUBSCRIPTIONS_A_USER` ("device" is an avoid-word for a
  push subscription), one `_pair` builder for a send's pair instead of three, and a line of the architecture rewrapped.
  Kept: "budget" (above), the two database-set tests (above), `deliver`'s `budget` parameter (the ticket names it), and the
  API reading the model's field lengths (one source for the limit).

**Things later tickets should know.**
- **`pushes.deliver` now returns `Delivered(retry, handed_on)`** and needs `started=`. A caller outside the job (none today)
  passes `pushes.clock()`.
- **To make a push slow on a scratch stack:** add an allowed host name pointing at `10.255.255.1` to the worker's
  `/etc/hosts` (`docker exec -u 0`). Through Docker Desktop each send then waits for its 10-second read timeout.

**From the main session (2026-11-11):** PR 9 merged into `main` as `2292114` by the ticket session, both workflows green on
`ef40a38` (only `[skip ci]` markdown after it). Dev stack rebuilt, no migration; health ok.

**Reviewed by the user (2026-11-11):** all four points kept as built.
- The order behind a push already waiting rests on Procrastinate's priority-then-id fetch, held by a test.
- A send handed on from a try again goes at normal priority, as the spec says.
- "Budget" stays for the push job's 30 seconds; `GLOSSARY.md`'s Time limit entry now says the word names only that, never a
  solve's time limit.
- The two tests that write the database directly stay.
