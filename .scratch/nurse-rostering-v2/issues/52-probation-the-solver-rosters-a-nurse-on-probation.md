# 52: The solver rosters a nurse on probation

**What to build:** The vendored solver's contract gains two optional per-nurse fields: that she is on probation, and her preceptor's id (absent means not on probation and no preceptor, so every stored solve input and close input still loads and gives what it gave). A nurse on probation counts toward nothing about a shift (headcount minimum and maximum, team leader, both genders, score target and balance, skill needs) and is left out of the day and night fairness, the weekend fairness, the overtime share and the unit's overtime totals, with her fairness balances zero in and zero out. She works no night shift. She works less than the hours she owes plus the length of her shortest allowed shift, the excess recorded as her own overtime; the shortfall rule is unchanged. One hard rule makes her follow her preceptor: on a followable day (a free day her preceptor works a day shift she is allowed, and she is not on leave, outside her dates or pinned) she works her preceptor's shift or is off, never another shift, and if any followable day is left off she works no free day that is not followable. With no preceptor there is nothing to follow, and precheck warns. Nothing in the app changes in this ticket. Spec: `.scratch/nurse-rostering-v2/specs/probation.md`; the words: `GLOSSARY.md` (Probation, Nurse on probation, Preceptor); the reasons: ADR 0014.

**Blocked by:** 49 The solver prices overtime above a nurse's share, and carries her balance (both change the solver's input, and she is left out of the overtime share)

**Status:** ready-for-agent

- [ ] The request loader accepts the two nurse fields, treats them as absent = not on probation and no preceptor, and refuses, with the usual `request: <field path>` error, a preceptor that is not another nurse of the input, one who is herself on probation, one named by two nurses, and a preceptor on a nurse not on probation; the problem's schema version notes the change
- [ ] She counts toward nothing about a shift: a headcount minimum is not met by her, a maximum not exceeded by her, a team leader, both-genders, score and skill rule not satisfied by her; the fairness figures, the overtime share and the unit's overtime totals are the same with and without her; her carried fairness balances are zero out
- [ ] She works no night shift: her allowed shifts are narrowed by the unit's night shift, and a pin of the night shift on a free day of hers is refused
- [ ] Her hours stay under what she owes plus her shortest allowed shift, shown with 12-hour shifts (208 owed, 18 shifts, 8 hours of overtime) and 8-hour shifts (26 shifts, none); the excess is her overtime for the month and the year; she may still end under one shift short and carry the debt
- [ ] The following rule, in the registry as a hard rule: on every followable day she is on her preceptor's shift or off; hours win when her preceptor's day shifts are more than her hours hold, and she then works no free day that is not followable; a pin and leave hold over following; elapsed days are facts; her own rest, run and succession rules apply
- [ ] With no preceptor she is rostered on freely placed day shifts, and precheck names her
- [ ] The validator's and the explanation's words name the nurse, the day, her preceptor's shift and hers; the per-nurse explanation carries them
- [ ] Tests in the constraint-verifier style for each of the above, expected values counted by hand; the service contract test's sample request and result carry the fields; the solver's suite, the service tests and the contract tests pass
- [ ] `solver/DESIGN.md` gains the contract change; `docs/ARCHITECTURE.md` section 6 names the fields

**Worth your review, already known:** her rounding overtime is on her own record but outside the unit's overtime totals (the department cap and the overtime share), so it does not move her colleagues' shares; with shifts of several lengths the hours bound is her shortest allowed shift, the mirror of the existing shortfall bound.

## Comments
