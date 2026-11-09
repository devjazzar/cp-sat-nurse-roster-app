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
