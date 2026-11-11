# 62: Audit follow-ups: no late approval, one solve a unit, no framing, no cross-site downloads

**What to build:** Four small changes the user decided on 2026-11-11, from the security audit of that day
(`docs/security/2026-11-11-security-audit.md`; the leads' full traces are in its `NEEDS-VALIDATION.md`, the late approval
in section 4).

1. **No approval once the month is over.** Submitting already refuses a month that is over
   (`rosters.review.why_not_submit`: "This month is over, so its draft cannot be submitted."). Approving does not
   (`why_not_approve`). So a roster left submitted past its month can be approved later. If the month after it has closed by
   then, every later close of the unit is refused for good, because `closes.making.why_not_close` finds an approved earlier
   month that is not closed, and the hourly close fails for that unit every hour. Reproduced in the audit, not fixed. The
   user's choice (option A): approving refuses a month that is over, the way submitting does; rejecting stays allowed. A month
   with no approved roster is skipped by the close, as section 5 of the architecture already says.
2. **One active solve a unit (audit lead 5).** Today at most one solve is active per unit and month (`solves.api`, line 76;
   `solves.replans.why_not`). One manager can queue a solve for every future month and hold the hospital-wide queue ahead of
   every other unit. The user's choice: at most one solve or re-plan of a unit is queued or running at a time, across all its
   months. A start while one is active is refused, naming the month that is active.
3. **No framing (audit lead 6).** No response carries `X-Frame-Options` or a `frame-ancestors` policy. Add Django's
   `XFrameOptionsMiddleware` with `DENY`, and `Content-Security-Policy: frame-ancestors 'none'` on every response Caddy
   serves (`deploy/Caddyfile`).
4. **No cross-site downloads (audit lead 7).** The file routes are plain GETs a page on another site can make a signed-in
   user's browser take: the staff list (`exportStaffList`, audited), a roster version's file (`exportRosterVersion`,
   audited), the two import templates, and the System Admin's backup download (`ops.api.download_backup`, whose names are
   predictable). Refuse each with 403 when the request says `Sec-Fetch-Site: cross-site`; a request without the header (an
   older browser, a script) is served as today.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] Approving a submitted roster of a month that is over is refused (409), in words like submit's, and nothing changes: the
      roster stays submitted, no version is made, no one is told. Rejecting it still works
- [x] The approver's page for such a roster says the month is over and offers no Approve (or shows the refusal beside it;
      **Worth your review** which)
- [x] A test of the audit's scenario: a roster submitted for May, June approved and closed, then approving May is refused and
      July's close is not blocked by May
- [x] Starting a solve or a re-plan while another of the same unit is queued or running, for any month, is refused (409),
      naming that month; a different unit's solve is not blocked; the month's own refusals stay as they are
- [x] Every response from `web` carries `X-Frame-Options: DENY`, and every response through Caddy carries
      `Content-Security-Policy: frame-ancestors 'none'` (checked on a scratch stack, and in `deploy/tests/operations.sh` if it
      fits there)
- [x] The five file routes answer 403 to `Sec-Fetch-Site: cross-site`, and serve `same-origin`, `same-site`, `none` and no
      header as today; the audit entries of the staff list and the roster file are written only for a file served
- [x] `docs/ARCHITECTURE.md`: section 5's approval paragraph says a month that is over can no longer be approved; section 4's
      Solve says one active solve a unit; section 8's Security says the framing and download rules
- [x] `docs/security/2026-11-11-security-audit.md`: the late approval and leads 5 to 7 marked fixed, with this ticket's commits
- [ ] Tests at the existing seams: the backend API suite (review, solves, the file routes, the middleware), the frontend's
      app-level suite for the approver's page, the Playwright files touched; the usual full suites and both workflows

## Comments

