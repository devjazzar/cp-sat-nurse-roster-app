# 47: The solver prices full runs above the cap

**What to build:** The vendored solver's contract gains one optional department field, the most full runs a nurse may work in the month (a whole number 0 to 31; absent means no cap, so every stored solve input and close input still loads and gives what it gave), and one soft rule with its weight, a full run above the most (absent means 0). A full run is a run of exactly the longest run, a run being consecutive worked days with a non-worked day, leave included, on each side. Each nurse's full runs beyond the cap cost the weight each, in the model's objective and in the validator's explanation alike; the match names the nurse, her count and the cap, and the per-nurse explanation carries it as it carries weekends above the most. A full run counts in the month that holds its last day: one begun in the history and ended in the month counts; one reaching the month's last day does not. With the longest run at 0 or 1 nothing is priced. The solver's own suite and the service contract tests cover it, and the CLI shows it on the sample. Nothing in the app changes in this ticket. Spec: `.scratch/nurse-rostering-v2/specs/full-runs.md`; the words: `GLOSSARY.md` (Run, Full run).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] The request loader accepts the new department field and the new weight, treats an absent cap as no cap and an absent weight as 0, and refuses a negative, a non-integer, a boolean or a cap above 31 with the usual `request: <field path>` error; the problem's schema version notes the change
- [x] On a known grid counted by hand, each full run beyond the cap costs the weight once; a solve's cost and a validation of the same grid agree; a nurse at or under the cap costs nothing
- [x] Leave ends a run; a run begun in the history and ended in the month counts; a run reaching the month's last day does not; the longest run at 0 or 1, or the weight at 0, prices nothing
- [x] The explanation's match names the nurse, her count and the cap; the per-nurse explanation carries it
- [x] With the cap set, a solve of the ER sample gives no nurse more full runs than the cap where the month allows it
- [x] The service contract test's sample request and result carry the field; the solver's suite, the service tests and the contract tests pass
- [x] `solver/DESIGN.md` names the rule beside the other run rules; `docs/ARCHITECTURE.md` section 6 names the field

**Worth your review, already known:** a full run that ends exactly on the month's last day is counted by neither month (the
month cannot see it ended, the next cannot change it). Confirm this reading or say why the next month should count it.

## Comments

**Implemented on 2026-11-09,** on branch `claude/ticket-47-full-runs-solver-2fc769`, pull request
MoustafaJazzar/cp-sat-nurse-roster-app#9, from `main` at `4d3e8fc` (`be4a4b3` the rule, the request, the tests and the
docs; then the review's points and this comment). The suites, locally:
- the solver's whole suite with the service tests (`cd solver && uv run --no-sync pytest -q`): 580 passed at the end; 579 before, after the result's
  penalty key list in `test_request.py` gained `excess_full_run`; then the review's changes, rerun on the three files they
  touched (`test_full_runs.py`, `test_skills.py`, `test_request.py`: 205 passed). 52 tests are new in `tests/test_full_runs.py`
  and one in `service_tests/test_contract.py`;
- the backend under pytest on a throwaway PostgreSQL 18 container of my own: 2670 passed and 8 failed. Seven were the
  solver's change: the app's tests load the solver's `service_tests/fixtures/four_nurses.json` as a unit's rules, and the
  field I had first added there is refused by the app's schema (422). The fixture is back as it was and the contract test
  adds the fields to its own copy (below). The eighth, `ops/tests/test_logs.py`, timed out under the full run's load. After
  the change those files and every other touched area were rerun (`ops/tests/test_logs.py`, `rosters/tests/test_pins.py`,
  `rosters/tests/test_versions.py`, `units`, `hospital`, `solves/tests/test_input.py`: 563 passed); GitHub's backend job is
  the full run;
- no frontend, OpenAPI or Playwright change: those runs are GitHub's, on the pull request.

**What the dev stack needs:** a **rebuild** (`docker compose up -d --build`) after the merge: the vendored solver package
changed. No dependency, migration, compose or Dockerfile change. The app writes neither field yet, read as no cap and a
weight of 0, so a solve on the stack prices exactly as before until ticket 48.

