# 43: Compare two results of the same month

**What to build:** A Unit Manager opens her unit's solve history filtered to a month and chooses two of that month's results that hold a roster. She reads them side by side on one page, older on the left and newer on the right: the two solves' facts; what changed between their solve inputs (hospital rules and weights and unit rules field by field, the time limit, Ramadan days and holidays, and per nurse only the kind of change: joined, left, attributes, leave, pins, carry-over; a re-plan's side saying the date and version it started from); each soft rule's amount, weight and penalty in each result on its own input, with a differing weight marked; the cells that differ with their count; each nurse's hours and cost with the difference; the hard rules broken and the recorded facts in three groups (both, only the older, only the newer); and the solver's statistics. The pair rides in the page's address, each result page links to the comparison, and nothing is changed or restored from it. The manager alone reads it. Spec: `../spec.md`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] A manager-only endpoint answers the comparison of two results of her unit and month in any order, naming the older and the newer; 400 for the same solve twice, different months or a result without a roster; 404 for another unit's solve as for a result; every other role refused; nothing audited
- [x] The inputs' differences: hospital rules and weights and unit rules field by field in the audit log's flattened words, the time limit, Ramadan days and public holidays; per nurse the kinds only, with no dates, pin values or figures; shifts under today's codes so a rename is no change; a re-plan's starting roster and date not diffed, its facts carrying the date and version
- [x] Each soft rule costing something in either result: amount, weight and penalty per side, each on its own input, `weight_differs`, ordered by the largest penalty difference; an unexplained side keeps its stored penalties with null amounts and weights and a flag
- [x] The cells that differ for the nurses in both results, under today's codes, by name then date; a nurse in one result only is named among the input changes and left out of the cells
- [x] Every nurse of either result in name order with both hours accountings, null on a side she is not in; violations and facts in three groups, the same when rule, nurse and date agree; each side's statistics
- [x] The solve history filtered to a month shows "Compare two results" with two pickers over that month's results with a roster, each leaving out the other's choice, the two newest by default, the pair in the address; absent without a month filter; one sentence with fewer than two; a failed read says so
- [x] The page reads older left, newer right, differences signed newer minus older, in the spec's section order, with the rule and unit-rule labels the rules pages use, the `change` rule with the plain solve's column empty, tables scrolling in their own regions at 375 px
- [x] Each result page links "Compare with another result" to the month's history with that result as one side and the newest other as the second
- [x] No schema change; OpenAPI document and generated client regenerated and matching
- [x] `docs/ARCHITECTURE.md`: section 8's "What a solve shows afterwards" and section 5's solve-history bullet each say that any two of a month's results holding a roster compare side by side, for the manager only, with the inputs' differences named
- [x] API tests through the solve history API with the scripted solver, and frontend tests in the app-level Vitest suite, covering every point in the spec's Testing Decisions; no Playwright journey
- [x] Driven on a scratch stack of its own: two real solves of one month with a weight changed between them, compared on the page and on a phone width; the stack removed after

## Comments

