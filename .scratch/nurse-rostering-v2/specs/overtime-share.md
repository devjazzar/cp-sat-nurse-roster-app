# Overtime share: a unit's overtime spread fairly among its nurses

Status: ready-for-agent
Type: feature
Published: 2026-11-09 by /to-spec
Decided: the grilling of 2026-11-09 (21 questions, three rounds), recorded in `GLOSSARY.md` (Overtime share). No ADR: the
rule follows ADR 0004 and the shape of the two fairness rules already there (nights, weekend days).

Vocabulary: `GLOSSARY.md`. Decisions and their reasons: `docs/ARCHITECTURE.md` and `docs/adr/`. Where this spec and those
documents disagree, the documents win and this spec is wrong.

## Problem Statement

When a unit's headcounts need more hours than its nurses owe, somebody works overtime, and nothing says who. Each hour of
overtime costs the solver the same whoever works it, so three extra shifts on one nurse cost exactly what one extra shift on
each of three nurses would. The hospital's caps (40 hours a month and 720 a year per nurse, hard; 400 a month per unit, soft)
bound the amount, not the spread.

ER's December 2026 draft on the dev stack had 51 hours of overtime to place, and placed them like this:

| Nurse | Hours worked | Hours owed | Overtime |
|---|---|---|---|
| Mana Mohamed | 252 | 216 | 36 |
| Abdullah Saad | 228 | 216 | 12 |
| Rayan Ahmed | 192 | 189 | 3 |
| 21 others | 216 | 216 | 0 |

One nurse carries three extra 12-hour shifts while 21 carry none. Overtime is tiring for the nurse loaded with it and paid
work the others were kept from, and nurses notice both. The unit manager has no control over it. Nights and weekend days
already have what is missing: a fair share for each nurse, a balance carried from month to month, and unit rules that switch
it on and set its tolerance.

## Solution

Each nurse has an overtime share: the part of the unit's overtime in the month that falls to her, in proportion to the hours
she owes. The solver prices each hour of her overtime above her share, beyond a tolerance the unit manager sets, so it spreads
the overtime one extra shift at a time instead of piling it on one nurse. How far her overtime has stood above or below her
share so far this year is carried from month to month as one more fairness balance, and moves her share next month: down if
she stands above, up if she stands below. So the extra shifts rotate. The balance resets each January with the other two.

