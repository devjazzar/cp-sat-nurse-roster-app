# Full runs: a priced cap on a nurse's full runs in a month

Status: ready-for-agent
Type: feature
Published: 2026-11-08 by /grill-with-docs
Decided: the grilling of 2026-11-08 (15 questions, three rounds), recorded in `GLOSSARY.md` (Run, Full run). No ADR: the
rule is small, priced and easy to reverse.

Vocabulary: `GLOSSARY.md`. Decisions and their reasons: `docs/ARCHITECTURE.md` and `docs/adr/`. Where this spec and those
documents disagree, the documents win and this spec is wrong.

## Problem Statement

A unit manager can bound how long a run is (the longest run), how much rest follows two runs with one day between them,
and whether a run may mix day and night shifts. Nothing bounds how many full runs a nurse works in a month. ER's December
2026 draft, solved on the dev stack, gave Layan Alharbi five full runs of three shifts, the most in the unit (the next had
four), with 20 shifts where most had 18:

```
N..DDD.DDD..DDD.N..NNN.N.NN.NNN
```

Three shifts in a row, five times in a month, wears a nurse down, and nurses notice who gets them. The unit manager has no
way to say "no more than three of those".

## Solution

Unit rules gain "Most full runs in a month", beside the longest run. Every unit starts at 3. The solver prices each full
run a nurse works beyond it, at a weight the CNO sets on the weights page ("Full run above the most", 4 by default, 0 to
switch it off), so it breaks the work into shorter runs where it can and says what it cost where it cannot. The manager
reads the cost in the draft's per-nurse explanation, as for weekends. Nothing is ever refused for it, and the nurse's own
pages do not change.

## User Stories

1. As a unit manager, I want to set the most full runs a nurse may work in a month, so that no nurse is worn down by long
   runs again and again.
2. As a unit manager, I want the field beside the longest run on Unit rules, so that the run rules read together.
3. As a unit manager, I want the field hidden while the longest run is 1, so that I am not asked about something that
   cannot matter.
4. As a unit manager, I want my value kept while the field is hidden, so that raising the longest run again restores it.
5. As a unit manager, I want the field's help to say what a full run is and what the cap does, so that I set it knowingly.
6. As a unit manager, I want a value outside 0 to 31 refused with the usual field error, so that I cannot save nonsense.
7. As a unit manager, I want every unit to start at 3, so that the rule works without my touching it.
8. As a unit manager, I want the cap to keep its number when I change the longest run, so that one change does not undo
   another.
9. As a unit manager, I want a change to the cap audited like every other unit rule, so that the log says who changed it.
10. As a unit manager, I want the solver to price each full run beyond the cap, so that a month that cannot meet it still
    solves.
11. As a unit manager, I want the draft's per-nurse explanation to show the cost of full runs beyond the cap, so that I can
    see who got too many and what it cost.
12. As a unit manager, I want a re-plan to price the cap as a solve does, so that fixing a sick call does not undo it.
13. As a unit manager, I want hand edits, swaps and covers never refused for the cap, so that a priced rule never blocks a
    real need.
14. As a unit manager, I want the same cap for every nurse in the unit, with no scaling for leave, so that the rule is plain.
15. As a unit manager, I want a day of leave to end a run as a day off does, so that a run never grows past the longest run.
16. As a unit manager, I want a full run that crosses the month's start counted in the month that holds its last day, so that
    the month that can still change it is the one that pays for it.
17. As a CNO, I want to set the weight of a full run above the most on the weights page, so that I decide how much it
    matters against the other priced rules.
18. As a CNO, I want a weight of 0 to switch the rule off hospital-wide, so that I can drop it without touching each unit.
19. As a CNO or Deputy CNO, I want to read each unit's cap as I read its other unit rules, so that I can compare units.
20. As a CNO, I want the weight's change audited as the other weights are, so that the log says who changed it.
21. As a staff nurse, I want my own pages unchanged, so that I am not shown the solver's prices.
22. As anyone re-solving an old month, I want a solve input stored without the field to mean no cap, so that every stored
    solve and close gives the same roster as before.
23. As the system, I want every new solve, re-plan and close input to carry the unit's cap, so that what the solver priced is
    in the input for good.

## Implementation Decisions

### The solver (vendored, `solver/`)

- The problem's department gains one optional field, the most full runs per nurse in the month: a whole number 0 to 31.
  Absent means no cap, so every stored solve input and close input loads and gives what it gave. The loader refuses a
  negative, a non-integer or a boolean with the usual `request: <field path>` error. The problem's schema version notes the
  change.
