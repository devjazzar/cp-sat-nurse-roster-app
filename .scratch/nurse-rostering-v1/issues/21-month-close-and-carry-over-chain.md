# 21: Month close and the carry-over chain

**What to build:** On the first day after a month, at the close time, the application closes every unit with an approved roster: the roster in force plus recorded leave and pins becomes fact, the solver validates and reports what the facts broke, and each nurse's carry-over is stored. The next month's solve input starts from the latest closed carry-over projected through the approved rosters in between; a close always takes the previous closed month's carry-over as input. The unit manager may record late facts and re-close while the next month is open, sees each nurse's projected carry-over, and opening values lock after the first close. The carry-over into January resets overtime-to-date and the fairness balances; transfers and shift-code renames are honoured in histories.

**Blocked by:** 17 Re-plan from a date

**Status:** ready-for-agent

- [ ] Close job on the schedule and on demand; a unit with no approved roster is skipped; the close result and per-nurse carry-over stored with source 'closed'
- [ ] Projection computed with the same solver computation and stored with source 'projected'; the assembler takes the latest closed carry-over projected forward, including the shift history
- [ ] Re-close allowed until the next month is closed; refused afterwards
- [ ] Opening values locked after the nurse's first close
- [ ] January input resets overtime-to-date and both fairness balances
- [ ] Shift-code renames mapped into histories; a transferred nurse's carry-over follows her into the new unit from the effective month
- [ ] 'Closed' shown in the overview; projected carry-over per nurse shown to the manager
- [ ] API and direct tests cover the chain across three months with the fake solver and one real closing of the four-nurse sample

## Comments

**From ticket 07a (2026-11-05): closed months have to stop a correction.** `nurses.api.correct_details` lets the CNO change a nurse's start date and gender and has no guard, because no month closes yet. Add the guard there, with its test:

- A closed month is a fact. Its stored close result and carry-over are never rewritten by a correction.
- **Start date:** refuse on `start_date` (`hospital.api.refuse`) a change that would alter which days counted in a closed month, on either the old or the new date's side. The refusal should say which month. While the month can still be re-closed, the alternative is to allow the change and tell the manager to re-close: decide which and record why.
- **First placement:** `membership.reach_back_to_start_date` must not move a placement back into a closed month.
- **Gender:** it changes no hours or carry-over, so it need not be refused. It applies from the next solve on, and closed months keep what their stored input says.

**From ticket 09 (2026-11-05).** Opening values are "editable until her first month closes", and no close exists yet, so nothing refuses them. Add that to `update_nurse_attributes` in `nurses/attributes_api.py`, refusing on the field and leaving the other attributes open. They travel in one body with the attributes, so compare them rather than refusing the save.

**From ticket 10 (2026-11-05): closed months have to stop leave too.** `record_leave`, `change_leave` and `remove_leave` in `nurses/leave_api.py` accept any date, because no month closes yet. In `_refuse_dates` and `_rows_to_change`, refuse a date in a closed month beside First day, leaving it open while the month can be re-closed, with a prompt to re-close: late facts are what that is for. A close reads `nurses.rostering.leave_dates`, adding days outside the start and end dates as a set. The month's manager is the one who answers, including a nurse since transferred, whom `membership.placed_in` finds.

**From ticket 11 (2026-11-05).** `solves/input.py` starts each nurse from `nurse_block`, so the opening values and an empty history, and that is where the projected carry-over replaces them, with `renamed_shifts` once a history can name an old code. "Open month" in `rosters.drafts.using_shift`, the hours guard, today means every month: narrow it to months not closed.

**From ticket 12 (2026-11-05).** A result's per-nurse `carry_over` is stored and shown nowhere: the panels show the hours accounting and cost the ticket named. If the close page wants to show it, `SolveResult.nurses` is where it would join. `elapsed_violations` is shown under "Recorded facts that broke rules" (`components/solve-result.tsx`), and the close's own report could reuse it. `rosters.drafts.using_shift` stays the hours guard: a shift no open draft uses can change hours while an older stored result still holds it, which is why `why_not_restore` compares a result's hours with the catalogue's. Once closed months count as not open, that holds the same.

**From ticket 13 (2026-11-05).** Pins exist: `rosters.models.PinnedCell`, current while `removed_at` is null. Three things for the close.

