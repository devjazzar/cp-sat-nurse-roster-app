# 09: Unit rules and rostering attributes

**What to build:** The unit manager edits his unit's rules (the shifts it works, chosen from the catalogue; headcounts per shift for weekdays and weekends; team leader and gender requirements; score targets; night rest; run limits; fairness; weekend limits; switches; the request cap and default time limit), each explained and seeded with the reviewed defaults. He sets each nurse's rostering attributes (team leader, score, allowed shifts, Ramadan-reduced, breastfeeding) and her opening values. The CNO is refused when retiring a shift a unit still uses.

**Blocked by:** 05 Shift catalogue; 07 Nurses

**Status:** ready-for-agent

- [ ] Unit rules form with every field of the solver's unit block, explanations, validation; clears the review flag on save; audited
- [ ] Shifts used are a subset of the active catalogue; retiring a shift in use by any unit is refused with the unit named
- [ ] A shift's rename carries through every unit's rules in the same transaction (see ticket 06's comments)
- [ ] Per-nurse rostering attributes form; allowed shifts restricted to the unit's shifts
- [ ] Opening values editable (overtime this year, hours balance, two fairness balances), default zero
- [ ] Only the unit's manager edits; CNO and Deputy CNO read; nurses never see attributes
- [ ] API tests cover rules, the retire guard, attributes and scoping

## Comments

**From ticket 07a (2026-11-05): gender stays out of this ticket's form.** The CNO sets and corrects it (`nurses.api.correct_details`), and section 3 now says so. It is not on this ticket's list of attributes, though the glossary counts it among them.
