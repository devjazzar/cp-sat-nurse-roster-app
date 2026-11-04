# 14: Submit, approve, reject

**What to build:** The unit manager submits the draft; it freezes. The Deputy CNO and the CNO see submitted rosters waiting on their home page, open one with the grid and every result detail, and approve or reject it with a comment. Approval makes it the roster in force: the unit's nurses now see it with colleagues' names and shifts only. A rejection returns it to draft with the comment visible to the manager. Approvers see a per-unit, per-month overview (no roster, draft, submitted, approved) and can view any unit's roster read-only.

**Blocked by:** 11 Run a solve

**Status:** ready-for-agent

- [ ] Roster states draft → submitted → approved, submitted → draft on rejection with the comment kept; a frozen draft refuses edits and solves
- [ ] Approvers' home lists submitted rosters; approve and reject with comment; both audited
- [ ] First approval creates roster version 1 with origin 'solve'
- [ ] Nurse roster page shows the approved roster for the current and coming months with names and shifts only
- [ ] Overview of every unit's state per month for the CNO and Deputy CNO; read-only roster view of any unit
- [ ] API tests cover the state machine, authorization of each transition, and the nurse view's field restriction