- **A month that is over holds up nothing:** a shift's hours and retiring it, a unit dropping a shift and narrowing a nurse's allowed shifts all look only at pins from the current month on (`rosters.pins.counted_uses`, `_counted_from_now_on`). So a closed or unclosed past month can hold a pin on a shift since retired, renamed or had its hours changed. The close has to read such a pin under the shift's code now and with the hours it had, as it reads the roster in force.
- **A pin set aside counts for nothing.** `rosters.pins.month_pins` sets aside a pin on leave, outside the nurse's dates, on a shift the unit no longer works or the nurse may not work, or of a nurse no longer in the month, and leaves it out of a solve input. The close's "every recorded pin becomes fact" should take the same set, from the same function.
- **Saving a pin on a month that is over is refused** (`rosters.api._why_not_edit`), as a solve and a restore are. Re-closing with late facts may want to reopen that for the month before; it is one place.

**From ticket 14 (2026-11-05).** "The roster in force" is the approved roster's latest `RosterVersion` (`roster.versions.first()`), whose grid is also `Roster.grid` under today's codes. A month still submitted at the close time has no roster in force and, as section 5 says, is skipped.

**From ticket 15 (2026-11-06).** A nurse's own month (`GET /api/rosters/mine/month`, page My month) shows hours for this month and later only. A month already over shows its leave and no hours, as My roster shows no month before this one.

- **What to change:** once a month is closed, its closed figures are the right answer for it: hours worked, overtime, and what was carried. `rosters.reading_api._in_force` cuts at `membership.this_month()`. Open earlier months there from the close.
- **"Carried into next month"** is the projected carry-over today, worked out from the version in force on the month as it stands. The page already says it is worked out again at the month close.
- **A close is not notified.** Add an `Event` in `notifications.models` and a function in `notifications/sending.py` if the manager should be told what the facts broke.

**From ticket 16 (2026-11-06).** What holds for a month that is over, until this ticket.

- **No edit:** the roster in force of a month already over cannot be changed by hand (`rosters.api._why_not_edit`, `IN_FORCE_OVER`). Re-closing with late facts may want to reopen that for the month before: it is one place.
- **Leave recorded late on a month that is over makes no version** (`rosters.versions.take_off_for_leave` skips months before `membership.this_month()`), so that month's grid can still hold a shift on a day of leave. The close reads leave itself and leave wins, as it already does in `rosters.own_month`.
- **The month under way** is edited and versioned as any other approved month. Its days already passed can change too: a sick day recorded the day after takes that shift off.
- "The roster in force" is still `roster.versions.first()`, and `Roster.grid` equals its grid under today's codes.

**From ticket 17 (2026-11-06).** Re-plans exist, and the close is the same mechanism with the date set to the first day after the month.

- **The input:** `solves.input.assemble_replan(unit, month, replan_from, in_force)` builds the month as a solve would, with the roster in force under today's codes as `published` (exactly the month's nurses: one who left is dropped, one who joined gets an empty row) and `replan_from`. Pass the first day after the month and the solver makes every day a fact: pins that count, then leave and the days outside a nurse's dates, then the roster in force. A pin set aside is no fact there either: check that is what the close wants.
- **Not through the re-plan's endpoint:** `solves.replans.why_not_from` refuses the first day after the month ("Choose a date in …") and `why_not` refuses a month that is over. Those refusals are the re-plan's; the close calls the solver's validate path or its own job.
- **A re-plan that ends after its month did** is `ReplanOutcome.MONTH_OVER` and changes nothing, so the roster a close reads is never moved by a late re-plan.
- `Solve.replan_from` marks a re-plan in the manager's history. The System Admin's history does not show it (a closed list); keep a close out of it the same way or decide.

**From ticket 19 (2026-11-06).** An accepted request is a pin of origin `request`, so the close reads it like any pin, through `rosters.pins.month_pins`. A request of a month that is over can no longer be accepted, edited or cancelled (`requesting.deciding.MONTH_OVER`), and a pending one stays pending until its manager rejects it: decide whether the close should end those. Re-closing with late facts that reopens pins for the month before would reopen requests' too, in `requesting.deciding.why_the_pin_cannot_move`.

**From ticket 20 (2026-11-06).** Swaps exist (`swaps`). An approved swap's cells are pins of origin `swap`, read by the close like any other through `rosters.pins.month_pins`. A swap still waiting when its month ends has already expired by date (`swaps.expiring`), and approving one of a month that is over is refused. A re-close or late fact that makes a version through `rosters.versions.make_version` expires waiting swaps whose cells it changes, as every version does; one that writes `Roster.grid` another way would skip that.
