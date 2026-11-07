# 05: Solving with skills

**What to build:** Every solve, re-plan, draft check, submit, approval, restore and month close of a unit carries its nurses' skills and its skill needs to the solver, as a version 2 solve input. A nurse's skill is sent with its expiry when that falls in the month, with its past expiry when it expired before the month (so the bar applies and absence means no record), and with none when it is valid past the month or does not expire; the required skills and the weight come from the hospital rules. The manager reads the precheck's warnings and the result's explanation for the new rules in dates, not day numbers; the draft check names a need he breaks or a barred day he fills; submit and approval refuse a roster that breaks one on the month as it stands; a draft is warned that skills changed since its solve.

**Blocked by:** 01 Solver; 03 A nurse's skills; 04 Skill needs and the price

**Status:** ready-for-agent

- [ ] The solve input assembler writes version 2 with the nurse `skills` clamped to the month as the spec says, `required_skills` and `skill_shortfall` from the hospital rules, and the unit's `skill_needs` and flag. A stored version 1 input is still explained, compared with, restored from and re-closed from.
- [ ] A skill rename is carried through stored inputs when they are read, as a shift rename is; stored inputs keep the names they were given.
- [ ] A draft's changes since its solve gain the kind `skills`: a nurse's skills as the month would see them differ from the stored input's, or the needs, the flag, the required skills or the weight differ.
- [ ] Precheck warnings, the result's explanation, violations and the draft check show the two rules in the page's words with dates; the shortfall per rule reads like any soft rule, a hard need or a barred day like any hard rule.
- [ ] Submit and approval refuse a grid breaking a hard skill need or filling a barred day, as for any hard rule; a re-plan honours skills on the days it plans; the close reports what the facts broke and never refuses.
- [ ] The failure kind `refused` covers a version 2 input the solver refuses, read as rules to review.
- [ ] The architecture document's solve input, lifecycle and "what a solve shows" paragraphs say so.
- [ ] Tests at the web API seam with the scripted solver for the assembled input (each clamping case, a nurse with no record, a renewed skill), changes since, the words in dates, submit and approval refusals; a few end to end with the real solver in process on a small month where a need or a bar decides the roster.
