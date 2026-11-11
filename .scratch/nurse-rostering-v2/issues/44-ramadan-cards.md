# 44: The Ramadan cards: confirm or shift a whole Ramadan

**What to build:** On Holidays and Ramadan the CNO sees, above the month table, one card per Ramadan with a day in the year shown ("Ramadan 1448: 8 February – 8 March 2027, 29 days. The calendar's."), its first and last day prefilled from the Umm al-Qura calendar and editable. Confirm fixes every Gregorian month the confirmed Ramadan touches, in the next or the previous year too, exactly as fixing each month by hand would, and the card then reads "The CNO: 9 February – 9 March 2027. The calendar says 8 February – 8 March." in plain text. Confirming the calendar's own dates still fixes the months. The month table and "Use the calendar" stay; every other role sees the page as today. Spec: `.scratch/nurse-rostering-v2/specs/ramadan-and-eid-from-the-calendar.md`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] The hospital API answers the Ramadans of a year: every Ramadan with at least one day in that Gregorian year, in date order, named by its Hijri year; none, one or two, and one across New Year listed on both years
- [x] Each card carries the days in force assembled month by month (first day, last day, count), whose they are ("the calendar's" when every month touched is derived, "the CNO" when any is fixed), and the calendar's first and last day
- [x] Confirming takes a first and a last day and fixes every month from the first day's to the last day's with the confirmed days that fall in it, through the existing per-month fix, under its lock, with one `ramadan_dates.changed` audit entry per month whose fixed dates change and none for a month unchanged
- [x] A month the calendar gave Ramadan days to that the confirmed range no longer touches is fixed to no days
- [x] Confirming the calendar's own dates writes fixed rows for every month touched; confirming again overwrites the earlier confirmation in every month touched
- [x] Refused beside the field: a last day before the first, a day outside the years the calendar covers, more than about 35 days between the two
- [x] Only the CNO may confirm (403 for every other role); the cards are read by the CNO only and the page for every other role is unchanged
- [x] The card's derivation is the solver's own calendar module, imported read-only as the month derivation is today
- [x] `hijridate` gets an upper bound on its major version in the solver's dependencies and the lock file, and a line in `docs/ARCHITECTURE.md` section 11
- [x] The page: the cards for the CNO with confirm as prefilled, shifting a day, the words after confirming, a refusal beside the field, the status line and focus after confirming, no sideways scroll at 375 px
- [x] API tests under pytest beside the Ramadan months' tests; the frontend's app-level suite in its "holidays and Ramadan page" block; the usual full suites and `e2e/ci.sh`

## Comments

**Implemented on 2026-11-11,** on branch `claude/ticket-44-ramadan-cards-2706dd` (`8e13a21` the API, `df3bf2f` the page,
`aea6dd2` the review's points, then the refusal's words and this comment), from `main` at `e8b1308`. Draft pull request
[devjazzar/cp-sat-nurse-roster-app#15](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/15).

The full suites ran locally on `aea6dd2`, under the heavy-run lock:
- the backend, on a throwaway PostgreSQL 18 container of my own (`nr-t44-pg`, removed): 3232 passed;
- the solver: 603 passed;
- the frontend: `npm test` 778 passed, and `npm run build` succeeded;
- `makemigrations --check`: "No changes detected". There is no migration;
- `frontend/openapi.json` matches the backend's export, and regenerating the client changed nothing.

The refusal's words changed after that run. `test_ramadan_cards.py` and `test_ramadan.py` ran again on the change: 84
passed. GitHub's two workflows were green on `df3bf2f` (backend, frontend with its six runs, image, solver, browser
checks).

**What the dev stack needs:** `docker compose up -d --build`, for the `web` code and the client. There is no migration
and no change to `deploy/compose.yaml` or the `Dockerfile`. `uv.lock` changes only in the `hijridate` specifiers, so
`hijridate` 2.6.0 is still what is installed.

**What was built, criterion by criterion.**
- **The Ramadans of a year.** `GET /api/hospital/ramadans?year=` is for the CNO only. It reads the solver's month
  derivation (`derived_ramadan_dates` → `nurse_roster.calendar.month_info`) from December of the year before to January
  of the year after, cuts the days into unbroken runs, and keeps each run with a day in the year. The list is in date
  order and each card is named by its Hijri year. Tests cover 2027 (one), 2030 (1451 and 1452), and 2031 (1452 again,
  the same card as on 2030, then 1453).
  - **"None" never happens.** A Hijri year is eleven days shorter than a Gregorian one, so every year from 1925 to 2076
    holds one or two Ramadans. A test sweeps all 152 years and finds only 1 or 2. There is no "none" case to show.
- **Each card** carries:
  - `first`, `last` and `days`: the days in force, assembled month by month;
  - `source`: `derived` when every month read follows the calendar, `fixed` when any is fixed;
  - `calendar_first` and `calendar_last`.
  - The months read are the calendar's Ramadan months, plus a neighbouring month whose fixed days continue the Ramadan
    over the edge. For the month before, that means its last fixed day is that month's last day; for the month after,
    its first fixed day is the 1st.
  - A card whose months are all fixed to none has `first` and `last` null and 0 days. A hand-entered list with a gap
    counts its days.
