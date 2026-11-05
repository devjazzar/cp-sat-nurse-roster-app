# 17: Re-plan from a date

**What to build:** Mid-month the unit manager chooses a date and re-plans: days before it are facts (the roster in force plus recorded leave and pins), the solver keeps the new roster close to the current one through the change weight, and the result is a new version in force with a comparison against the previous one and the recorded facts that broke rules shown as facts, not errors.

**Blocked by:** 16 Changes after approval

**Status:** ready-for-agent

- [ ] Solve input assembler supports the published roster and the re-plan date; facts before the date are pinned from the roster in force, leave and pins
- [ ] Re-plan solve runs through the same queue with progress and cancel; success creates a version with origin 're-plan'
- [ ] Comparison view: cells changed, cost before and after, per-rule differences; elapsed violations listed as facts
- [ ] API tests cover the assembler's fact pinning and the version created, with the fake and once with the real solver

## Comments

**From ticket 11 (2026-11-05).** `solves.input.assemble` has no re-plan yet. A month that has started can be solved from scratch today, which replaces the draft's whole grid: `_what_stops_it` refuses only a month that is over. Once a month has an approved roster a plain solve should be refused in favour of a re-plan.

**From ticket 12 (2026-11-05).** `rosters.drafts.why_not_restore` refuses a month that is over and allows the month under way, as `_what_stops_it` does for a solve. When this ticket refuses a plain solve once a month has an approved roster, restore needs the same refusal, which ticket 14's state check will already give. A result's `replan` block is not shown anywhere yet: `solves/history_api.py`'s `SolveResult` leaves it out, and section 8's "in a re-plan the comparison with the roster in force" is yours to add to `components/solve-result.tsx`.
