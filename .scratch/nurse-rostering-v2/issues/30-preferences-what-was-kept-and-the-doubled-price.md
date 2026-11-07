# 30: What was kept, and the doubled price

**What to build:** The carry-over chain carries each nurse's count of unkept preferences out of every month, from the solver's carry-over block: projected from the roster in force, corrected at the close and re-worked at a re-close, 0 through a month with no roster for her and for her first month, not reset in January, following a transfer. The solve input hands the count to the solver, so a nurse one of whose preferences the month before did not keep pays double this month in every solve and re-plan. My month tells her: once the roster is approved the Preferences card says "4 of 5 kept" and marks each preference Kept, Not kept or On leave, read from the roster in force however it came about (edits and re-plans count) and, once the month is closed, from the close in force; before approval it says "No roster yet"; and when it applies, "One of your preferences was not kept in May, so this month yours count double.", read from the same chain value the solve input takes. Spec: `.scratch/nurse-rostering-v2/specs/preferences.md`; the words: `GLOSSARY.md` (Kept); the reasons: ADR 0013 and ADR 0004.

**Blocked by:** 28 The solver prices a preference double after an unkept month, and carries what was not kept; 29 A nurse's preferences, kept by the solver at a price

**Status:** ready-for-agent

- [ ] The chain carries the count as one more carried field from the result's carry-over block; a month with no roster for her hands on 0; opening values carry 0 with no new field; January does not reset it; a transfer carries it along; a re-close re-works it
- [ ] The solve input, a re-plan's included, carries each nurse's count; a nurse with a count above zero pays double in a real solve on a scratch stack, and the draft's per-nurse explanation says so
- [ ] My month's preference read carries each preference's outcome (`kept`, `not_kept`, `on_leave`, none before approval), the counts kept and keepable, and whether she counts double this month with the month that caused it
- [ ] Outcomes are read from the version in force on the month as it stands, so a manager's edit or a re-plan that breaks one counts as not kept; a closed month's from the close in force's facts; a date on leave is On leave and counted neither way
- [ ] The Preferences card: "4 of 5 kept" once approved, "No roster yet" before, each preference Kept, Not kept or On leave, and the doubled line with its month; nothing of a colleague
- [ ] Tests at the agreed seams: closes (projected, corrected with late leave, no roster, first month, January, transfer, re-close), solves' input, rosters' own month with expected values counted by hand on the sound rosters fixture, and the frontend app-level suite (six runs at once)
- [ ] `docs/ARCHITECTURE.md` sections 6 and 7 updated; the OpenAPI document and the generated client regenerated