- **Confirming:** `PUT /api/hospital/ramadans/{hijri_year}` with `{first, last}`, for the CNO only.
  - It writes every month from the first day's to the last day's, the months the card read, and any neighbour it read.
  - Each month gets the confirmed days that fall in it, through `_fix_month`. That is the body of the existing per-month
    fix, now shared by both endpoints. It locks the row with `select_for_update` and audits `ramadan_dates.changed` only
    when what is in force changes.
  - Everything runs in one transaction, with the months taken in order.
  - Tests:
    - confirming the calendar's own dates writes fixed rows for February and March;
    - a shift by a day writes each month's share;
    - a day moved into January is fixed there;
    - March, once the range leaves it, is fixed to none;
    - 1452 across New Year writes December 2030 and January 2031;
    - confirming again overwrites, and January, which held a day from the first confirmation, is fixed to none;
    - one audit entry per changed month, and none for a month that was already right.
- **Refused beside the field, nothing written:**
  - a last day before the first (on `last`);
  - more than 35 days, counted inclusively (on `last`): 35 is accepted and 36 refused;
  - a day outside 1925–2076: the existing `IsoDate` refuses it on its own field;
  - a range that does not touch the calendar's Ramadan at all (on `first`). See Decisions.
  - An unknown Hijri year, or one beyond the whole years the calendar covers (1342, 1500, 1501), is a 404.
- **Roles.** Every other role gets 403 on both endpoints, and `test_authorization.py`'s walk now covers them too. The
  page asks for the cards only for the CNO. A reader's test checks that no request goes out and no card is shown.
- **The derivation** is the solver's own calendar module, imported read-only as before; the solver is unchanged. A test
  holds each card's calendar days to `month_info(...).ramadan_days` for five years.
  - `hijridate` is called directly in `hospital/catalogue.py`, but only to name a run by its Hijri year
    (`Gregorian(...).to_hijri()`) and to find a Hijri year's Gregorian year for a confirmation.
- **`hijridate`** is `>=2.6.0,<3` in `solver/pyproject.toml` and, since the backend now imports it, in
  `backend/pyproject.toml` too; `uv.lock` matches. Section 11 of `docs/ARCHITECTURE.md` has the line.
- **The page.** For the CNO, above the month table, there is one card per Ramadan:
  - a heading "Ramadan 1448";
  - the line "8 February – 8 March 2027, 29 days. The calendar's.";
  - First day and Last day fields, prefilled;
  - a Confirm button.
  - After confirming, the line reads "The CNO: 9 February – 9 March 2027, 29 days. The calendar says 8 February – 8
    March." in plain muted text. The section's status line says "Ramadan 1448 is confirmed: 9 February – 9 March 2027."
  - Focus stays on Confirm.
  - Both lists, the months and the cards, are read again for every year, since a confirmation can write into the next
    year.
  - A refusal shows beside its field, with focus on it.
  - At 375 px the fields stack and nothing scrolls sideways.
  - The month table and "Use the calendar" are unchanged.
- **Tests at the seams:**
  - `backend/hospital/tests/test_ramadan_cards.py`: 44 tests;
  - eight new tests in the frontend's "holidays and Ramadan page" block, and the reader's test extended;
  - two of the month form's tests now look for "First day" and "Last day" inside their own card, since the cards have
    fields of those names.

**What was driven, and how.** I used my own scratch stack, `e2e/stack.sh up nr-t44` (seeded) on port 18440, on
2026-11-11, in the app's built-in Chromium. As `carla`, the CNO, on Holidays and Ramadan for 2027:
- **The card at first:** "Ramadan 1448 / 8 February – 8 March 2027, 29 days. The calendar's.", with the fields
  prefilled.
- **Confirm as prefilled:**
  - the status line read "Ramadan 1448 is confirmed: 8 February – 8 March 2027.";
  - focus was on "Confirm Ramadan 1448";
  - the card read "The CNO: 8 February – 8 March 2027, 29 days.";
  - February and March turned to "The CNO", with "The calendar says: 8 to 28" and "1 to 8".
- **Shifted to 9 February – 9 March:**
  - the card read "The CNO: 9 February – 9 March 2027, 29 days. The calendar says 8 February – 8 March.";
  - the months read "9 to 28" and "1 to 9", and January stayed with the calendar.
- **The audit log** in the database had four `ramadan_dates.changed` entries by `carla`: February and March, twice.
- **The 2026 dates** were refused beside First day, which was marked invalid and had focus.
- **At 375 px:** the page's `scrollWidth` was 375, and the fields stacked.
- **As `Amal`, a staff nurse:** the page was as before, with the table and no cards. The network log had no request to
  `/api/hospital/ramadans` from that page.

The stack, its volumes and its image are gone, and the lock is released.

**What was found, and fixed.**
- **The review found that a range in the wrong year went through.** `PUT /ramadans/1448` with 2026's dates would fix
  1447's months and empty 1448's. Such a range is now refused (see Decisions).
