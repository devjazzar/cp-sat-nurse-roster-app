# 48: Full runs: the unit rule, the weight and the explanation

**What to build:** Unit rules gain "Most full runs in a month", default 3 for every unit, existing ones included, on the Unit rules page beside the longest run, with the help "A full run is as many shifts in a row as the longest run allows. Each one beyond this costs the solver, which then breaks the work into shorter runs." It shows only while the longest run is above 1, and keeps its value while hidden and through any change to the longest run; a whole number 0 to 31, refused otherwise with the usual field error; edited by the unit manager alone, read by the CNO and Deputy CNO as the other unit rules, audited as they are. The hospital's weights gain "Full run above the most", default 4, on the weights page with a description in the voice of the others; 0 switches it off hospital-wide; audited as the other weights. Every new solve, re-plan and close input carries the unit's cap and the weight, and the draft's per-nurse explanation shows the cost by the solver's words, as for a weekend above the most. Hand edits, swaps, covers and requests are never refused for it, and no nurse page changes. Spec: `.scratch/nurse-rostering-v2/specs/full-runs.md`; the words: `GLOSSARY.md` (Run, Full run).

**Blocked by:** 47 The solver prices full runs above the cap

**Status:** ready-for-agent

- [x] The unit rule: default 3 for new and existing units, the edit and its refusal, the unit manager alone editing it, the CNO and Deputy CNO reading it, its audit entry
- [x] The field on Unit rules beside the longest run, hidden at a longest run of 1 and back with its value when raised, with its label and help
- [x] The weight: default 4, edit, audit, and its description on the weights page; 0 prices nothing
- [x] The solve input, a re-plan's and a close's included, carries the cap and the weight; a stored input without them still reproduces
- [x] The draft's per-nurse explanation shows the cost of full runs above the cap; nothing on My month, My roster or any nurse page
- [x] Tests at the agreed seams: the backend API suite (units rules, hospital rules, `test_input.py`, `test_replan.py`) and the frontend app-level suite (six runs at once)
- [x] Driven on a scratch stack: a month like ER's December with the cap at 3 gives no nurse more than three full runs where the month allows it, and the explanation shows the cost where it does not
- [x] `docs/ARCHITECTURE.md` names the rule beside the other run rules and the weight beside the others; the OpenAPI document and the generated client regenerated

## Comments

**From ticket 47 (2026-11-09), the solver's side.** The names are the department's `max_full_runs` (a whole number 0..31,
or null for no cap) and the weight `excess_full_run`; the rule's id is `excess_full_run`, as `excess_weekend` is
`max_weekends`'s. Both are optional in either request version, so the app may keep writing version 1 and add them. Ticket 47
narrowed three backend test files that hold the app's blocks to the solver's: `units/tests/test_unit_rules.py` and
`units/tests/test_rules_api.py` subtract `FULL_RUN_FIELDS = {"max_full_runs"}`, `hospital/tests/test_rules.py`
subtracts `FULL_RUN_FIELDS = {"excess_full_run"}` from the weights, each with a comment that this ticket deletes the set
and its subtraction. The match reads "Layan: 5 full runs of 3 shifts, max 3" (nurse set, no date, amount the runs above the
cap). On ER's sample month the spec's weight of 4 did not always hold the cap in a 10 s search (a nurse left at four or
five, priced); see ticket 47's comment before choosing the default or the solve's time.

**From the review of ticket 47 (2026-11-09), decided by the user:**
- **Price the full run that reaches the month's last day in that month.** With the longest run hard it cannot grow (the next month forbids a shift on its day 0), so today a nurse may carry one unpriced full run at the end of each month. In the solver, drop the "off on t + 1" literal at the month's last day in the model and count such a run in `validate.count_full_runs`; update the solver tests that expect it uncounted, `solver/DESIGN.md` and the spec's Further Notes. A small solver change inside this ticket; the dev stack then needs a rebuild.
- **Measure before you set the default weight.** On a scratch stack seeded like ER's December (Layan Alharbi had five full runs there), solve with the cap at 3 and the weight at 4, 20, 50 and 200, a few solves each at the unit's solve time, and put the counts of nurses above the cap and the month's cost in your comment as **Worth your review**. Set the default from what you find, and say which and why; the user decides at review.

