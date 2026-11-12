# 45: The holidays card: the Eids and the national days proposed

**What to build:** On Holidays and Ramadan the CNO sees a card proposing, for the year shown, what the calendar knows and the year's public holidays do not yet hold: Eid al-Fitr, four days from the day after the 29th day of the Ramadan in force; Eid al-Adha, four days from Arafat Day by the calendar; National Day (23 September) and Founding Day (22 February), one day each. Each line's first day and length are editable; Add creates the named public holidays, skipping any date already entered, and the line is gone once its first day is a holiday. Nothing is stored for a proposal and nothing is dismissed. Every other role sees the page as today. Spec: `.scratch/nurse-rostering-v2/specs/ramadan-and-eid-from-the-calendar.md`.

**Blocked by:** 44 The Ramadan cards (the Ramadan in force, assembled across months)

**Status:** ready-for-agent

- [x] The hospital API answers the proposals of a year in date order, each with a name, a first day and a length, only while its first day is not a public holiday
- [x] Eid al-Fitr's first day is the day after the 29th Ramadan day in force, counting the days in force in order, so a Ramadan fixed to 30 days has its 30th day inside the Eid and one fixed to start a day late moves its Eid a day; a Ramadan with fewer than 29 days in force proposes no Eid al-Fitr
- [x] Eid al-Adha's first day is Arafat Day (9 Dhu al-Hijjah) by the calendar; National Day and Founding Day fall on their fixed dates; the lengths are four, four, one and one
- [x] Adding takes a name, a first day in the year shown and a length from 1 to 14, creates one public holiday per day under that name through the existing holiday create, each audited as `public_holiday.created`, skips dates that are holidays already, and answers how many were added and which were skipped
- [x] A proposal whose days run into January is listed on the year its first day falls in and adds its later days in the next year
- [x] Only the CNO may add (403 for every other role); the card is read by the CNO only and the page for every other role is unchanged
- [x] An added holiday reaches the solver like any public holiday (a solve input test)
- [x] The page: the card for the CNO with each line's first day and length editable, Add with its status line naming what was added and skipped, a refusal beside the field, focus after adding, the line gone afterwards, no sideways scroll at 375 px
- [x] API tests under pytest beside the public holidays' tests, including Eid al-Fitr after a shortened and a lengthened Ramadan; the frontend's app-level suite in its "holidays and Ramadan page" block; the usual full suites and `e2e/ci.sh`

## Comments

**From ticket 44 (2026-11-11).** The Ramadan in force is a card: `_card(calendar_ramadan(h), _fixed_around(year))` in
`backend/hospital/catalogue_api.py`, with `first`, `last` and `days` assembled month by month. It includes a
neighbouring month whose fixed days continue the Ramadan over the edge. A card with gaps (a list entered by hand)
counts its days, so "the 29th day in force" means the 29th of the sorted days, not `first + 28`. A card fixed to none
has `days == 0` and no first day. `calendar_ramadans(year)` in `hospital/catalogue.py` gives the calendar's Ramadans with
a day in a year; every year from 1925 to 2076 has one or two. The page's cards sit in the Ramadan section, above the
month table. The section's status line is the one the cards write to.

