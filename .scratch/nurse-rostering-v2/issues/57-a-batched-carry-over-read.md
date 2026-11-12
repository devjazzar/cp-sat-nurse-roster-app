# 57: A batched carry-over read

**What to build:** Reading a unit's carry-over for a month in one go instead of one nurse at a time. Today the carry-over chain (`closes.chain.Chain.carry_in`) is read per nurse, and every solve input's assembly (`solves.input.assemble`) does that for each nurse of the unit. The Day view (ticket 39) assembles every unit for its date, and measured about 7 ms a nurse on the seeded stack, nearly all of it in the chain: a 300-nurse hospital would wait about 2 seconds. A batched read takes the unit's nurses and the month and answers every nurse's carried values with a fixed number of queries, whatever the count of nurses. The answers are exactly what the per-nurse read gives today, for every case the chain covers (projected, closed, re-closed, no roster for her, first month, January, a transfer, a close stored before a field existed). Nothing a reader sees changes, only how fast it comes. Decided by the user in the review of ticket 39 (2026-11-09).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] A batched read of the chain for a unit's nurses and a month, answering the same values as `Chain.carry_in` for each nurse
- [x] `solves.input.assemble` uses it, so a solve, a re-plan, a close, My month, the Day view and every check gain from it
- [x] Tests: for every case in `closes/tests/test_close.py`'s chain tests, the batched answer equals the per-nurse answer; the number of queries for a unit does not grow with its nurses (`django_assert_max_num_queries`)
- [x] The Day view's read timed again on a seeded scratch stack, before and after, in the ticket comment
- [x] No change to any API answer, the OpenAPI document or the frontend

## Comments

**From ticket 43 (2026-11-10):** on GitHub's runner, ICU's December roster page (64 nurses) took 2.3–3.5 s for each of the result, the versions' compare, `replans/preview` and `close`. That kept "Loading…" past the 5 s wait in `e2e/tests/desktop/roles.spec.ts:22` once. Time those calls before and after this ticket too.

**From the small-fixes session (2026-11-10):** the roster page's calls timed on a seeded scratch stack (`e2e/stack.sh`, ICU's December: 64 nurses, approved, one version), as `omar`, each warm and in the `web` process (the best of three; `solves.input.assemble` and `Chain.carry_in` timed by wrapping them):

| Call | Time | Queries | Assembles | `carry_in` calls, time |
|---|---|---|---|---|
| `roster`, before | 631 ms | 699 | 2 × ~255 ms | 128, 291 ms |
| `roster`, after this session's fix | 313 ms | 365 | 1 × 233 ms | 64, 134 ms |
| `solve-history/{id}` (the result) | 146 ms | 145 | 0 | 0 |
| `roster/versions/compare` | 9 ms | 9 | 0 | 0 |
| `replans/preview` | 308 ms | 345 | 1 × 218 ms | 64, 123 ms |
| `close` | 460 ms | 537 | 1 × 275 ms (inside `Chain.carry_out`'s projection) | 128, 282 ms |

- The page's time is mostly assembly, and about half of each assembly is the per-nurse carry-over read: about 2 ms a nurse here. The rest is the other per-nurse reads in `assemble` (placement, credited days, skills, pins).
- `roster` assembled the same month twice (in `changes_since` and again for the editor), and three times for a draft edited or out of date (`check_saved`) or a submitted roster (`review.new_since`). This session made it read the month once (`rosters/tests/test_roster_month_reads.py`), so that part is done. The submit and approve endpoints still check with an assembly of their own before `_roster_month` reads again; that is left as it was.
- `close` reads every nurse's carry-in twice: once in the projection's assembly, then again in `closes.api._carry_over` for the `into` column, on the same `Chain`. A batched read serves both.
- The result and the compare never assemble, so this ticket does not make them faster. Their 2.3–3.5 s on GitHub's runner is not their own work (9 ms and 146 ms here). The page sends them at the same moment as `replans/preview`, `close` and `solves/preview` to gunicorn's 3 sync workers, on a 4-core runner that is also running Chromium, the solver and a second stack. With this stack's `web` limited to one CPU (`docker update --cpus 1`), firing them together made `replans/preview` and `close` about 1.7 times slower, and the compare once waited 438 ms for a worker. That fits waiting for a CPU or a worker, but nobody has measured it on the runner.

**From ticket 50 (2026-11-12):** the chain now reads one more profile field and resets one more value in January.
`closes.chain.opening` takes the nurse's `overtime_balance` (her opening value, `NurseProfile.overtime_balance`, default 0)
instead of a literal 0.0, and `NEW_YEAR` gains `"overtime_balance": 0.0`, applied in `Carried.into` as before. `CARRIED` and
`CARRIED_SINCE` are unchanged (ticket 49 had added the field to both). A batched read must give the same: the field from the
profile for a first month, carried unchanged through a month with no roster (it is not in `NO_HISTORY`), 0 in January and 0 out
of a close stored before it. The cases are `closes/tests/test_close.py`'s `TestTheOvertimeBalance`, beside
`TestTheCountOfPreferencesNotKept`; its helper `shares_overtime` writes the unit's switch straight into `unit.rules` until
ticket 51 makes it a unit rule.

**From ticket 51's review (the user, 2026-11-12).** The draft's per-nurse explanation puts the nurse's name before the
solver's own words, which already begin with her id, so a line reads "Amal Saleh: Amal: 20 h overtime, share 4.7 h, 3 h
priced". Drop the repetition for every rule's line (the page's name, then the solver's words without their leading id), with
its frontend test.

**Implemented on 2026-11-12,** on branch `claude/ticket-57-batched-carry-over-67c293`, pull request
devjazzar/cp-sat-nurse-roster-app#33, from `main` at `8c83302` (`ff91b98` the build, `6b950fe` the code review's points, then
this comment). The suites, locally, under the heavy-run lock, on `6b950fe`:
- the backend under pytest on a throwaway PostgreSQL 18 container of my own: **3627 passed**; `makemigrations --check`: no
  changes;