**What was built, criterion by criterion.**
- **The loader.** `department.max_full_runs` (a whole number 0..31; absent or null = no cap) and `weights.excess_full_run`
  (absent = 0), optional in **both** request versions (`request._full_runs`, on copies; the stored input is untouched,
  tested on the version 1 and 2 samples). Refused with the usual path: -1, 32, 2.5, 3.0, `true`, `"3"` ("request:
  department.max_full_runs must be a whole number within 0..31 or null, got 32"); a negative or boolean weight by the
  weights' own check. The problem's schema goes 5 → 6: both fields required in a problem file (Python defaults null and 0,
  as ticket 31's), a version-5 file refused like any other. The request's version stays 2 and still reads 1.
- **The price.** Rule `excess_full_run`, soft, weight of the same name, unit "full run above the maximum", on when the cap
  is set and the longest run is above 1. Model: per nurse, one literal per month day t before the last, forced to 1 by "K
  worked days to t, off on t + 1, off on t − K"; `ex ≥ Σ − cap`, priced at the weight. Validator:
  `validate.count_full_runs` over her history and month. Hand-counted grids (three full runs at caps 0, 1, 3, 5; runs of 1
  and 2 not full); a forced solve whose objective equals the validated cost (8); a two-nurse month where the solver finds
  runs of two at no cost; the per-rule drift test in `test_rules.py` now covers it with the cap at 0.
- **What counts.** Leave ends a run; a run begun in the history and ended on day 0 counts, one ended on the history's last
  day does not; a run reaching the month's last day is not counted, the one ending the day before is; a run longer than the
  longest run (only a recorded fact can be) is not full; the longest run at 0 or 1, no cap, or the weight at 0 price nothing
  and leave the rule inactive. The start of a nurse's own history bounds a run like an off day, and the model never reads
  the free padding before a short history (tested: a forced solve cannot dodge the price there). A history shift the unit
  no longer works is a worked day of the run, in both (tested).
- **The words.** "N03: 4 full runs of 3 shifts, max 3": nurse set, no date, amount the runs above the cap, as
  `excess_weekend`'s; the per-nurse explanation carries it unchanged (`explain.nurses`), tested.
- **A real solve.** The ER sample (25 nurses, longest run 3), solved 10 s on 4 workers with the cap at 3 and the weight
  at 200: no nurse above three full runs (counted apart from the validator, from the grid as text), the cost priced 0, the validator equal to the
  result. Without the cap the same solve gave nurses up to four. See Worth your review for the weight.
- **Contract and docs.** The service contract test's sample (`fixtures/four_nurses.json`, version 1) is given
  `max_full_runs: 3` and `excess_full_run: 4` in the test (`capped`), not in the file (see Worth your review); the solve's
  `penalties` carry the key; `/validate` on a roster giving Amal six full runs of four
  prices 3 × 4 in the solver's words, dated null. `solver/DESIGN.md` (request note, schema 6, the rule beside the run
  rules), `solver/how-to.md` (both fields) and `docs/ARCHITECTURE.md` section 6.

**What was driven, and how.** The CLI on the ER sample with the cap at 3 and the spec's weight of 4
(`uv run python -m nurse_roster solve <er_request_2026-03.json with the two fields> --explain --workers 4`): FEASIBLE in
10 s, `excess_full_run 8 = 2 x 4 (full run above the maximum)` with "N03: 4 full runs of 3 shifts, max 3" and "N13: 4 full
runs of 3 shifts, max 3", the hard rules all met. Nothing in a browser: nothing in the app changed.

**What was NOT checked:**
- A solve on a stack with the fields fed: the app writes neither until 48.
- A re-plan with elapsed days holding full runs: both model and validator count elapsed days (as every soft rule does), by
  reading, not by a test.
- How the weight competes on ER's December (Layan Alharbi's five), the spec's check after 48.
- Performance beyond the ER sample: one literal and one clause per nurse-day, small next to the run rule's own.

