# 51: Overtime share: the unit rules, the weight and the explanation

**What to build:** A unit manager controls how the unit's overtime is shared. Unit rules gain three fields in the fairness group, beside the weekend spread: "Share overtime evenly", a switch, on by default ("Overtime is spread among the unit's nurses in proportion to the hours each owes."); "Overtime tolerance (hours)", default 12 ("How many hours of overtime a nurse may work above their fair share before it starts to cost."); and "Most a month's overtime share can move (hours)", default 12 ("The limit on how far what is carried can move a nurse's overtime share in one month."). Every unit, existing ones included, starts with the defaults; the two numbers take whole hours 0 to 744, refused otherwise with the usual field error; the unit manager alone edits them, the CNO and Deputy CNO read them as the other unit rules, and every change is audited as theirs are. The description of "Carry fairness between months" gains overtime, since that switch governs the carry for it too. The hospital's weights gain "Overtime away from the fair share", default 1, on the weights page with a description in the voice of the others; 0 switches the rule off hospital-wide; audited as the other weights. Every new solve, re-plan and close input carries the unit's three fields and the weight, and the draft's per-nurse explanation shows each nurse's overtime above her share and its cost by the solver's words. Hand edits, swaps, covers and requests are never refused for it, and the cover ranking, the Day view and every nurse page are unchanged. Spec: `.scratch/nurse-rostering-v2/specs/overtime-share.md`; the words: `GLOSSARY.md` (Overtime share).

**Blocked by:** 49 The solver prices overtime above a nurse's share, and carries her balance; 50 The carry-over chain carries a nurse's overtime balance, from her opening values to January

**Status:** ready-for-agent

- [x] The three unit rules: the defaults for new and existing units, the edit and its refusals, the unit manager alone editing, the CNO and Deputy CNO reading, the audit entries
- [x] The three fields on Unit rules beside the weekend spread, with their labels and help, visible whatever the hospital's hours rule says; the carry switch's description names overtime
- [x] The weight: default 1, edit, audit, and its description on the weights page; 0 prices nothing
- [x] The solve input, a re-plan's and a close's included, carries the three fields and the weight; a stored input without them still reproduces
- [x] The narrowing ticket 49 left in the tests that hold the app's blocks to every field of the solver's is removed
- [x] The draft's per-nurse explanation shows the cost of overtime above a share; nothing on My month, My roster, the Day view, a cover's offer or any nurse page
- [x] A hand edit, a swap and a cover that give a nurse overtime above her share are not refused, and her balance at the next projection shows it
- [x] Tests at the agreed seams: the backend API suite (units rules, hospital rules, `test_input.py`, `test_replan.py`) and the frontend app-level suite (six runs at once)
- [x] Driven on a scratch stack with the real solver: a month like ER's December 2026 (24 nurses, about 51 hours of overtime forced) gives no nurse more than one extra shift, and the next month's solve gives the extra shifts to other nurses; the explanation shows the cost where a month cannot avoid it
- [x] `docs/ARCHITECTURE.md` names the rule beside the other fairness rules and the weight beside the others; the OpenAPI document and the generated client regenerated; a migration giving existing units the defaults, `makemigrations --check` clean

## Comments

**Note from ticket 49 (2026-11-12):** the solver's fields are `department.share_overtime`, `overtime_tolerance`,
`overtime_carry_cap` and `general.weights.overtime_above_share`, optional in both versions. Delete `OVERTIME_SHARE_FIELDS` in
`units/tests/test_unit_rules.py`, `units/tests/test_rules_api.py` and `hospital/tests/test_rules.py`. Read ticket 49's
"Worth your review" on the weight against `nurse_overtime` before the weight's description.

**From ticket 49's review (the user, 2026-11-12).** The share rises with the unit's overtime, so with the overtime share
weight above `nurse_overtime`'s the solver can lower the rule's cost by adding overtime, and through rounding when many
nurses are priced at once. The user chose: the weights page and API refuse an overtime share weight above the hour of
overtime's weight (the refusal says why, beside the field), and this ticket's tests hold "with the rule on, the month's total
overtime is never above what it is with the rule off" on a month larger than ticket 49's small one. Ticket 49's comment
has the detail.

**From ticket 50's review (the user, 2026-11-12).** Rename the opening value's label on the rostering attributes form from
"Overtime above or below their fair share (hours)" to the glossary's term, "Overtime above or below their overtime share
(hours)", with its frontend test.

