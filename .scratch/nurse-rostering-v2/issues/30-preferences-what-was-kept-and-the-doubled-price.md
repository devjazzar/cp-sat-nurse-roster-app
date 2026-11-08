# 30: What was kept, and the doubled price

**What to build:** The carry-over chain carries each nurse's count of unkept preferences out of every month, from the solver's carry-over block: projected from the roster in force, corrected at the close and re-worked at a re-close, 0 through a month with no roster for her and for her first month, not reset in January, following a transfer. The solve input hands the count to the solver, so a nurse one of whose preferences the month before did not keep pays double this month in every solve and re-plan. My month tells her: once the roster is approved the Preferences card says "4 of 5 kept" and marks each preference Kept, Not kept or On leave, read from the roster in force however it came about (edits and re-plans count) and, once the month is closed, from the close in force; before approval it says "No roster yet"; and when it applies, "One of your preferences was not kept in May, so this month yours count double.", read from the same chain value the solve input takes. Spec: `.scratch/nurse-rostering-v2/specs/preferences.md`; the words: `GLOSSARY.md` (Kept); the reasons: ADR 0013 and ADR 0004.

**Blocked by:** 28 The solver prices a preference double after an unkept month, and carries what was not kept; 29 A nurse's preferences, kept by the solver at a price

**Status:** ready-for-agent

- [x] The chain carries the count as one more carried field from the result's carry-over block; a month with no roster for her hands on 0; opening values carry 0 with no new field; January does not reset it; a transfer carries it along; a re-close re-works it
- [x] The solve input, a re-plan's included, carries each nurse's count; a nurse with a count above zero pays double in a real solve on a scratch stack, and the draft's per-nurse explanation says so
- [x] My month's preference read carries each preference's outcome (`kept`, `not_kept`, `on_leave`, none before approval), the counts kept and keepable, and whether she counts double this month with the month that caused it
- [x] Outcomes are read from the version in force on the month as it stands, so a manager's edit or a re-plan that breaks one counts as not kept; a closed month's from the close in force's facts; a date on leave is On leave and counted neither way
- [x] The Preferences card: "4 of 5 kept" once approved, "No roster yet" before, each preference Kept, Not kept or On leave, and the doubled line with its month; nothing of a colleague
- [x] Tests at the agreed seams: closes (projected, corrected with late leave, no roster, first month, January, transfer, re-close), solves' input, rosters' own month with expected values counted by hand on the sound rosters fixture, and the frontend app-level suite (six runs at once)
- [x] `docs/ARCHITECTURE.md` sections 6 and 7 updated; the OpenAPI document and the generated client regenerated

## Comments

**From ticket 28 (2026-11-08),** the solver's side this ticket carries. The count is `preferences_not_kept`, the same name
in a solve input's nurse (optional, absent = 0, a whole number 0..62) and in a result's `nurses[id].carry_over`: her days
asked off that were worked plus those asked to work that were off, leave left out, counted in days and whatever the two
weights. Above 0 it doubles every preference of hers, whatever the count. **Ticket 28 already passes it through the chain**
(decided by the main session, to keep the backend suite green): `closes/chain.py`'s `CARRIED` holds it, `NO_HISTORY` gives
0 (opening values, a month with no roster for her), and `BEFORE_PREFERENCES` gives 0 to a close stored before ticket 28. So
every solve input carries it already, always 0 until the app feeds preferences (ticket 29). Yours: the tests that it is
projected from real preferences, corrected at the close with late leave, carried through a transfer and re-worked on a
re-close (January has one: `test_the_carry_over_into_january_resets_overtime_and_both_balances` keeps a count of 1). A doubled match has `amount` 2 and its
text ends "counts double, a preference was not kept last month"; the per-nurse cost carries it. With a weight at 0 the
price is 0 but the count still carries, so the "count double" line may show while nothing is priced (ticket 28's Worth
your review). `docs/ARCHITECTURE.md` section 6 already has a paragraph on the field; section 7's chain paragraph is yours.

**Implemented on 2026-11-08,** on branch `claude/ticket-30-preferences-kept-8ce296`, pull request
MoustafaJazzar/cp-sat-nurse-roster-app#4, from `main` at `eb2ed52` (`58aa10b`, `70db245`, `7c12934`, then this comment and its follow-ups). The
suites, locally:
- the backend under pytest on a throwaway PostgreSQL 18 container of my own (`nr-t30-pytest`): 2556 passed and 1 failed on
  `70db245`. The failure was `ops/tests/test_logs.py::test_gunicorn_logs_its_own_lines_and_each_request_as_json`, while my
  scratch stack was building beside it; alone it passes (4 of 4), and nothing here touches logging. After the review's fixes,
  `closes`, `swaps`, `requesting`, `rosters/tests/test_own_month.py` and `solves/tests/test_input.py` again: 263 passed.
  `makemigrations --check` clean: no migration;