The unit manager controls it on Unit rules, beside the weekend spread: a switch ("Share overtime evenly", on by default), the
tolerance in hours (default 12) and how far the carry may move one month's share (default 12 hours). The existing switch
"Carry fairness between months" governs the carry for overtime too. The CNO sets the weight on the weights page ("Overtime
away from the fair share", 1 by default, 0 to switch it off hospital-wide). The manager reads the cost in the draft's
per-nurse explanation. Nothing is ever refused for it, and no nurse page changes.

With the defaults, ER's December comes out as four nurses with one extra shift each and Rayan's 3 hours, and January's
overtime goes to four others.

## User Stories

1. As a unit manager, I want the solver to spread my unit's overtime among its nurses, so that no nurse carries three extra
   shifts while the rest carry none.
2. As a unit manager, I want a switch, "Share overtime evenly", on Unit rules beside the weekend spread, so that I decide
   whether my unit shares its overtime.
3. As a unit manager, I want the switch on by default, so that the rule works without my touching it.
4. As a unit manager, I want to set the hours a nurse may stand above her share for free, so that I decide how tight the
   spread is.
5. As a unit manager, I want the tolerance to start at 12 hours, so that one extra long shift is free and a second one costs.
6. As a unit manager, I want each nurse's share to follow the hours she owes this month, so that a nurse on leave, on reduced
   hours or starting mid-month is not expected to take a full share.
7. As a unit manager, I want a nurse who owes no hours this month to have no share, so that the overtime is shared among
   those who can work it.
8. As a unit manager, I want only overtime above a nurse's share priced, never overtime below it, so that the rule can never
   pay the solver to hand out a shift nobody needs.
9. As a unit manager, I want what a nurse has had above or below her share so far this year to move her share this month, so
   that the nurse who took last month's extra shift is not the one who takes this month's.
10. As a unit manager, I want the existing "Carry fairness between months" switch to govern that carry for overtime too, so
    that one switch says whether my unit's fairness looks back.
11. As a unit manager, I want to limit how far the carry moves one month's share, so that a nurse far below her share is not
    handed several extra shifts in one month.
12. As a unit manager, I want that limit to start at 12 hours, so that the carry moves a share by one long shift at most.
13. As a unit manager, I want a nurse with no overtime never to cost anything under this rule, so that the explanation does
    not blame a nurse for hours she did not work.
14. As a unit manager, I want the tolerance and the limit to take whole hours from 0 to 744, and anything else refused with
    the usual field error, so that I cannot save nonsense.
15. As a unit manager, I want my changes to the three fields audited like every other unit rule, so that the log says who
    changed them.
16. As a unit manager, I want the draft's per-nurse explanation to show each nurse's overtime above her share and what it
    cost, so that I can see who got too much and why the solver allowed it.
17. As a unit manager, I want a re-plan to price the rule as a solve does, so that fixing a sick call does not pile the
    overtime back on one nurse.
18. As a unit manager, I want hand edits, swaps, covers and requests never refused for the rule, so that a priced rule never
    blocks a real need.
19. As a unit manager, I want the overtime a cover, a swap or a hand edit gives a nurse to enter her balance, so that later
    solves steer overtime away from her.
20. As a unit manager, I want to enter a new nurse's overtime above or below her fair share among her opening values, default
    0, so that a nurse who joins mid-year starts level and is not handed the unit's overtime until she "catches up".
21. As a unit manager, I want that opening value locked with the others once her first month closes, so that the chain is the
    one record from then on.
22. As a unit manager, I want a nurse's balance to follow her across a transfer, so that her year is one year whichever unit
    she works in.
23. As a unit manager, I want a nurse's balance to carry unchanged through a month with no roster for her, so that a month of
    leave neither helps nor hurts her standing.
24. As a unit manager, I want every nurse to start at 0 when the rule arrives, with no working back through this year's
    months, so that months solved without the rule are not held against anyone.
25. As a unit manager, I want the balance corrected at the month close from what really happened, and re-worked at a
    re-close, so that sick days and covers count as they fell.
26. As a unit manager, I want the hospital's monthly and yearly overtime caps to stay hard and above this rule, so that
    fairness never pushes a nurse past a cap.
27. As a CNO, I want to set the weight of an hour of overtime above the fair share on the weights page, so that I decide how
    much the spread matters against the other priced rules.
28. As a CNO, I want a weight of 0 to switch the rule off hospital-wide, so that I can drop it without touching each unit.
29. As a CNO, I want the weight's change audited as the other weights are, so that the log says who changed it.
30. As a CNO or Deputy CNO, I want to read each unit's three fields as I read its other unit rules, so that I can compare
    units.
31. As a CNO, I want the rule to do nothing while the hospital's hours rule is off, so that a hospital that does not count
    hours is not priced for overtime it does not count.
32. As a staff nurse, I want the unit's overtime to come round to each of us in turn, so that I am neither worn down by it nor
    kept from it.
33. As a staff nurse, I want my balance to reset each January, so that each year starts level, as my overtime this year does.
34. As a staff nurse, I want my own pages unchanged, so that I am not shown the solver's prices.
35. As a nurse offered a cover, I want the offer ranked as before, so that this rule changes who the solver picks, not who is
    asked.
36. As anyone re-solving an old month, I want a solve input stored without the new fields to mean the rule off and a balance
    of 0, so that every stored solve and close gives what it gave.
37. As the system, I want every new solve, re-plan and close input to carry the unit's three fields, the weight and each
    nurse's balance, so that what the solver priced is in the input for good.

## Implementation Decisions

### The rule, said once

- The unit's overtime in a month is the sum of its nurses' overtime hours, as the solver's hours accounting already counts
  them. A nurse's **overtime share** is that sum times the hours she owes this month over the hours all the unit's nurses in
  the solve input owe this month. "Owes" is the solver's own figure for the month (the result's `required`), so leave, a
  reduced-hours month and days outside her dates lower it. A nurse who owes none has a share of 0 and is not priced.
- Her **target** is her share, less her carried balance when the unit carries fairness between months, the balance first
  held within plus or minus the unit's limit on the carry.
- Her **priced hours** are her overtime above her target, beyond the unit's tolerance, and never more than her overtime: a
  nurse with no overtime costs nothing whatever she carries. Hours below the target are never priced.
- The cost is the weight per priced hour, in the model's objective and in the validator's explanation alike, so a solve's
  cost and a validation of the same grid agree. The rule is soft only. It is active when the unit's switch is on, the weight
  is above 0 and the hospital's hours rule is on.