- The weights gain one soft rule, a full run above the most, with its own weight. Absent from a stored input means 0.
- A run is a stretch of consecutive worked days with a non-worked day on each side; leave is non-worked. A full run is a run
  of exactly the longest run (`max_consecutive_shifts`). With the longest run at 0 (unbounded) or 1, nothing is priced.
- A full run counts in the month that holds its last day: a run begun in the history and ended inside the month counts in
  the month; a run that reaches the month's last day is not counted (the month cannot see whether it ends there). See
  Further Notes for the one run this leaves uncounted.
- The cost per nurse is the weight times the number of her full runs beyond the cap, in the model's objective and in the
  validator's explanation alike, so a solve's cost and a validation of the same grid agree. The match names the nurse, the
  count and the cap, and the per-nurse explanation carries it as for weekends above the most.
- No precheck: a priced rule cannot make a month infeasible.

### The app

- Unit rules gain the cap, default 3 for every unit, existing ones included, on the Unit rules page beside the longest run,
  labelled "Most full runs in a month", with the help "A full run is as many shifts in a row as the longest run allows. Each
  one beyond this costs the solver, which then breaks the work into shorter runs." The field is shown only while the longest
  run is above 1; its value is kept while hidden and through any change to the longest run. A whole number 0 to 31; outside
  that, the usual field error. Edited by the unit manager only; read by the CNO and Deputy CNO as the other unit rules.
  Audited as the other unit rules are.
- The hospital's weights gain "Full run above the most", default 4, on the weights page with a description in the voice of
  the others; 0 switches it off. Audited as the other weights are.
- The solve input (`solves.input.assemble`) fills the cap and the weight in every new solve, re-plan and close input.
- The draft's per-nurse explanation shows the new match by the solver's words, as it shows a weekend above the most.
- Hand edits, swaps, covers and requests are never refused for it. Nothing on My month, My roster or any nurse page.
- The OpenAPI document and the generated client are regenerated. `docs/ARCHITECTURE.md` names the rule beside the other run
  rules and the weight beside the others.

## Testing Decisions

Good tests check what a caller sees: a priced cost, an explanation's words, an API answer, a page. Prior art is named per
seam.

- **Seam 1, the solver's own suite and the service contract tests** (`solver/tests`, `solver/service_tests`): the loader
  accepts the field, treats it as absent = no cap, refuses a bad value; on a known grid counted by hand, full runs beyond the
  cap cost the weight each, in the model and the validator; a run ended by leave; a run begun in the history and ended in the
  month counts; a run reaching the last day does not; the longest run at 0 and at 1 prices nothing; a weight of 0 prices
  nothing; the contract test's sample request and result carry the field. Prior art: `test_request.py`, `test_rules.py`,
  `test_preferences.py`, `test_contract.py`.
- **Seam 2, the backend API suite** on a throwaway PostgreSQL 18 with the scripted solver: the unit rule's default, edit,
  refusal, the unit manager alone editing it, the CNO and Deputy CNO reading it, its audit entry; the weight's default, edit
  and audit; the solve input, a re-plan's and a close's included, carrying the cap and the weight (`units` rules tests,
  `hospital` rules tests, `solves/tests/test_input.py`, `test_replan.py`).
- **Seam 3, the frontend's app-level Vitest suite** (`app.test.tsx` through `start` and `hold`): the field beside the
  longest run, hidden at a longest run of 1 and back with its value when raised, its refusal; the weights page's new weight.
  Ticket 11's rules: no raised timeout, no fake timers, no wait that proves something did not happen; six runs at once.
- **The real thing:** on a scratch stack, a month like ER's December with the cap at 3 gives no nurse more than three full
  runs where the month allows it, and the explanation shows the cost where it does not.

## Out of Scope

- A cap per nurse, or one scaled for leave or a part-time contract.
- A hard cap, a precheck for it, or refusing an edit, swap or cover for it.
- Counting runs shorter than the longest run, or capping runs of any length.
- Showing a nurse her full runs or their cost.
- Carrying anything about full runs into the next month.

## Further Notes

- **A full run that ends exactly on the month's last day is counted by neither month.** The month cannot see that it ended
  (the next day is the next month's), and the next month cannot change it (it is in the history), so pricing it there would
  be a constant cost the search cannot avoid. Ticket 47 should confirm this reading in its Worth your review.
- Capping full runs does not lower the month's shifts, so a nurse with fewer full runs works more, shorter runs: with 18
  shifts, a longest run of 3 and a cap of 2, at least 8 runs. The weight is what trades the two.
- After ticket 48 lands, a re-plan of ER's December on the dev stack is the check that Layan Alharbi has at most three.