**Implemented on 2026-11-12,** on branch `claude/ticket-45-ramadan-holidays-card-0b299a` (`13f0d3b` the API and the page,
`980879a` the review's points, `d3c8195` the merge of ticket 46 with Add's notification, then this comment), from `main` at
`3579d76`. Draft pull request
[devjazzar/cp-sat-nurse-roster-app#20](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/20).

The full suites ran locally on `980879a`, under the heavy-run lock:
- the backend, on a throwaway PostgreSQL 18 container of my own (`nr-t45-pg`, removed): 3384 passed;
- the frontend: `npm test` 805 passed, and `npm run build` succeeded;
- `makemigrations --check`: "No changes detected". There is no migration;
- `frontend/openapi.json` matches the backend's export, and regenerating the client changed nothing.
- The solver was not touched, so its suite was left to GitHub.

After the merge of ticket 46 (`d3c8195`):
- `notifications/tests/test_events.py`, `hospital/tests/`, `solves/tests/test_input.py` and `test_authorization.py` ran
  again: 1300 passed.
- The frontend's "holidays and Ramadan page" block ran again: 37 passed.
- The OpenAPI document and the client still match the export.

**What the dev stack needs:** `docker compose up -d --build`, for the `web` code and the client. There is no migration,
no change to `deploy/compose.yaml`, the `Dockerfile`, the solver or any dependency.

**What was built, criterion by criterion.**
- **The proposals.** `GET /api/hospital/holiday-proposals?year=` is for the CNO only. It answers a list in date order of
  `{name, first, length}`, each only while its first day is not a public holiday, whatever that holiday's name.
  - A year with every proposal entered answers `[]`.
  - Every year from 1925 to 2076 answers, and a test walks them all.
- **Eid al-Fitr** starts the day after the 29th of the days in force, sorted, read through `_days_in_force`. That
  function was factored out of ticket 44's `_card`, which now uses it too.
  - The Ramadans read are those of the year shown and the year before, keyed by Hijri year. A December Ramadan whose
    29th day is the 31st has its Eid on 1 January, so the year before is read too.
  - The Eid is kept only when it falls in the year shown, so one after a Ramadan across New Year is on the next year.
  - Fewer than 29 days in force (fixed to none, or a short list) propose none.
  - Tests:
    - 2026's 30-day Ramadan 1447 puts its 30th day, 19 March, as the Eid's first;
    - started a day late, 9 February – 9 March 2027, the Eid moves to 10 March;
    - lengthened to 30 days, 7 February – 8 March, it moves to 8 March;
    - 1447 shortened by a day at its start moves to 20 March;
    - 28 days in force propose none, and nor do months fixed to none;
    - a hand list with a gap counts its 29th day, not `first + 28`;
    - a confirmation that starts in February counts toward 1446's Eid in March 2025;
    - 1452 across New Year proposes 24 January 2031 on 2031;
    - 1387 started a day late puts its Eid on 1 January 1968;
    - 2033 holds two Eid al-Fitrs.
- **Eid al-Adha** starts on Arafat Day, 9 Dhu al-Hijjah, by the calendar (`calendar_arafat_days(year)` in
  `hospital/catalogue.py`); 2039 holds two. **Founding Day** is on 22 February and **National Day** on 23 September. The
  lengths are 4, 4, 1 and 1.
- **Adding:** `POST /api/hospital/holiday-proposals?year=` with `{name, first, length}`, for the CNO only.
  - The first day must be in the year asked for, refused on `first`. The length runs from 1 to 14, refused on `length`.
    The name is the holidays' own `Name`.
  - It creates one public holiday a day under the name, through the holiday create. That is now
    `_create_holiday(request, day, name)`, the body of the existing endpoint, shared by both. Each day is audited as
    `public_holiday.created`.
  - A date that is a holiday already is skipped. So is one another user creates in the meantime: the save's savepoint
    refuses it and it is counted as skipped.
  - It answers `{added: [dates], skipped: [dates]}`.
  - Days running into January are added in the next year. Days past 2076 are refused on `length`.
- **Ticket 46's notification:**
  - The hand create calls `_holidays_changed` for its one day, as 46 wrote it.
  - Add calls it once, after its loop, with every day it added, so a four-day Eid tells a manager once a month.
  - Nothing is called when every day was skipped.
  - Two tests beside ticket 46's hold this in `notifications/tests/test_events.py`. One is six days across June and July
    with one skipped: one note each for June and July. The other is an Add of only skipped days: no note.
- **Roles:** every other role gets 403 on both endpoints, and `test_authorization.py`'s walk covers them too.
- **The solver:** `solves/tests/test_input.py` adds Eid al-Adha through the endpoint for eight days from 26 May 2026. June's
  solve input then holds 1 and 2 June among its `public_holidays`.
- **The page,** for the CNO only: a card, "Proposed by the calendar", in the Public holidays section, between the table and
  "Add a public holiday".
  - Each line is a fieldset named by the holiday, with "From Tuesday, 9 March 2027, 4 days.", the fields "First day" and
    "Days", and an Add button.
  - Two of one Eid in a year are named by their month ("Eid al-Fitr in January 2033").
  - The status line is the section's: "Eid al-Fitr is added on 3 days from 9 March 2027. 10 March 2027 was a holiday
    already and is left as it was.", or "Founding Day adds no day: 22 February 2027 is a holiday already."
  - A refusal shows beside its field, with focus on it. The page checks the year and the 1 to 14 itself first.
  - When the line goes, focus moves to the next line's first day, or to the card's heading when none is left.
  - When the CNO changed the first day, the line stays as the calendar gives it, its fields back to the proposal, with
    focus on Add.
  - The proposals are read again after any holiday is added, changed or removed by hand, and after any Ramadan
    confirmation, fix or "Use the calendar". Eid al-Fitr follows the Ramadan.
  - Every other role sees the page as before, with no request for the proposals.
- **Tests at the seams:**
  - `backend/hospital/tests/test_holiday_proposals.py`: 39 tests, counting each parameter;
  - the solve input test, and the two notification tests;
  - twelve new tests (counting each case) in the frontend's "holidays and Ramadan page" block, and the reader's test extended.

**What was driven, and how.** I used my own scratch stack, `e2e/stack.sh up nr-t45` (seeded) on port 18450, on
2026-11-12, in the app's built-in Chromium, on `980879a`. As `carla`, the CNO, on Holidays and Ramadan:
- **2027:** the card listed Founding Day 22 February, Eid al-Fitr 9 March, Eid al-Adha 15 May and National Day 23
  September.
- **Add with a day skipped:** I entered 10 March 2027 by hand as "Entered by hand", then pressed Add on Eid al-Fitr.
  - The status line read "Eid al-Fitr is added on 3 days from 9 March 2027. 10 March 2027 was a holiday already and is
    left as it was.";
  - the table showed 9, 11 and 12 March as Eid al-Fitr, and 10 March kept its own name;
  - the line was gone, and focus was on "First day of Eid al-Adha".
- **Add with a changed first day and length:** Eid al-Adha from 16 May for 6 days.
  - The status line read "Eid al-Adha is added on 6 days from 16 May 2027.";
  - 16 to 21 May were in the table;
  - the line stayed with 15 May and 4, and focus stayed on "Add Eid al-Adha".
- **A refusal:** 15 days on National Day was refused beside Days, with "Enter a number of days from 1 to 14.", with focus
  on it and the field marked invalid.
- **At 375 px:** the page's `scrollWidth` was 375, and the card's fields stacked.
- **2028, the Eid moves with the Ramadan:** Eid al-Fitr was proposed from 26 February. I confirmed Ramadan 1449 a day late,
  29 January – 26 February, on its card. The line read 27 February with no reload, and the Ramadan section's status line
  said it was confirmed.
- **The audit log** in the database had ten `public_holiday.created` entries by `carla`: 9 to 12 March and 16 to 21 May.
- **As `Amal`, a staff nurse:** the page was as before, with no card and no request for the proposals. A `fetch` of both
  endpoints answered 403.

The stack, its volumes and its image are gone, and the lock is released.

**What was found, and fixed.**
- **The review's Standards axis:** see Review.
- **Ticket 46 landed first.** Its notification sat in the create endpoint's body, which this ticket had moved into
  `_create_holiday`. The merge keeps it in the endpoint and adds the single call to Add, with two tests. A test removed
  the call and saw the June-and-July test fail.

**Findings for you, not fixed.**
- **A test that fails for 20 seconds a day.** `ops/tests/test_logs.py::test_the_queues_command_line_logs_what_it_would_print`
  failed on GitHub on `980879a` and passed on the rerun.
  - `ops.TechnicalSettings.close_time` defaults to `time(0, 30)`. Django's system check warns about a fixed time default
    (`fields.W161`) only when it is within 10 seconds of now. The run reached that test at 00:30:35 UTC, so the warning
    went to stderr and the test's `stderr == ""` failed.
  - Any run between about 00:29:50 and 00:30:10 UTC fails it. That is not this ticket's to fix. The fix is a callable
    default, or silencing W161 for that field.

**What was NOT checked.**
- **Some cases were not driven on the page:** a year with two of one Eid, a proposal running into January, a refusal from
  the API rather than the page, and the empty card. The API and frontend tests cover them.
- **Two CNOs adding at once:** the skip on a concurrent insert is reasoned from the savepoint, not tested concurrently.
- **The 2033 and 2039 dates** come from the Umm al-Qura tables (hijridate), which no announcement has reached yet. The
  2025 to 2027 dates match Saudi Arabia's announced ones.
- **The card in a screen reader:** names, descriptions and the status line were read through the accessibility tree and
  tests only.
- **The merge of ticket 46 was not driven on a stack.** Its tests ran.

**Decisions taken here.**
- **Endpoints:** `GET` and `POST /api/hospital/holiday-proposals`, both with `?year=` as the holidays' list takes it. The
  year is the one shown, which the first day must fall in.
- **The answer to Add** lists the days added and skipped, not counts, so the status line can name them.
- **The shared create** is a helper, as ticket 44's `_fix_month` is, not a call to the endpoint function.
- **A concurrent insert is skipped,** not refused.
- **Days past 2076 are refused** on `length`, since the holidays' dates keep to the years the calendar covers.
- **Eid al-Adha needs no Ramadan:** it comes straight from the calendar, as the spec says, and no CNO confirmation moves it.

**Worth your review.**
- **Where the card sits:** in the Public holidays section, between the table and "Add a public holiday", writing to that
  section's status line. Ticket 44's note put "the cards" in the Ramadan section. These proposals are holidays and land
  in the holidays' table, so they sit with them.
- **A line whose first day the CNO changed stays.** The spec's rule is "shown while its first day is not a public holiday".
  Eid al-Adha added from 16 May leaves the 15 May line showing. I kept the spec's rule; the CNO can ignore the line.
  - The alternative: hide a line once any of its proposed days is a holiday.
- **The card's words:**
  - the heading "Proposed by the calendar";
  - the description "The Eids by the Umm al-Qura calendar and the Ramadan in force, and the national days, until their
    first day is a holiday. Change the first day or the days to follow the year's circular.";
  - the line "From Tuesday, 9 March 2027, 4 days.";
  - the fields "First day" and "Days", and the button "Add".
- **The status line's words:**
  - "Eid al-Fitr is added on 3 days from 9 March 2027. 10 March 2027 was a holiday already and is left as it was.";
  - "Founding Day adds no day: 22 February 2027 is a holiday already.";
  - the refusals "This is not in 2027. Go to that year to add it.", "Enter a number of days from 1 to 14.", "This runs
    past 2076, the last year the calendar covers."
- **A year with no proposal left:** the API answers `[]`. The card stays, saying "Every holiday the calendar proposes for
  2027 is entered.", so the CNO sees it was checked rather than the card vanishing.
- **Focus after Add:** to the next line's first day, or to the card's heading when none is left. When the line stays, it
  stays on Add.
- **"Proposal" in the API's names** (`/holiday-proposals`, `HolidayProposal`). `GLOSSARY.md` uses "proposal" for a swap.
  The spec says "proposes". A glossary line, or a rename to "suggested holidays", is yours to decide.
- **Founding Day is proposed for every year back to 1925,** though it was first kept in 2022. The spec names no first year.

**Review.** `code-review` was run against `3579d76`, both axes in fresh sub-agents.
- **Spec axis:** nothing missing and no defect. It checked:
  - which Ramadans feed an Eid;
  - the 29th day over the sorted days;
  - the New Year crossings;
  - the ends 1925 and 2076;
  - the savepoint under a concurrent Add.
  The extras it listed (the 2076 refusal, the page's own checks, the empty line, Eids named by month, the re-reads) are
  under Decisions or Worth your review.
- **Standards axis:** no hard violation. Fixed:
  - one save for the holiday's taken date (`_save_holiday`), shared by create and update;
  - the proposals built as their schema and sorted by `first`, not as tuples sorted by position;
  - one `readProposalsAgain` on the page instead of six scattered invalidations;
  - an error message no longer named `days`;
  - the 2033 and 2039 test dates now name their source.
  Kept:
  - the pre-check beside the concurrent-insert catch, which saves a failed insert per known holiday;
  - "proposal" in the names (Worth your review).

**Things later tickets should know.**
- **Every holiday create goes through `_create_holiday`** in `hospital/catalogue_api.py`. The caller holds the transaction
  and calls `_holidays_changed` once for all the days it created.
- **`_days_in_force(ramadan, fixed)`** is the sorted days a Ramadan has in force. Anything that needs its nth day should
  read it there.
- **`calendar_arafat_days(year)`** gives the Arafat Days in a Gregorian year.
- **The page's `readProposalsAgain`** must be called by any new write to the holidays or the Ramadan days.
