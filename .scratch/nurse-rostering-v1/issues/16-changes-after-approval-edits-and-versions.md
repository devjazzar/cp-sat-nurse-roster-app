# 16: Changes after approval: direct edits and versions

**What to build:** After approval the unit manager edits cells directly (a cover, a late leave, a swap agreed offline) with the same instant validation, and each save is a new roster version in force at once, with who, when and why. The version list shows the history and any two versions can be compared cell by cell; the unit's nurses are notified of a change.

**Blocked by:** 13 Edit the draft by hand; 14 Submit, approve, reject

**Status:** ready-for-agent

- [ ] Edits on an approved roster create a new version with origin 'edit' and a required reason; the latest version is in force
- [ ] Edited cells become pinned cells with origin 'manager' so later re-plans keep them
- [ ] Version list with author, time, reason, origin; compare any two versions
- [ ] Nurses notified on every new version
- [ ] API tests cover versioning, pins, compare and notification

## Comments

**From ticket 10 (2026-11-05): leave on an approved roster.** Ticket 10's writes (`nurses/leave_api.py`, one comment marks them) record, correct and remove leave with no roster to look at. Once one exists, late leave on a day with a shift breaks the solver's hard `unavailable` rule against the roster in force, and removed leave leaves a day with nothing owed. Decide here: a new version with origin `edit` taking the cell off, with the reason saved without the type, or a prompt to do so. Colleagues are notified of a change with no word of why. `Leave` keeps no roster reference, and a version's grid keeps what it had.