- the frontend: `npm test` **846 passed**, `npm run build` clean, the typecheck clean. No schema or endpoint changed, so the
  OpenAPI document and the client are untouched (GitHub's backend job compares them with the export);
- the solver's suite not run: nothing in `solver/` changed. GitHub ran it, with the rest, on every push.

**What the dev stack needs:** a **rebuild** (`docker compose up -d --build`) for the backend's code and the SPA. No migration,
dependency, compose, Dockerfile or solver change.

**What was built, criterion by criterion.**
- **A batched read.** `closes.chain.Chain.carry_ins(nurses, month) -> {hospital ID: Carried}`. The per-nurse walk did no
  queries of its own; what it read per nurse was where her chain starts. `carry_ins` reads that for all the nurses at once:
  - her latest closed month in force (`latest_closed`, now for a list): the closed rows' ids, months and closes without their
    values, the closes in force of those units' months (ids only, no longer whole `MonthClose` rows with their inputs and
    results), then the values of the rows chosen: three queries. The rule is unchanged: the first row by month, then close
    time, whose close is in force, so a re-close that dropped her falls back to the month before;
  - her first month, from her placements, prefetched once for the nurses (`prefetch_related_objects`), where `_added` used to
    query again past the prefetch;
  - her first approved roster from her start's month, for those with no closed month: one query of each approved roster's
    month and the hospital IDs in its grid (`ARRAY(SELECT jsonb_object_keys(grid))`, filtered by `?|` on the IDs asked), each
    nurse's first taken in Python.
  The walk itself (`_walk`, the old loop, a run of months with no roster as one step) is unchanged. The answers are memoised
  on the reading by nurse and month, beside the unit's months and projections it already memoised, so a second ask reads
  nothing. `carry_in(nurse, month)` is `carry_ins` for one (My month, `rosters.own_month`, uses it). A close's chain
  (`project=False`) reads no rosters, as before.
