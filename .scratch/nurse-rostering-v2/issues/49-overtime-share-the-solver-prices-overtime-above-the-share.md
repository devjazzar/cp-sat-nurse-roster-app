# 49: The solver prices overtime above a nurse's share, and carries her balance

**What to build:** The vendored solver's contract gains the overtime share. The department block gains three optional fields: whether the unit shares its overtime, the tolerance in whole hours and the limit on the carry in whole hours (0 to 744 each); the weights gain the hour of overtime above the share; each nurse gains one optional carried value, her overtime balance in hours. Absent means the rule off, a weight of 0 and a balance of 0, so every stored solve input and close input still loads and gives what it gave. A nurse's share is the unit's overtime in the month times the hours she owes over the hours all the nurses in the input owe; her target is her share less her carried balance (held within plus or minus the limit) when the unit carries fairness between months; her priced hours are her overtime above the target, beyond the tolerance, and never more than her overtime, so a nurse with no overtime costs nothing and hours below a share are never priced. The cost is the weight per priced hour, in the model's objective and in the validator's explanation alike; the match names the nurse, her overtime, her share and the hours priced. The result's carry-over block gains her balance for next month: her balance in, plus her overtime, minus her share, moving while the unit's switch is on whether or not it carries fairness, and handed on unchanged with the switch or the hospital's hours rule off. The existing price per hour of overtime, the unit's soft cap and the hard per-nurse caps are unchanged. The solver's own suite and the service contract tests cover it, and the CLI shows it on a sample. Nothing a user sees changes in this ticket. Spec: `.scratch/nurse-rostering-v2/specs/overtime-share.md`; the words: `GLOSSARY.md` (Overtime share).

**Blocked by:** 47 The solver prices full runs above the cap (both change the solver's input, so they go one after the other)

**Status:** ready-for-agent

- [x] The request loader accepts the three department fields, the weight and the nurse's balance, treats each absent one as off or 0, and refuses a bad value (a negative or non-integer number of hours, a boolean, hours above 744, a balance beyond the solver's bound) with the usual `request: <field path>` error; the problem's schema version notes the change
- [x] One soft rule in the registry with its weight, active when the unit's switch is on, the weight is above 0 and the hours rule is on; model, validator and explain follow the registry
- [x] On a small month whose headcounts force a known amount of overtime, with the rule on no nurse holds a second extra shift while another holds none; the cost of a hand-built uneven grid is the weight times the hours counted by hand; a solve's cost and a validation of the same grid agree
- [x] A nurse with no overtime costs nothing whatever she carries; hours below a share cost nothing; with the rule on the month's total overtime is never above what it is with the rule off
- [x] A share follows the hours owed: lower for a nurse on leave and one on reduced hours, none for a nurse who owes none
- [x] A carried balance moves the target, is held within the limit, and is ignored when the unit does not carry fairness between months
- [x] The carry-over block's balance, counted by hand: moving with the carry off, unchanged with the switch off and with the hours rule off
- [x] The hard monthly and yearly caps still bind; in a re-plan the elapsed days count; the weight at 0, the switch off and the hours rule off each price nothing
- [x] The explanation's match names the nurse, her overtime, her share and the hours priced; the per-nurse explanation carries it
- [x] The service contract test's sample request and result carry the fields; the solver's suite, the service tests and the contract tests pass
- [x] The backend suite stays green: the balance passes through the carry-over chain with a default of 0, and the tests that hold the app's blocks to every field of the solver's leave out a named set of the new fields, with a comment that tickets 50 and 51 remove it (as tickets 28 and 31 did)
- [x] `solver/DESIGN.md` names the rule beside the other fairness rules and the contract change; `docs/ARCHITECTURE.md` section 6 names the fields

**Worth your review, already known:** a share is a fraction of an hour (51 hours among 24 nurses is about 2.1 each). Choose the whole-number unit the model works in and how a fraction rounds, the same in the model and the validator, and say what you chose and why.

## Comments

**Implemented on 2026-11-12,** on branch `claude/ticket-49-overtime-share-solver-4fd906`, pull request
devjazzar/cp-sat-nurse-roster-app#22, from `main` at `3579d76` (`131795e` the solver, `c7ba747` the backend pass-through,
`a8a0350` the docs, `929e2b3` the review's points; then a merge of `main` with tickets 46 and 58, and this comment). The suites,
locally, under the heavy-run lock, on `929e2b3`:
- the solver's whole suite with the service tests (`cd solver && uv run --no-sync pytest -q`): **700 passed**. 95 tests are
  new in `tests/test_overtime_share.py` and two in `service_tests/test_contract.py`;