**Implemented on 2026-11-12,** on branch `claude/ticket-51-overtime-share-rules-410b31`, pull request
devjazzar/cp-sat-nurse-roster-app#29, from `main` at `fca2e29` (`3439449` the backend, the solver's sample and the regenerated
client; `a566a21` the screens; `3eeb14c` the larger month and the architecture document; `112a3d4` the review's points; `8d68553`
a merge of `main` with ticket 60; then this comment). The suites, locally, under the heavy-run lock, on `3eeb14c`:
- the backend under pytest on a throwaway PostgreSQL 18 container of my own: **3528 passed**; `makemigrations --check`: no
  changes;
- the solver's whole suite with the service tests: **738 passed** (two new tests on the larger month);
- the frontend: `npm test` **834 passed**, `npm run build` clean, the typecheck clean; the OpenAPI document exported again and
  the client generated from it, matching the export (again after the merge of ticket 60);
- GitHub's run on `112a3d4`: backend, solver, frontend (six at once), image and browser checks all green. The run on the head
  that reached `main` is named in the merge's line below.

**What the dev stack needs:** a **rebuild** (`docker compose up -d --build`): **two migrations** (`units.0006_overtime_share`,
which gives every unit the three rules, and `hospital.0008_overtime_above_share_weight`) and the SPA. No dependency, compose,
Dockerfile or solver code change (the solver's sample file and tests changed, not its package). **The rule is on from the
rebuild for every unit**: the next solve of ER's December prices it.

**What was built, criterion by criterion.**
- **The three unit rules.** `DEFAULT_UNIT_RULES` gains `share_overtime: True`, `overtime_tolerance: 12`,
  `overtime_carry_cap: 12`; `UnitRules` and `UnitRulesAnswer` the three fields, the two numbers whole hours bounded by the
  solver's own `MAX_OVERTIME_HOURS` (744), strict as every unit rule (2.5, 12.0, "12", true, null, -1, 745 refused on the
  field; a missing field refused, not defaulted). Migration `units.0006_overtime_share` writes the literal defaults into every
  unit that lacks them and leaves one that has them alone. Who edits, who reads and the audit entry are the unit rules' own:
  tests in `units/tests/test_rules_api.py` (the manager's change audited as `unit_rules.changed` with only the three before
  and after; the CNO and the Deputy CNO read and get 403 writing) and `test_unit_rules.py` (a new unit's block, a unit from
  before the rule, the migration leaving set values alone).
- **The screen.** Unit rules' Fairness group: "Spread weekend days fairly", then "Share overtime evenly", "Overtime tolerance
  (hours)", "Carry fairness between months" (its description now "Nights, weekend days and overtime above or below a nurse's
  fair share so far move this month's fair share."), "Most a month's share can move (shifts)", "Most a month's overtime share can
  move (hours)"; the help as the ticket words them; refused before the API is asked with the page's usual words ("Between 0
  and 744.", "Enter a whole number.") and the API's refusal put beside the field; the CNO and the Deputy read the three with
  their help. The page reads nothing of the hospital's hours rule, so the fields show whatever it says. `app.test.tsx`.
- **The weight.** `overtime_above_share`, "Overtime away from the fair share", default 1, after the three fairness weights on
  the weights page: "Each hour of overtime a nurse works above their overtime share, beyond the unit's overtime tolerance. At
  most the weight of Nurse overtime, so that adding overtime never lowers this cost." Audited as `weights.overtime_above_share`.
  0 makes the rule inactive (`nurse_roster.rules.active`), tested. **The cap (the user's decision on ticket 49's review):**
  the API refuses a share weight above `nurse_overtime`, on `weights.overtime_above_share` whichever of the two moved, with
  "Cannot be above Nurse overtime, or the solver could lower this cost by adding overtime."; the page refuses the same before
  sending, beside the field, focus on it, and shows the API's refusal there too. Equal is accepted.
  Migration `hospital.0008` writes 1, or `nurse_overtime` where that is below 1 (see Worth your review).