**Implemented on 2026-11-09,** on branch `claude/ticket-48-full-runs-app-b6c39c`, draft pull request
Nurse-Fold/cp-sat-nurse-roster-app#11, from `main` at `ef31b31`. The commits:
- `135080d`: the solver's last-day change;
- `0892040`: the backend, its migrations and the regenerated client;
- `85c5177`: the frontend and the architecture document;
- `ed5a705`: the review's points;
- then the measurement script and this comment.

The suites ran locally, one at a time under the heavy-run lock:
- the solver's whole suite with the service tests: 583 passed;
- the backend on a throwaway PostgreSQL 18 container of my own: 2740 passed;
- the frontend: one `npm test` run, 661 passed, and `npm run build` succeeded;
- `makemigrations --check`: "No changes detected". Both new migrations were also run forwards, back and forwards again on
  the throwaway database;
- the OpenAPI document and the generated client match the export (no diff after regenerating).

GitHub runs the six parallel frontend runs and the browser checks (`e2e/ci.sh`) on the pull request. No Playwright file
changed.

**What the dev stack needs:** a **rebuild** (`docker compose up -d --build`), because the vendored solver changed. Two data
migrations run when `web` starts:
- `units/0004_max_full_runs` writes `max_full_runs: 3` into every unit's rules, leaving any unit that already has a value
  alone;
- `hospital/0004_excess_full_run_weight` writes `excess_full_run: 4` into the hospital's weights.

Neither raises a review flag. There is no compose, Dockerfile or dependency change.

**What was built, criterion by criterion.**
- **The unit rule.** `max_full_runs` sits in the unit's rules block, kept in the solver's field name as every unit rule
  is: a whole number 0..31 (`nurse_roster.problem.MAX_FULL_RUNS`), required in a save.
  - Default 3 for new units (`DEFAULT_UNIT_RULES`) and for existing ones (the migration, tested on a unit stored without
    it).
  - A value outside 0..31, a fraction, a string, a boolean or null is refused beside `rules.max_full_runs`. A missing one
    is refused rather than defaulted.
  - Only the unit manager saves it (the CNO's and the Deputy CNO's saves get 403). Both read it. A change is audited as
    `unit_rules.changed` with `max_full_runs` before and after.
  - It keeps its number through any change to the longest run (1, 0, 4, tested).
- **The field.** On Unit rules, in "Runs of shifts", right after "Longest run of shifts", with the spec's label and help
  word for word.
  - It shows while the longest run is above 1, and also while that box is blank, so the field does not jump while a new
    number is typed. It keeps its value while hidden.
  - The browser refuses a value outside 0..31 with "Between 0 and 31." and moves focus to the field.
  - A wrong value left behind the hidden field is not sent: the saved value goes instead (`withFullRunsKept`).
  - The read-only view (CNO, Deputy CNO) lists it in the same place, under the same rule of showing.
- **The weight.** `excess_full_run`, default 4, on the weights page beside "Too many weekend days", as "Full run above the
  most", with the description: "Each full run a nurse works in a month above the unit's most. A full run is as many shifts
  in a row as the unit's longest run allows."
  - An edit is audited as `weights.excess_full_run`.
  - At 0 the solver's rule is inactive (tested through the solver's own `rules.active`).
  - The migration adds it to an existing installation (tested).
- **The inputs.** `solves.input.assemble` already passes the unit's rules and the hospital's weights through, so both fields
  reach every new solve, re-plan and close input. Each is tested:
  - `TestFullRuns` in `solves/tests/test_input.py`;
  - `test_the_units_full_run_cap_and_the_hospitals_weight_reach_a_re_plan_as_they_reach_a_solve` in
    `rosters/tests/test_replan.py`;
  - `test_the_close_input_carries_the_units_full_run_cap_and_the_hospitals_weight` in `closes/tests/test_close.py`.

  A stored input without the two fields loads as no cap, and its validation equals the new input's with `excess_full_run`
  at 0, every other penalty the same (tested on SOUND's June with Amal given six full runs).
- **The explanation.** Nothing in the backend changed: the result's rules come from the solver's own validator, by rule
  name. The weight's label in `src/lib/weights.ts` names the rule in "Penalties per rule" beside the draft. The app-level
  test shows "Full run above the most", "2 × 4", and the nurse's line in the solver's words.

  Hand edits, swaps, covers and requests check no soft rule, so none is refused for this one. No nurse page reads it.
- **The solver: a full run reaching the month's last day now counts in that month** (the user's decision at ticket 47's
  review).
  - In `model.py`, the literal for day t runs to the last day, and "off on t + 1" is left out there.
  - `validate.count_full_runs` accepts the end of the sequence as the run's end.
  - Tests: `test_a_run_reaching_the_months_last_day_counts_in_that_month` (a run of 3 at the end counts; a run of 2 does
    not; two full runs, one of them at the end) and a forced solve whose objective equals the validator's on that grid.
    The ER test's own count reads a run up to the month's end.
  - `solver/DESIGN.md`, `solver/how-to.md`, the `request.py` docstring, `docs/ARCHITECTURE.md` section 6 and the spec's
    Further Notes say so.
