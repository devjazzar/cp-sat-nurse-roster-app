# 01: Compare two results of the same month

**What to build:** A Unit Manager opens her unit's solve history filtered to a month and chooses two of that month's results that hold a roster. She reads them side by side on one page, older on the left and newer on the right: the two solves' facts; what changed between their solve inputs (hospital rules and weights and unit rules field by field, the time limit, Ramadan days and holidays, and per nurse only the kind of change: joined, left, attributes, leave, pins, carry-over; a re-plan's side saying the date and version it started from); each soft rule's amount, weight and penalty in each result on its own input, with a differing weight marked; the cells that differ with their count; each nurse's hours and cost with the difference; the hard rules broken and the recorded facts in three groups (both, only the older, only the newer); and the solver's statistics. The pair rides in the page's address, each result page links to the comparison, and nothing is changed or restored from it. The manager alone reads it. Spec: `../spec.md`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] A manager-only endpoint answers the comparison of two results of her unit and month in any order, naming the older and the newer; 400 for the same solve twice, different months or a result without a roster; 404 for another unit's solve as for a result; every other role refused; nothing audited
- [ ] The inputs' differences: hospital rules and weights and unit rules field by field in the audit log's flattened words, the time limit, Ramadan days and public holidays; per nurse the kinds only, with no dates, pin values or figures; shifts under today's codes so a rename is no change; a re-plan's starting roster and date not diffed, its facts carrying the date and version
- [ ] Each soft rule costing something in either result: amount, weight and penalty per side, each on its own input, `weight_differs`, ordered by the largest penalty difference; an unexplained side keeps its stored penalties with null amounts and weights and a flag
- [ ] The cells that differ for the nurses in both results, under today's codes, by name then date; a nurse in one result only is named among the input changes and left out of the cells
- [ ] Every nurse of either result in name order with both hours accountings, null on a side she is not in; violations and facts in three groups, the same when rule, nurse and date agree; each side's statistics
- [ ] The solve history filtered to a month shows "Compare two results" with two pickers over that month's results with a roster, each leaving out the other's choice, the two newest by default, the pair in the address; absent without a month filter; one sentence with fewer than two; a failed read says so
- [ ] The page reads older left, newer right, differences signed newer minus older, in the spec's section order, with the rule and unit-rule labels the rules pages use, the `change` rule with the plain solve's column empty, tables scrolling in their own regions at 375 px
- [ ] Each result page links "Compare with another result" to the month's history with that result as one side and the newest other as the second
- [ ] No schema change; OpenAPI document and generated client regenerated and matching
- [ ] `docs/ARCHITECTURE.md`: section 8's "What a solve shows afterwards" and section 5's solve-history bullet each say that any two of a month's results holding a roster compare side by side, for the manager only, with the inputs' differences named
- [ ] API tests through the solve history API with the scripted solver, and frontend tests in the app-level Vitest suite, covering every point in the spec's Testing Decisions; no Playwright journey
- [ ] Driven on a scratch stack of its own: two real solves of one month with a weight changed between them, compared on the page and on a phone width; the stack removed after
