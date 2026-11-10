# 57: A batched carry-over read

**What to build:** Reading a unit's carry-over for a month in one go instead of one nurse at a time. Today the carry-over chain (`closes.chain.Chain.carry_in`) is read per nurse, and every solve input's assembly (`solves.input.assemble`) does that for each nurse of the unit. The Day view (ticket 39) assembles every unit for its date, and measured about 7 ms a nurse on the seeded stack, nearly all of it in the chain: a 300-nurse hospital would wait about 2 seconds. A batched read takes the unit's nurses and the month and answers every nurse's carried values with a fixed number of queries, whatever the count of nurses. The answers are exactly what the per-nurse read gives today, for every case the chain covers (projected, closed, re-closed, no roster for her, first month, January, a transfer, a close stored before a field existed). Nothing a reader sees changes, only how fast it comes. Decided by the user in the review of ticket 39 (2026-11-09).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] A batched read of the chain for a unit's nurses and a month, answering the same values as `Chain.carry_in` for each nurse
- [ ] `solves.input.assemble` uses it, so a solve, a re-plan, a close, My month, the Day view and every check gain from it
- [ ] Tests: for every case in `closes/tests/test_close.py`'s chain tests, the batched answer equals the per-nurse answer; the number of queries for a unit does not grow with its nurses (`django_assert_max_num_queries`)
- [ ] The Day view's read timed again on a seeded scratch stack, before and after, in the ticket comment
- [ ] No change to any API answer, the OpenAPI document or the frontend

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
