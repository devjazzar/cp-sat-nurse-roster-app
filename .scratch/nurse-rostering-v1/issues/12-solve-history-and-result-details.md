# 12: Solve history and result details

**What to build:** Next to the draft grid the unit manager and, later, the approvers see everything the result holds: each nurse's hours accounting (contract, leave credit, required, worked, overtime, shortfall) and cost, the explanation of the largest violations per rule, the solver's statistics and what stopped it, and any recorded facts that broke rules. The unit's solve history lists every solve with its status, duration and cost; any result can be restored as the draft. The System Admin sees the solve history across all units.

**Blocked by:** 11 Run a solve

**Status:** ready-for-agent

- [ ] Result details panels: per-nurse accounting and cost, explanations per rule, solver statistics, precheck, elapsed violations
- [ ] Unit solve history with status, who asked, duration, cost; open any result; restore it as the draft
- [ ] System Admin solve history across units without roster content
- [ ] API tests cover history, restore and the admin view
