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
