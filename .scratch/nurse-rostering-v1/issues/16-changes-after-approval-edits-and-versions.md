# 16: Changes after approval: direct edits and versions

**What to build:** After approval the unit manager edits cells directly (a cover, a late leave, a swap agreed offline) with the same instant validation, and each save is a new roster version in force at once, with who, when and why. The version list shows the history and any two versions can be compared cell by cell; the unit's nurses are notified of a change.

**Blocked by:** 13 Edit the draft by hand; 14 Submit, approve, reject

**Status:** ready-for-agent

- [x] Edits on an approved roster create a new version with origin 'edit' and a required reason; the latest version is in force
- [x] Edited cells become pinned cells with origin 'manager' so later re-plans keep them (the manager's edits; leave taking a shift off makes no pin, see Comments)
- [x] Version list with author, time, reason, origin; compare any two versions
- [x] Nurses notified on every new version
- [x] API tests cover versioning, pins, compare and notification

## Comments

**From ticket 10 (2026-11-05): leave on an approved roster.** Ticket 10's writes (`nurses/leave_api.py`, one comment marks them) record, correct and remove leave with no roster to look at. Once one exists, late leave on a day with a shift breaks the solver's hard `unavailable` rule against the roster in force, and removed leave leaves a day with nothing owed. Decide here: a new version with origin `edit` taking the cell off, with the reason saved without the type, or a prompt to do so. Colleagues are notified of a change with no word of why. `Leave` keeps no roster reference, and a version's grid keeps what it had.


**From ticket 13 (2026-11-05).** The draft's cell editor and its pins are built: `rosters.models.PinnedCell` with `origin` `manager`, saved through `POST /units/{id}/roster/pins` (`rosters.api.save_pins`) and checked first through `POST /units/{id}/roster/check`. An edit of the approved roster that becomes a manager's pin can reuse `rosters.editing.Month` (refusals, the cell after an edit, writing the pins) and the page's `CellEditor` and pending edits. What differs is the version: the draft's save writes `Roster.grid` in place and no version, which is right only before approval. Ticket 14 freezes the submitted and approved roster in `rosters.api._why_not_edit`, and this ticket reopens editing there for the approved one through a new version.

**From ticket 14 (2026-11-05).** What exists now:

- **`rosters.models.RosterVersion`**: roster, `number`, `grid`, `origin` (`solve`, `edit`, `replan`, `swap`, `request`), `solve` (null unless a solve produced it), `created_by`, `created_at`, `reason`. The first approval makes number 1 with origin `solve` and the roster's solve (`rosters.review.approve`). Its grid is `Roster.grid` as approved, **hand edits included**, so version 1 can differ from its solve's result: the pins say why. The latest version is in force: `roster.versions.first()` by the model's ordering.
- **`Roster.grid` must stay equal to the latest version's grid**, under today's codes. `Roster.grid` follows a rename (`carry_rename_through_grids`), a version keeps the codes it was saved with and is read through `in_current_codes`, as a stored result is. The hours guard (`drafts.using_shift`) reads `Roster.grid` only, which is enough while the two agree.
- **An approved roster is frozen** by `rosters.drafts.why_frozen`, the one check behind a solve's start and end, a restore and a save of pins. `_why_not_edit` in `rosters/api.py` reads it; reopen editing there for `approved`, through a new version instead of writing `Roster.grid` in place. `why_frozen` will still have to refuse a solve and a restore of an approved month (ticket 17 has the re-plan).
- **Leave on an approved roster** is recorded with no check, as before, and ends a pin; nothing reads the approved month's grid against it yet. The approver's re-check exists only for a submitted roster.
- The nurse's read (`rosters.reading_api.my_roster`) shows the latest version and its number, and needs no change for new versions.

**From ticket 15 (2026-11-06).** "Roster changed" is yours to emit. Nothing sends it yet.

- **What to call:** add `Event.ROSTER_CHANGED` and `sending.roster_changed(unit, month, by)`. Call it in the save that makes the new version, after its audit entry.
- **Recipients:** the unit's nurses of that month (`User.objects.filter(nurse_profile__in=membership.placed_in(unit, month))`), as an approval's are. Leave the manager out, since they made the change.
- **Words:** say only that the roster of the unit and month has changed. **Never the reason, the cells or whose they are:** a reason or a cell taken off can say it was leave, and a colleague must not learn that. Each nurse reads their own row on My roster. Keep the version number out of the payload, as the approval does: a later version would make it untrue.
- **A nurse's own month needs nothing:** `rosters.reading_api.my_month` reads the latest version and the month as it stands. A shift left on a day of leave recorded since is not counted as worked there (`rosters.own_month`), and your version that takes it off changes nothing in those hours.

How to add an event, the same for each: add it to `notifications.models.Event`, which is a migration only of `choices`. Write a function beside the others in `notifications/sending.py` that works out the recipients and calls `notify(users, Event.X, **payload)`. Call that function inside the change's transaction, after its audit entry. Then give the event its words in `notifications.reading.text_of` and its link in `link_of`, adding a page to `NotificationLink.page` and to `Open` in `routes/_signed-in/notifications.tsx` if it needs one. **A payload holds identifiers only** (`unit_id`, `month`, `by`, and the request's or swap's id): the words are worked out when read, so nothing goes stale and nothing about a person is stored. `text_of` reads `payload["month"]` for every event today, so an event with no month needs its own branch first. `notify` already skips deactivated users and tells each user once.


**Implemented on 2026-11-06,** on branch `claude/ticket-16-versions-d325e2`. The backend ran under pytest on a throwaway PostgreSQL 18 container of my own, and the frontend under Vitest with the real routes and generated client over a stubbed `fetch`.

- Results on the final code: backend 1785 passed, frontend 456 of 456, and `npm run build` clean.
- `makemigrations --check` is clean, and `frontend/openapi.json` is the same as a fresh export.
- **The frontend suite ran alone in the working tree, not in clean exports in parallel.** That is left to the session that brings this into `main`.
- The solver's suite was not run: nothing under `solver/` changed.

What was built:

- **`rosters/versions.py`, the one way a version is made.** `make_version(roster, grid, origin, by, reason, solve)` numbers it (latest + 1) under the roster's row lock and writes `Roster.grid` from it, so `Roster.grid` is always the latest version's grid under today's codes. The first approval now makes version 1 through it too. `differences` compares two grids cell by cell under today's codes. `take_off_for_leave` is the late-leave hook.
- **Direct edits:** `POST /units/{id}/roster/versions` (`saveRosterVersion`), body `month`, `edits` and a required `reason`.
  - It reuses ticket 13's `DraftEdits`: the same refusals, each edited cell a manager's pin, the same live check (`POST /roster/check`, now open on an approved roster).
  - A save that changes something makes a version with origin `edit`. Then comes the audit entry `roster.changed` with `{"version", "pins", "cells"}` and no reason. Then the nurses are told.
  - A save that changes nothing makes no version and tells nobody.
  - The draft's `POST /roster/pins` refuses an approved roster and says a change there is a version.
- **Reads, for the unit's manager, the CNO and the Deputy CNO only:**
  - `GET /units/{id}/roster/versions` (`listRosterVersions`) lists versions newest first, with number, origin, author, time, reason, and cells changed from the one before.
  - `GET /units/{id}/roster/versions/compare?month&from_version&to_version` (`compareRosterVersions`) compares any two versions, in either order: nurse, date, before, after. A rename between them is not a change.
- **`Event.ROSTER_CHANGED`** (`notifications.0002`, a migration of `choices` only), with `sending.roster_changed`, its words and its link, as ticket 15's comment said.
- **The editor knows who has left the month:** `DraftEditor.gone` lists them, and clearing their cell takes the shift off (`DraftEdits.cell_after`).
- **Pages:**
  - On the Roster page, an approved roster's cells open the same menu. The unsaved panel asks "Why" and saves through `saveRosterVersion`, then says "N changes saved as version 2, now in force. The unit's nurses are told the roster has changed." Focus goes back to the cell.
  - A new **Versions** section (`components/roster-versions.tsx`) shows the table and "Compare two versions", with the latest two by default. The manager's page and the approvers' unit roster share it.
  - The Leave page says which shifts leave took off, and re-reads the roster.
  - The audit log page has a label for `roster.changed`.

Seams:
- `rosters/tests/test_versions.py` (50 tests, some parametrised): the API with the scripted solver on a real optimal roster of the four-nurse sample (`fixtures/sound_rosters.json`), so each check is the solver's own code.
- `rosters/tests/test_two_at_once.py`: four new races on real connections, with the order forced, not hoped for:
  - two version saves;
  - leave and an edit of the same nurse;
  - leave of one nurse and an edit of another;
  - a rename and leave over two approved months.
- `accounts/tests/test_authorization.py` names the three new endpoints' roles.
- `app.test.tsx`: 7 new tests, through `start` and `hold`. No raised timeout, no fake timers, no wait that proves something did not happen.
- The backend tests were written first and failed before the code. The page code came first, so I broke two of its guards by hand (saving through the draft's endpoint, and the "gone" nurse) and saw those tests fail.

**A race test found a real deadlock, now fixed.** Postgres checks a foreign key at commit with a key-share lock on the row it names. Leave for Badr inserts "roster changed" notifications naming every nurse's user row, Amal's included. A concurrent edit of Amal held her user row `FOR UPDATE` and waited on the roster row the leave held. **The nurse and user locks are now `FOR NO KEY UPDATE`** (`no_key=True`) in all five places that take them: `nurses/api.py`, `attributes_api.py`, `leave_api.py`, `rosters/api.py` and `rosters/review.py`. They still serialise those writes among themselves exactly as before, and they take the same lock a plain `UPDATE` of the row takes. The code review then found a second deadlock by reading, with no test reaching it: a rename locked every roster in no order. It now locks them by month, then unit, the order a leave over two months takes them, and a race test holds that.

**Driven in the built-in browser,** on scratch project `nr-t16`:
- The setup:
  - It ran the production compose file with its own image (`nr-t16-app`), secrets and volumes.
  - `web` was published on `127.0.0.1:18016` under `DJANGO_DEBUG`. It was also joined to the `public` network, since the internal networks publish no port. There was no Caddy, and the real solver and worker ran.
  - The unit was the solver's four-nurse sample as ER, rostering December 2026.
- **As the manager:** a real solve of 15 s (cost 127), then a real submit.
- **As the CNO:** a real approval through the dialog, to "Version 1 is in force".
- **As the manager, the direct edit:**
  - Amal pinned to Day and Emad to a day off on 1 December. Emad's menu offered Day only, his allowed shift.
  - The live check said "breaks no hard rule, and costs 1139 (+1012)".
  - Saving with no reason was refused on the page, with focus on Why.
  - Saved with "Emad is sick on the 1st; Amal covers his day.", the page said "2 changes saved as version 2, now in force…", with focus back on Emad's cell.
  - The Versions table showed 2 (in force), Changed by hand, Mona Ali, 2 cells, the reason. Compare showed the two cells, D to Off and Off to D.
- **As the manager, late leave:** Sick for Amal on 3 December, a day she worked. The Leave page said "It took a shift off the approved roster: D on 3 Dec 2026. Version 3 is now in force, and the unit's nurses are told the roster has changed, not why."
- **The database then held:**
  - `Roster.grid` equal to version 3 under today's codes.
  - Version 3 by Mona with the reason "Leave recorded for Amal Saleh took their shift off 3 December 2026", which names no type.
  - Two `roster_changed` notifications for each of the four nurses, each payload only `unit_id`, `month` and `by`. Mona had none.
  - In the audit log, `roster.changed` `{"pins": 2, "cells": 2, "version": 2}`, and for the leave only `leave.recorded`.
- **As Badr:**
  - The bell read "Notifications, 3 unread": twice "Mona Ali changed the ER roster for December 2026." and the approval.
  - The newest led to My roster for December.
  - Amal's 3 December read "Off" and her 1 December "Day". The page said nothing of her leave.
- At 375 px on the Roster page: no sideways page scroll. The Versions and compare tables scroll inside themselves.
- Everything has been removed since.

That run found two bugs, both fixed with tests: the check of an approved roster's changes said "the draft", and the compare said "1 cell differ".

What was NOT checked:
- **The approvers' unit roster with versions, and Amal's own My roster after her leave, in the browser.** Vitest and API tests only. The CNO's page was driven only before any change.
- **A save that breaks a hard rule, a refusal of a request's pin, a transferred nurse's "Take the shift off this day", and a month over, in the browser.** API and Vitest tests only.
- **Leave removed after a version took the cell off, in the browser.** API test only: the cell stays off and no version is made.
- **The races in a browser.** They are tests on real connections only.
- **The deadlock between a manager's deactivation and an edit.** It is older than this ticket and was not tested. A System Admin deactivating a manager locks that manager's user row, then the unit's. An edit or pin save holds the unit, and at commit its foreign key to the manager (`created_by`, `pinned_by`) waits on that user row. Postgres would end one of them with an error, which the user would see as a failed save to retry.
- **Dark mode, 320 px, 200% zoom, RTL, a screen reader, browsers other than the built-in one, and through Caddy.**
- **A large unit.** Each version list and compare reads every version's grid of the month.

**Decisions taken here:**

- **Worth your review: leave recorded on a day an approved roster works takes the shift off at once, as a new version with origin `edit`.** The alternative was a prompt for the manager to do it.
  - **Why:** leave wins over a shift everywhere else (pins, My month's hours), and otherwise colleagues would see a nurse working on her leave day until the manager acted.
  - The version is by whoever recorded the leave, the unit's manager of that month, including one who took the unit over after the approval (a test).
  - **Its reason says leave and names the nurse and dates, never the type.**
  - **It makes no pin:** the leave is the fact a re-plan keeps. This is why the second criterion holds for the manager's edits only.
  - It covers the unit's approved rosters of months not over, one version per roster, so a write over 30 June and 1 July makes two.
  - A day off changes nothing and makes no version.
  - A draft keeps its shift until a solve or a hand edit (ticket 13), and a submitted roster keeps it for the approver to see (ticket 14).
  - **Removing the leave afterwards puts nothing back.** The cell stays off, and the roster's check shows what that now breaks. The manager puts a shift back by hand.
  - The manager is told on the Leave page and in the version list, and must still find a cover.
- **Worth your review: an edit that breaks a hard rule saves, with its warning, on an approved roster as on a draft.** This follows from the decision above, since taking a sick nurse off can leave a shift short. The roster in force has to say what is so, and the page lists what it breaks. `why_frozen` still refuses a solve and a restore of an approved month: ticket 17 owns re-plans. Its words for an approved roster now send the manager to the cells.
- **Worth your review: a leave-made version has no audit entry of its own.** An entry beside `leave.recorded` would tell the System Admin the month of that nurse's leave, the reason ticket 13 gave a pin ended by leave no entry. The version row keeps who and when. The manager's edits are audited as `roster.changed` with the version and the counts, never the reason.
- **Who reads a reason:** the unit's manager, the CNO and the Deputy CNO, in the version list. Never a nurse, a notification or the audit log, and tests search all three for it. An approver reads the reasons because they read a roster's leave with its type already (ticket 10's change).
- **Worth your review: nurses have no version list and no compare.** A nurse reads the roster in force on My roster, with its version number as before, and is told of each change by the bell. Showing a nurse what changed in a colleague's row would say when a colleague's shift went, and a cell taken off for leave is exactly what must read as a day off. A nurse's own row could one day mark what changed for them; nothing does now.
- **Compare:** any two versions, in either order, under today's codes. A day not worked reads "Off" for everyone, so an approver's compare shows leave as Off too. The approver can read the leave on the Leave page.
- **Every save that changes a pin or a cell is a version** and tells the nurses, because the criterion says "notified on every new version". Pinning a cell to what it already holds is a version with no cell changed. **Worth your review:** the nurses are then told of a change they cannot see. It keeps the manager's reason and pin on record for a re-plan. Telling only when a cell changes would be one line.
- **The "roster changed" notification** follows ticket 15's comment exactly:
  - Recipients are the unit's nurses of the month (`membership.placed_in`), less whoever made the change.
  - It reads "Mona Ali changed the ER roster for December 2026." and links to My roster.
  - Its payload is `unit_id`, `month` and `by`: no version number, cell, name or reason.
- **Locks:** a direct edit takes the catalogue's, the edited nurses' (`FOR NO KEY UPDATE`), the unit's, then the roster's, as a pin save does. A leave write takes the nurse's, then each roster's row lock in month order, never the catalogue's. Version numbers are unique by constraint and ordered by the roster's lock.
- **A month already over:** an edit is refused ("its roster in force cannot change"), and late leave makes no version there. Ticket 21's close reads leave itself.
- **The month under way** is edited like any other approved month, past days included, so a sick day recorded the day after takes that shift off.
- **A nurse transferred out of an approved month:** nothing can be pinned for them, and clearing their cell takes the shift off. The page offers "Take the shift off this day". This also changes the draft: clearing such a nurse's cell there now gives off rather than the solve's shift. A nurse transferred out is no longer among that month's nurses, so they are not told when that roster changes, though their row stays on it until the manager clears it.
- **A start date corrected after approval:** pinning outside the dates is refused, and clearing takes the shift off, as on the draft. **Neither a transfer nor a date correction makes a version on its own,** unlike leave. They are the CNO's acts on other pages, and the manager sees what they break in the roster's check.

`docs/ARCHITECTURE.md` sections 3, 4 and 5 and the glossary's Roster version and Notification moved.

**Review.** The `code-review` skill's two axes against `b29a2c4`.

Spec found:
- The rename's unordered lock, above.
- A save that changed nothing still saying "saved as version N".
- The Leave page not re-reading the roster after leave took a shift off.
- "in this draft" in a refusal on an approved roster.

All fixed, the first two with tests. It also raised the leave-made version's missing audit entry, the draft's changed clearing of a transferred nurse, the `no_key` change in earlier tickets' code, and the pin-only version's notification. All four are kept and recorded above.

Standards found:
- Imports out of order.
- An untyped `solve`.
- `_Begun.told` both telling and building the answer.

All fixed. Left as judgement calls:
- `origin` typed `str` in `make_version`, as `VersionOrigin.EDIT` does not type-check as the enum.
- `VersionRow.origin`'s literal beside `VersionOrigin`, as ticket 14 did for the state.
- The `approved ?` branches in the Roster page's copy.
- The lock chain repeated in five places rather than shared.
- `_locked_for_edits` taking the request.

`better-interface` and its domain skills, held by hand against the code and the run:
- The reason field has its label, description and error, wired by `aria-describedby`. A refusal puts focus on it.
- The status line announces the save, and focus returns to the cell.
- Each table has a caption for screen readers and scrolls inside itself on a phone.
- The selects have visible labels.
- The new copy uses the glossary's words: version, roster in force, leave, pin.
- No new colour, type or motion.
- `interface-review` is yours to invoke.

**Things later tickets should know:** comments are on 17, 19, 20 and 21. `rosters/versions.py` is where a version is made; call `make_version`, then `record("roster.changed", ...)` and `sending.roster_changed`. Any new lock on a nurse or user row should be `FOR NO KEY UPDATE`.

**The dev stack was not touched:** no restart, no migration, no login. When this branch reaches `main`, restart `web` and `worker` there for `notifications.0002`. It changes only the event's choices, so nothing fails before that restart, but the version endpoints and pages need the new code.