- **A neighbouring month's fixed days counted even when they did not continue the Ramadan,** such as a hand-entered 30
  January or 2 April. Now they count only when they reach the edge, as the spec's "continue it" says.
- **The wrong-year refusal named ISO dates,** which wrapped mid-date at 375 px. It now says "These days do not touch
  Ramadan 1448, which the calendar puts at 8 February – 8 March 2027."

**What was NOT checked.**
- The 1925 and 2076 ends were tested through the API's sweep but not driven on the page. Neither was a Ramadan across
  New Year, which the API and frontend tests cover.
- Two CNOs confirming at once: the locks are the per-month fix's, taken in month order, but no concurrent test was run.
- The card in a screen reader: names, descriptions and the status line were read through the accessibility tree and
  tests only.
- GitHub's run on the last two commits: `aea6dd2` and the refusal's words. The merge waits for both to be green.

**Decisions taken here.**
- **Endpoints:** `/api/hospital/ramadans` (the cards) and `/api/hospital/ramadans/{hijri_year}` (confirm, a `PUT`, as
  the month fix is). They sit beside `/ramadan`, not under it, so no path collides with `/ramadan/{month}`.
- **A confirmation is keyed by the Hijri year,** so "a month the calendar gave days to that the range no longer
  touches" has a Ramadan to refer to.
- **The 35 days are counted inclusively:** 35 is accepted, 36 is refused on Last day with "That makes 36 days. A
  Ramadan has 29 or 30, so at most 35 are taken."
- **A range that does not touch the calendar's Ramadan is refused** on First day. One day of overlap is enough.
- **Prefill after confirming:** the fields show the days in force, falling back to the calendar's when none are in force.
- **The card line after confirming keeps the count:** ", 29 days".
- **The calendar's words after a confirmation appear only when they differ.** When the CNO confirmed the calendar's own
  dates, the card reads "The CNO: 8 February – 8 March 2027, 29 days." with no "The calendar says".
- **Confirm is never disabled while sending.** A second press is ignored instead, so focus stays on the button. The
  month forms disable theirs.
- **`hijridate` is called by the backend directly,** and so declared in its dependencies with the same bound. It is used
  only to name and to find a Ramadan; the days stay the solver's.

**Worth your review.**
- **The wrong-year refusal is a fourth refusal the spec does not list.** The spec expects the 35-day bound to catch a
  wrong year, but it catches only a range that spans two years. A whole range typed in the wrong year passed, and it
  silently overwrote another Ramadan's months and emptied this one's. The new refusal asks only that the days touch the
  calendar's Ramadan, so no sighting is second-guessed.
- **Prefill after a confirmation.** The ticket says the fields are prefilled "from the calendar". I prefill the days in
  force, which are the calendar's until a confirmation. Prefilling the calendar's after a shift would make a second press
  quietly undo the shift.
- **The count stays in the CNO's line.** The spec's example has none. It is there because a lengthened or shortened
  Ramadan differs in its count, which the dates alone make you work out.
- **The 35-day limit, inclusive.** "More than about 35 days between the two" could also mean a difference of 35.
- **The words of each refusal:**
  - "must not be before the first day", the month fix's own words, which the page's own check usually pre-empts with
    "This is before the first day.";
  - "That makes 36 days. A Ramadan has 29 or 30, so at most 35 are taken.";
  - "These days do not touch Ramadan 1448, which the calendar puts at 8 February – 8 March 2027.";
  - "must be between 1925 and 2076", the existing date check.
- **Focus after confirming stays on Confirm,** where the user was. The status line above the cards says what was done.

**Review.** `code-review` was run against `e8b1308`, both axes in fresh sub-agents.
- **Spec axis:**
  - It found the wrong-year gap and the loose reading of "continue it". Both are fixed, with tests.
  - It found the prefill and the count. Both are kept, and are under Worth your review.
  - It noted that 375 px is not tested. 375 px was driven; there is no test for it, as for the other pages.
- **Standards axis:**
  - It found that the architecture line said `hijridate` was reached only through the solver's module. The line now says
    what the backend calls directly.
  - It found the Hijri lookup in the API module. It moved to `hospital/catalogue.py` as `calendar_ramadan`.
  - It found months sliced as strings. They now go through `month_of` and `shift_month`.
  - It found the dense same-year test in `inForce`. It is now one set of years.
  - Kept:
    - the test that holds the cards to `month_info`, which the ticket asks for ("the derivation matching the solver's").
      The other card tests use hard-coded Umm al-Qura dates.
    - Confirm not being disabled while sending (see Decisions).
    - The cards showing nothing while loading, since the month table beside them already says "Loading…".

**Things later tickets should know.**
- **45** reads the Ramadan in force from `_card` in `hospital/catalogue_api.py`. A card's first, last and count are what
  "the 29th day in force" needs. A card with gaps counts its days; one fixed to none has no days.
- **46** finds every Ramadan write in `_fix_month`, which the per-month fix and the confirmation share. A notification
  there covers both. A confirmation already audits once per changed month inside one transaction, so a notification per
  month fits beside it.