- **`solves.input.assemble` uses it** for the month's serving nurses (those left out are not asked, so `carried` holds the same
  nurses as before), so a solve, a re-plan, a close, My month, the Day view and every check gain from it. **`close`** reads
  each nurse once: `closes.api._carry_over` asks the same reading as the projection's assembly, and gets the memo. The order of
  `nurses`, `left_out`, `to_check` and every field of the input are as they were (ticket 56 reads them).
  - **The one other per-nurse read in `assemble`, leave, is batched too** (`nurses.rostering.leave_of`, one query for the
    month's nurses; `leave_dates` is it for one). Once the chain was batched it was the only query left that grew with the
    nurses, in every assembly and in every projection's.
- **Tests.**
  - `closes/tests/test_close.py`, `every_batched_read_is_the_one_at_a_time_read`, autouse: every batched read in the file, of
    every month a test asks and every month before it a projection steps through, is held for each nurse to the chain as it
    was read one nurse at a time (`one_at_a_time`, the old `carry_in` with its three per-nurse queries kept in the test file,
    as `walked` was kept before it), on a reading of its own, the whole `Carried` compared (values, source, month, year).
    Inside the reference, the months before are read one nurse at a time too. That covers every chain case of the file:
    `TestTheChain`, `TestAFarMonth`, `TestTheCountOfPreferencesNotKept`, `TestTheOvertimeBalance`, `TestThreeMonths`, and the
    schedule's, the facts' and closing-again's on the way. Checked that it bites: choosing the older closed month, or dropping
    the first roster, fails it with the nurse and month named.
  - `TestTheBatchedRead`: ER's four nurses and one joining, then four more, the chain's queries for the unit's month at nine
    no more than at five (`django_assert_max_num_queries`), for a chain that projects and a close's, on her opening values,
    a projected June, a closed June, and a closed June then a projected July; the month's whole assembly likewise (opening,
    projected, closed); and the close's view of an approved June reading where each nurse's chain starts once for both
    columns.
  - The existing `solves`, `rosters`, `closes` and Day view tests unchanged and green.
- **Timings** on a seeded scratch stack (`e2e/stack.sh up nr-t57`), ICU's December, 64 nurses, approved, one version; in
  `web`'s own process with Django's test client signed in (as `omar`; the Day view of 10 December as `hala`), each warm, the
  best of three; `assemble` and the chain's reads timed by wrapping them (`carry_in` before, `carry_ins` after):

| Call | Time | Queries | Assembles | Chain reads, time |
|---|---|---|---|---|
| `roster`, before | 296 ms | 305 | 1 × 212 ms | 64 `carry_in`, 138 ms |
| `roster`, after | 112 ms | 52 | 1 × 29 ms | 1 `carry_ins`, 3 ms |
| `replans/preview`, before | 363 ms | 286 | 1 × 256 ms | 64, 169 ms |
| `replans/preview`, after | 128 ms | 33 | 1 × 30 ms | 1, 3 ms |
| `close`, before | 380 ms | 477 | 1 × 198 ms (inside `Chain.carry_out`'s projection) | 128, 247 ms |
| `close`, after | 88 ms | 32 | 1 × 29 ms | 2 (the second from the memo), 3 ms |
| Day view (10 December), before | 329 ms | 361 | 2 × 263 ms in all | 68, 176 ms |
| Day view (10 December), after | 129 ms | 82 | 2 × 69 ms in all | 2, 29 ms |

- **No change** to any API answer or the OpenAPI document. The frontend's one change is below.

**The explanation line (the user's decision in ticket 51's review), made in the frontend.** `lib/solve-words.ts` gains
`ownWords`, the solver's words without the `"<her id>: "` they begin with, only her own id and only exactly that, and
`solverLine`, the name (and the day when the words do not hold it) then `ownWords`. It is used wherever the page puts a
nurse's name before the solver's words: each rule's largest occurrences and the recorded facts in the result
(`solve-result.tsx`), the comparison's facts and hard rules (`result-comparison.tsx`, whose own copy of `whose` it replaces),
the close's facts (`month-close.tsx`) and the check's hard rules (`roster-notes.tsx`). Why not the backend's `solves.result`:
the API's `text` is the solver's own words and is read as such (a compare, a close's stored facts, ticket 56's rows); stripping
it there changes an API answer, which this ticket must not. `app.test.tsx`: "Amal Saleh: 20 h overtime, share 4.7 h, 3 h
priced" and "Amal Saleh: 5 full runs of 3 shifts, max 3"; a line beginning with another nurse's id (`h10:`) left whole; a
nurse with no name keeps her id; the close's fact and the check's hard rule.

**What was driven, and how.** My scratch stack (`e2e/stack.sh up nr-t57`, seeded), twice: on `8c83302` for the timings before,
on `6b950fe` for those after, with a script run in `web` (`manage.py shell`) calling the four endpoints through Django's test
client. The stack went down after each.

**What was NOT checked:**
- The explanation line in a browser: the frontend tests render it; no Playwright file changed. GitHub's browser checks ran.
- Timings on GitHub's runner (ticket 43's 2.3–3.5 s): not measured there.
- The query-count tests grow the unit by nurses on their opening values, in no roster and no close (ER's scripted June holds
  four); the batched read's queries are per kind of start, not per nurse, but nine closed or projected nurses were not counted.
