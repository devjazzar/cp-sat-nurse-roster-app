# 17: Re-plan from a date

**What to build:** Mid-month the unit manager chooses a date and re-plans: days before it are facts (the roster in force plus recorded leave and pins), the solver keeps the new roster close to the current one through the change weight, and the result is a new version in force with a comparison against the previous one and the recorded facts that broke rules shown as facts, not errors.

**Blocked by:** 16 Changes after approval

**Status:** ready-for-agent

- [ ] Solve input assembler supports the published roster and the re-plan date; facts before the date are pinned from the roster in force, leave and pins
- [ ] Re-plan solve runs through the same queue with progress and cancel; success creates a version with origin 're-plan'
- [ ] Comparison view: cells changed, cost before and after, per-rule differences; elapsed violations listed as facts
- [ ] API tests cover the assembler's fact pinning and the version created, with the fake and once with the real solver

## Comments

**From ticket 11 (2026-11-05).** `solves.input.assemble` has no re-plan yet. A month that has started can be solved from scratch today, which replaces the draft's whole grid: `_what_stops_it` refuses only a month that is over. Once a month has an approved roster a plain solve should be refused in favour of a re-plan.

**From ticket 12 (2026-11-05).** `rosters.drafts.why_not_restore` refuses a month that is over and allows the month under way, as `_what_stops_it` does for a solve. When this ticket refuses a plain solve once a month has an approved roster, restore needs the same refusal, which ticket 14's state check will already give. A result's `replan` block is not shown anywhere yet: `solves/history_api.py`'s `SolveResult` leaves it out, and section 8's "in a re-plan the comparison with the roster in force" is yours to add to `components/solve-result.tsx`.

**From ticket 14 (2026-11-05).** A submitted or approved month refuses a plain solve, its end on the grid and a restore, all through `rosters.drafts.why_frozen` (`solves.api._what_stops_it`, `solves.running._finish`, `drafts.why_not_restore`). A re-plan of an approved month has to pass that check on purpose and end in a new `RosterVersion` with origin `replan` (ticket 16), not through `drafts.replace_grid`, which refuses a frozen roster outright.

**From ticket 16 (2026-11-06).** Versions exist, and one function makes them.

- **Make the re-plan's version with `rosters.versions.make_version(roster, grid, VersionOrigin.REPLAN, by, reason, solve=solve)`**, holding the roster's row lock. It numbers it (latest + 1) and writes `Roster.grid` from it, so `Roster.grid` stays the latest version's grid under today's codes. Then `record("roster.changed", ...)` with the version and counts and no reason, and `notifications.sending.roster_changed(unit, month, by)`, as `rosters.api.save_version` does.
- **`rosters.drafts.why_frozen` still refuses an approved month's solve, `_finish` and a restore.** That is on purpose: your re-plan passes it deliberately. Its words for an approved roster now point the manager at editing cells by hand.
- **The comparison with the roster in force:** `rosters.versions.differences(before, after)` compares two grids cell by cell under today's codes, and `GET /units/{id}/roster/versions/compare` answers any two versions. The page's `components/roster-versions.tsx` already labels origin `replan` "Re-planned".
- **Facts before the date** include the manager's pins (origin `manager`, which every direct edit now makes) and leave. Leave recorded on a worked day of an approved roster already took the shift off as a version of its own (origin `edit`), with no pin: the leave is the fact.
- **Locks:** the nurses' locks are now `FOR NO KEY UPDATE` (`no_key=True`). A notification's foreign key to a colleague's user is checked at commit, and `FOR UPDATE` deadlocked a leave against an edit (`rosters/tests/test_two_at_once.py`). Keep any new nurse lock the same.