- the frontend: `npm test` 612 passed, `npm run build` clean, `tsc -b` clean; the preferences and My month tests again after
  the review;
- the OpenAPI document and the generated client regenerated, matching the export on the head;
- the solver untouched, so its suite was not run; no Playwright file changed, so none was run here; `e2e/ci.sh` and the six
  parallel frontend runs are GitHub's, on the pull request.

**What the dev stack needs:** a **rebuild** of `web` and `worker` (`docker compose up -d --build`): backend and frontend code
only. No migration, and no change to `deploy/compose.yaml`, the `Dockerfile`, the solver or any dependency.

**What was built, criterion by criterion.**
- **The chain.** No code: ticket 28 already carries `preferences_not_kept` (`CARRIED`, `NO_HISTORY`, `BEFORE_PREFERENCES`).
  New tests in `closes/tests/test_close.py` (`TestTheCountOfPreferencesNotKept`) on Amal's five June preferences, counted by
  hand on SOUND's June (`NNNN.NNN...NN.....NN..DDDD..DD`): a day off on the 2nd (worked), 5th and 10th (off), a working day
  on the 15th (off) and 23rd (worked), so 2 not kept. They test that July's input carries 2, projected from the roster in
  force; that a close after leave on the 2nd stores 1 and July starts from 1, closed; that August starts from 0 after a July
  with no roster; that a first month is 0 with no field of hers; that the 2 follows her into ICU after a transfer; and that a
  re-close after late leave moves the close's 2 to 1, which July then takes. January:
  `test_the_carry_over_into_january_resets_overtime_and_both_balances` keeps a count of 1, as before.
- **The solve input.** `solves/tests/test_input.py` (`TestTheCountCarriedIn`): a closed May hands Dana 1 and Amal 0, and the
  solver package's own validator on SOUND's June prices Dana's broken day off at 2 and Amal's at 1, Dana's match ending
  "counts double, a preference was not kept last month)". `rosters/tests/test_replan.py`: a re-plan's input carries Amal's 2.
  **A real solve** is below.
- **The read.** `GET /api/preferences/mine` gains, per preference, `outcome` (`kept`, `not_kept`, `on_leave`, or null), and
  `kept`, `keepable` and `doubled_by` (`YYYY-MM`). The outcomes come from `rosters.own_month`, beside `own_hours` and
  `closed_hours`. `own_preferences` reads the version in force on the month as it stands: the month's solve input, assembled
  now, gives her leave and her preference lists, and the version gives her row. `closed_preferences` reads the close in force's
  input and facts. Both judge with the solver package's own `nurse_roster.validate.unkept_days`, the one reading the price and
  the carry-over share, so what she reads adds up to what the next month is priced on, whatever the weights.
  `test_what_she_reads_is_what_the_month_after_is_priced_on` holds `keepable − kept` to July's `preferences_not_kept`, and both
  to the hand count of 2. `doubled_by` is `Chain().carry_in(nurse, month)`, the call `solves.input.assemble` makes.
- **Outcomes,** in `rosters/tests/test_own_month.py` (`TestWhatWasKept`, `TestCountingDouble`,
  `TestNothingOfAColleaguesPreferences`), with expected values by hand:
  - before approval, all null and the counts null;
  - approved, 3 of 5;
  - leave on the 2nd recorded since, On leave and 3 of 4;
  - a version 2 putting her on the 10th, a manager's edit or a re-plan's, Not kept and 2 of 5;
  - a withdrawn one has no outcome, even on the date of a day off made again there;
  - closed with leave on the 2nd, 3 of 4. Leave on the 10th recorded after the close changes nothing until the month is
    closed again, then 2 of 3;
  - doubled by June in July, for Amal only;
  - none after a close whose late leave took both unkept days;
  - a colleague's preference changes nothing of hers, and no colleague is named.
- **The card.** "2 of 3 kept" beside the heading once approved, "No roster yet" before. An Outcome column (Kept, Not kept, On
  leave) once approved. "One of your preferences was not kept in November, so this month yours count double." under the
  window's sentence, the month by name alone (`monthAlone`). Four app-level tests in `app.test.tsx`.
- **Docs:** `docs/ARCHITECTURE.md` section 6 (how the app fills the field and what My month reads), section 7's chain
  paragraph (the carried count, its rules and its one month of memory), and section 8's Staff Nurse line (the card); the
  OpenAPI document and the client regenerated.

