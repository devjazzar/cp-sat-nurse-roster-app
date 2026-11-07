# Compare two results of the same month

Status: ready-for-agent
Type: enhancement
Published: 2026-11-07 by /to-spec

Spec drawn from the grilling of 2026-11-07 (sixteen questions in two rounds, every recommendation taken). Vocabulary:
`GLOSSARY.md`. Decisions and their reasons: `docs/ARCHITECTURE.md` and `docs/adr/`. Where this spec and those documents
disagree, the documents win and this spec is wrong.

## Problem Statement

**A Unit Manager tunes blind.** She changes a weight, a unit rule or the time limit and solves the month again. The solve
history keeps every solve with its solve input and result, and she can open each result in full: its roster, the penalty
of each soft rule, each nurse's hours and cost, the violations, the solver's statistics. But she can only ever open one at a
time. To learn what her change did she holds one page in her head while reading the other, or writes numbers down. She
cannot see which cells moved, whether the rule she meant to help was broken less, what that cost the other rules, or
whether anything else of the month changed between the two solves (leave recorded, a pin, a nurse who joined) that would
explain the difference as well as her change would.

A re-plan already has such a comparison, against the roster in force it started from (ticket 17): the cells changed, the
cost of each rule before and after, the facts that broke rules. Nothing of the kind exists between two results.

## Solution

**Compare two results.** On her unit's solve history, filtered to a month, the manager chooses two of that month's results
that hold a roster and reads them side by side on one page, older on the left and newer on the right:

- **The two solves' facts:** who asked for each and when, its outcome, how long it searched and its time limit, its total
  cost and the unit's own cost, which of the two is the draft today, and for a re-plan the date it planned from and the
  version it started from.
- **What changed between their inputs:** hospital rules and weights field by field (`weights.night_rest: 5 → 8`), unit
  rules field by field, the time limit, the Ramadan days and public holidays; and for each nurse only the kind of what
  changed: joined, left, attributes, leave, pins, carry-over.