- **The sample, and the test sets.**
  - The service sample `four_nurses.json` (and its copy in `how-to.md` 2.5) now carries `max_full_runs: 3` and
    `excess_full_run: 4`. The contract test's `capped` fixture folds into it.
  - The backend and `e2e/seed.py` load that file as a unit's rules, so the app's now-required field had to be in it.
  - The three `FULL_RUN_FIELDS` sets and their subtractions are deleted.
- **Docs.** `docs/ARCHITECTURE.md` section 6 names the rule among the run rules and the weight beside the others, with
  where each lives in the app. Section 9 gives both defaults.

**What was driven, and how.** I drove my own scratch stack (`e2e/stack.sh up nr48`, seeded, ports 18280/18643) in the
desktop app's browser, at desktop width. It was taken down afterwards with `e2e/stack.sh down nr48`.
- **As Mona (ER's manager), on Unit rules:**
  - "Most full runs in a month" showed 3, right after "Longest run of shifts", with its help text.
  - I typed 2, then set the longest run to 1: the field went. I set it back to 4: the field came back holding 2.
  - 32 was refused beside the field with "Between 0 and 31.".
  - Saving 2 gave "Saved." and an audit entry `unit_rules.changed` by mona on ER: `max_full_runs` 3 → 2.
- **As Carla (CNO), on Unit rules:** ER's page was read-only and showed 2 in the same place, with no input.
- **As Carla, on Hospital rules:** "Full run above the most" showed 4 with its description, beside "Too many weekend
  days". I saved 0, then 4. The audit log shows `weights.excess_full_run` 4 → 0, then 0 → 4.
- **The real thing, as ER25's manager** (the unit the measurement made, below). I set the cap to 0, so that the month
  could not meet it, and started a solve of December 2026 from the Roster page at the default 60 s.
  - The draft's "Penalties per rule" showed "Full run above the most, 8, 2 × 4, its weight. Counted in: full run above
    the maximum", then "ER25 N03: er25-N03: 1 full runs of 3 shifts, max 0" and the same for N17.
  - The stored input held `max_full_runs` 0 and the weight 4.
  - With the cap at 0 the solver broke almost all the work into runs of two: two full runs in the whole unit.
- **As Amal (ER staff nurse):** neither My month nor My roster mentions full runs.

**The weight measurement: Worth your review.** The script is `.scratch/nurse-rostering-v2/issues/48-measure.py`, and it ran
in the scratch stack's web container.
- **The unit.** "ER25": the solver's ER sample (25 nurses, longest run 3) as this app holds it, which is what the dev
  stack's ER was made from. Cap 3, December 2026, the hospital's reviewed default rules.
- **How it solved.** Each input was built by `solves.input.assemble`, and each solve ran in-process for the unit's 60 s
  with 8 workers (this Mac's 8 CPUs).
- **What was not carried.** The sample's leave (its dates are in March) and its history: December starts from opening
  values with no history.

The full-run penalty was 0 in every solve below; "most" is the highest number of full runs any one nurse had.

| Weight | Solve 1 | Solve 2 | Solve 3 | Nurses above 3 |
|---|---|---|---|---|
| 0 (control) | cost 392; 4 nurses above, most 5 | cost 341; 1 nurse above, most 4 | cost 346; 5 nurses above, most 4 | 1 to 5 |
| 4 | cost 445, most 3 | cost 477, most 3 | cost 360, most 3 | none |
| 20 | cost 455 | cost 448 | cost 373 | none |
| 50 | cost 379 | cost 404 | cost 363 | none |
| 200 | cost 340 | cost 425 | cost 623 | none |

Every solve stopped at the time limit, FEASIBLE.

What this shows:
- Without the price, this month gives one to five nurses four or five full runs, like Layan Alharbi's five. At any of the
  four weights, all twelve solves held every nurse at three or fewer.
- The month's cost shows no trend with the weight: 340 to 623, and the 623 at 200 looks like search noise.

**Decided: the default stays 4.** It is the lowest weight measured, and it held the cap in every solve. A higher weight
would make one full run outweigh a weekend above the most (6) or a night/day switch (8), which nothing here asked for.

**But:** ticket 47 saw 4 fail to hold the cap on the ER sample's March month: with its history and leave, at a cost of
about 2,500 in a 10 s search, it left one or two nurses at four or five full runs. Neither its 10 s nor this December's
lack of leave and history is the dev stack's real month. The check the spec names, a re-plan of ER's December on the dev
stack after the rebuild, decides it. If Layan Alharbi or anyone is still above three there, raise the weight to 20. That
is the step that changed nothing measurable here, and it still sits below the switch and well below the hours' prices.
The weight is the CNO's to change on the weights page, so no release is needed for that.

**What was found, and fixed.** Nothing beyond the review's points below.

**Findings for you, not fixed:**
- The solver's words say "1 full runs of 3 shifts", plural at 1, in the explanation (seen on the stack). It is the
  solver's match text, shared with the CLI, and every other match ("2 Fridays", "3 h overtime") has the same shape. Not
  changed here.

**What was NOT checked:**
- A re-plan on the stack. The tests show its input carries both fields, but no month on the stack was re-planned with
  full runs.
- The CNO's or the Deputy CNO's read of a unit at a longest run of 1 on the stack. It is tested in the app suite.
- Phone widths, and screen readers beyond the app suite's accessible-name and description checks.
- The six parallel frontend runs and the browser checks locally: they are GitHub's, on the pull request.
- The measurement with leave and history, and at any time limit but 60 s.
- The Unit rules and weights screens were held against `better-interface`, `better-writing` and `better-accessibility`
  by hand, not by running the skills:
  - the label and help are the spec's own words;
  - the weight's description follows its neighbours' "Each … above the unit's …";
  - the field has its label and its description as its accessible description, and a refusal takes focus;
  - a field appearing and disappearing is not announced, as no field on these pages is.

**Decisions taken here, and Worth your review:**
- **Worth your review: the default weight stays 4,** with the measurement above and the dev-stack check to confirm it.
- **Worth your review: the read-only view hides the cap at a longest run of 0 or 1 too.** The spec asks this only of the
  manager's field. I kept the two views the same, so that the CNO is never shown a number that cannot matter.
- **Worth your review: a wrong value left behind the hidden field is replaced by the saved one on save,** rather than
  blocking a save whose error cannot be seen.
- **Worth your review: null is refused,** though the solver reads it as no cap. The spec's rule is a whole number from 0
  to 31, and 31 is no cap in practice.
- **Worth your review: the "defaults are the reviewed set" tests** compare against the ER sample plus
  `max_full_runs: 3` and `excess_full_run: 4`. The solver's ER fixture was left without them, so the solver's own ER
  tests price exactly as before.
- **Worth your review: the service sample carries the fields** (ticket 47's open point), so the contract test's `capped`
  fixture is gone.
- The migration tests run the migration's own function against today's app registry, not a migrated-back schema: enough
  for a JSON-only step.

**Review:** `code-review` against `ef31b31`, both axes.
- **Standards:** no hard violation. Fixed:
  - the cap's bound now uses an `Annotated` alias as its neighbours do (`FullRuns`);
  - `fullRunsApply` says `Number.isNaN(longest) || longest > 1` outright;
  - the hide test asserts the longest run's new value before checking that the field is gone;
  - a missing verb in `ARCHITECTURE.md`.

  Kept: two near-identical `general_block(...)` lines in the hospital tests, and the two migrations' same shape (each
  states its value on purpose).
- **Spec:** nothing missing.
  - Its one "possible issue", that `superRefine` might not run while other fields are wrong, is disproved by the existing
    test that shows "Cannot be the night shift too." beside other errors.
  - Its scope notes are the review points above.

No adversarial review, by the brief.

**Things later tickets should know.**
- **49 (overtime share):**
  - A new required unit-rule field needs a data migration (the pattern is `units/0004_max_full_runs`), and the service
    sample `four_nurses.json` must carry it before the app's schema requires it, because the backend and `e2e/seed.py`
    load that file as a unit's rules.
  - Add it to the "defaults are the reviewed set" tests as `reviewed | {...}`.
- **Anyone touching the measurement:** `48-measure.py` makes a unit `ER25` on any scratch stack, solves a month at
  several weights and prints `MEASURE` lines. It puts the hospital rules back afterwards.
