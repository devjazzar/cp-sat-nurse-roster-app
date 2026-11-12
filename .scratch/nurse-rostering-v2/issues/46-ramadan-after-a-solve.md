# 46: After a solve: warned and told when the dates change

**What to build:** When a month's Ramadan days or public holidays change after a solve, a unit manager's draft is warned that they changed since its solve, blocking nothing, as after a correction to leave; a submitted roster shows the reviewer that something changed since it was submitted; and every unit manager whose unit has a draft, a submitted or an approved roster in a month touched is told once, naming the month, from the transaction that makes the change. Approved cells, versions and pins stay; the next solve or re-plan uses the dates as they stand, as today. The change may come from the month fixed or returned to the calendar in the table, from a holiday created, changed or removed, or from the cards of tickets 44 and 45, which write through those same operations. Spec: `.scratch/nurse-rostering-v2/specs/ramadan-and-eid-from-the-calendar.md`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] The draft's "changed since its solve" list gains two month-level changes, the month's Ramadan days and its public holidays, each the stored solve input's list compared with the month as it stands, carried with no nurse; the per-nurse changes are as before
- [x] The draft page words them ("The Ramadan days of March 2027 changed since this draft was solved", and the same for the public holidays); submit goes through with the warning and the check on submit runs on the month as it stands, as today
- [x] A submission records the month's Ramadan days and public holidays at submit beside the nurses it records (a migration), and the submitted roster's "changed since it was submitted" compares them too
- [x] One new notification kind, sent to the manager of every unit with a draft, submitted or approved roster in a month whose Ramadan days or public holidays changed, once per change per month, inside the transaction that makes the change, after its audit entry; its payload is the month and its words name the month and say which changed; the one who made the change is not a recipient, nor is a manager with no roster in the month
- [x] The existing per-month fix and "Use the calendar", and the holiday create, change and remove, send it; a change that leaves the month's dates as they were sends nothing
- [x] API tests under pytest beside the draft's "changed since" tests and the notification events' tests: a draft and a submitted roster warned after a Ramadan change and after a holiday change, unwarned when nothing moved, submit going through; the manager of a unit with each kind of roster told once per month, a manager with no roster not told, the CNO not told
- [x] The frontend's app-level suite: the draft page's new warning line and the notification's words; the usual full suites and `e2e/ci.sh`

## Comments

**From ticket 44 (2026-11-11).** Every Ramadan write goes through `_fix_month` in `backend/hospital/catalogue_api.py`:
the per-month fix and the whole-Ramadan confirmation (`PUT /api/hospital/ramadans/{hijri_year}`) both call it. "Use the
calendar" (`unfix_ramadan_month`) still writes on its own. `_fix_month` audits `ramadan_dates.changed` only when what is
in force changes, so a notification beside that `record` call sends nothing for an unchanged month. A confirmation runs
in one transaction and can touch three or four months, including one in the next or the previous year (Ramadan 1452
writes December 2030 and January 2031). That makes one notification per changed month with a roster.