- **Each soft rule side by side:** how much it was broken (the amount, in the rule's own unit), the weight, and the
  penalty, in each result on its own input. Where the weight differs between the two, the page says so beside the rule; the
  amount is then the like-for-like column, since the two penalties were priced differently.
- **The cells that differ:** nurse, date, the older result's shift, the newer's, grouped by nurse, with the count.
- **Each nurse's hours:** contract, required, worked, overtime, shortfall and cost in each result, with the difference,
  every nurse of either result in name order.
- **The hard rules each roster breaks and the recorded facts that broke rules,** in three groups: in both, only in the
  older, only in the newer.
- **The solver's statistics** of each: what stopped it, improving rosters, cost as the search counted it, lowest cost
  proven.

It is read-only and the manager's alone. She still restores a result as the draft from the result's own page, as today.
Each result page gets a link, "Compare with another result", that opens the month's history with that result as one side.

## User Stories

1. As a Unit Manager, I want to choose two results of one month from my solve history, so that I can see what changed between them without holding one page in my head.
2. As a Unit Manager, I want the comparison to list which hospital rules and weights differ between the two solve inputs, field by field, so that I know which change of the CNO's the difference may come from.
3. As a Unit Manager, I want the comparison to list which unit rules differ, field by field, so that I can tell my own change from everything else.
4. As a Unit Manager, I want the comparison to say when the time limit differed, so that I know whether a cheaper roster came from a longer search.
5. As a Unit Manager, I want to know when Ramadan days or public holidays differed between the two inputs, so that a change in hours owed is not mistaken for a change in the roster's quality.
6. As a Unit Manager, I want each nurse whose input changed named with the kind of change (joined, left, attributes, leave, pins, carry-over), so that I know a nurse's leave or a new pin may explain the cells that moved.
7. As a Unit Manager, I want no leave dates, pin values or carry-over figures in that list, only the kind of change, so that the list stays a short answer to "what else changed" and not a second copy of the month.
8. As a Unit Manager, I want each soft rule's amount, weight and penalty for both results side by side, so that I can see whether the rule I meant to help was broken less and what the others paid.
9. As a Unit Manager, I want a rule whose weight differs between the two marked as such, so that I do not compare two penalties priced differently as if they were alike.
10. As a Unit Manager, I want the rules ordered by the size of their difference, so that what moved most is read first.
11. As a Unit Manager, I want rules that cost nothing in either result left out, with a line saying so, so that the table holds only what matters.
12. As a Unit Manager, I want the `change` rule of a re-plan shown with the plain solve's column empty, so that a re-plan's price for moving cells is visible and not mistaken for a missing figure.
13. As a Unit Manager, I want the cells that differ listed by nurse and date with both shifts, so that I can see exactly where the two rosters disagree.
14. As a Unit Manager, I want the count of differing cells, so that I know at a glance whether a small change of weight redrew the month.
15. As a Unit Manager, I want a nurse present in only one of the two results named once among the input changes and not listed cell by cell, so that her every day does not read as a change from Off.
16. As a Unit Manager, I want each nurse's contract, required, worked, overtime, shortfall and cost in both results with the difference, so that I can see who gained and who lost hours.
17. As a Unit Manager, I want every nurse of either result in that table in name order, not only those whose hours changed, so that I can see a nurse did not move as readily as that one did.
18. As a Unit Manager, I want the hard rules each roster breaks grouped as in both, only the older and only the newer, so that I can see whether a change fixed or caused a violation.
19. As a Unit Manager, I want the recorded facts that broke rules grouped the same way, so that facts are read as facts and not as the solver's failing.
20. As a Unit Manager, I want the solver's statistics of both (what stopped it, improving rosters, cost as searched, lowest cost proven), so that I can tell a better roster from a longer search.
21. As a Unit Manager, I want the older result always on the left and the newer on the right with every difference signed newer minus older, whichever way I filled the pickers, so that the page reads the same every time.
22. As a Unit Manager, I want the two solves' facts at the top (who asked and when, outcome, duration and time limit, cost, which is the draft, a re-plan's date and version), so that I know which two I am looking at.
23. As a Unit Manager, I want a re-plan's side to say "re-planned from <date> of version N" rather than a diff of its starting roster, so that the input list says what it was in my words.
24. As a Unit Manager, I want the pickers to offer only the month's results that hold a roster, so that I cannot choose a failed solve with nothing to compare.
25. As a Unit Manager, I want each picker to leave out what the other holds, so that I cannot compare a result with itself.
26. As a Unit Manager, I want the two newest results with a roster chosen by default, so that the comparison I most often want is one click away.
27. As a Unit Manager, I want the chosen pair in the page's address, so that I can reopen or bookmark the comparison and come back to it after a solve.
28. As a Unit Manager, I want the Compare section only when the history is filtered to a month, so that I am not offered a pair that cannot be compared.
29. As a Unit Manager, I want a sentence instead of pickers when a month has fewer than two results with a roster, so that the page says why there is nothing to compare.
30. As a Unit Manager, I want a result the solver's code can no longer explain to show its stored totals with its amounts and weights as "Not known" and a sentence saying so, so that an old result still compares as far as it can.
31. As a Unit Manager, I want a "Compare with another result" link on a result's page, so that I reach the comparison from the result I am reading.
32. As a Unit Manager, I want shifts under their codes in use now on both sides, so that a rename between the two solves is not a change.
33. As a Unit Manager, I want the comparison to change nothing and offer no Restore, so that I keep choosing the draft from the result's page as I do today.
34. As a Unit Manager on a phone, I want each table to scroll inside itself with no sideways page scroll, so that I can read the comparison where I am.
35. As a Unit Manager, I want the page to say when the comparison could not be read and how to try again, so that a failed read does not look like an empty month.
36. As a Unit Manager of another unit, I want to be refused a pair of a unit not mine, so that no unit reads another's results.
37. As the CNO, the Deputy CNO, a Staff Nurse or the System Admin, I want no comparison page and no answer from its endpoint, so that tuning stays the manager's and the System Admin reads no roster.
38. As the System Admin, I want my solve history unchanged, so that nothing of a roster or a nurse reaches it.

## Implementation Decisions

