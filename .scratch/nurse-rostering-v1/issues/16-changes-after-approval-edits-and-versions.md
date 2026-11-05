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


**From ticket 13 (2026-11-05).** The draft's cell editor and its pins are built: `rosters.models.PinnedCell` with `origin` `manager`, saved through `POST /units/{id}/roster/pins` (`rosters.api.save_pins`) and checked first through `POST /units/{id}/roster/check`. An edit of the approved roster that becomes a manager's pin can reuse `rosters.editing.Month` (refusals, the cell after an edit, writing the pins) and the page's `CellEditor` and pending edits. What differs is the version: the draft's save writes `Roster.grid` in place and no version, which is right only before approval. Ticket 14 freezes the submitted and approved roster in `rosters.api._why_not_edit`, and this ticket reopens editing there for the approved one through a new version.

**From ticket 14 (2026-11-05).** What exists now:

- **`rosters.models.RosterVersion`**: roster, `number`, `grid`, `origin` (`solve`, `edit`, `replan`, `swap`, `request`), `solve` (null unless a solve produced it), `created_by`, `created_at`, `reason`. The first approval makes number 1 with origin `solve` and the roster's solve (`rosters.review.approve`). Its grid is `Roster.grid` as approved, **hand edits included**, so version 1 can differ from its solve's result: the pins say why. The latest version is in force: `roster.versions.first()` by the model's ordering.
- **`Roster.grid` must stay equal to the latest version's grid**, under today's codes. `Roster.grid` follows a rename (`carry_rename_through_grids`), a version keeps the codes it was saved with and is read through `in_current_codes`, as a stored result is. The hours guard (`drafts.using_shift`) reads `Roster.grid` only, which is enough while the two agree.
- **An approved roster is frozen** by `rosters.drafts.why_frozen`, the one check behind a solve's start and end, a restore and a save of pins. `_why_not_edit` in `rosters/api.py` reads it; reopen editing there for `approved`, through a new version instead of writing `Roster.grid` in place. `why_frozen` will still have to refuse a solve and a restore of an approved month (ticket 17 has the re-plan).
- **Leave on an approved roster** is recorded with no check, as before, and ends a pin; nothing reads the approved month's grid against it yet. The approver's re-check exists only for a submitted roster.
- The nurse's read (`rosters.reading_api.my_roster`) shows the latest version and its number, and needs no change for new versions.