- A re-close that drops a nurse, and a roster in a nurse's start month: kept as the old read had them (the same rule), but no
  test of the file has either case, so the reference check has not seen them.

**Decisions taken here.**
- **Worth your review: the interface.** `Chain.carry_ins(nurses, month)`, a method of the reading, answering by hospital ID as
  `Assembled.carried` is keyed; `carry_in` kept as its one-nurse form; answers memoised on the reading. One reading is one
  moment: every caller already makes a `Chain` per request, per close and per projection task, and the projection task writes
  only projected rows, which the chain never reads.
- **Worth your review: leave batched too.** The ticket names the chain; once it was batched, leave was the one read left in
  `assemble` growing with the nurses, so the assembly's query count is now fixed as well. None left that I chose not to batch;
  `changes_since`'s `_closed_since` (one query a nurse, a draft's "closed" warning) is outside `assemble` and left as it was.
- **Worth your review: the explanation line everywhere a name precedes the solver's words** (five lists), not only the rule
  explanation: the same repetition showed in each, and "every rule's line" read as all of them.
- **Worth your review: the timings** (the table above): each of the roster page's three assembling calls is now 2.6 to 4.3 times faster and makes 32 to 52 queries instead of 286 to 477; an assembly of ICU's 64 nurses takes about 30 ms instead of 200 to 260 ms, the chain about 3 ms of it. What is left of `roster` (about 80 ms) and `replans/preview` (about 100 ms, the preview asks the solver service's precheck) is outside `assemble`, as is the Day view's 60 ms. The Day view's 29 ms of chain is ER's December, which projects through November, an assembly of its own; it does not grow with the nurses. Measured in `web`'s process with the test client, warm, on this machine, not through gunicorn and Caddy, and not on GitHub's runner; the small-fixes session's table was measured the same way, and its `roster` row after its own fix (313 ms, 365 queries) is close to this one's before (296 ms, 305: `main` has gained tickets since).

**Review:** `code-review` against `8c83302`, both axes, on `ff91b98`.
*Standards:*
(1) the reference reuses the chain's own `_through` and `_next_roster_month`, against "never recomputed the way the code
computes them": kept. The batch changed only the reads where a chain starts, which the reference keeps per nurse; the walk is
the old code, and the hand-counted tests pin its answers.
(2) the close's test read the private memo: it now counts the nurses whose start is read (`latest_closed`).
(3) a stray blank line: removed.
(4) duplicated code, the reference repeating the chain's queries: kept, since that is the reference.
(5) `no_longer_serving` asked twice a nurse: `assemble` now sorts its nurses once.
(6) middle men, `carry_in` and `leave_dates`: kept as the one-nurse forms, used by My month and the leave tests.
(7) tuple columns by position and untyped `dict` returns: named, and typed.
(8) `todo`: renamed `unread`.
(9) `queries_counted` switching the check off by its name: kept, said in its docstring.
(10) a `(nurse.pk, month)` key: kept.
(11) double blank lines in two components: removed.
*Spec:* no case found where the batched read answers differently.
(1) the reference's months before were read by the batch: they are now read one nurse at a time too.
(2) the query tests grow the unit with opening-path nurses only: kept, under "NOT checked".
(3) `month-close.tsx` and `roster-notes.tsx` still repeated the id: fixed, with tests.
(4) leave batched and the line changed beyond the rule explanation, as scope: kept, under Worth your review.
(5) `_first_rosters` reads every approved roster holding any of the nurses, with no lower month bound: kept. It is one query
whose rows are the approved months holding them since their start, and it is asked only for nurses with no closed month.
The fixes were small; no second run. No Codex review, by the brief.

**Things later tickets should know.**
- Read the chain for many nurses with `Chain.carry_ins`; one `Chain` is one moment, so make a new one after a close or a new
  version (as every caller does).
- `nurses.rostering.leave_of` is the month's recorded leave for many nurses in one query.
- `lib/solve-words.ts`'s `solverLine` / `ownWords` are how a page puts a nurse's name before the solver's words.
- `closes_in_force` is gone (`_closes_in_force` returns ids only); `latest_closed` takes a list and answers by nurse id.
