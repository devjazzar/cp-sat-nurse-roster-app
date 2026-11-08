# 28: The solver prices a preference double after an unkept month, and carries what was not kept

**What to build:** The vendored solver's contract gains one optional per-nurse input: how many of her preferences the month before did not keep (a whole number, 0 or more; absent means 0, so every stored solve input and close input still loads). For a nurse whose count is above zero, every entry of hers in the two soft rules, a day asked off and a day asked to work, costs twice the weight, in the model's objective and in the validator's explanation alike, and the explanation's words for such a match say it counted double. The result's carry-over block gains the count for next month: her days asked off that were worked plus her days asked to work that were off, leave days excluded, worked out from the month's facts like every carried value. The solver's own suite and the service contract tests cover it, and the CLI shows it on the sample. Nothing in the app changes in this ticket. Spec: `.scratch/nurse-rostering-v2/specs/preferences.md`; the reasons: ADR 0013.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] The request loader accepts the new nurse field, defaults it to 0 when absent, and refuses a negative, a non-integer or a boolean with the usual `request: <field path>` error; the problem's schema version notes the change
- [x] With the count above zero a nurse's day-off and working-day preferences cost twice the weight; another nurse's cost once; a solve's cost and a validation of the same grid agree
- [x] The explanation's match for a doubled preference says it counted double; the per-nurse explanation reflects it
- [x] The result's carry-over block carries the count of unkept preferences, computed from the month's facts with leave days excluded; a nurse with none carries 0
- [x] The day-list rules are unchanged: a leave day ignored, a day listed twice or in both lists refused
- [x] The service contract test's sample request and result carry the field; the solver's suite, the service tests and the contract tests pass

## Comments

**Implemented on 2026-11-08,** on branch `claude/ticket-28-solver-unkept-e19381`, pull request
MoustafaJazzar/cp-sat-nurse-roster-app#2, from `main` at `a3cd509` (`94faad6`, `ad7ce6e`, then the chain's pass-through and this comment). The suites, locally:
- the solver's whole suite with the service tests (`cd solver && uv run --no-sync pytest -q`): 469 passed on `ad7ce6e` (14 new in `tests/test_preferences.py`, six new loader cases, two new contract tests);
- the backend under pytest on a throwaway PostgreSQL 18 container of my own: 2457 passed on the head with the chain change (2456 before plus the new close test); `makemigrations --check` clean
  (no model changed);
- no frontend, OpenAPI or Playwright change: the six frontend runs and the browser checks are GitHub's, on the pull request.

**What the dev stack needs:** a **rebuild** of `web`, `worker` and `solver` after the merge (`docker compose up -d --build`):
the vendored solver package changed, and so did `backend/closes/chain.py`. No dependency, migration, compose or Dockerfile
change. Until ticket 29 lands the app feeds no preference, so the count the chain carries is always 0 and a solve on the
stack prices exactly as before.

**What was built, criterion by criterion.**
- **The input.** Each nurse of a request may carry `preferences_not_kept`, a whole number of 0 or more; absent means 0
  (`request._NURSE_OPTIONAL`, `Nurse.preferences_not_kept = 0`), so every stored solve input and close input loads unchanged.
  A negative, a float, a string, null or a boolean is refused as `request: nurses[i].preferences_not_kept: must be a whole
  number, 0 or more, got …`; above 62 (`MAX_DAYS`) the problem refuses it as `request: N01: preferences_not_kept must be an
  integer within 0..62`. The problem's `SCHEMA_VERSION` is 4, its comment dated and saying why; a version-3 problem file is
  refused like any other. The request's own version stays 1, the field being optional.
- **The price.** `problem.preference_factor(nurse)` is 2 when the count is above 0, else 1, whatever the count. The model
  lists each of her preference terms that many times in the rule's term list, so `WSum` gives it twice the weight; the
  validator's match for that day has amount 2. `validate()`, `explain()` (per rule and per nurse) and the result's `cost`
  all read the amounts, so a solve's cost and a validation of the same grid agree: tested on a fixed three-day grid (the
  doubled nurse 6, the other 3, solver objective = validated cost = 9, counted on paper), and by a free solve in which the
  optimum keeps the doubled nurse's day off and gives the shift to her colleague.