**What was driven, and how.** Scratch stack `nr-t30` (`E2E_PORT=18300`), built from this branch at `58aa10b` (the code of `70db245`), through the API
as the four ER nurses, Mona and Carla, then in the browser pane as Amal:
- All four preferred 15 January 2027 off. A real 20-second solve kept Dana's and Badr's and paid `undesired_day` 4 for Amal's
  and Emad's (weight 2, amount 1 each). It was submitted and approved.
- `GET /api/preferences/mine`: January shows Amal and Emad Not kept, 0 of 1, and Badr and Dana Kept, 1 of 1. For February,
  `doubled_by` is `2027-01` for Amal and Emad only.
- Mona closed January's window early and opened February's. All four preferred 10 February off, and a real solve kept Amal's
  and Emad's (the doubled ones) and broke Badr's and Dana's at 1 each.
- Amal then preferred nine more days off (11 to 19 February). The next real solve broke her 10th: amount 2,
  "Amal: works 2027-02-10 (asked off; counts double, a preference was not kept last month)", beside Badr's at 1. The
  per-nurse costs carry it.
- In the browser at 375 px: January's card shows "0 of 1 kept" beside the heading and "15 Jan 2027 · A day off · Made · Not
  kept". February's shows "No roster yet" and "One of your preferences was not kept in January, so this month yours count
  double.". No sideways scroll.

**What was NOT checked:**
- a re-plan's version made by a real re-plan, or an edit through the edit API: the outcome tests write version 2 directly,
  with each origin, as ticket 16's own-month test does;
- a screen-reader run, and the card in a desktop browser by hand; held against `better-interface`, `better-writing` and
  `better-accessibility` by hand only (names, reading order, words);
- the six frontend runs at once, and the browser suite: GitHub's;
- the dev stack: untouched.

**Decisions taken here:**
- **Worth your review: the doubled line shows whatever the two weights.** At a weight of 0 nothing is priced, but the count
  still carries and the solve input still holds it, and the read says what the chain says, so My month and the solve input
  never disagree. Hiding it would tie a nurse's read to the CNO's weights for one sentence, and the line would come and go as
  a weight is changed mid-month. The other reading: hide it when both preference weights are 0.
- **Worth your review: "4 of 5 kept" sits beside the heading, not in it.** It is in the card's header (`CardAction`), read
  right after the heading. The heading's accessible name stays "Preferences", which the page's other tests and the phone
  check find it by.
- **Worth your review: "No roster yet" only when she has a preference made.** With none, the card says nothing about rosters.
  An approved month where none of hers could be kept (all on leave) says no count either, rather than "0 of 0 kept".
- **Worth your review: a date outside her dates reads On leave.** The solver's carry-over leaves it out, as it does leave
  (`nurse.unavailable`), so it is counted neither way, and the word is the glossary's nearest one. The spec makes one
  impossible at the form; only a later correction to her dates makes one.
- **An outcome only for a preference that reached the unit's solve:** made, of the unit's windows for her month. A withdrawn
  one, one asked for as a request, and one a transfer left on the old unit's record have none, and count neither way.
- **A month over and not yet closed reads as before approval** ("No roster yet"), as My month's hours do: `in_force` shows a
  past month only once it has closed.
- **`doubled_by` of a closed month walks the chain as a solve would** (`Chain()`, with projection), while that month's close
  read `Chain(project=False)`. They agree except for a nurse transferred in from a unit whose month before is approved and
  not closed: there a close of hers can precede that unclosed month, and the close's input says 0 where the read says the
  projected count. The literal value the close took is its input's nurse row; the read takes what any solve of the month
  takes.
- **`_in_force` became `in_force`, and `_InForce` `MonthInForce`:** the preference read uses it, and `swaps/mine_api.py`
  already imported the private name.

**Review:** `code-review` against `eb2ed52`, both axes; no adversarial review, by the user's call.
- *Spec:* the per-nurse explanation is shown by the real solve above, not by a test (the scripted solver has none). The other
  points are under Worth your review and Decisions. A re-plan's version is now tested beside an edit's.
- *Standards:* no GLOSSARY breach. Fixed:
  - a test's docstring placed after an import;
  - an import out of order;
  - the private `_InForce` crossing modules;
  - the kinds as `PreferenceKind`;
  - two names: `_kept`, which took the whole request, is now `_what_was_kept(user, …)`; the card's `kept` is now `keptLine`.

  Kept: `_what_was_kept` mirrors `my_month`'s close-or-version branch (four lines, each reading a different thing). The test
  helpers that find a nurse's row in an input stay per file, as the files had them.

**Things later tickets should know.** The outcome reading is `rosters.own_month.own_preferences` and `closed_preferences`
(`OwnPreferences.outcomes` by date and kind), and the doubled month is `doubled_by`. A manager's view of what was kept would
reuse them per nurse. The solver's `counted_in` for `undesired_day` still says "requested-off day worked" (ticket 29's
finding), now beside the doubled words.
