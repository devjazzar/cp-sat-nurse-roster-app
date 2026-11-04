# 13: Edit the draft by hand

**What to build:** The unit manager clicks a cell of the draft and pins a shift, pins a day off, or clears it; within a moment he sees whether the grid now breaks a hard rule and how its cost changed, through the solver's validate call. A re-solve keeps his pins.

**Blocked by:** 11 Run a solve

**Status:** ready-for-agent

- [ ] Cell editor for pin shift, pin off, clear; pending edits held client-side and saved explicitly
- [ ] Live validation debounced through one hook, calling validate with the grid as it would be; violations and cost delta shown
- [ ] Saved pins stored as pinned cells with origin 'manager' and included in the next solve input
- [ ] API tests cover saving pins, validation pass-through and that a re-solve keeps pins
