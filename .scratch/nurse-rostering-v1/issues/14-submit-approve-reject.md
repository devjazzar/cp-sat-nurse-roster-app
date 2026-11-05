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

## Comments

**From ticket 10 (2026-11-05): two things to hold.**

- **Colleagues see a day off.** Ticket 10 ticked this at the seam only, and this ticket's nurse roster page is where it becomes true or false. A colleague's leave day must be the same `""` as any day off, which `roster` in a result already is. So the read's plain schema must not take anything from the result's `nurses[id]` (it holds `leave` and `leave_credit`), from the stored input's `nurses[].leave`, or from `Leave`, for anyone but the nurse reading. Add a test that a colleague's leave day and day off are indistinguishable in the answer, and one that their own cell may differ. An approver's read-only view may show leave as leave. A stored input and a result hold no type, so any type it shows comes from `Leave`, which the CNO and the Deputy CNO may read since the change on ticket 10 (2026-11-05).
- **Leave under a frozen or approved roster.** Leave writes look at no roster today. A submitted roster is frozen, but leave recorded during it changes what the approver is deciding on: refuse it there, or re-validate and show it, in `_refuse_dates` and `_rows_to_change` in `nurses/leave_api.py`. Ticket 16 has the approved case.

**Decisions from the user (2026-11-05).** A draft older than a change to a start date, gender or leave: warn, and block submit only if validating again fails. So submit validates such a draft again through the solver's validate call: a pass goes through with the warning shown, a failure refuses the submit. Ticket 11 has the warning.

**Leave recorded while a roster is submitted is allowed** (settled 2026-11-05), which answers "refuse it there, or re-validate and show it" above. Warn the approver and validate again at approval, blocking approval only if that fails.

**From ticket 11 (2026-11-05).** What to hold when freezing: `solves.api.start_solve` looks at no roster state, and `solves.running._finish` calls `drafts.replace_grid` whatever the state. A solve queued before a submit must not replace a frozen grid when it ends, so check in both. `changes_since(solve.input, unit, month)` in `solves/input.py` is the stale-draft comparison, and `Draft.changes` is the warning: submit validates such a draft again through the solver's validate call and refuses only if that fails. It compares gender, credited days and who is in the month, and start and end dates count through their credited days. `Roster.solve` is the solve of the grid; once a hand edit exists, compare with that input still. Roster versions were not begun here: the first approval creates version 1, as this ticket says. Open reading of `getRosterMonth` to the approvers here: it is manager-only today.

**From ticket 12 (2026-11-05).** Three things.

- **Restore is a third path that must check the roster's state.** Beside `start_solve` and `_finish` (the comment above), `solves.history_api.restore_result` writes `Roster.grid` through `rosters.drafts.replace_grid`. It looks at no state today. Refuse it while the month's roster is submitted or approved, in `rosters.drafts.why_not_restore`, which the page also reads to say why instead of offering the button, so that one place holds. A test should hold it.
- **Opening the panels to the approvers is yours.** `getSolveResult` (`/units/{id}/solve-history/{solve_id}`), which holds the accounting, the explanations, the statistics, the facts and the grid, and `listUnitSolveHistory` are the manager's only, as `getRosterMonth` is. To open them, widen `auth=manager` in `solves/history_api.py`, and keep `restoreSolveResult` the manager's. `components/solve-result.tsx` is the panels and takes a `SolveResult`; `restore_refusal` should be left out or ignored for an approver, because they cannot restore. A stored result holds leave dates, which an approver may read, and no type.
- `accounts/tests/test_authorization.py` walks the endpoints; a test in `solves/tests/test_history.py` currently holds that the CNO and the Deputy CNO are refused these reads. Change it when you open them.