**Decisions taken here:**
- **Worth your review, the ticket's own: a full run ending exactly on the month's last day is counted by neither month.
  Confirmed as built, with a correction to its reason.** The spec says the month "cannot see that it ended". With the
  longest run hard, it can: a run of exactly K reaching the last day cannot grow, since this month forbids K + 1 and the
  next month's hard rule, reading the history, forbids a shift on its day 0. So the real effect is one unpriced full run a
  nurse may park at the end of each month (the next month pays a forced day off, not the price). Pricing it in the month
  that ends it would be right and cheap (in the model, drop the "off on t + 1" literal at the month's last day; in the
  validator, accept the sequence's end), and would make the "counts in the month that holds its last day" rule hold without
  exception. I kept the spec's reading because it is decided, it never over-charges, and it is one line each way to flip.
  My recommendation: flip it, either here before the merge or in 48.
- **Worth your review: the spec's weight of 4 does not reliably hold the cap on ER.** Against an ER month costing about
  2,500, a 10 s search with the weight at 4 kept the cap in some solves and left one or two nurses at four or five full runs
  in others (the CLI run above: two at four), always priced and explained. At 50 it still left one nurse at four in about
  one solve in three under pytest; at 200 it held the cap in fourteen of fourteen, so the ER test uses 200 and says why. A cap of 2 was not reached in 20 s even then. The CNO's weight, and the
  solve's time, are ticket 48's and the user's to weigh; nothing here assumes 4.
- **Worth your review: optional in both request versions, no version 3.** The app still writes version 1, so refusing the
  fields in version 1 would have pushed ticket 48 onto version 2 and every skill field. Absent changes nothing, as
  `preferences_not_kept` already did. A null cap is accepted as "no cap" (a problem file writes it so).
- **Worth your review: names.** `max_full_runs` and `excess_full_run`, mirroring `max_weekends` / `excess_weekend`; the
  rule's id is its weight's.
- **Worth your review: the start of a nurse's own history bounds a run like an off day.** A nurse whose history is shorter
  than the longest run plus one may be charged for a run whose real start the app did not send. The app sends a month of
  history, so this touches only a nurse new to the unit; the alternative (unknown = not a full run) would let the model
  fill the padding. The validator's run rule (`_consecutive`) already reads it so.
- **Worth your review: the service sample file does not carry the fields.** The ticket asks that "the service contract
  test's sample request and result carry the field". They do in the test; the file `four_nurses.json` does not, because the
  backend's tests load it as a unit's rules and the app's schema refuses an unknown field until 48. Ticket 48 may add the two
  fields to the file once its schema has them (the contract test's `capped` then becomes the sample itself).
- **Worth your review: the cap is accepted, inert, while the longest run is 0 or 1**, as the spec's "prices nothing".
- **Worth your review: three backend test files narrowed (decided by the main session).** `units/tests/test_unit_rules.py`
  and `units/tests/test_rules_api.py` subtract `FULL_RUN_FIELDS = {"max_full_runs"}`, `hospital/tests/test_rules.py`
  subtracts `FULL_RUN_FIELDS = {"excess_full_run"}` from the weights, each with a comment that ticket 48 deletes it; ticket
  48's file says so. Four assertions in three files, as ticket 31's (one test is parametrised over two schemas). No app code
  changed.

**Review:** `code-review` against `4d3e8fc`, both axes. *Standards:* the ER test's hand count was a copy of the validator's
counter, so it is now an independent reading (the grid as text, a regular expression); "runs" for solves in a docstring of
this file renamed; the request's default dicts are used, not their keys restated. Kept: "whole number … or null, got …" in
the new check (the spec's words, and the value named), against the older checks' "integer within"; `FULL_RUN_FIELDS`
repeated in three test files, the precedent ticket 31 set, deleted by 48. *Spec:* a test added for a history shift the unit
no longer works; the comment, the CLI run and the weight finding above. After the review, the backend run found the shared
fixture break (above) and a rerun found the ER test flaky at 50, now 200. Kept: the note on ticket 48's file (its
hand-over, not app code). No adversarial review, by the user's call.

**Things later tickets should know.**
- **48:** write `department.max_full_runs` (int 0..31, or null) and `general.weights.excess_full_run` into every solve,
  re-plan and close input; version 1 or 2 both take them. Delete `FULL_RUN_FIELDS` from the three test files, and add the two
  fields to `solver/service_tests/fixtures/four_nurses.json` if you like (the contract test's `capped` fixture then folds). The
  violation rule in `/validate` is `excess_full_run`, per nurse, `date` null, amount the runs above the cap. Read the weight
  finding above before setting the default of 4.
- **49 (overtime share):** the same shape works for an optional rule field: optional in the request (`request._full_runs`'s
  pattern, on copies, both versions), required in the problem file with a schema bump to 7, a Python default on the
  dataclass, the registry entry with its `enabled`, a validator check in `CHECKS`, and the drift test's branch in
  `test_rules.py`. The result's penalty key list in `test_request.py::test_result_roster_and_carry_over_round_trip` and
  `test_audit16`'s schema pin move with it. A carried balance is a nurse scalar: optional in the request as
  `preferences_not_kept` is.