- **The words.** The match reads "a: works day 0 (asked off; counts double, a preference was not kept last month)" and
  "a: off on day 1 (asked to work; counts double, a preference was not kept last month)"; a colleague's match is unchanged.
  The per-nurse explanation (`Analysis.nurses`, the result's `nurses[id].cost`) carries the doubled amount. The CLI's
  `--explain` prints it (`undesired_day 4 = 2 x 2` and the match), tested on a one-nurse June.
- **The carry-over.** `nurses[id].carry_over.preferences_not_kept`, the request's own field name, is
  `validate.preferences_not_kept(nurse, row)`: her days asked off that the grid works plus those asked to work that it has
  off, a leave day counted neither way, counted in days (a nurse already doubled carries 3 for three days, not 6) and
  whatever the two weights. It reads the same `validate.unkept_days` as the two checks, so the price and the count cannot
  drift apart. It is in `result.nurse_accounting`, so a solve's result and the service's `nurses_of` on a month's facts (a
  close) agree; a roster in force holding a shift on a leave day counts nothing (`month_facts` gives leave first). A nurse
  with no preferences carries 0. Next month's request loads the block as is (the round-trip tests).
- **The day-list rules,** unchanged: a leave day ignored (for a doubled nurse too, tested), a day listed twice or in both
  lists refused (the existing tests, still green).
- **The contract.** `service_tests/fixtures/four_nurses.json` and the how-to's four-nurse sample give Dana a working-day
  preference and `preferences_not_kept: 1`; the contract test checks every nurse's carry-over carries the field, a solve with
  Dana's two preferences pinned the wrong way carries 2 for her and 0 for the rest, and `/validate` prices her two broken
  preferences at twice the weights with "counts double" in both matches. The ER sample (`er_request_2026-03.json`) gives
  N05 `preferences_not_kept: 1`, and the CLI test checks it loads and is worded doubled.
- **Docs:** the solver's `how-to.md` (the nurse table, the four-nurse sample, the result sample, the carry-over list and
  meaning, the weights table) and `DESIGN.md` (request, result and schema 4); `docs/ARCHITECTURE.md` section 6 gains one
  paragraph on the contract's new field. Nothing under `frontend/` changed.