- **Every input.** The unit's rules and the hospital's weights already reach every solve, re-plan and close input whole
  (`unit_block`, `general_block`), so no code there changed; tests prove it: `solves/tests/test_input.py`
  (`TestTheOvertimeShare`: the four values set and loaded; the price in the solver's words on SOUND's June with Amal 24 h
  ahead: "Amal: 20 h overtime, share 4.7 h, 3 h priced", weight 1, penalty 3, counted by hand; a stored input without the
  four reads as the rule off and prices the rest exactly as before), `rosters/tests/test_replan.py` (a re-plan's input) and
  `closes/tests/test_close.py` (a close's input). The solver's sample `four_nurses.json` carries the three and the weight as a
  unit's defaults would (ticket 48 did the same for the full-run cap), so `shared` in the contract tests folded to Amal's
  balance alone and the solver's "input without the fields" test strips them first.
- **The narrowing.** `OVERTIME_SHARE_FIELDS` deleted in `units/tests/test_unit_rules.py`, `units/tests/test_rules_api.py` and
  `hospital/tests/test_rules.py`; the defaults tests hold the ER sample plus the three and the weight. Ticket 50's
  `shares_overtime` deleted in `closes/tests/test_close.py`: `TestTheOvertimeBalance` now runs on the sample's own rules, and
  its hand counts hold unchanged.
- **The explanation.** Nothing to build: the result's explanation follows the solver's registry, and the weights page's label
  names the rule. Tested at both seams: `solves/tests/test_history.py` (a result's rule row: penalty 3, weight 1, amount 3,
  "hour of overtime above the share", the largest match Amal's in the solver's words) and `app.test.tsx` (the Roster page's
  "Penalties per rule" names it "Overtime away from the fair share", "3 × 1", the nurse's line). No nurse page, My month, My
  roster, the Day view or a cover's offer changed (no file of theirs is in the diff).
- **Never refused.** A hand edit (`rosters/tests/test_versions.py`), a swap (`swaps/tests/test_swaps.py`) and a cover
  (`covers/tests/test_offers.py`) each give a nurse coming into June 24 h ahead one more 12 h shift: 32 h over, 12 h priced,
  accepted, and July's projected input carries her +24.47 and the others' −8.51 / −7.45, counted by hand in
  `closes.tests.test_close.one_more_shift_past_her_share`.
- **The larger month (the user's decision on ticket 49's review).** `solver/tests/test_overtime_share.py`: February 2026, ten
  nurses, six to eight on Day every day, 96 h of overtime forced, nothing free, one nurse held to 36 h over so six are priced at
  once: the month's total overtime is 96 h with the rule on and off (OPTIMAL both; one more extra shift would lower the rule by
  5 and cost 12). And with 12 h free, the eight extra shifts go one each; with the weight at 0 the solver gives 36, 36 and 24 h
  to three nurses.
- **Docs.** `docs/ARCHITECTURE.md`'s overtime share paragraph: the app's three rules beside the weekend spread, the carry
  switch, the weight, its cap and why, the two migrations, the sample, the inputs, nothing refused. The renamed label (the user's
  decision on ticket 50's review): "Overtime above or below their overtime share (hours)", its tests updated.

**What was driven, and how.** My scratch stack (`e2e/stack.sh up nr-t51`, seeded, the clock put back 31 days to 12 October), a
unit "Ward" made in the stack's shell with 24 nurses (12 women, 12 men, eight team leaders, one breastfeeding, "Rayan") and the
app's default rules but seven on Day and seven on Night every day: December owes 23 × 216 + 189 against 31 × 14 × 12, so 51 h of
overtime forced, as ER's December on the dev stack; November 74 h. A throwaway Playwright file in headless Chromium (removed
after), the real solver through the worker, 120 s a solve:
- as the manager, Unit rules: the three fields in Fairness in the order above, on, 12 and 12, with their help;
- November solved (FEASIBLE at the time limit), submitted, approved by the CNO: **no nurse holds a second extra shift**: 14
  nurses work 216 h against 208 owed (8 h over each), ten are 4 h short; total overtime 112 h, since 208 h is not a whole
  number of 12 h shifts;
- the CNO on the weights page: the weight at 1, 2 typed, Save: "Cannot be above Nurse overtime, or the solver could lower this
  cost by adding overtime." beside the field, focus on it, nothing sent;
- the Deputy CNO reading Ward's Fairness group: On, 12, On, 12, with the help;
- December's input carries the balances November left: +3.31 for the fourteen, −4.69 for the ten, −4.10 for Rayan;
- December solved: **the extra shifts go to the nurses who had none**: 8 h over each for eight (run 1), nine (run 2) and six
  (run 3) of November's ten short nurses, Rayan 1 h, nobody of November's fourteen. Three runs on fresh stacks: different
  nurses each November, the same rotation each December;
- the explanation where the month cannot avoid the cost (run 3): the manager typed 745 into "Overtime tolerance (hours)":
  "Between 0 and 744." beside it; then 0, and "Carry fairness between months" off, saved ("Saved."); December solved again:
  four nurses 8 h over and Rayan 1 h, 33 h in all, a share of 1.4 h each, and the Roster page's "Penalties per rule" shows
  "Overtime away from the fair share 24", "24 × 1, its weight. Counted in: hour of overtime above the share.", and for each of
  the four "Ward Nurse 04: w04: 8 h overtime, share 1.4 h, 6 h priced". (At 0 free with the carry still on, run 2 priced
  nothing: the nurses taking December's extra shifts carried −4.69 h, which put their targets near 7.4 h and left 0.56 h,
  rounded down.)
The stack is down; the throwaway file, the unit and the stack went with it.

**What was NOT checked:**
- The solves reached FEASIBLE at 120 s, not OPTIMAL: what the drive shows is what a time-limited solve gives, as a manager's would.
- ER's own December on the dev stack (the user's data): the main session's re-solve after the rebuild is the check the spec
  names ("Mana Mohamed no longer holds 36 hours").
- January: the balance resets there (ticket 50), so the rotation the spec's "January's overtime goes to four others" describes
  cannot come from the carry across December–January; the drive used November → December instead. See Worth your review.
- The browser suite locally; GitHub's run.

**Decisions taken here:**
- **Worth your review: the weight's description and the refusal's words.** Description: "Each hour of overtime a nurse works
  above their overtime share, beyond the unit's overtime tolerance. At most the weight of Nurse overtime, so that adding overtime
  never lowers this cost." Refusal: "Cannot be above Nurse overtime, or the solver could lower this cost by adding overtime."
  Both name "Nurse overtime" by its label on the same page. The same refusal words are written in `hospital/api.py` and
  `frontend/src/lib/weights.ts`, so the page says the same before and after a round trip.
- **Worth your review: the migration writes `min(1, nurse_overtime)`.** An installation pricing an hour of overtime at 0 would
  otherwise hold a weight its own page then refuses on every save. Tested.
- **Worth your review: the explanation's line** is the solver's own words, as for every rule: "Amal Saleh: Amal: 20 h overtime,
  share 4.7 h, 3 h priced" (the name, then the solver's line, which opens with the hospital ID). Nothing written here.
- **Worth your review: what the real solve showed about the defaults.** With 12 h free and the carry at 12, a month like ER's
  December comes out as single extra shifts and the rule prices nothing; its work is the carry, which moved December's extra
  shifts to November's short nurses in all three runs. At 0 free and with the carry off, the solve left 20 h short rather than
  give more overtime (33 h, against 49 with the defaults): an hour short and an hour of overtime both cost 1, and the rule makes
  overtime dearer, so it tips the month toward leaving nurses short. Worth knowing before a unit sets the tolerance at 0.
- **Worth your review: January.** As above: the spec's sentence that January's overtime goes to four others cannot hold with
  the balance reset in January (ADR 0004, ticket 50); within a year the carry rotates the extra shifts as the spec says.
- The weight sits after the three fairness weights on the weights page (the list's order is `WEIGHTS`'). The labels "Overtime
  away from the fair share" and the help's "fair share" are the spec's and the ticket's words, kept; the weight's description,
  mine, says "overtime share", the glossary's term.
- The solver's sample carries the rule on, as a unit's defaults do, so the backend's sample-based tests run with the rule on.

**Review:** `code-review` against `fca2e29`, both axes, on `3eeb14c`. *Standards:* no hard violation. (1) "fair share" against
the glossary's "overtime share" in the new words: the label and the two helps are the spec's and the ticket's, kept; the
weight's description, mine, now says "overtime share" (`112a3d4`). (2) The three field names repeated across tests: kept, each
test file names what it checks, as ticket 48's did. (3) The refusal's words written twice: kept, on purpose (above). (4) The
Fairness group's order written in the form, the read-only list and the labels: kept, the page's existing pattern. (5) The
helper `one_more_shift_past_her_share` in `test_close.py` imported by three apps' tests: kept, as `SOUND` is shared. (6) One
limit constant used for both numbers: a comment now says both are the solver's `MAX_OVERTIME_HOURS` (`112a3d4`). (7) A double
blank line: removed. *Spec:* nothing missing; it recounted every hand count and got the same. (a) No test that nurse pages are
unchanged, or that the fields show with the hours rule off: no file of those pages is in the diff, and the Unit rules page reads
nothing of the hours rule, so there is nothing to hold; kept as is. (b) The migration's `min(1, …)`, the description's second
sentence and the sample carrying the fields: kept, above. (c) The cap's check reads `nurse_overtime` declared before it, and
passes when that field is itself refused, whose own error then refuses the save: kept. The fixes were small; no second run. No
Codex review, by the brief.

**Things later tickets should know.**
- **57:** nothing of the chain changed here; the balance now moves for every unit (the rule is on by default), so the chain's
  carried `overtime_balance` is no longer 0 in practice.
- Whoever adds the next unit rule or weight: the fields reach every input by themselves (`unit_block`, `general_block`); add the
  default, the two schemas, a migration with literal values, the page's words (`unit-rules-words.ts`, `UNIT_RULE_LABELS`, read by
  the result comparison too) and, if the solver's sample should carry it, `four_nurses.json`.
- A weight bounded by another weight is a `field_validator` on `Weights` reading `info.data`, declared after the one it reads, and
  the same check in the page's `superRefine`.
