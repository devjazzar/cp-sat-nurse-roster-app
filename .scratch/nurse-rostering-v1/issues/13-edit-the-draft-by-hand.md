# 13: Edit the draft by hand

**What to build:** The unit manager clicks a cell of the draft and pins a shift, pins a day off, or clears it; within a moment he sees whether the grid now breaks a hard rule and how its cost changed, through the solver's validate call. A re-solve keeps his pins.

**Blocked by:** 11 Run a solve

**Status:** ready-for-agent

- [ ] Cell editor for pin shift, pin off, clear; pending edits held client-side and saved explicitly
- [ ] Live validation debounced through one hook, calling validate with the grid as it would be; violations and cost delta shown
- [ ] Saved pins stored as pinned cells with origin 'manager' and included in the next solve input
- [ ] API tests cover saving pins, validation pass-through and that a re-solve keeps pins

## Comments

**From ticket 10 (2026-11-05).** The solver refuses a shift pinned on a leave date. The cell editor must refuse pinning a shift on one, and leave can now arrive on a date already pinned: `_refuse_dates` in `nurses/leave_api.py` is the path of every write that adds a date, where a refusal or a warning belongs. Removing leave goes only through `_rows_to_change`, and leaves the cell as it stands.

**Decisions from the user (2026-11-05).** Leave wins over a pinned shift.

- **Recording leave on a pinned day removes the pin and tells the manager.** The write is not refused. `_refuse_dates` in `nurses/leave_api.py` is the path of every write that adds a date, as the comment above says, so the removal belongs on that path and the answer has to carry what the page tells the manager.
- **Pinning a shift on a leave day is refused,** in the cell editor and when saving pins.