- **Backend code changed (decided by the main session):** the backend suite went red, 7 of 2456, because a close's stored
  carry-over block now holds the new key and the chain's `CARRIED` did not, so "next month starts from the close's block,
  field for field" no longer held; and `solves/tests/test_input.py` compares the app's input with the solver's four-nurse
  sample, which now gives Dana the field. So `closes/chain.py` passes the field through: `CARRIED` gains
  `preferences_not_kept`, `NO_HISTORY` gives it 0 (opening values and a month with no roster), and `BEFORE_PREFERENCES`
  gives 0 to a close stored before this change, whose block has no such key (without it, `solves/input.py` would raise
  `KeyError` on the user's existing closes). **The solve input now carries the field** for every nurse, always 0 until the
  app feeds preferences. Tests: `test_a_close_stored_before_the_count_existed_hands_on_zero` (new), the January test now
  stores a count of 1 and expects it kept, and `test_input` expects 0 for every nurse of the sample.

**What was driven, and how.** Nothing in a browser: nothing in the app changed. The CLI ran on the samples through the tests.

**What was found, and fixed.** Nothing beyond the code review's points below.

**What was NOT checked:**
- A real solve on a stack with the field fed: the app does not feed it until tickets 29 and 30.
- Whether doubling is the right price against the fairness weights: the CNO's to judge after a real month (the spec says so).
- The solver's timing-sensitive tests on GitHub's runners beyond this pull request's own runs.

**Decisions taken here:**
- **Worth your review: backend code changed, decided by the main session, not by you.** `closes/chain.py` passes
  `preferences_not_kept` through, so **every solve input the app builds now carries it**, always 0 until preferences exist,
  and a close stored before this change hands on 0 (`BEFORE_PREFERENCES`; without it the app's next solve input would have
  failed on your existing closes). The alternative was to leave the chain alone and narrow six close tests to the fields it
  carries. `docs/ARCHITECTURE.md` section 7's chain paragraph does not name the field yet: the spec gives section 7 to
  ticket 30, and it is knowingly left there.
- **Worth your review: the field's name, `preferences_not_kept`,** in the request and in the result's `carry_over` (one name,
  so the block is copied as is). It follows the glossary's "not kept" and the solver's style (`rest_owed`,
  `last_shift_kind`); the spec left the name to the implementer. `unkept_preferences` was the other candidate.
- **Worth your review: its place:** optional, unlike the twelve required scalars, because absent must mean 0 for every stored
  input. The problem bounds it at 62 (`MAX_DAYS`, the most days a problem may have), a sanity bound the spec did not ask for;
  that refusal names the nurse, not the field path, as every problem-level bound does (`rest_owed` above 7 reads the same).
- **Worth your review: the words,** "counts double, a preference was not kept last month", in the present tense like the
  match's own "works day 4"; the spec's "says it counted double" is the gist. The match's `amount` is 2, so the explanation's
  `raw` for a rule counts a doubled day as 2 ("undesired_day 4 = 2 x 2": one day, twice); the alternative, a separate factor
  on each match, would have changed the explanation's shape for every rule.
- **Worth your review: the count ignores the weights.** With `undesired_day` or `desired_day` at 0 the price is 0 (doubled,
  still 0), but the carried count still says what happened. Ticket 30's "your preferences count double this month" line
  could then show while the price is 0; whether to hide it then is ticket 30's to decide.
- **Problem schema 4 refuses a version-3 problem file.** No stored input is a problem file (the app stores requests,
  version 1), so nothing stored is affected; the ADR names 4.
- **Worth your review: the ER sample's N05 now counts double,** so the end-to-end tests and benchmarks that use it price her two preferences
  twice; nothing in them asserts a cost.

**Review:** `code-review` against `a3cd509`, both axes.
- *Spec:* faithful, nothing missing; "the CLI shows it on the sample" was tested only through the result and a direct
  `explain()`: fixed, with a test of the CLI's printed `--explain`. Kept: the 0..62 bound and N05's count (above).
- *Standards:* the contract test worked out Dana's count the way the code does (guide section 5.2, "never recomputed"): fixed,
  her preferences are pinned and 2 is expected. The leave-and-cell predicate was repeated between the checks and the count:
  fixed, `validate.unkept_days`. The model's comment said "requests": now "preferences" (glossary). The ARCHITECTURE
  paragraph said "changed once": now names the change. Kept: the `rest_owed`-style whole-number check written out again in
  the loader (two lines, the file's own pattern), `preference_factor` as a function beside `Nurse` (the module's style),
  ADR 0002's "contract change with the app code that depends on it": the chain now passes the field through in this same
  change (above); feeding it is 29's and 30's.
- No adversarial review, by the user's call.

**Things later tickets should know.**
- **29:** the solve input's nurse fields are `undesired_days` (her live day-off preferences) and `desired_days` (working-day
  ones), as ISO dates of the month; a day on leave is ignored by the solver, but a day listed twice, or in both lists, is
  refused (`request: nurses[i].desired_days: … is listed twice`, `… is both desired and undesired`), so one wish a date
  must hold in the input too. `preferences_not_kept` is already in every nurse's input, from the chain (0 until the
  carried count is real); once 29 fills the lists, the next month's projection counts them.
- **30:** the count is `preferences_not_kept`, the same name in the solve input's nurse and in the result's
  `nurses[id].carry_over`. `backend/closes/chain.py` already passes it through (`CARRIED`, 0 in `NO_HISTORY` and for a
  close stored before ticket 28, `BEFORE_PREFERENCES`), so it is always 0 until 29 feeds preferences; the tests for a
  transfer, a re-close, a month with no roster and a projection with real preferences are yours (January has one). A close
  stores the whole `carry_over` block (`closes/making.py`). A doubled match's `amount` is 2 and its text ends "counts double, a preference was not kept
  last month"; the per-nurse cost carries it. `docs/ARCHITECTURE.md` section 6 already has a paragraph on the field.