- Her **balance out** of the month is her balance in, plus her overtime, minus her share. It moves while the unit's switch
  is on, whether or not the unit carries fairness between months, as the night balance does; with the switch off, or the
  hours rule off, it is handed on unchanged. It is rounded as the two shift balances are.
- In a re-plan the elapsed days count, as for every soft rule.
- The existing price per hour of overtime, the unit's soft cap and the per-nurse hard caps are unchanged. The caps bound
  what any nurse can be given; this rule only chooses among what they allow.

### The solver (vendored)

- The department block gains three optional fields: the switch, the tolerance in whole hours and the limit on the carry in
  whole hours (0 to 744 each). The weights gain one, the hour of overtime above the share. Each nurse gains one optional
  carried value, her overtime balance in hours, and the result's carry-over block gains the same value for next month.
  Absent means the rule off, a weight of 0 and a balance of 0, so every stored solve input and close input loads and gives
  what it gave. The loader refuses a bad value with the usual `request: <field path>` error. The problem's schema version
  notes the change.
- One soft rule joins the registry, with its weight; model, validator and explain follow the registry as for every rule.
  The match names the nurse, her overtime, her share and the hours priced, and the per-nurse explanation carries it.
- Shares are fractions of an hour. The solver ticket chooses the whole-number unit the model works in and how a fraction
  rounds, the same in the model and the validator, and says so under Worth your review.
- No precheck: a priced rule cannot make a month infeasible.

### The carry-over chain (ADR 0004)

- The balance is one more carried value, taken from the result's carry-over block: projected from the roster in force,
  corrected at the close from the month's facts and re-worked at a re-close.
- It follows the nurse across a transfer and carries unchanged through a month with no roster for her, as her night and
  weekend balances do.
- The carry-over handed into January has it reset to zero, with overtime this year and the other two balances.
- A close stored before the balance existed hands on 0, as a close stored before ticket 28 hands on a preferences count
  of 0. Nothing is worked back through earlier months.
- A nurse's opening values gain it: "Overtime above or below their fair share (hours)", default 0, on the rostering
  attributes form beside the night and weekend balances, read and written through the same API, locked with them once her
  first month closes, audited with them.
- Every solve input, a re-plan's and a close's included, carries each nurse's balance from the chain.

### The app

- Unit rules gain the three fields, on the Unit rules page in the fairness group beside the weekend spread and the two
  existing fairness numbers:
  - "Share overtime evenly", a switch, default on. Help: "Overtime is spread among the unit's nurses in proportion to the
    hours each owes."
  - "Overtime tolerance (hours)", default 12. Help: "How many hours of overtime a nurse may work above their
    fair share before it starts to cost."
  - "Most a month's overtime share can move (hours)", default 12. Help: "The limit on how far what is carried can move a
    nurse's overtime share in one month."
  The description of "Carry fairness between months" gains overtime: nights, weekend days and overtime above or below a
  nurse's fair share so far move this month's fair share.
- Every unit, existing ones included, starts with the defaults. The fields stay visible whatever the hospital's hours rule
  says, as the other fairness fields do.
- Edited by the unit manager alone; read by the CNO and Deputy CNO as the other unit rules; audited as they are. The two
  numbers take whole hours 0 to 744, refused otherwise with the usual field error.
