# 20: Swaps

**What to build:** On an approved roster a nurse composes a swap: a set of cell changes on her own cells and on colleagues' cells needed to make it work, for dates not yet passed. It is refused at once if the resulting grid breaks a hard rule. Every involved colleague accepts or rejects; one rejection ends it. When all accept, the unit manager sees before and after, the re-run validation and the cost change, and approves (the cells become pinned cells in a new version in force) or rejects. The proposer may withdraw; a proposal expires when a date passes or a new version changes one of its cells. Everyone involved is notified at each step and every swap stays on record.

**Blocked by:** 16 Changes after approval; 15 Nurse's own month and notifications

**Status:** ready-for-agent

- [x] Swap composer for a nurse: pick cells of herself and colleagues in her unit, choose new values; validation at proposal refuses hard violations with the reason
- [x] Participants accept or reject; states pending, awaiting_manager, approved, rejected, withdrawn, expired
- [x] Manager decision view with before/after, validation and cost change; approval writes pins with origin 'swap' as a new version with origin 'swap'
- [x] Hourly expiry job; expiry also on a new version touching the cells
- [x] Notifications at each step; audit entries; a nurse sees her swaps and their status
- [x] API tests cover composition, refusal, acceptance paths, manager decision, expiry and authorization

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

**Implemented on 2026-11-06,** on branch `claude/ticket-20-swaps-312d42`. The backend ran under pytest on a throwaway PostgreSQL 18 container of my own, the frontend under Vitest with the real routes and generated client over a stubbed `fetch`.

- Results on the final code: backend 2166 passed, frontend 516 of 516, and `npm run build` clean.
- `makemigrations --check` is clean, and `frontend/openapi.json` is the same as a fresh export.
- **The frontend suite ran alone in this worktree, not in clean exports in parallel.** That is left to the session that brings this into `main`.
- The solver's suite was not run: nothing under `solver/` changed.

What was built:

- **A new app, `swaps`.** Migrations `swaps.0001_swaps` and `notifications.0004_swap_step` (choices only).
  - `Swap`: unit, roster, `proposed_on` (the version in force), proposer, the proposer's `note`, state (`pending`, `awaiting_manager`, `approved`, `rejected`, `withdrawn`, `expired`), `ended_by`/`ended_at`, `expired_why` (`date_passed` or `cell_changed`, the manager's to read), the manager's `reason` and `made_version`.
  - `SwapCell`: nurse, date, `before` and `after` (shifts, null for off, so a rename needs nothing) and the `pin` its approval made.
  - `SwapParticipant`: every colleague whose cells change, never the proposer, with their answer.
- **`swaps/judging.py`, the one place a swap is judged and worded.** Each cell first, then the grid on the month as it stands with the solver's own code (`rosters.editing.scored`), the swap's cells put in as pins so a manager's pin there does not count against it. Only hard violations the roster in force does not already break are the swap's. Each reason has the manager's words and the proposer's.
- **`swaps/steps.py`:** propose, a colleague's answer, withdraw, and the manager's approve and reject. Each refusal, then the write, the audit entry and whoever is told.
- **`swaps/expiring.py`:** `state_now` (every page reads the dates), `expire_passed` (the hourly job `swaps.tasks.expire_swaps` at minute 15, and every write about a swap first) and `on_new_version`, called by `rosters.versions.make_version` under the roster's row lock, so every version expires a waiting swap whose cell it changes: an edit, leave, a re-plan, an accepted request, another swap.
- **Endpoints:**
  - For staff nurses only: `GET /api/swaps/compose?month` (the roster in force from today, the unit's shifts, the staff nurses' rows), `GET/POST /api/swaps/mine`, `POST /api/swaps/mine/{id}/withdraw|accept|reject`.
  - For the unit's manager only: `GET /api/units/{id}/swaps?month`, `GET /api/units/{id}/swaps/{swap_id}` (the decision view), `POST .../approve|reject`.