**Implemented on 2026-11-10,** on branch `claude/ticket-43-compare-results-1987e0` (`4b7f2a7`, `6ade442`, `96ef52c`, `99b38dd`,
then `origin/main` merged in as `d3cb7a4`, with ticket 41), from `main` at `0c4393f`. Draft pull request
[Nurse-Fold/cp-sat-nurse-roster-app#30](https://github.com/Nurse-Fold/cp-sat-nurse-roster-app/pull/30).

The suites ran locally under the heavy-run lock, the backend on a throwaway PostgreSQL 18 container of my own:
- the backend, on `6ade442`: 2990 passed. After the review's fixes (`99b38dd`) I reran `solves/`,
  `hospital/tests/test_rules.py` and `rosters/tests/test_replan.py`: 336 passed;
- the frontend: one `npm test` run on `99b38dd`, 738 passed; after the merge with `main`, 758 passed; `npm run build`
  succeeded;
- `makemigrations --check`: "No changes detected";
- the OpenAPI document and the client were regenerated after the API commit, and again after the merge, with no
  difference.

**What the dev stack needs:** a **rebuild** (`docker compose up -d --build`) to serve the new page and endpoint. There is
no migration, no new dependency, and no change to compose, the `Dockerfile` or the solver. Ticket 41's merge brings its
own needs, which its comment states.

**What was built, criterion by criterion.**
- **The endpoint:** `GET /api/units/{id}/solve-history/compare?a&b` (`compareSolveResults`, `solves.history_api`). It
  takes the `manager` auth, so every other role gets the manager-only refusal. The solves are looked up with
  `filter(unit=unit)`, so another unit's solve under her own unit's address is a 404, and another unit's address is a
  403, as for a result. The pair is put in order by `requested_at`, then id. It answers 400 for:
  - the same solve twice: "Choose two different results to compare.";
  - two months: "Only two results of the same month compare.";
  - a result without a roster to keep: "Only results that hold a roster compare." (`has_a_roster_to_keep`, the
    history's own test).

  It writes nothing and records nothing in the audit log.
- **The comparison itself is in `solves/comparison.py`;** the API module builds the answer from it.
  - **Today's names:** both inputs go through `in_current_skill_names`. Every shift code either input names (the
    catalogue's hours, the forbidden successions, the unit's shift fields and skill needs, each nurse's allowed shifts,
    history and pins) is read through `rosters.drafts.current_codes`, and the unit block through
    `units.rules.with_shift_codes`. So a rename between the two solves is no change.
  - **Hospital rules** are flattened by `hospital.rules.flattened`, now shared with `changes`, so the field names are the
    audit log's (`weights.night_rest`). The unit block is compared field by field, without `name`.
  - **Time limit** and the **calendar** (`ramadan_days`, `public_holidays`) each have their own group.
- **The nurses:** only the kinds, in a fixed order: `joined`, `left`, `attributes`, `leave`, `pins`, `carry_over`, plus
  `preferences` and `skills` (see **Worth your review**). No date, pin value or figure is sent. A re-plan's `published`
  and `replan_from` are not compared. Each side's facts carry `replan_from` and `replan_of`, and the page words them as
  "12 June, of version 1".
- **The rules:** each side's per-rule `weight` and `raw` come from `validate_grid`'s full list of soft rules on its own
  input. The result page's `explanation` keeps only the rules that cost something, so a rule costing 0 on one side would
  lose its weight there. The penalties are the stored ones.
  - The `change` rule of a solve that is no re-plan is null on that side.
  - A side the solver's code no longer reads keeps its penalties, with null amounts and weights and its flag.
  - The rows are ordered by the largest absolute difference of penalty, a null counting as 0, then by name.
- **The cells:** only the nurses in both results, under today's codes, by name then date. On the page they are grouped by
  nurse, the name once with her count.
- **Hours:** every nurse of either result, by name, null on a side she is not in.
- **Violations and facts:** three groups each, matched on rule, nurse and date as a multiset, so two unit-wide entries
  on one side and one on the other leave one over.
- **The page:** `components/result-comparison.tsx`, a "Compare two results" section on the manager's history filtered to
  a month.
  - **The pickers:** two of them over the page's rows that hold a roster, each leaving out the other's choice. They
    default to the two newest, or with one result in the address to the newest other. The pair is written to the address
    as `a` and `b`. A pair from an older page shows as "A result from an older page of the history".
  - **Fewer than two results** holding a roster: one sentence and no pickers. **A failed read** says so, and how to try
    again.
  - **The sections:** in the spec's order, each table in its own scrolling region, the older on the left, every
    difference newer minus older. No Restore, no file.
- **The labels:** the rules pages' label tables moved, unchanged, to `lib/hospital-rules-words.ts` and
  `lib/unit-rules-words.ts`. Both pages and the comparison read them from there.
  - A weight reads "Weight: Night rest".
  - The two catalogue-made fields read "Hours of each shift, from the shift catalogue" and "Skills required to work,
    from the skill catalogue".
  - Values read in the pages' words: On and Off, weekday names, "D then C", the headcounts and skill needs written out.
- **The link:** each result page that holds a roster has "Compare with another result", pointing to
  `/solve-history?month=…&a=<this result>`.
- **ARCHITECTURE:** section 5's solve-history bullet gains one clause, and section 8's "What a solve shows afterwards"
  gains the sentences.
- **Tests at the agreed seams:**
  - `backend/solves/tests/test_compare.py` (28) covers every point of the spec's Testing Decisions, and a version 1 input
    against a version 2 one.
  - `src/app.test.tsx`, "comparing two results (ticket 43)" (14) covers:
    - the section only with a month;
    - the default pair and the pickers' exclusions;
    - the address written and read, an older page's id included;
    - one id in the address;
    - the sections' order, the columns, the labels, the signs, the weight mark and the empty `change` side;
    - the three groups;
    - the unexplained side, fewer than two, and a failed read;
    - the result page's link, and none without a roster;
    - the CNO and the Deputy CNO kept out.

**What was driven, and how.** I used my own scratch stack, `e2e/stack.sh up t43` (ports 18430 and 18944), on 10 November
2026, in the desktop app's browser pane.
- As Mona, on the roster page, I solved January 2027 for real (10 s), at a cost of 130.
- Carla then raised the weight of a fair share of night shifts from 1 to 4, through `PUT /api/hospital/rules` over
  Caddy's HTTPS (a scratch script, since the CSRF cookie is Secure).
- Mona solved again, at a cost of 277.
- **The history of January 2027** showed the section with the two solves chosen, the newer as "One result".
  - The inputs read only "Weight: Fair share of night shifts 1 → 4".
  - The rules read "Fair share of night shifts", marked Weight differs: 49 × 1 = 49 against 49 × 4 = 196, +147. "Fair
    share of day shifts" and "Hours short" were unchanged.
  - 72 cells differ, the hours and costs per nurse, no violation, no fact, and the statistics.
- **At 375 px:** the page did not scroll sideways (`scrollWidth` 375). After `96ef52c` and the rebuild, the facts and
  statistics tables fit, and the four wider tables scroll in their own regions. The pickers' option text fits after it
  dropped "Asked for at".
- **From the older result's page,** "Compare with another result" opened the history with it as `a` and the newer as
  `b`, the older still on the left.
- I held the page by hand against `better-interface`, `better-writing` and `better-accessibility`:
  - every table has a named region and row headers, and the two-level header of the rules table names each column's
    side for a screen reader;
  - the pickers have labels;
  - a failed read is an alert;
  - the wording matches the result page's.

The stack is down and its volumes gone. My PostgreSQL container is stopped.

**What was found, and fixed.**
- In the first draft, the result page's link carried `#compare`. The browser could not jump to it, because the section
  renders after its data, so the hash was dropped.
- The section and its first table shared a name, so a screen reader met two regions called "The two solves". The tables
  now have names of their own.

**Findings for you, not fixed.**
- **A browser check near its margin, not caused by this ticket.** Browser checks attempt 1 on `a1b96aa` failed
  `tests/desktop/roles.spec.ts:22`, "every page of the Unit Manager with a nurse profile opens on a desktop".
  - **What failed:** `toHaveCount(0)` on "Loading…" (`e2e/support.ts:108`) saw one, then two, for 5 s. It counts loading
    texts, not pages.
  - **Where:** the trace shows ICU's roster page for December, 64 nurses. Its calls took 1.5 s (`roster`), then 2.3–3.5 s
    each (the result, the versions' compare, `replans/preview`, `close`), so the roster page's and the month close's
    "Loading…" outlasted the wait.
  - **Not this ticket's:** none of those endpoints or components changed here; the roster page only imports `ruleName` and
    `signed` from a new place. This ticket adds no header link, so the pages the test walks are the same.
  - **Already close on `main`:** the test took 6.8–8.1 s in all on `main`'s last four runs, against 8.4 s for the failed
    attempt. Attempt 2 on the same head passed in 8.2 s, with all 73 checks.
  - **Not fixed here:** a longer wait is what the suites' rules forbid, and the roster page's loads are not this ticket's.
    **Recommendation:** whoever next touches the roster page or the month close looks at why `close` and
    `replans/preview` take over 3 s for 64 nurses on GitHub's runner.

**What was NOT checked.**
- **A re-plan side on a real stack.** It was covered only through the API with the scripted solver and with a stubbed
  answer.
- **A version 1 input on a real stack.** It was covered only by the API test, which edits a stored input.
- **The six parallel frontend runs and the browser checks, locally.** GitHub runs them on the pull request.
- **A screen reader**, beyond the accessibility tree.

**Decisions taken here.**
- **The values sent for a rule are the stored values, under today's names.** The page words them. The API's
  `older`/`newer` are untyped JSON (`Any`).
- **The time limit is the solve's `time_limit_seconds`,** not the input's copy of it. They are the same number.
- **The rules come from `validate_grid`'s full list of soft rules,** not from `explanation`. See the rules above.
- **"Not in its input"** is what the page shows for a field one input lacks, with one sentence explaining it.

**Worth your review.**
- **Two nurse kinds beyond the spec's six: `preferences` (her desired and undesired days) and `skills`.**
  - Both sit in a nurse's block, and neither fits the six.
  - Leaving them out would have the page say "Both solves were given the same month" when a nurse's preferences or skills
    differed, which can explain moved cells as well as a weight change.
  - The words are the stale-draft warning's (`changes_since`).
  - **Recommendation:** keep them, and add them to the spec's list.
- **A version 1 input against a version 2 one always shows its four skill fields as changed**, from "Not in its input" to
  the newer's values: `required_skills`, `weights.skill_shortfall`, `skill_needs` and `skill_needs_hard`. That is true,
  since the older solve was given no skills, even when the newer's values are the defaults the solver assumes.
  **Recommendation:** keep it; it is honest and rare.
- **"Holding a roster" is `has_a_roster_to_keep`,** which also requires `ok`, as the spec says ("the same test the history
  uses"). A roster that breaks a hard rule can therefore not be chosen, so the "hard rules each roster breaks" groups are
  empty in practice; only the facts carry anything. The grilling's notes had allowed `ok` false. **Recommendation:**
  keep the spec's test; widening it would also change what the history calls "found a roster".
- **The pickers read the page's rows,** as the spec says. After "Older solves", the defaults are the newest of that page.
  **Recommendation:** accept, per the spec's own note on fifty solves.

**Review.** `code-review` against `0c4393f` ran its two axes in parallel.
- **Standards.**
  - Fixed in `99b38dd`:
    - **(hard)** two test expectations were worked out by the same `validate_grid` call the code makes. The weights now
      come from the solver's sample fixture, and the amounts are held equal on both sides and above 0;
    - the CNO and Deputy guard test waited on the address and then checked for an absence. It now waits for the home's
      heading;
    - the rule names and `signed` are shared from `lib/solve-words.ts` with the result page;
    - `Explained` is no longer declared twice;
    - the headcounts and skill needs use the generated types.
  - Kept, with reasons:
    - The comparison module's dataclasses mirror the API's schemas. The module stays free of Ninja, as `rosters.versions`
      and its `CellChange` are.
    - `valueShown` branches on field names. Those are the fields whose values need words, and one place holds them.
    - The older/newer pairs are the subject itself.
- **Spec.**
  - Fixed in `99b38dd`:
    - the cells are now grouped by nurse;
    - the shift codes named in skill needs are collected too. A need can only name one of the unit's shifts, which were
      collected already, so this was a safeguard, and the test also passes without it.
  - The route guard test it asked for was already there.
  - Its other points are the **Worth your review** items above, and they are noted there.

**Things later tickets should know.**
- The rules pages' words are in `lib/hospital-rules-words.ts` and `lib/unit-rules-words.ts`, with `HOSPITAL_RULE_LABELS`
  and `UNIT_RULE_LABELS` keyed by the stored field. A new rule field gets its label there once.
- `lib/solve-words.ts` now has `ruleName` and `signed`.
- `hospital.rules.flattened` is the audit log's field-by-field reading of the hospital rules.
- `solves.comparison.soft_rules(solve)` gives every soft rule of a stored result on its own input, costing or not.

**Reviewed by the user (2026-11-10):** all four points kept as recommended.
- The nurse kinds `preferences` and `skills` are kept, and added to the spec's list.
- A version 1 input shows its skill fields as changed.
- "Holding a roster" is `has_a_roster_to_keep`.
- The pickers read the page's rows.
