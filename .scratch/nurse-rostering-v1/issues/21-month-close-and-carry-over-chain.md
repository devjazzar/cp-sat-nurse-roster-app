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