- **Approval**, under the catalogue's lock, the swap's nurses' (`FOR NO KEY UPDATE`), the unit's, the roster's and the swap's: judged again, then `rosters.pins.pin_cell(..., PinOrigin.SWAP, manager)` for every cell, then `make_version(..., VersionOrigin.SWAP, ...)`, `roster.changed` with the version and counts, `sending.roster_changed`, and the swap's own step.
- **`Event.SWAP_STEP`** with the step in the payload (`notifications.sending.SwapStep`: proposed, accepted, awaiting, rejected, withdrawn, expired, approved), a sender `sending.swap_step`, words in `reading._swap_words` read from the swap when shown, and links to the new pages `swaps` and `unit_swaps`.
- **Pages:**
  - **Swaps** (`/swaps`, in the nurse's header): the composer, a cell a row (nurse, date, what it becomes, and what it is now), a refusal beside the cell it is about or as an alert for the whole swap; and the nurse's swaps, each with its cells before and after, each colleague's answer, the note, the manager's reason, and Accept, Reject or Withdraw, the last two behind a question.
  - **Swaps** (`/unit-swaps`, in the manager's header): the month's swaps, and the decision view of one: before, after, the cell in force now and the pin approval replaces, the check of the grid with its violations and the cost against the roster in force, every reason it cannot be approved, and Approve (reason optional) or Reject (reason required) in a dialog.

Seams:
- `swaps/tests/test_swaps.py` (47 tests, some parametrised): the API with the scripted solver on the real optimal June of the four-nurse sample, so every check is the solver's own code.
- `swaps/tests/test_two_at_once.py` (6 tests) on real connections with the order forced: the last two acceptances (the manager is told once), an acceptance against a withdrawal, an approval against leave and against an edit, and a proposal against an edit both ways.
- `swaps/tests/test_with_replans.py` (2 tests): a re-plan's version expires a swap, and a swap approved while a re-plan runs makes it end `outdated`.
- `accounts/tests/test_authorization.py` names every swap endpoint's roles; the walk holds every other role, the System Admin, the CNO and the Deputy CNO included, to 403.
- `app.test.tsx`: 14 new tests and both pages in the route guards, through `start`. No raised timeout, no fake timers, no wait that proves something did not happen.
- **Honestly: the code came just ahead of most of its tests, not after a red one.** I broke guards by hand and saw tests fail for each: the proposer's words for a hidden cell (4 failed), solver text for a colleague (1), team leader and gender said as they are (2), the `make_version` hook removed (6), the hook reading `roster.grid`, which a direct edit has already written, instead of the version before (6), the swap's row lock removed (2 races), and counting a hard rule the roster already broke (2).

**Driven in the built-in browser,** on scratch project `nr-t20`:
- The setup: the production compose file with its own image (`nr-t20-app`), secrets and volumes; `web` published on `127.0.0.1:18020` under `DJANGO_DEBUG`, no Caddy, the real solver and worker. ER was the solver's four-nurse sample with Mona (manager) and Carla (CNO), seeded by a script. **December 2026 was solved for real** (15 s, cost 127), submitted and approved through the API, on the real clock (6 November). Sick leave for Amal on 3 December, her day off, so no version.
- **As Badr, refused for hidden facts:**
  - Badr off and Emad on Night on 2 December (Emad works Day only): "This swap cannot work for Emad Nasser on 2 December 2026.", beside Emad's cell, with focus on it.
  - Badr off and Amal on Night on 3 December (her leave), sent by `fetch` from the page: a 422 whose whole body was the same sentence for Amal and nothing else.
- **As Badr, one that works:** Badr off and Amal on Night on 5 December with a note. "Your swap is proposed. Amal Saleh is asked to accept it, then your manager decides." A second, on the 9th, he withdrew through its question; the status line took focus.
- **As Emad** (proposed by `fetch` from his page): a swap on the 7th changing Dana's, Badr's and Amal's cells, and one on the 10th changing Dana's.
- **Dana and Badr** accepted the 7th, and **Amal** accepted Badr's 5th ("Everyone in it has now accepted, so it waits for the manager.") and rejected Emad's 7th through its question.
- **As Mona:** the bell said "The swap Badr Omar proposed on the ER roster for December 2026 waits for your decision." The decision view showed both cells before, after and in force now, "breaks no hard rule", and cost 135 against 1159. Approving with a reason made **version 2, origin `swap`**, "Swap proposed by Badr Omar approved: Badr Omar, Amal Saleh on 5 December 2026.", and the status line said so.
- **Expiry by a version:** a direct edit by Mona of Dana's 10 December (version 3, by `fetch` to the edit endpoint) expired Emad's swap on the 10th, `cell_changed`, which only the manager's view says.
- **The bells:**
  - Emad's: each acceptance, Amal's rejection, "The swap you proposed on the ER roster for December 2026 has expired, so it changes nothing.", and two roster changes.
  - Badr's: the proposal on the 7th, Amal's acceptance, Mona's approval, Amal's rejection of Emad's swap, and two roster changes.
  - Dana's: the two proposals and the approval of the roster.
- **The database then held:** swap payloads with `unit_id`, `month`, `swap_id`, `step` and `by` only (no `by` on an expiry); `swap.proposed|withdrawn|accepted|rejected|approved` entries targeting the proposer, with no before or after; `roster.changed` `{"version": 2, "pins": 2, "cells": 2}`; two pins of origin `swap`; `Roster.grid` equal to version 3.
- At 375 px, Swaps had no sideways page scroll.
- **That run found three things, all fixed with tests:** two swaps' buttons had the same names ("Withdraw", "Accept Emad Nasser's swap"), so each now names its dates; an expired swap's view said a pin "which approving replaces"; and an ended swap said a colleague had "not answered yet" (now "did not answer"). The rebuilt image was checked again on the nurse's page.
- **The real worker's registry** lists `swaps.tasks.expire_swaps` at `15 * * * *`.
- Everything of `nr-t20` has been removed since: containers, volumes, networks and image, and my PostgreSQL container for the tests.

What was NOT checked:
- **Expiry by a passing date, in the browser, and the hourly job firing in the real worker.** The real clock could not reach a December date; the API tests move the hospital's clock (`membership.today` patched) and call the job directly. The job's registration was read from the real worker.
- **Expiry by leave, a re-plan or an accepted request, in the browser.** API tests only, and the re-plan race on its own.
- **Ramadan reduction, breastfeeding and contract hours as hidden facts, by test.** They reach the swap only through the solver's `hours_bounds` rule for that colleague, which is hidden by the same branch the overtime test covers. I found no swap of the sample that newly breaks them. A score is a soft rule and never refuses a swap, and the proposer reads no cost.
- **The Deputy CNO, the CNO and the System Admin reading swaps in the browser.** The authorization walk holds them to 403.
- **A manager with a nurse profile** in the browser: API test only (their cells are refused, and the composer leaves them out).
- **The manager's page at 375 px, the reject dialog and the races, in the browser.**
- **Dark mode, 320 px, 200% zoom, RTL, a screen reader, browsers other than the built-in one, and through Caddy.**
- **A large unit.** The decision view and every proposal check the whole month with the solver's code.

**Decisions taken here:**

- **Worth your review: what the proposer may learn.** The proposer learns nothing about a colleague that My roster would not show. `swaps.judging` checks what My roster shows first (a date passed, a shift the unit does not work, a cell already holding its change, how many work a shift that day) and says it as it is. Every reason that rests on a colleague's facts then reads the same sentence, "This swap cannot work for Badr Omar on 5 December 2026.": their leave, dates, transfer or deactivation, allowed shifts, hours (overtime, Ramadan, breastfeeding, contract), an accepted request of theirs, or their cell in another swap. A shift-day left without a team leader or both genders reads "This swap cannot work on 10 December 2026: that day's shifts would break the unit's rules." The proposer reads no rule, solver text or cost about anyone else; her own reasons are said in full ("You are on leave on…", "N is not one of the shifts you work.", "This swap breaks a rule for you: …"). The manager reads every reason in full.
  - **What remains is the one bit a refusal is.** A nurse who proposes the same change day after day can learn on which days a colleague cannot take a shift, without learning why. That comes with refusing at once, which the ticket asks for.
  - **The order matters, and the spec review found it:** with leave checked first, asking a colleague's leave day for a day off answered differently from a plain day off. A test now holds that both answer "already a day off".
- **Worth your review: a colleague's accepted request on a cell refuses the swap**, hidden like her leave. The alternative was to allow it and end the request with a state of its own. The request is the manager's promise to her. **A manager's pin is replaced** by approval, which the decision view says first, and so is an earlier swap's pin.
- **Worth your review: a cell is in at most one waiting swap.** A second is refused, the proposer's own cell named ("Your cell on … is already in another swap."), a colleague's hidden.
- **Worth your review: a swap of only the proposer's own cells is allowed** and goes straight to the manager. The glossary's "any colleagues needed" can be none.
- **Worth your review: the proposer may withdraw while it waits for its colleagues or the manager.** Section 5 said "while pending"; nothing is committed until the manager decides. The manager is told of a withdrawal or an expiry of one that was awaiting him.
- **A swap must change at least one of the proposer's own cells, and every cell must change** (the user's rule for ticket 16). **Dates not yet passed include today**, on the hospital's clock; a swap expires when its earliest date has passed.
- **Only staff nurses' cells are swapped.** A manager with a nurse profile proposes nothing (section 3 gives swaps to staff nurses), and their cells are refused by name, since who manages the unit is no secret.
- **A hard rule the roster in force already breaks is not the swap's**, since a direct edit may save one (ticket 16). One broken further, or on another shift that day, is new.
- **Approval is judged again** and refused, with every reason in full, when a cell can no longer hold its change or the grid would newly break a hard rule: leave on a day off, a transfer or an end date may come after the proposal and make no version. The manager rejects it, or edits the roster.
- **Colleagues answer without a reason.** The manager's reason is optional to approve and required to reject, and the proposer and every colleague in it read it, as the dialog says. The proposer's note is read by the same people and the manager.
- **Worth your review: an expiry has no audit entry.** It is nobody's act, and an entry beside the version that caused it could date a colleague's leave for the System Admin, as ticket 16 kept a leave-made version out. The swap row keeps when and why.
- **Notifications** follow ticket 15's comment: the colleagues when proposed, the proposer at each acceptance, the manager when all have accepted, and the proposer and every colleague at a rejection, a withdrawal, an expiry and an approval, never whoever took the step. The approval also tells the unit's nurses the roster changed, those in the swap included. An expiry never says why.
- **The version's reason** names the proposer, the nurses and the dates, never the note: the CNO and the Deputy CNO read it.
- **An approved roster never goes back to draft or submitted** (section 5), so "no longer approved" cannot happen. A month that is over takes no approval, and its waiting swaps have expired by date.
- **Locks:** a proposal and an approval take the catalogue's, the named nurses' `FOR NO KEY UPDATE`, the unit's, the roster's and then the swap's, as a direct edit does; an answer and a withdrawal take the swap's only. `make_version` locks the swaps it expires after the roster. The decision's 404 for another unit comes before any nurse's row is locked.

`docs/ARCHITECTURE.md` sections 4, 5, 7 and 8 and the glossary's Swap, Roster version and Notification moved.

**Review.** The `code-review` skill's two axes against `5c0b2f8`.
- Spec found:
  - the order-of-checks leak above;
  - another swap's existence told about a colleague;
  - a manager's nurse locks taken before the 404.

  All fixed, the first two with tests. It also listed the scope beyond the ticket (a swap of one's own cells only, telling the manager of a withdrawal or expiry of one awaiting him, the 62-cell cap, the back-links), kept and recorded above, and the untested hidden facts above.
- Standards found no hard violation. Fixed:
  - `NO_CONNECTION` defined twice;
  - missing type hints;
  - the state sentence rebuilt;
  - `Grid` redefined;
  - names (`_is`, `made`, `version`, `Month`, `_key`, `why_not_approve`);
  - the audit target rebuilt;
  - the decision dialog's six switches.

  **"live" was the glossary's avoided word for Approved**, so a swap still deciding is now "waiting" in code and docs. Left as judgement calls:
  - `swaps.api` importing `rosters.api._grid_check` and `mine_api` importing `rosters.reading_api._in_force`, private names other apps already reach across;
  - `SwapStep` in `notifications.sending`, and `notifications.reading` importing `swaps.models`, as ticket 19 kept for requests;
  - the function-local import in `make_version`, which avoids a cycle.

`better-interface` and its domain skills, held by hand against the code and the run:
- Every select has a visible label. A cell's refusal is tied to its nurse select by `aria-describedby`, with `aria-invalid` and focus on it. "In the roster in force: …" describes each row's selects.
- A refusal of the whole swap is an alert and takes focus. The status line announces each outcome and takes focus.
- Each table has a scroll region with a name. Each action's name says whose swap and which dates. Reject, Withdraw and the manager's decisions ask first.
- The copy uses the glossary's words: swap, roster in force, version, pin, leave. "Off" is what a day not worked reads, as on My roster.
- No new colour, type or motion.
- `interface-review` is yours to invoke.

**Things later tickets should know:**
- **Month close (21):** a pin of origin `swap` is read by the close like any pin (`rosters.pins.month_pins`). A waiting swap of a month that is over has expired by date. An approval of a month that is over is refused (`steps.MONTH_OVER`).
- **Browser journeys (24):** the nurse's journey is My roster → Swaps → propose → a colleague accepts → the manager approves on Swaps (`/unit-swaps`) → version in force.
- **Every version expires the waiting swaps whose cells it changes, in `make_version`.** Anything that writes `Roster.grid` of an approved roster without it would skip that.
- **The dev stack was not touched:** no restart, no migration, no login. When this branch reaches `main`, restart `web` and `worker` there for `swaps.0001` and `notifications.0004`, and so the worker picks up `expire_swaps`. Without the restart every new version fails, since `make_version` imports the new app. **No new dependency.**

