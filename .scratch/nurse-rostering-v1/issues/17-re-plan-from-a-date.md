# 17: Re-plan from a date

**What to build:** Mid-month the unit manager chooses a date and re-plans: days before it are facts (the roster in force plus recorded leave and pins), the solver keeps the new roster close to the current one through the change weight, and the result is a new version in force with a comparison against the previous one and the recorded facts that broke rules shown as facts, not errors.

**Blocked by:** 16 Changes after approval

**Status:** ready-for-agent

- [ ] Solve input assembler supports the published roster and the re-plan date; facts before the date are pinned from the roster in force, leave and pins
- [ ] Re-plan solve runs through the same queue with progress and cancel; success creates a version with origin 're-plan'
- [ ] Comparison view: cells changed, cost before and after, per-rule differences; elapsed violations listed as facts
- [ ] API tests cover the assembler's fact pinning and the version created, with the fake and once with the real solver
