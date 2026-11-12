# 50: The carry-over chain carries a nurse's overtime balance, from her opening values to January

**What to build:** A nurse's overtime balance, how far her overtime has stood above or below her overtime share so far this year, is one more carried value in the carry-over chain, from the result's carry-over block: projected from the roster in force, corrected at the close from the month's facts and re-worked at a re-close; carried unchanged through a month with no roster for her; following her across a transfer; reset to zero in the carry-over handed into January, with overtime this year and the night and weekend balances; and 0 out of a close stored before the balance existed, with nothing worked back through earlier months. Her opening values gain it: "Overtime above or below their fair share (hours)", default 0, on the rostering attributes form beside the night and weekend balances, read and written through the same API by the same people, locked with them once her first month closes and audited with them. Every solve input, a re-plan's and a close's included, carries each nurse's balance from the chain. Until ticket 51 switches the rule on for a unit the solver hands every balance on unchanged, so this ticket is proven with the solver's unit fields set in the tests. Spec: `.scratch/nurse-rostering-v2/specs/overtime-share.md`; the words: `GLOSSARY.md` (Overtime share, Carry-over, Opening values); the reason for the chain: ADR 0004.

**Blocked by:** 49 The solver prices overtime above a nurse's share, and carries her balance

**Status:** ready-for-agent

- [ ] The chain carries the balance from the result's carry-over block: projected from the roster in force, corrected at the close with what really happened, re-worked on a re-close
- [ ] A month with no roster for her hands her balance on unchanged; a transfer carries it into the new unit; the carry-over into January has it at zero; a close stored before the balance existed hands on 0
- [ ] The opening value: default 0, edited and read by those who edit and read the other opening values, refused outside the solver's bound with the usual field error, locked once her first month closes, in the audit entry beside the others
- [ ] The rostering attributes form shows it beside the night and weekend balances with its label and help, and read-only once locked
- [ ] Every solve input, a re-plan's and a close's included, carries each nurse's balance from the chain; a nurse's first month takes her opening value
- [ ] The narrowing ticket 49 left for the carried value is removed
- [ ] Tests at the agreed seams: the backend API suite (closes: projected, corrected, re-close, no roster, transfer, January, a close stored before, opening values; nurses: the opening value; solves: the input and a re-plan's) and the frontend app-level suite (six runs at once)
- [ ] `docs/ARCHITECTURE.md`: the balance among the opening values, in the chain's paragraph and in the January reset; the OpenAPI document and the generated client regenerated; a migration for the new opening value, `makemigrations --check` clean

## Comments

**Note from ticket 49 (2026-11-12):** the balance already passes through the chain (`closes.chain.CARRIED`), 0 from opening
values (`chain.opening`, a literal to replace) and from a close stored before it (`CARRIED_SINCE`); the January reset is not
done (`NEW_YEAR`). Ticket 49 left no narrowing for the carried value, so the criterion removing one has nothing to act on.
Details in ticket 49's comment, "Things later tickets should know".