**Implemented on 2026-11-11,** on branch `claude/ticket-62-audit-follow-ups-103b86` (`0cac2f5`, `d4404f5`, `2b70344`,
`6cda1dd`, `2897479`, `3b2fc9e`, `89c1d66`, then this comment), from `main` at `b8095b6`. Draft pull request
[devjazzar/cp-sat-nurse-roster-app#5](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/5).

The suites ran locally under the heavy-run lock, the backend on a throwaway PostgreSQL 18 container of my own:
- the backend, on `2897479`: 3124 passed, 1 failed. The failure was `test_a_row_whose_job_is_gone_does_not_stay_active_for_good`,
  which kept a solve queued by starting a second month of the same unit, as the new rule forbids. It now uses a second unit
  (`3b2fc9e`). After that commit I reran every test file the branch touches: 451 passed;
- the frontend: `npm test` on `89c1d66`, 765 passed; `npm run build` succeeded;
- `makemigrations --check`: "No changes detected";
- the OpenAPI document was regenerated: the five file routes name a new security scheme, `SignedInForAFile`, and the
  generated client is unchanged;
- no Playwright file changed. `deploy/tests/operations.sh` gained a check that only GitHub's browser-checks workflow runs.

**What the dev stack needs:** a **rebuild** (`docker compose up -d --build`). It picks up `backend/config/settings.py`'s new
middleware and **`deploy/Caddyfile`'s new `header` line**, which reaches Caddy only when its container is recreated with the
file. There is no migration, no new dependency, and no change to compose, the `Dockerfile` or the solver.

**What was built, criterion by criterion.**
- **No late approval.**
  - `rosters.review.why_not_approve_before_checking` refuses a roster whose month is over, after "no roster waiting" and
    "approved already". The words: "This month is over, so its roster cannot be approved. Reject it with a comment, so it
    no longer waits for a decision."
  - The approve route asks it before it checks the grid. On a refusal it writes no version, no audit entry and no
    notification, and the roster stays submitted. Rejecting is unchanged.
- **The approver's page:** no page change was needed. `unit-roster.tsx` already shows `approve_refusal` beside a disabled
  Approve, so the server's words reach it as they are. `89c1d66` ties them to the button with `aria-describedby`. A page
  opened before the month ended gets the 409 in the confirming dialog, which already shows a refusal there.
- **The audit's scenario,** a month on, since the sound fixtures are June to August
  (`closes/tests/test_close.py`, `test_a_roster_left_submitted_past_its_month_cannot_be_approved_and_block_the_closes_after_it`):
  - June is left submitted, and July and August are approved;
  - on 3 August the catch-up closes July;
  - June's approval is refused;
  - on 1 September the catch-up closes August.

  Without the fix, the test fails at the approval: June is approved with a 200.
- **One active solve a unit:** `solves.models.why_not_another_month`.
  - `_what_stops_the_month` (solve start and preview) and `replans.why_not` (re-plan start and preview) ask it after the
    month's own refusals, which keep their words. It names the other month, and whether that one is a solve or a re-plan:
    "A solve of November 2026 is already queued or running. A unit solves one month at a time, so stop it or wait for it
    first." A re-plan reads "A re-plan of June 2026 …".
  - Both start routes hold the hospital settings' lock, then the unit's row `FOR UPDATE`, so two starts of one unit read it
    in turn.
  - The database constraint stays one per unit and month (see Decisions).
  - Other units are not held (`solves/tests/test_queue.py`). The queue's first-come-first-served test now runs over ER,
    ICU and a new CCU.
- **No framing:**
  - `XFrameOptionsMiddleware` sits second in `MIDDLEWARE`, before WhiteNoise, which answers its files itself and would
    otherwise skip it. `X_FRAME_OPTIONS = "DENY"` is set explicitly.
  - `deploy/Caddyfile`'s site block has `header Content-Security-Policy "frame-ancestors 'none'"`.
  - Nothing in the app frames itself. A search of `frontend/src` and `index.html` for `iframe`, frames and `embed` finds
    none, and the print page is a page of its own. The PWA's service worker has no fetch listener.
  - Tests: `ops/tests/test_spa.py` checks the SPA document, a deep link, WhiteNoise's `index.html`, `sw.js` and a hashed
    asset, an API 404, and a missing-build 404. `operations.sh` checks `/`, `/unit-roster`, `/api/health` and the
    `/metrics` refusal through Caddy.
- **No cross-site downloads:**
  - One class, `accounts.authz.SignedInForAFile`, through `for_a_file(<auth>)`, is the auth of `exportStaffList`,
    `downloadNurseImportTemplate`, `downloadSkillsImportTemplate`, `exportRosterVersion` and `downloadBackup`. A grep
    for `csv_response`, `xlsx_response`, `FileResponse` and `attachment` finds no sixth file route.
  - It answers 403 to `Sec-Fetch-Site: cross-site` before the user and the role are read, so the answer is the same
    signed out, as a nurse or as the CNO. It writes no audit entry, and for the backup it does not say whether the name
    exists.
  - It marks the request as not activity, so a refused request does not restart the 12-hour idle limit. The spec review
    caught that (`3b2fc9e`).
  - `same-origin`, `same-site`, `none` and no header are served as before.
  - The roster's print-page sheet is no file and is not refused.
- **Docs:**
  - `docs/ARCHITECTURE.md`: section 4's Solve (one active a unit, and why the constraint stays per month); section 5's
    approval paragraph and re-plan bullet; section 7's `run_solve`; section 8's Security (framing and the file routes).
  - The audit record: leads 5, 6 and 7 and the late approval are marked fixed with their commits, with a note that
    `NEEDS-VALIDATION.md` numbers them as its sections 6, 3 and 5.

**What was driven, and how.** I used my own scratch stack, `e2e/stack.sh up nr-t62` (ports 18620 and 18621), on 11 November
2026. I drove it through Caddy's HTTPS with a scratch Python client, as the seed's people, and with headless Chromium through
Playwright 1.64.1.
- **Headers through Caddy:**
  - `/`, `/unit-roster`, `/api/health` and `/assets/` carry `content-security-policy: frame-ancestors 'none'` and
    `x-frame-options: DENY`;
  - Caddy's own `/metrics` 404 carries the CSP;
  - web straight on 18620 sends `X-Frame-Options: DENY`.
- **A real frame:** a page served from `http://127.0.0.1:18630` framing `https://localhost:18621/unit-roster`. Chromium
  logged "Framing 'https://localhost:18621/' violates the following Content Security Policy directive: frame-ancestors
  'none'", and no document loaded in the frame.
- **The file routes, as Carla:**
  - the staff list and both templates: 403 with the refusal for `cross-site`, and 200 with the attachment for
    `same-origin`, `same-site`, `none` and no header;
  - signed out and cross-site: 403;
  - the database then held exactly four `nurses.exported` rows, one for each export served.
- **The backup, as the System Admin:** a real backup's name cross-site was 403, a made-up name cross-site was 403, and the
  real one same-origin was 200 with one `backup.downloaded` row.
- **A roster file, as Mona:** December's CSV cross-site was 403, and its workbook same-origin was 200, with one
  `roster.exported` row.
- **A real cross-site navigation in Chromium,** signed in as Carla: a page on `127.0.0.1` set `location.href` to
  `https://localhost:18621/api/nurses/export`. The browser showed the JSON 403 and saved no file.
- **One solve a unit, as Mona:**
  - November 2026 for ER started (201), and January 2027 was refused at once with "A solve of November 2026 is already
    queued or running. …". January's preview said the same.
  - Omar's ICU January preview had no refusal.
  - November ran for real and succeeded, and Mona submitted it.
- **The late approval:**
  - With `stack.sh clock nr-t62 21` (2 December), Hala's roster answer for November held the refusal, and her approve was
    409 with it. November stayed submitted and no `roster.approved` row was written.
  - In Chromium, Hala's "Your decision" section showed the refusal above a disabled Approve, with "Reject with this
    comment" still offered. At 375 px it fit (`scrollWidth` 375).
- **The close after it:**
  - `stack.sh fire … close_month` closed October and skipped November.
  - With the clock at 2 January, `making.catch_up` at a 2 January moment closed December for ER and ICU, past the
    refused November. `fire` alone did not close December: see "Things later tickets should know".
- **Held by hand against `better-interface`, `better-writing` and `better-accessibility`:**
  - The refusal's words match submit's and say what to do next.
  - The Approve button stays focusable (`aria-disabled`) and now carries the refusal as its description.
  - The solve refusal is an alert in place of the form.

The stack is down, its volumes and `e2e/.stack/nr-t62.*` are gone, and my PostgreSQL container is stopped.

**What was found, and fixed.**
- A refused cross-site request kept the session alive, as the idle middleware saves on every answer. It is now not
  activity, with a test that fails without the fix (`3b2fc9e`).
- The refusal beside Approve was not tied to the button, so a screen reader's user who tabbed to it heard nothing of why
  (`89c1d66`).

**Findings for you, not fixed.**
- **`stack.sh clock` moves the hospital's date, not the moment `closes.making.due` compares with the close time.** A
  month's close comes due only once its close time has passed in real time. So `fire close_month` after moving the clock a
  month on closes nothing that is not already due by the real clock. The browser checks have not needed it so far.
- **A submitted roster of a month that is over still waits** on the approvers' home until someone rejects it. The refusal
  tells them to reject it. Nothing rejects it by itself.

**What was NOT checked.**
- The whole browser suite and `operations.sh` with its new header check: GitHub's, on the pull request.
- The six parallel frontend runs: GitHub's.
- Safari and Firefox with the cross-site navigation and the frame: only Chromium was driven. Each browser that sends
  `Sec-Fetch-Site` is covered by the same header; a browser that sends none is served, as the ticket says.
- A same-site frame (a sibling host under one registrable domain): the frame check was cross-site. `frame-ancestors 'none'`
  and `DENY` refuse every ancestor, same-site included, by specification.
- A long queue with the real solver for audit lead 5's size: the change bounds a unit to one solve, so the size no longer
  turns on it.

**Decisions taken here.**
- **The constraint stays one per unit and month in the database; one per unit is checked in the code under the unit's row
  lock.** A unique index per unit would fail its migration on an installation that has two months of a unit queued at the
  moment it upgrades.
- **The cross-site guard is an auth class, not a decorator or a middleware.** It runs before the session's user is read, so
  the answer cannot tell roles apart. It is named in the OpenAPI document like `Polled` is.
- **The refusal is 403 with a JSON `detail`,** like every refusal of the API, so the app's own error handling reads it.

**Worth your review.**
- **The approver's page shows the refusal beside a disabled Approve** rather than hiding Approve. The page already did this
  for every approve refusal, so it needed no change. Hiding it would make a month that is over look like a page with no
  decision, and Reject is still the way forward.
- **The words of the late approval:** "This month is over, so its roster cannot be approved. Reject it with a comment, so it
  no longer waits for a decision."
- **The words of one solve a unit:** "A solve of November 2026 is already queued or running. A unit solves one month at a
  time, so stop it or wait for it first." "A re-plan of …" when it is one. The same-month refusal keeps its own words.
- **The roster page says which month holds the unit's solve before Solve is pressed.** The solve preview's `refusal` carries
  the sentence, and the page shows it as an alert in place of the start form, with no page change. It is read when the
  page loads. If the other month's solve ends while the page is open, the form comes back only on a reload or a change of
  month.
- **A solve stuck `queued` or `running` now holds every month of its unit,** not only its own, until its manager stops it
  or `recover_lost_jobs` ends it.
- **The cross-site refusal's words:** "This file opens only from the app's own pages, not from a link on another site." A
  person sees them only when another site sent them there.

**Review:** `code-review` against `b8095b6`, two axes in fresh subagents.
- **Standards:** no hard violations.
  - Fixed: two names, `why_not_approve_before_checking` (was `_at_all`) and the `*_for_files` auths (were `*_of_a_file`),
    and `why_not_another_month`'s untyped `unit`.
  - Kept:
    - `why_not_another_month` stays in `solves.models` beside `ACTIVE_STATES` and the constraint it complements: both
      `solves.api` and `solves.replans` import it from there without a cycle.
    - The test copies of the refusal strings stay: section 5.2 wants expected values from an independent source.
- **Spec:** every criterion is met.
  - Fixed: the idle limit (above).
  - Kept: the month-over check runs twice on an approve, once before the grid's check and once inside `why_not_approve`,
    as `why_not_decide` already did. Splitting it would leave the page's answer and the route's refusal on two different
    functions.
  - Noted: a stuck solve holds its unit (Worth your review).

**Things later tickets should know.**
- When the hardening feature adds a fuller content security policy, `frame-ancestors 'none'` must go into that one policy.
  Two `Content-Security-Policy` headers are both enforced, so a second one would not replace this line in the Caddyfile.
- A new route that answers with a file takes `for_a_file(<its auth>)` (`accounts.authz`).
- A test that needs two solves active at once needs two units now.