**Implemented on 2026-11-12,** on branch `claude/ticket-46-ramadan-after-a-solve-51efd4` (`28045dc` the build, `11c73f4` the
review's points, `f7a02db` this comment, then the spec's sentence on the manager's page and the advisor's points), from `main` at `3579d76`. Draft pull request
[devjazzar/cp-sat-nurse-roster-app#21](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/21).

The full suites ran locally under the heavy-run lock:
- the backend on a throwaway PostgreSQL 18 container of my own (`nr-t46-pg`, removed): 3343 passed, 1 failed. The failure
  was `test_replan.py`'s new test, whose import the review's tidy-up had dropped. Once restored, `test_replan.py`,
  `test_events.py` and `test_reading.py` passed again (96).
- the frontend: `npm test` 796 passed, and `npm run build` succeeded;
- the solver was not touched and was not run locally. GitHub ran it.
- `makemigrations --check`: "No changes detected".
- `frontend/openapi.json` matches the backend's export, and regenerating the client changed nothing after `28045dc`.
- GitHub's two workflows were green on `28045dc`, every job: solver, backend, frontend with its six runs, image, and the
  browser checks.

**What the dev stack needs:** `docker compose up -d --build`. It brings two migrations, which run at start:
- `rosters` 0006 adds `Submission.dates_at_submit`, nullable, with no backfill;
- `notifications` 0010 adds the event choice only.

There is no change to `deploy/compose.yaml`, the `Dockerfile`, the solver or a dependency.

**What was built, criterion by criterion.**
- **The draft's changes since its solve.** `solves.input.changes_since` takes `month_dates=True` from the roster page and
  from a submission's `new_since`. With it, the list gains `{"hospital_id": "", "what": "ramadan_days"}` and
  `"public_holidays"` when the stored list differs from the month as it stands.
  - Both sides are sorted before comparing, since the holiday query has no guaranteed order.
  - A list is compared only when the stored input holds it.
  - The per-nurse changes are unchanged. `DraftChange.what` gains the two values.
- **The page's words.** On the manager's page, `changeSays(change, month, since)` gives the spec's sentences: "The Ramadan
  days of June 2026 changed since this draft was solved" and "The public holidays of June 2026 changed since this draft was
  solved". On an approved roster they say "since this roster was solved". Both sit under the existing heading "This draft
  was solved before these changes:".
  - The approvers' page gives the short form, "The Ramadan days of June 2026 changed", and adds ", since it was submitted"
    as for any change.
  - Nothing blocks. Submit runs the existing check on the month as it stands, since any change makes `_checked` score the
    grid again.
- **The submission records the dates.** `Submission.dates_at_submit` holds `{"ramadan_days": [...], "public_holidays":
  [...]}`, read from the same `assemble` as the nurses. `new_since` compares them, so the CNO's home flag ("Something has
  changed since it was submitted") turns on for them too.
  - It is null on a submission made before the migration, and such a submission compares no dates. Otherwise every
    waiting roster in a month with a holiday would light up on deploy.
- **The notification.** `Event.MONTH_DATES_CHANGED` (`month_dates_changed`), sent by
  `notifications.sending.month_dates_changed(months, what, by)`.
  - Recipients: the manager of every unit with a roster in that month, whatever its state, never `by`.
  - Payload: `unit_id`, `month`, `what` and `by`, all identifiers, as every event's is.
  - Words: "Carla Haddad changed the Ramadan days of January 2027. Check the ICU roster for that month: it was planned on
    the dates before." A holiday change says "public holidays" instead.
  - Link: the manager's own roster page for the month.
  - Bell only, with no push: it has no deadline (ADR 0012).
- **Who sends it, inside the transaction and after the audit entry:**
  - `_fix_month`, which serves the per-month fix and a Ramadan confirmed, once a month;
  - `unfix_ramadan_month` ("Use the calendar");
  - the holiday create and remove;
  - the holiday change, for both the old and the new month when the date moved.
  - It compares the dates, not the audit, so no notification goes out when the dates are as they were. That covers three
    writes that are audited but move no day:
    - fixing a month to the calendar's own days;
    - "Use the calendar" on a month fixed to the calendar's days;
    - a holiday renamed.
- **Nothing else moves.** No cell, version or pin is touched. A re-plan's end does not compare the month's dates (see
  Worth your review).
- **Tests:**
  - `rosters/tests/test_review.py` `TestTheMonthsDates` (6):
    - a draft warned after a Ramadan change, and after a holiday change, and submitting;
    - unwarned when nothing moved;
    - a submitted roster's `new_since` and the home flag;
    - a change warned of before the submit is not new;
    - an old submission with no recorded dates.
  - `notifications/tests/test_events.py` `TestMonthDatesChanged` (6):
    - a draft, a submitted and an approved roster's managers are told once each, with the words and the link;
    - NICU's manager with no roster, the CNO, the Deputy CNO and a nurse are not told;
    - a holiday created, moved and removed;
    - unchanged dates tell nobody;
    - a holiday moved across months tells both months;
    - a confirmation across February and March tells each month once;
    - confirming the calendar's own dates tells nobody.
  - `rosters/tests/test_replan.py`: a Ramadan day and a holiday changed while a re-plan runs still let its roster in. I
    checked that this test fails with `month_dates` on by default.
  - Frontend, `app.test.tsx` (3):
    - the draft's warning lines with Submit enabled;
    - the approver's line with ", since it was submitted";
    - the notification's words and link.

**What was driven, and how.** My own scratch stack, `e2e/stack.sh up nr-t46` (seeded), in the app's built-in browser, on
2026-11-12:
- **As `carla`, the CNO:** I added a holiday on 3 December 2026, where ER and ICU have approved rosters, and fixed January
  2027's Ramadan days to 30–31 January, where ICU had a draft. Her own bell stayed empty.
- **As `omar`, ICU's manager:** two unread notifications, with the words above for each month. "Open the roster" led to
  `/roster?month=2027-01`.
  - The draft read "This draft was solved before these changes: The Ramadan days of January 2027 changed". That was before
    the page took the spec's full sentence; the new words are covered by the frontend test only.
  - Submit went through.
- **As `carla` again:** I added a holiday on 1 January 2027.
  - ICU's submitted roster read "The Ramadan days of January 2027 changed | The public holidays of January 2027 changed,
    since it was submitted".
  - Her home said "Something has changed since it was submitted."
  - At 375 px, the page's `scrollWidth` was 375.
- **The database** held exactly these notifications:
  - `mona` for December's holidays;
  - `omar` for December's holidays;
  - `omar` for January's holidays;
  - `omar` for January's Ramadan days.
  
  ER has no January roster, so `mona` was not told of January.

The stack, its volumes and its image are gone, and the lock is released.

**What was found, and fixed.**
- **Ticket 44's comment says a notification beside `_fix_month`'s `record` call sends nothing for an unchanged month.**
  That is not quite so: the audit also fires when only who decides changes (calendar to CNO, or back). The notification
  compares the dates instead, with the three tests above.

**What was NOT checked.**
- A holiday moved across months, a removal, and a confirmation across two months were not driven; the API tests cover them.
- The notification in a screen reader: it is an existing list item with new words.
- The full backend suite after `11c73f4`: the changed files ran again, and GitHub runs everything.
- The approved page's "since this roster was solved" is not covered by a test of its own; it is the same function with
  the state's word.
- The screens against `better-interface`, `better-writing` and `better-accessibility`, held by hand:
  - The lines are plain list items in the existing `role="alert"` box.
  - The notification is an existing list item with its link "Open the roster".
  - The month is named in full, and there is no colour beyond the box's.
  - At 375 px, nothing scrolls sideways.
  - No skill was run against them.

**Decisions taken here.**
- **`changes_since` opts in** (`month_dates=True`) rather than opting out, so any other caller keeps today's behaviour.
- **The payload carries `unit_id`, `what` and `by` beside the month.**
  - `unit_id`: a manager manages one unit (`Unit.manager` is one-to-one), so the words can name the unit's roster and the
    link follows the existing rules.
  - `what`: so the words can say which dates changed.
- **An approved roster shows the warning too.** Its page already lists changes since its solve under "This roster was
  solved before these changes", and the two new lines follow that list.

**Worth your review.**
- **The words of the draft's line.** The page uses the spec's sentence, "The Ramadan days of March 2027 changed since this
  draft was solved", under the heading "This draft was solved before these changes:", so it says "solved" twice. A
  shorter "The Ramadan days of March 2027 changed", as the approvers' page has, would read better under that heading. It
  is one argument at the call in `roster.tsx`.
- **A month already over is told too.** A holiday entered late, such as National Day added after September, tells the
  managers of that month's rosters, approved ones included. That follows the ticket's "every unit manager whose unit has
  a … roster in a month touched".
- **The notification's kind and words.** `month_dates_changed`, worded "Carla Haddad changed the Ramadan days of January
  2027. Check the ICU roster for that month: it was planned on the dates before."
  - It names who changed them, as every other notification does.
  - It says what to do without assuming a state, since a submitted roster can only be read.
- **A confirmation across several months is told one notification per month**, as the ticket says: a manager with
  rosters in both February and March gets two, each naming its month.
- **A re-plan is not made outdated by a date change while it runs.** The spec says nothing else moves, and a re-plan's
  outdated check is about the nurses, leave, pins and the version in force (section 5). Its roster goes in force, and the
  manager, told of the change, re-plans again. If you would rather such a re-plan be kept in the history as outdated, it
  is one argument (`month_dates=True`) in `solves/replans.py`.
- **The migration's shape.** One nullable JSON field, `dates_at_submit`, in the solve input's own key names, rather than
  two fields. It has no backfill, because the dates at a past submit are not known.

**Review.** `code-review` against `3579d76` found no breach of a documented standard and no missing requirement.
- **Fixed:**
  - the two switches on the kind of date became one map on each side (`MONTH_DATES_SAY`); an unknown value now reads
    "dates" rather than "Ramadan days";
  - `CHANGE_SAYS` no longer carries entries it never shows;
  - the notification's docstring now says how it is called;
  - imports are in order.
- **Kept:**
  - the two names are spelled out in four places, the enum, `MONTH_DATES`, the API's `Literal` and the frontend type,
    with a comment linking them. Importing the enum into `solves.input` would tie the solve input to the notifications
    module.
  - the payload beyond the month, and the warning on an approved roster (see Decisions).
- **Raised and not mine to fix:** if ticket 45's Add calls the holiday create once per day, a four-day Eid would tell each
  manager four times (see below).

**Things later tickets should know.**
- **Ticket 45's Add must call `_holidays_changed(request, *days)` (`hospital/catalogue_api.py`) once with every day it
  created.** The notification is in the endpoint bodies, not in `_write_holiday`. An Add that writes rows itself tells
  nobody; one that calls the create per day tells a manager once per day. Ticket 45 was not on `main` when this merged. A
  hand-over note is in the sessions' shared notes (`ticket-46-to-45-holiday-notification.md`), and the ticket 45 session
  was sent the same.
- **A new month-level change** goes in `MONTH_DATES` (`solves/input.py`), `DraftChange.what`, `MonthDates` and the frontend's
  `MONTH_DATES_SAY`.

**Reviewed by the user (2026-11-12):** all six points kept as built.
- The draft's line keeps the spec's sentence ("… changed since this draft was solved") under its heading.
- The notification's words as built.
- A Ramadan confirmed across two months tells a manager with rosters in both once for each month.
- A re-plan still goes into force when a date changes while it runs; the manager is told and re-plans again.
- A month already over is told too.
- The submission's dates are one nullable field holding both lists, with no backfill.