- the backend under pytest on a throwaway PostgreSQL 18 container of my own: **3332 passed**; `makemigrations --check`: no
  changes;
- no frontend, OpenAPI or Playwright change (no API schema names a carried value; `closes/api.py` picks its fields), so
  `npm test`, `npm run build` and the browser checks are GitHub's, on the pull request: both workflows (five jobs) green on
  `929e2b3`, before the merge of `main` (tickets 46 and 58); the head that reached `main` is named in the merge's line below.

**What the dev stack needs:** a **rebuild** (`docker compose up -d --build`): the vendored solver changed. No migration,
dependency, compose or Dockerfile change. The app writes none of the unit's fields or the weight yet, so the rule is off for
every unit and every balance is handed on as 0: a solve on the stack prices exactly as before until ticket 51.

**What was built, criterion by criterion.**
- **The loader.** `department.share_overtime` (absent = false), `department.overtime_tolerance` and
  `department.overtime_carry_cap` (whole hours 0..744, absent = 0), `general.weights.overtime_above_share` (absent = 0) and a
  nurse's `overtime_balance` (hours, absent = 0), optional in **both** request versions (`request._optional_rules`, which
  now fills the full-run fields too, on copies; the stored input untouched, tested on the version 1 and 2 samples). Refused
  with the usual path: -1, 745, 2.5, 3.0, `true`, `"3"` ("request: department.overtime_tolerance must be a whole number of
  hours within 0..744, got 745"); the switch not a boolean; a negative or boolean weight; a balance that is a boolean, a
  string, NaN or beyond ±1 000 000 ("request: nurses[0].overtime_balance: must be a number of hours within ±1000000, got
  True"). The problem's schema goes 6 → 7: the four rule fields required in a problem file (Python defaults off and 0), the
  balance optional there as `preferences_not_kept` is; a version-6 file refused like any other.
- **The rule.** `overtime_above_share`, soft, weight of the same name, unit "hour of overtime above the share", on while the
  unit's switch and the hours rule are on (active with the weight above 0). Shared arithmetic in `fairness.py`
  (`overtime_owed`, `overtime_adj_100`, `overtime_share`, `overtime_priced`, `overtime_balance_out`); the model and the
  validator (`validate._overtime_above_share`) both read it. The per-rule drift test in `test_rules.py` covers it.
- **The price, counted by hand on a seven-day month** (six days owed at 8 h, 12 h day shifts, two a day, three nurses: 24 h
  of overtime forced, shares of 8 h): with 12 h free the solver spreads the two extra shifts one each, at no cost; with none
  it spreads them still, 8 h priced against 16 for one nurse holding both; a hand-built uneven grid costs 4 h × 3; the
  forced solve's objective equals the validation (36). A nurse with no overtime costs nothing with a balance of +24 h and a
  limit of 24; hours below the target are never priced; with a nurse held to 24 h over and room for a third nurse a day,
  the total overtime is 24 h with the rule on and off (OPTIMAL both).
- **The share follows the hours owed** (February 2026, read off a grid): 17.45 h for a full-time nurse, 15.27 h for one on
  three days' leave and for one breastfeeding (168 h each), none for one on leave every day she owes, whose 24 h of
  overtime still count in the unit's total and are not priced.
- **The balance.** It moves the target (−6 h: her 12 h are below a target of 14, nothing priced; +3 h: 7 priced), is held
  within the limit (+30 h at a limit of 2: target 6), and is ignored without carry-over fairness. The balance out counted by
  hand: 24 − 17.45 = 6.55, −15.27, −15.27, +24; 5 + 6.55 = 11.55 carried on; moving with the carry off and with the weight
  at 0; handed on unchanged with the switch off and with the hours rule off.
- **The caps, a re-plan, and off.** A nurse at 720 h this year, and one under a monthly cap of 12 h, each carrying 24 h below
  her share (overtime free for her), get no more than the caps allow and the month solves with no hard error. A re-plan
  from day 5 prices a nurse's 12 h over, all of it in the elapsed days (4 h), and gives the free days to the others. The
  weight at 0, the switch off and the hours rule off each price nothing and leave the rule inactive.
- **The words.** "a: 24 h overtime, share 8.0 h, 4 h priced", per nurse, no day; with ", target 5.0 h after the carried
  balance" when the balance moves the target; the per-nurse explanation carries it (`explain.nurses`) and `report` prints
  `overtime_above_share 12 = 4 x 3  (hour of overtime above the share)`.
- **Contract.** The service test's copy of the sample (`shared`) carries the five fields; a month-end reconciliation of a
  hand-built June (Amal 312 h, the others nothing) returns each balance counted by hand (79.12, −25.28, −23.96, −27.38) and
  `/validate` prices Amal's 104 h at 67 in the solver's words, the target named. The result's `penalties` gain the key and
  `carry_over` gains `overtime_balance` (the round-trip test in `test_request.py` reloads it).
- **The backend.** `closes.chain.CARRIED` gains `overtime_balance`; opening values hand on 0.0 (`opening`), as does a close
  stored before it (`CARRIED_SINCE`, renamed from `BEFORE_PREFERENCES`, which it now outgrew), and a stored input compares as
  0 (`solves.comparison`). A new test carries a closed October's −7.25 into November's input; `test_input.py` and the January
  test in `test_close.py` expect the 0. The three tests that hold the app's blocks to every field of the solver's
  (`units/tests/test_unit_rules.py`, `units/tests/test_rules_api.py`, `hospital/tests/test_rules.py`) subtract
  `OVERTIME_SHARE_FIELDS`, each with a comment that ticket 51 deletes it.
- **Docs.** `solver/DESIGN.md` (the request note, schema 7, the rule beside the fairness rules with its unit, rounding and
  limits), `solver/how-to.md` (the five fields), `docs/ARCHITECTURE.md` section 6.

**What was driven, and how.** The CLI on the ER sample with the switch on, 12 h free, a limit of 12, the weight at 1 and N03
carrying +10 h (`uv run --no-sync python -m nurse_roster solve <er_request_2026-03.json with the fields> --explain
--workers 4`, 20 s): FEASIBLE, every hard rule kept, "cost matches the solver objective",
`overtime_above_share 6 = 6 x 1` with "N18: 36 h overtime, share 18.9 h, 5 h priced" and "N21: 32 h overtime, share 18.2 h,
1 h priced". That month places 427 h of overtime, so shares are about 18 h and most nurses stand within 12 h of theirs.
Nothing in a browser: nothing in the app changed.

**What was NOT checked:**
- A month like ER's December 2026 (51 h among 24 nurses): the spec's check after ticket 51, with the fields fed.
- That the rule never raises the month's total overtime in general (below): tested on one forced small month only.
- Performance beyond the ER sample: one integer variable, one linear constraint and at most one boolean per nurse, and one
  for the unit's total.
- The frontend suites locally: nothing in `frontend/` changed; GitHub's six runs and the browser checks are the evidence.

**Decisions taken here:**
- **Worth your review, the ticket's own: the unit is the whole hour, the excess rounded down.** The weight is per hour (the
  spec's "Overtime away from the fair share", per hour of overtime), so the priced amount must be whole hours. Rounding the
  excess down is rounding her target up in her favour: a part hour is never priced, so the rule never charges a nurse for
  hours the arithmetic of a share invented (51 h among 24 nurses is 2.125 h each), and it never over-charges, as ticket 47's
  choice. The arithmetic is exact integers in both the model and the validator (S = 100 × the hours owed, the balance in
  hundredths of an hour; `fairness.overtime_priced`), so a solve and a validation agree to the hour; the alternative,
  rounding up, would price 0.1 h as a whole hour. Shares and balances are shown and carried to hundredths.
- **Worth your review: the rule can, in a corner, pay the solver to make overtime.** The share rises with the unit's
  overtime, so h more hours anywhere lower the priced nurses' excess by h × their part of the hours owed (less than h), plus
  up to an hour each where the rounded-down excess crosses a whole hour. Exactly, the rule never pays for overtime while its
  weight is at most `nurse_overtime`'s (the spec's default 1 against ER's 1), but rounding can when many nurses are priced at
  once and the extra shift is short, and a weight above `nurse_overtime`'s can by up to the difference per hour. The spec
  decides the share as the month's overtime in proportion, so I built it as written and recorded the limit in
  `solver/DESIGN.md`. If it matters, ticket 51's weight page could say the weight should not exceed the hour of overtime, or
  the share could be taken from the overtime the month needs; both are your call.
- **Worth your review: her overtime is held to exactly what she worked above what she owes while the rule is on**
  (`add_max_equality`). Without it, with weights at 0, the model could raise a nurse's overtime and shortfall together to
  move everyone's share; the validator reads the real overtime, so the two would disagree.
- **Worth your review: the cap at her overtime is an either-or** (priced ≥ her overtime, or the rounded-down excess), added
  only where her held balance is above the tolerance, the one case the excess can exceed her overtime. A plain upper bound
  would make such a month infeasible; tested with a balance of +24 h and a limit of 24.
- **Worth your review: names.** `share_overtime`, `overtime_tolerance`, `overtime_carry_cap` (as `carry_cap`),
  `overtime_above_share` (the rule's id is its weight's, as 47's) and `overtime_balance`.
- **Worth your review: a nurse who owes no hours is not priced, but her overtime counts in the unit's total and in her
  balance** (in + overtime − 0), as the spec's formula says. She raises the others' shares a little.
- **Worth your review: the balance's bound is ±1 000 000 hours,** a sanity bound as `hours_balance`'s; it enters the target
  only after the limit (at most 744 h) holds it.
- **Worth your review: the service sample file does not carry the fields,** as ticket 47's did not: the backend loads
  `four_nurses.json` as a unit's rules and its schema refuses unknown fields until ticket 51. The contract tests add them to a
  copy (`shared`).

**Review:** `code-review` against `3579d76`, both axes. *Standards:* the first contract test computed the expected balance
with the code's own formula; it is now a month-end reconciliation of a hand-built month with the four balances counted by
hand. A comment named a function that does not exist (`fairness.overtime_target`, now `overtime_adj_100`).
`BEFORE_PREFERENCES` renamed `CARRIED_SINCE`. Kept: the defaults of a carried value written both in `closes/chain.py` and
`solves/comparison.py` (they existed apart before; ticket 50 touches both); `(overtime, total, owed)` passed together to
the `fairness` functions (three callers, plain integers, as the shift balances' `share` / `per`); the balance checked in
the request and in the problem (the `preferences_not_kept` pattern). *Spec:* recounted every hand count, found no error; it
flagged the incentive limit above (documented, kept as decided) and asked where the CLI run is (here, above, as ticket 47's).
No adversarial review, by the brief.

**Things later tickets should know.**
- **50:** the chain already passes `overtime_balance` through (`CARRIED`), 0 out of opening values (`chain.opening`, a
  literal 0.0 to replace with the nurse's opening value) and out of a close stored before it (`CARRIED_SINCE`), and it carries
  unchanged through a month with no roster (it is not in `NO_HISTORY`). **Not done:** the January reset (`NEW_YEAR` has no
  `overtime_balance`, and `test_close.py`'s January test expects only the 0 from an old close). There is no narrowing for the
  carried value to remove: your criterion "the narrowing ticket 49 left for the carried value is removed" has nothing to act
  on. Until 51 the solver hands every balance on unchanged, so prove the chain with `share_overtime` set in the test's input.
- **51:** write `department.share_overtime`, `overtime_tolerance`, `overtime_carry_cap` and
  `general.weights.overtime_above_share` into every solve, re-plan and close input; version 1 or 2 both take them. Delete
  `OVERTIME_SHARE_FIELDS` from the three test files, and add the fields to `solver/service_tests/fixtures/four_nurses.json` if
  you like (the contract tests' `shared` then folds). The violation rule in `/validate` is `overtime_above_share`, per nurse,
  `date` null, amount the hours priced. Read the incentive point above before the weight's description.

**Merged on 2026-11-12:** `main` fast-forwarded to `4e9d9b5`, the branch's head after merging `main` with tickets 45, 46, 58
and 71 and the fix to `operations.sh` (`bf16ca8`); both workflows green on it (backend, solver, frontend, image, browser
checks). On `ae1c600` the browser checks had failed on ticket 71's one-CPU confirmation check (28.7 s, inside gunicorn's 30 s),
as `main`'s own run did; the main session fixed it on `main`. The local suites ran on `929e2b3`, before those merges; the
merges touched nothing in `solver/` or `backend/closes/`.

**Reviewed by the user (2026-11-12):** all points kept as built; the weight's cap goes to ticket 51.
- Whole hours priced, the excess rounded down, the same integer arithmetic in the model and the validator.
- Overtime that pays: ticket 51 refuses an overtime share weight above the hour of overtime's weight, and its tests hold
  "the rule never raises the month's total overtime" on a larger month than this ticket's.
- A nurse's overtime fixed to exactly what she worked above what she owes while the rule is on; the cap at her overtime an
  either-or; a nurse owing no hours never priced, her overtime still in the unit's total; the sample file without the fields.
