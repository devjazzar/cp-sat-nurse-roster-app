# 12: Solve history and result details

**What to build:** Next to the draft grid the unit manager and, later, the approvers see everything the result holds: each nurse's hours accounting (contract, leave credit, required, worked, overtime, shortfall) and cost, the explanation of the largest violations per rule, the solver's statistics and what stopped it, and any recorded facts that broke rules. The unit's solve history lists every solve with its status, duration and cost; any result can be restored as the draft. The System Admin sees the solve history across all units.

**Blocked by:** 11 Run a solve

**Status:** ready-for-agent

- [ ] Result details panels: per-nurse accounting and cost, explanations per rule, solver statistics, precheck, elapsed violations
- [ ] Unit solve history with status, who asked, duration, cost; open any result; restore it as the draft
- [ ] System Admin solve history across units without roster content
- [ ] API tests cover history, restore and the admin view

## Comments

**From ticket 10 (2026-11-05).** A stored solve input and a result name a nurse's leave dates (`nurses[].leave`, `nurses[id].leave`). They hold no type. The System Admin's history "without roster content" must leave out both blocks: a run of leave dates against a nurse's ID is what ticket 10 kept out of the audit log.

**From ticket 11 (2026-11-05).** `Solve` is in `solves/models.py`, with `input` and `result` as the solver had them, except that `jsonb` keeps no key order. A row that ended with no roster: `succeeded` with `result.ok` false, or `cancelled` with `result.roster` null, or `result` null when it was stopped before a job started. `failed` has no result, and `failure` is `solver` or `refused`; `refused` reads as rules to review, not as a failed solve. `error` keeps the last attempt's reason. `Roster.solve` is the solve the grid came from, and restoring a result means `rosters.drafts.replace_grid`, which carries renames. The stored grid in `result.roster` holds shift codes as they were then. The page's `SolveProgress` has a `precheck` and `message` to reuse; `LastSolve` in `routes/_signed-in/roster.tsx` is the first thing to replace with these panels.
