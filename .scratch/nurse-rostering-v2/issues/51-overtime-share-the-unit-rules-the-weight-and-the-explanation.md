# 51: Overtime share: the unit rules, the weight and the explanation

**What to build:** A unit manager controls how the unit's overtime is shared. Unit rules gain three fields in the fairness group, beside the weekend spread: "Share overtime evenly", a switch, on by default ("Overtime is spread among the unit's nurses in proportion to the hours each owes."); "Overtime tolerance (hours)", default 12 ("How many hours of overtime a nurse may work above their fair share before it starts to cost."); and "Most a month's overtime share can move (hours)", default 12 ("The limit on how far what is carried can move a nurse's overtime share in one month."). Every unit, existing ones included, starts with the defaults; the two numbers take whole hours 0 to 744, refused otherwise with the usual field error; the unit manager alone edits them, the CNO and Deputy CNO read them as the other unit rules, and every change is audited as theirs are. The description of "Carry fairness between months" gains overtime, since that switch governs the carry for it too. The hospital's weights gain "Overtime away from the fair share", default 1, on the weights page with a description in the voice of the others; 0 switches the rule off hospital-wide; audited as the other weights. Every new solve, re-plan and close input carries the unit's three fields and the weight, and the draft's per-nurse explanation shows each nurse's overtime above her share and its cost by the solver's words. Hand edits, swaps, covers and requests are never refused for it, and the cover ranking, the Day view and every nurse page are unchanged. Spec: `.scratch/nurse-rostering-v2/specs/overtime-share.md`; the words: `GLOSSARY.md` (Overtime share).

**Blocked by:** 49 The solver prices overtime above a nurse's share, and carries her balance; 50 The carry-over chain carries a nurse's overtime balance, from her opening values to January

**Status:** ready-for-agent

- [ ] The three unit rules: the defaults for new and existing units, the edit and its refusals, the unit manager alone editing, the CNO and Deputy CNO reading, the audit entries
- [ ] The three fields on Unit rules beside the weekend spread, with their labels and help, visible whatever the hospital's hours rule says; the carry switch's description names overtime
- [ ] The weight: default 1, edit, audit, and its description on the weights page; 0 prices nothing
- [ ] The solve input, a re-plan's and a close's included, carries the three fields and the weight; a stored input without them still reproduces
- [ ] The narrowing ticket 49 left in the tests that hold the app's blocks to every field of the solver's is removed
- [ ] The draft's per-nurse explanation shows the cost of overtime above a share; nothing on My month, My roster, the Day view, a cover's offer or any nurse page
- [ ] A hand edit, a swap and a cover that give a nurse overtime above her share are not refused, and her balance at the next projection shows it
- [ ] Tests at the agreed seams: the backend API suite (units rules, hospital rules, `test_input.py`, `test_replan.py`) and the frontend app-level suite (six runs at once)
- [ ] Driven on a scratch stack with the real solver: a month like ER's December 2026 (24 nurses, about 51 hours of overtime forced) gives no nurse more than one extra shift, and the next month's solve gives the extra shifts to other nurses; the explanation shows the cost where a month cannot avoid it
- [ ] `docs/ARCHITECTURE.md` names the rule beside the other fairness rules and the weight beside the others; the OpenAPI document and the generated client regenerated; a migration giving existing units the defaults, `makemigrations --check` clean

## Comments

**Note from ticket 49 (2026-11-12):** the solver's fields are `department.share_overtime`, `overtime_tolerance`,
`overtime_carry_cap` and `general.weights.overtime_above_share`, optional in both versions. Delete `OVERTIME_SHARE_FIELDS` in
`units/tests/test_unit_rules.py`, `units/tests/test_rules_api.py` and `hospital/tests/test_rules.py`. Read ticket 49's
"Worth your review" on the weight against `nurse_overtime` before the weight's description.
