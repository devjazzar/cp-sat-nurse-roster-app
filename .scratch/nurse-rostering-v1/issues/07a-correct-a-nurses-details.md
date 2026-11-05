# 07a: Correct a nurse's details

**What to build:** The CNO corrects a nurse's full name, gender and start date after adding them, from a form on the Nurses page. Hospital ID is the username and usernames cannot be reused, so ending a nurse and adding them again is impossible, and both gender and start date feed the roster. Ticket 08 could create many such rows at once, so this comes before it.

**Hospital ID still cannot be corrected.** The user accepted that it can wait: it is out of scope here.

**Blocked by:** 07 Nurses

**Status:** ready-for-agent

- [x] An endpoint and a form on the Nurses page correct full name, gender and start date
- [x] CNO only: managers, staff nurses, the Deputy CNO and the System Admin get 403
- [x] A start date keeps to the end date under ticket 07's rule, including its exception for a nurse who has not started
- [x] A start date before the nurse's first placement leaves no month without a unit, says so, and rewrites no unit they were already placed in
- [x] A manager's nurse profile: gender and start date correct; their name is refused, because it is on the account
- [x] The audit entry holds what changed, and of gender only that it changed
- [x] Locks taken as `_locked_nurse` does; a save with no change writes nothing; refusals name their field
- [x] Notes left for tickets 11 and 21 on a start date or gender changing after a month has been solved or closed
- [x] API tests cover each field, refusals, the no-change save, the audit entry, a manager's profile and authorization; frontend tests cover the form

## Comments

Implemented on 2026-11-05. Backend under pytest on real PostgreSQL 18, frontend under Vitest with the real routes and generated client over a stubbed `fetch`.

Driven on the dev overlay in the built-in browser as the CNO: a name corrected, including one that moved the row to the bottom of the list, with focus staying on its button; gender and a start date together, the second reaching back before the first placement and the page saying what became of their time in ER, in its final words "Their time in ER now begins in May 2025."; a save with no change; a start date after the end date refused beside the field with focus on it, including a future one for a nurse who worked; Cancel with focus back on the row; a manager's profile with the name read-only, focus on gender and gender saved; no sideways page scroll at 375 px with the list and with the form open, the last two runs at that width, and at 320 px with the form open. The audit entries were read from the database after that run.

What was not checked:

- **Two people at once.** The locks are by design; no test races them, as in ticket 07.
- **The production compose file through Caddy.** Only the dev overlay ran.
- **The System Admin reading these entries on the audit log page.** Read from the database and tested at the API. The page shows any action's before and after the same way.
- **Browsers other than the app's built-in one.** A renamed row keeps focus because React restores it after moving the row (held with the refetch delayed by 1.5 s); it should hold elsewhere, but only this one ran.

Decisions this ticket took:

- **`PUT /api/nurses/{id}/details` takes all three fields,** and refuses a hospital ID as an unknown field. **The hospital ID still cannot be corrected,** and the form says so.
- **A manager's name is refused (422 on `full_name`); their gender and start date are corrected.** `full_name` is on the user, section 3 gives manager accounts to the System Admin, and ticket 07 kept the end date and the reset to the same line. Gender and start date are on the profile the CNO gave them. **Worth your review:** the System Admin has no way to rename an account either, so today nobody can correct a manager's name. Closed by ticket 07b: the user decided the System Admin corrects it.
- **An end date before a start date stays only for a nurse who has not started.** The end date form uses `membership.end_date_fits`, as it did. A correction uses `membership.start_date_fits`, which also asks that the old start date had not arrived, so a nurse who really worked cannot be corrected into one never present and lose their days in ticket 11. It is checked only when the start date changes, so a nurse who was never present can still have their name corrected.
- **A start date before the first placement makes that placement begin in the date's month.** Those months had no unit, so no unit is rewritten, and a nurse's transfers stay as they are. It assumes they were in that first unit, so the page says "Their time in ER now begins in October 2025." and the audit entry records `first_placement` before and after. **Worth your review.**
- **A later start date changes no placement,** so a typo that reached back leaves the earlier first month behind when it is corrected. That does no harm: a placement before the start date already happens for a nurse added before they start, and days before the start date count like leave. Bringing it forward could leave a nurse with none in force. After every save the first placement begins by the start month.
- **No unit row is locked.** Who belongs to a unit, now or to come, does not depend on the start date, gender or name, and a correction moves only the earliest placement, further back. `_locked_nurse` takes the user and profile, so a transfer or end date cannot interleave.
- **A correction changes no account state:** an ended nurse stays ended, whatever the start date becomes.
- **The audit entry holds only what changed:** `full_name` and `start_date` with their values, `gender_changed: true` with no values because the System Admin reads the log, and `first_placement` when it moved. No change writes no entry.
- **The CNO's row actions are now two by two,** because a fourth button in a line pushed "Reset password" out of view at 1024 px.

Things a later ticket should know:

- **Solve input (11) and month close (21):** a start date or gender can change after a month is solved or closed. Each of those tickets now has a comment saying what must happen: ticket 11 warns and validates again, ticket 21 adds a guard in `correct_details`.
- **Rostering attributes (09):** gender stays out of its form, because the CNO sets and corrects it. Section 3 and the glossary now say so, and ticket 09 has a comment.
- **Import (08):** a row wrongly imported can now be corrected one at a time, except its hospital ID.
- **Audit action added:** `nurse.details_corrected`, named in `ACTION_NAMES`.

**Review (2026-11-05).** The `code-review` skill's two axes found a nurse who had worked able to be corrected into one never present, "They now belong to ER" false for a nurse since transferred, the documents disagreeing over who owns gender, a note saying both later tickets add a guard, ticket 07's decisions rewritten rather than added to, "moved" in the API against the glossary, and a misnamed variable. All fixed. The browser also found the row's buttons overlapping at 375 px from a grid column that could shrink, fixed, and a read-only name that looked editable, fixed. Left as judgement calls: the ticket keeps the `07a` name the brief asked for, though the tracker's convention is two digits; `UnitName(id=..., name=...)` repeats as it already did; `tuple[Placement, dt.date]` stays a pair; the form works out "nothing changed" itself rather than asking the API. The `interface-review` skill was not run, because it is user-invoked. `better-interface` and its six domain skills were held against the form and row actions by hand with nothing further found; dark mode was not looked at.

**Reviewed by the user (2026-11-05), and kept as built:** hospital IDs cannot be corrected; the start and end date correction rules, including a first placement reaching back; row buttons two by two; the `07a` ticket name.
