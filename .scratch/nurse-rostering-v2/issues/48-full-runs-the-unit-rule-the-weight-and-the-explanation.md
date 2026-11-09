# 48: Full runs: the unit rule, the weight and the explanation

**What to build:** Unit rules gain "Most full runs in a month", default 3 for every unit, existing ones included, on the Unit rules page beside the longest run, with the help "A full run is as many shifts in a row as the longest run allows. Each one beyond this costs the solver, which then breaks the work into shorter runs." It shows only while the longest run is above 1, and keeps its value while hidden and through any change to the longest run; a whole number 0 to 31, refused otherwise with the usual field error; edited by the unit manager alone, read by the CNO and Deputy CNO as the other unit rules, audited as they are. The hospital's weights gain "Full run above the most", default 4, on the weights page with a description in the voice of the others; 0 switches it off hospital-wide; audited as the other weights. Every new solve, re-plan and close input carries the unit's cap and the weight, and the draft's per-nurse explanation shows the cost by the solver's words, as for a weekend above the most. Hand edits, swaps, covers and requests are never refused for it, and no nurse page changes. Spec: `.scratch/nurse-rostering-v2/specs/full-runs.md`; the words: `GLOSSARY.md` (Run, Full run).

**Blocked by:** 47 The solver prices full runs above the cap

**Status:** ready-for-agent

- [ ] The unit rule: default 3 for new and existing units, the edit and its refusal, the unit manager alone editing it, the CNO and Deputy CNO reading it, its audit entry
- [ ] The field on Unit rules beside the longest run, hidden at a longest run of 1 and back with its value when raised, with its label and help
- [ ] The weight: default 4, edit, audit, and its description on the weights page; 0 prices nothing
- [ ] The solve input, a re-plan's and a close's included, carries the cap and the weight; a stored input without them still reproduces
- [ ] The draft's per-nurse explanation shows the cost of full runs above the cap; nothing on My month, My roster or any nurse page
- [ ] Tests at the agreed seams: the backend API suite (units rules, hospital rules, `test_input.py`, `test_replan.py`) and the frontend app-level suite (six runs at once)
- [ ] Driven on a scratch stack: a month like ER's December with the cap at 3 gives no nurse more than three full runs where the month allows it, and the explanation shows the cost where it does not
- [ ] `docs/ARCHITECTURE.md` names the rule beside the other run rules and the weight beside the others; the OpenAPI document and the generated client regenerated

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