**One read-only endpoint, the manager's.** `GET /api/units/{unit_id}/solve-history/compare?a=<solve id>&b=<solve id>`
(operation `compareSolveResults`), under the same authentication as starting a solve: the unit's manager only. It answers a
`ResultComparison`. The order of `a` and `b` does not matter: the answer names the older (by when it was asked for) and the
newer. It answers 400 when the two are the same solve, of different months, or either holds no roster to keep
(the same test the history uses for "found a roster"); a solve of another unit, or one that does not exist, is a 404 like a
result's. Every other role gets the refusal the manager-only endpoints give. Nothing is written and nothing is audited: it is
a read of two results the manager may already read.

**Both results stand as they are.** Each is costed on its own solve input: the stored penalties are the result's own, and
the per-rule amount and weight come from the same explanation the result page works out (the solver's own code on the
stored input and roster, in the web process, no solver running). No roster is priced on the other solve's input: the
solver's validator refuses a roster whose nurses are not exactly the input's, so that would fail whenever a nurse joined or
left, and the amounts already answer whether a rule was broken less. When the explanation of one side cannot be worked out,
that side's rules carry its stored penalties and null amounts and weights, and a flag per side says so.

**The answer's shape.**
- `month`, and `older` and `newer`: each the history row the manager already knows (who, when, state, failure, duration,
  time limit, cost, found a roster, in the draft, re-plan date and outcome), plus the unit's own cost, the re-plan's version
  started from, and the solver's statistics as the result page has them.
- `inputs`: the differences between the two solve inputs, as a list of changes, each with a group and a field name, the
  older value and the newer value: group `hospital_rules` (the general block flattened as the audit log flattens it, each
  weight as `weights.<name>`), group `unit_rules` (the department block field by field, the same way; fields that name
  shifts are read under today's codes, so a rename is no change), group `time_limit`, group `calendar` (`ramadan_days`,
  `public_holidays`). Then `nurses`: one entry per nurse whose block differs, with hospital ID, full name and the kinds that
  differ, from `joined`, `left`, `attributes` (gender, team leader, score, Ramadan-reduced, breastfeeding, allowed shifts),
  `leave`, `pins` (under today's codes, as the stale-draft check compares them), `carry_over` (the carried values and the
  history). No dates, pin values or figures are sent for a nurse. A re-plan's `published` and `replan_from` are not diffed:
  the side's facts carry its date and version, and the page words them.
- `rules`: each soft rule that costs something in either result, with the older's and the newer's amount, weight and
  penalty (amount and weight null when that side is unexplained), and `weight_differs`. Ordered by the largest absolute
  difference of penalty, then by name.
- `cells`: the cells that differ between the two rosters, both under today's codes, for the nurses present in both
  results: hospital ID, full name, date, older shift, newer shift, empty for a day not worked. Ordered by name then date.
- `nurses`: every nurse of either result in name order, with the older's and the newer's hours accounting (contract, leave
  credit, required, worked, overtime, shortfall, shifts, cost), null on a side she is not in.