- The hospital's weights gain "Overtime away from the fair share", default 1, on the weights page with a description in the
  voice of the others (each hour of overtime a nurse works above their fair share, beyond the unit's free hours); 0
  switches the rule off hospital-wide. Audited as the other weights are.
- The solve input carries the unit's three fields and the weight in every new solve, re-plan and close input.
- The draft's per-nurse explanation shows the new match by the solver's words, as it shows the other fairness rules.
- Hand edits, swaps, covers and requests are never refused for it. The cover ranking, My month, My roster, the Day view and
  every nurse page are unchanged.
- The OpenAPI document and the generated client are regenerated. `docs/ARCHITECTURE.md` names the rule beside the other
  fairness rules, the balance among the opening values and in the chain's paragraph, and the January reset; ADR 0004's
  sentence on what January resets is read as covering it (a fairness balance).

## Testing Decisions

Good tests check what a caller sees: a priced cost, an explanation's words, a carried value, an API answer, a page. Expected
values are counted by hand on a small month, never recomputed the way the code computes them. The seams are the three every
v2 feature uses; none is new.

- **Seam 1, the solver's own suite and the service contract tests:** the loader accepts the new fields, treats each absent
  one as off or 0, and refuses a bad value. On a small month where the headcounts force a known amount of overtime: with the
  rule on, no nurse holds a second extra shift while another holds none; the cost of a hand-built uneven grid is the weight
  times the hours counted by hand, in the model and the validator; a nurse with no overtime costs nothing whatever she
  carries; hours below the share cost nothing, and the rule never raises the month's total overtime; a share prorated for
  leave and for reduced hours; a nurse owing none left out; a carried balance moving the target, held within the limit, and
  ignored with the carry off; the balance out counted by hand, moving with the carry off and still with the switch off; the
  weight at 0, the switch off and the hours rule off each pricing nothing; the hard caps still binding; elapsed days in a
  re-plan. The explain words. The contract test's sample request and result carry the fields. Prior art: the fairness tests,
  `test_rules.py`, `test_request.py`, `test_preferences.py`, `test_carry_over.py`, `test_contract.py`.
- **Seam 2, the backend API suite** on a throwaway PostgreSQL 18 with the scripted solver and the real worker's code:
  - `closes`: the balance projected from the roster in force, corrected at the close, re-worked on a re-close, unchanged
    through a month with no roster, following a transfer, reset across January, 0 out of a close stored before it existed,
    and out of opening values (`test_close.py`, as ticket 30's cases for the preferences count).
  - `nurses`: the opening value's default, edit, lock, who may set and read it, its audit entry (the attributes tests).
  - `units` and `hospital`: the three unit rules' defaults for new and existing units, edit, refusals, the unit manager
    alone editing, the CNO and Deputy CNO reading, the audit entries; the weight's default, edit and audit; the tests that
    hold the app's blocks to every field of the solver's.
  - `solves`: the solve input, a re-plan's and a close's included, carrying the three fields, the weight and each nurse's
    balance; a stored input without them still reproducing (`test_input.py`, `test_replan.py`).
- **Seam 3, the frontend's app-level Vitest suite** (`app.test.tsx` through `start` and `hold`): the three fields on Unit
  rules with their labels and help, their refusals, read-only for the CNO and Deputy CNO; the weights page's new weight;
  the opening value on the rostering attributes form, and locked. Ticket 11's rules: no raised timeout, no fake timers, no
  wait that proves something did not happen; six runs at once.
- **The real thing:** on a scratch stack, a month like ER's December (24 nurses, about 51 hours of overtime forced) gives no
  nurse more than one extra shift, and the next month's solve gives the extra shifts to other nurses; the explanation shows
  the cost where the month cannot avoid it.

## Out of Scope

- A hard rule on the spread, a precheck for it, or refusing an edit, swap or cover for it.
- Pricing overtime below a nurse's share, or anything that could make the solver create overtime.
- A share that differs by nurse beyond the hours she owes: no opt-out, no "wants overtime" flag, no seniority.
- Working balances back through months solved before the rule.
- Changing the cover ranking, the per-nurse caps, the unit's soft cap or the price per hour of overtime.
- Showing a nurse her share, her balance or their cost; a report of overtime by nurse.
- A longer memory than the year: the balance resets each January with overtime this year.

## Further Notes

- **Three tickets, at the end of the v2 queue:** 49, the solver prices overtime above the share and carries the balance
  (after ticket 47, which also changes the solver's input); 50, the chain carries the balance, with the opening value and the
  January reset; 51, the unit rules, the weight and the explanation.
- **Ticket 49 will meet the field-sync tests.** Four backend tests hold the app's hospital and unit blocks to every field of
  the solver's, and the chain's tests name every carried value. Tickets 28 and 31 met the same thing: the solver ticket
  passes the carried value through the chain with a default and narrows the block tests by a named set, and the app tickets
  remove the narrowing.
- **The tolerance is loose on purpose.** At 12 hours a nurse may hold one long shift above her share for free, so a month's
  overtime comes out as single extra shifts, and the carry is what moves them to other nurses the month after. A unit of
  8-hour shifts may want 8.
- **Why a balance and not overtime this year.** A nurse who joins in October with no overtime this year would otherwise be
  handed the unit's overtime for months, and her opening overtime cannot be raised to fix it because it counts against her
  yearly cap. A balance starts her level.
- After ticket 51 lands, a re-solve of ER's December on the dev stack is the check that Mana Mohamed no longer holds 36
  hours.
