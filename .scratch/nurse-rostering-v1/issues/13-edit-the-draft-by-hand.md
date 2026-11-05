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

**From ticket 11 (2026-11-05).** Pins go in `solves/input.py`, `assemble`, which counts them for the summary too: `Summary.pins` in `solves/api.py` is a literal 0 until then. Its docstring holds the decision: if a row ever holds a shift pinned on a credited day, leave wins and the pin is dropped there, so it is not a failed solve. A pin in the input also has to be part of `changes_since`, or a pin saved after a solve will not warn. `Roster.grid` is what the cell editor edits, and it follows renames through `rosters.drafts.carry_rename_through_grids`.

**From ticket 12 (2026-11-05).** Three things once a draft can be edited.

- **Restoring and pins.** `rosters.drafts.replace_grid` swaps the whole grid. A restored result knows nothing of a pin saved since it was solved, so a saved pin can then disagree with the grid. Decide whether a restore keeps pins, removes them or refuses, and whether a pin saved since counts in `changes_since`.
- **Restoring the draft's own solve** is refused today as "This result is the draft already" (`why_not_restore`, and `in_draft` in the history), because nothing could differ. After a hand edit it can differ, and a manager may want the solve's grid back, so that refusal has to look at whether the grid was edited. `in_draft` then means "came from this solve", not "is this result".
- **`roster_month`'s `last_solve`** counts a failed solve as old news once `Roster.updated_at` is newer than it. That was written for a restore. A hand edit also moves `updated_at`, so a solve that failed before an edit stops being mentioned. Check that is what you want.