- `violations` and `facts`: each a triple of lists, `both`, `only_older`, `only_newer`, of the result page's violation shape
  (rule, hospital ID, full name, date, text with dates in place of the solver's day numbers), where two entries are the same
  when rule, nurse and date agree.
- `explained_older`, `explained_newer`: whether each side's explanation could be worked out.

Names are resolved as the result page resolves them; a nurse whose account is gone keeps her hospital ID.

**Where the page lives.** The manager's solve history page, filtered to a month, gets a **Compare two results** section
(the pattern of the Versions section's "Compare two versions"): two pickers over the month's results that hold a roster,
each named by when it was asked for and its cost, each leaving out the other's choice, and the comparison beneath. The
pair rides in the address as `a` and `b` beside `month`, so the comparison reopens from a bookmark and survives a reload;
with neither set, the two newest results with a roster are chosen. The pickers offer the rows of the month-filtered history
the page already holds (a month's history is short in practice; a pair from an older page still compares when the address
carries it). With fewer than two results holding a roster the section is one sentence and no pickers. Without a month filter
the section is absent. A failed read says so and how to try again, as the history does.

**The page's layout.** Older on the left, newer on the right, each column headed by when the solve was asked for.
Differences are signed newer minus older. The sections, in order: the two solves' facts; what changed between the inputs
(or "Both solves were given the same month"); each rule side by side (amount, weight, penalty per side, difference of
penalty, a mark and a sentence where the weight differs, the `change` rule shown with the plain solve's column empty, and
the line that every other soft rule costs nothing); the cells that differ with the count (or that no cell differs), with a
nurse present in only one result named in the inputs section and left out here; each nurse's hours with the difference;
violations and facts in their three groups; the solver's statistics. Rule names take the labels the hospital rules page
uses; unit rule fields take the labels the unit rules page uses where it has one, else the field's name. Tables scroll in
their own regions, as every table on the history does. No Restore, no print sheet, no file.

**The result page's link.** Each result page gets "Compare with another result", a link to the solve history filtered to
the result's month with this result as `a`; `b` falls to the newest other result with a roster.

**No schema change, no migration, no new dependency.** The stored solve input and result already hold everything; the
OpenAPI document and the generated client are regenerated for the new endpoint.

**Documentation.** No glossary term and no ADR. Two sentences belong in `docs/ARCHITECTURE.md`, which the grilling session
could not edit: section 8's "What a solve shows afterwards" says that any two of a month's results holding a roster compare
side by side, for the manager only, with the inputs' differences named; section 5's bullet on the solve history says the
same in one clause. The ticket makes those edits.

## Testing Decisions

A good test drives the feature from outside, through the two agreed seams, and reads only what a user or a client would:
the endpoint's JSON and the page's text and controls. It never reaches into the modules that compute the comparison.

**Seam 1: the solve history API,** through Django's test client with the scripted solver and real PostgreSQL, as the
history's and the result's tests do today. Cover: two results of one month compared, with the older named first whatever
the order of the parameters; the input differences for a weight, a unit rule, the time limit, a holiday, a nurse's leave, a
pin, a nurse who joined and one who left, each as its group, field and kind and nothing more of the nurse; a rename between
the two reading as no change in cells and in the unit rules; the rules with amounts, weights and penalties, `weight_differs`,
the order by difference, and rules costing nothing in both left out; the cells that differ, with a nurse in one result only
left out; each nurse's hours with null on the side she is not in; violations and facts in three groups; a re-plan on one
side, its facts naming the date and version and its `change` rule present; one side the solver's code cannot explain
(stored totals, null amounts, the flag); the refusals: same solve twice, different months, a result with no roster, another
unit's pair, and every other role; and that nothing is written to the audit log.

**Seam 2: the frontend's app-level Vitest suite,** through the real routes and generated client over a stubbed `fetch`.
Cover: the Compare section present on the month-filtered history and absent without a month; the default pair and the
pickers' exclusion of each other's choice; the pair taken from the address and written to it; the comparison's sections
rendered from a stubbed answer, the differing-weight mark, the three violation groups, the unexplained-side sentence; the
one-sentence state with fewer than two results; the failed-read message; the result page's link and where it leads; the
route guard keeping every other role out. No raised timeout, no fake timers, no wait that proves something did not happen.

Prior art: the history and result tests under the solves app's tests, and the solve history and roster versions tests in
the app-level suite.

## Out of Scope

- Pricing one result's roster on the other's input (the re-plan's cross-pricing).
- Two grids side by side, or a grid with the differing cells marked.
- The CNO, the Deputy CNO or the System Admin reading a comparison.
- A result against the draft, a roster version or the roster in force (versions compare already; a re-plan shows itself
  against the roster in force).
- A print sheet, CSV or Excel of the comparison.
- Restoring a result from the comparison page.
- Comparing results of different months or units.
- An audit entry for a comparison read.

## Further Notes

- The grilling's decisions and its notes for this spec are in the shared side-session notes folder of the main session,
  file `grill-6-compare-solves.md`.
- The spec was written on the grilling's branch at the user's request, outside the branch's agreed two files; the session
  that merges the seven grilling branches takes it with the rest.
- The pickers read the history page's own rows; a month with more results than one page holds offers only that page's, and
  the address still carries any pair of the month. If a unit ever solves a month more than fifty times, give the pickers
  the month's candidates from the endpoint rather than the page.
- The `change` rule exists only on a re-plan's input, so under own-input costing its row has the plain solve's column
  empty by design.
