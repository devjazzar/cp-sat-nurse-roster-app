# 20: Swaps

**What to build:** On an approved roster a nurse composes a swap: a set of cell changes on her own cells and on colleagues' cells needed to make it work, for dates not yet passed. It is refused at once if the resulting grid breaks a hard rule. Every involved colleague accepts or rejects; one rejection ends it. When all accept, the unit manager sees before and after, the re-run validation and the cost change, and approves (the cells become pinned cells in a new version in force) or rejects. The proposer may withdraw; a proposal expires when a date passes or a new version changes one of its cells. Everyone involved is notified at each step and every swap stays on record.

**Blocked by:** 16 Changes after approval; 15 Nurse's own month and notifications

**Status:** ready-for-agent

- [ ] Swap composer for a nurse: pick cells of herself and colleagues in her unit, choose new values; validation at proposal refuses hard violations with the reason
- [ ] Participants accept or reject; states pending, awaiting_manager, approved, rejected, withdrawn, expired
- [ ] Manager decision view with before/after, validation and cost change; approval writes pins with origin 'swap' as a new version with origin 'swap'
- [ ] Hourly expiry job; expiry also on a new version touching the cells
- [ ] Notifications at each step; audit entries; a nurse sees her swaps and their status
- [ ] API tests cover composition, refusal, acceptance paths, manager decision, expiry and authorization

**From ticket 15 (2026-11-06).** Every step of a swap is yours to notify. Nothing sends one yet.

- **What to call:** add one `Event` per step, or one `SWAP_STEP` event with the step in the payload, and a function in `notifications/sending.py`.
- **Recipients, in the ticket's words:** "everyone involved".
  - When the swap is proposed, the colleagues whose cells change.
  - At each acceptance, the proposer.
  - When all have accepted, the unit's manager. This is "something awaits him".
  - At the decision, at a rejection, at a withdrawal and at an expiry, the proposer and every colleague involved.
- **Privacy:** the words must not say a colleague's cell was leave. A swap's cells are shifts on an approved roster, and a colleague of a nurse sees a day off where she is on leave. Keep the cells out of the payload, and link to the swap's page.

How to add an event, the same for each: add it to `notifications.models.Event`, which is a migration only of `choices`. Write a function beside the others in `notifications/sending.py` that works out the recipients and calls `notify(users, Event.X, **payload)`. Call that function inside the change's transaction, after its audit entry. Then give the event its words in `notifications.reading.text_of` and its link in `link_of`, adding a page to `NotificationLink.page` and to `Open` in `routes/_signed-in/notifications.tsx` if it needs one. **A payload holds identifiers only** (`unit_id`, `month`, `by`, and the request's or swap's id): the words are worked out when read, so nothing goes stale and nothing about a person is stored. `text_of` reads `payload["month"]` for every event today, so an event with no month needs its own branch first. `notify` already skips deactivated users and tells each user once.

**From ticket 16 (2026-11-06).** Versions and direct edits exist.

- **Approving a swap:** write its pins with origin `swap`, then `rosters.versions.make_version(roster, grid, VersionOrigin.SWAP, by, reason)` under the roster's row lock, then the audit entry and `notifications.sending.roster_changed`, as `rosters.api.save_version` does for an edit. The manager's editor already refuses to change a pin of origin `swap` ("change it there").
- **Expiry on a new version touching its cells:** every version is made in `rosters.versions.make_version`, by a direct edit (`rosters.api.save_version`) or by leave recorded on a worked day (`take_off_for_leave`, called from `nurses.leave_api._begin`). Expire there, or compare the proposal's cells with `rosters.versions.differences` against the version it was proposed on. A leave-made version changes a cell too, and its colleagues must not learn it was leave, so the expiry's words should not say why.
- **A version's reason is for the manager and the approvers.** A swap's own reason is the proposer's to read, but keep it out of the version's notification as the edit does.

**From ticket 17 (2026-11-06).** A re-plan (`solves.replans`) runs in the queue and, when it ends, puts its roster in force as a version only if the version it started from (`Solve.replan_of`) is still the latest and `solves.input.changes_since` finds nothing. An approved swap makes a version and pins, so a swap approved while a re-plan of that month runs makes the re-plan end `outdated`, with nothing applied: that is intended. A pin of origin `swap` before a re-plan's date is a fact, after it a pin the re-plan keeps. A re-plan's version can change a cell a pending swap names: expire it there as for any other version (`make_version` is the one place).

**From ticket 19 (2026-11-06).** Requests are built (`requesting`), and their pins are ordinary pins of origin `request`.

- **Writing a swap's pins:** `rosters.pins.pin_cell(unit, nurse, day, shift, PinOrigin.SWAP, by)` is the one way a pin is made. It ends whatever pin the nurse held that day, a manager's or an accepted request's, as `replaced`. A request whose pin a swap ended stays `accepted` and points at an ended pin, so decide whether a swap may land on an accepted request's cell (refuse it, or end the request with a state of its own and tell its nurse). `rosters.pins.Judge.refusal` gives the words a pin's refusal uses.
- **The other way round:** accepting a request is refused where an accepted swap's pin holds the cell ("…so change it there"), in `requesting.deciding.refusal_to_pin`.
- **A version after approval:** `requesting.deciding._onto_roster` makes one with `make_version` only when a cell changes, then the audit entry, then `sending.roster_changed`, as ticket 16 asked.
- **Notifications:** `sending.request_decided` and `reading._decision_words` show an event whose payload is a step and an id, and whose words read the row when shown.
