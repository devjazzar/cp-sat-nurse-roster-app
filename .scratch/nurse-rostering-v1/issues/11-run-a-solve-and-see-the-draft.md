# 11: Run a solve and see the draft

**What to build:** The unit manager picks a month, sees a summary of what the solver will receive (nurses, leave, pins) and the precheck warnings, chooses a time limit up to the cap, and starts a solve. He sees his position in the hospital-wide queue, then the best cost so far and the number of improving rosters as it runs, can stop early and keep the best roster found, and when it finishes sees the draft grid with the penalties per soft rule. Each solve replaces the draft's grid. The hours of a shift an open month uses cannot be changed.

**Blocked by:** 10 Leave

**Status:** ready-for-agent

- [ ] Solve input assembler builds the complete solver JSON from hospital rules, unit rules, Ramadan days, holidays, nurses with opening values or zero carry-over, leave, and credits days outside start and end dates like leave; the input is stored verbatim with the solve
- [ ] Precheck shown before solving via the solver's precheck call
- [ ] Time limit defaults to the unit's and is capped by the technical setting
- [ ] Solve rows go through the queue; the worker runs one at a time under a hospital-wide lock, writes queue position and progress, relays cancellation, retries a failed solve once and records the failure reason
- [ ] The draft roster is created or its grid replaced on success; the result is stored verbatim
- [ ] Draft grid shows the nurse × date cells with shift colours, leave, and the penalties per rule
- [ ] Changing a shift's hours is refused while any open month's roster uses it
- [ ] API tests run the whole flow with the scripted solver fake and once end to end with the real solver service on the four-nurse sample, including cancellation and the queue order across two units

## Comments

**From ticket 07a (2026-11-05): a start date or gender can now change after a solve.** The CNO corrects them at `nurses.api.correct_details`, which has no guard because no roster exists yet. This ticket has to decide and test what follows. What must hold:

- A stored solve input stays as it was: it is the record of what the solver was given. The next solve reads the corrected values.
- A draft or roster solved from the old values must not pass silently as current. A new gender can break a gender requirement, and a new start date changes which days are credited like leave and can leave worked cells before the start. Compare the nurse's start date and gender with the latest solve input, warn the unit manager, and validate again before submit.
- `correct_details` can move a nurse's first placement back to cover an earlier start date (`membership.reach_back_to_start_date`). A nurse whose first placement begins before their start date is normal, and a nurse whose end date is before their start date was never present. A nurse who worked cannot be corrected into that state (`membership.start_date_fits`).

**From ticket 09 (2026-11-05).** Four things for this ticket.

- **The hours guard:** rosters arrive here, so add section 4's "hours cannot change while an open month's roster uses the shift" to `update_shift` in `hospital/catalogue_api.py`, as `refuse((("hours",), ...))` under its lock. Ticket 09 could not: there was nothing to check.
- **A nurse in the input:** start from `nurses.rostering.nurse_block(nurse, placement)`, with the placement of that month, since allowed shifts are on the placement. Add leave and pins, and replace the opening values and empty history with the carry-over once there is one.
- **A block the solver now refuses:** a unit's save checks its night and day shifts against the CNO's `night_rest` and `shift_switch` weights as they stood. A one-shift unit saved with them at 0 is refused if one rises. Show that like a gap from seeding, as "review the unit rules", not as a failed solve.
- **The time limit:** `Unit.default_time_limit` may be above the cap, if the System Admin lowered the cap after the unit's save. Use the lower. A nurse's `allowed_shifts_to_check` may still be up: consider a warning beside the precheck.

**From ticket 10 (2026-11-05): leave in the solve input.** The seam is proven in `nurses/tests/test_leave.py`; extend it there.

- **The nurses of a month:** `membership.rostered_in(unit, month)`, and each one's block from `nurse_block(nurse, membership.placement_in(nurse, month))`, not their latest placement. It leaves out a nurse who was never present. It does not filter on the account: a manager's profile whose account the System Admin deactivated, with no end date, is still on it, so decide what that means.
- **Leave:** `block["leave"] = nurses.rostering.leave_dates(nurse, month)`: ISO dates in order, each once. An empty list is accepted.
- **Days outside the start and end dates:** add them as a set, not a list. A date recorded before a correction can also be outside them (the manager sees it flagged), and the solver refuses `lists a day twice`.
- **No type in a solve input,** and a test holds it. It is stored for good and read by people who may not see one. The summary before a solve can count leave per nurse; the manager's grid may look a type up from `Leave` for their own month.
- **A pin on a leave day:** `load_request` refuses a shift pinned on a leave date (`on leave but pinned`), though `""` is fine and a desired or undesired day on leave is simply superseded. Leave does not look at pins, so the assembler must not pass such a pair on as a failed solve. Decide with ticket 13 which wins.
- **Leave changed since the last solve:** like a corrected start date (see the comment from 07a), a draft solved before leave was recorded, corrected or removed must not pass as current. Compare with the stored input, warn, and validate before submit.

