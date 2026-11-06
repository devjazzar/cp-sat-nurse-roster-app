# 19: Request windows and requests

**What to build:** The unit manager opens a request window for a target month with open and close dates and may close it early; nurses are told. During the window a nurse makes requests (a day off, or a specific shift on a date) up to the unit's cap and may withdraw a pending one. The manager accepts or rejects each with a reason, and may later edit or cancel an accepted one. Accepted requests become pinned cells in that month's solve input; rejected and cancelled ones stay on record and the nurse sees every outcome.

**Blocked by:** 15 Nurse's own month and notifications

**Status:** ready-for-agent

- [x] Window with target month, open and close dates, close early; at most one open per unit; nurses notified on open
- [x] Requests of two kinds within the cap; withdraw while open; states pending, accepted, rejected, withdrawn, cancelled
- [x] Manager decision with reason; edit and cancel of accepted ones; all audited and notified
- [x] Accepted requests appear as pinned cells with origin 'request' in the solve input and are kept on re-solve
- [x] Nurse sees her requests and outcomes; manager sees the unit's requests per window
- [x] API tests cover the window rules, the cap, each state transition, authorization and the solve input

## Comments

**From ticket 09 (2026-11-05).** The cap is `Unit.request_cap`, from 0 to 31, default 3, which the unit manager sets on the unit rules page. 0 means no requests.

**From ticket 10 (2026-11-05).** An accepted request for a shift becomes a pin, and the solver refuses a shift pinned on a leave date. Accepting one on a leave date should be refused, and leave recorded later over an accepted one is ticket 11's to resolve. A nurse may request on their own leave date from the solver's side (it is superseded), so decide what the form says.

**Decisions from the user (2026-11-05).** Leave wins over a pinned shift. An accepted request for a shift is a pin, so:

- **Accepting a shift request on a leave date is refused,** because pinning a shift on a leave day is refused.
- **Leave recorded later over an accepted request removes the pin and tells the manager,** which answers "ticket 11's to resolve" above. The request then takes a new final state saying leave replaced it, stays on record, and the nurse is told. What the form says about a request on a nurse's own leave date is still for this ticket.

**From ticket 11 (2026-11-05).** An accepted request reaches a solve as a pin, through `solves/input.py`: see the comment on ticket 13.

**From ticket 13 (2026-11-05).** Pins are built, and an accepted request is one of them.

- **One table, one origin:** `rosters.models.PinnedCell`, with `origin` already holding `request` and `swap` beside `manager`. A row belongs to the unit whose month it is (`unit`), and one nurse has at most one current pin a date (`rosters_one_current_pin_a_nurse_date`). Nothing deletes one: a pin ends with `removed_at`, `removed_by` and `removed_why` (`cleared`, `replaced`, `leave`). Accepting a request that lands on a cell the manager pinned has to end that pin as `replaced`, or the constraint refuses it; decide whether that is allowed or refused. Cancelling an accepted request ends its pin, perhaps with a new `removed_why`.
- **The manager cannot change a request's pin from the Roster page:** `rosters.editing.Month.refusal` refuses any edit of a pin whose origin is not `manager`, "change it there", and the page offers nothing on such a cell. That is the hook for "the manager may edit or cancel it later" through the request.
- **What counts reaches the solve on its own:** `solves.input.assemble` takes every current pin of the unit's month through `rosters.pins.month_pins`, whatever its origin, and sets aside one that is on leave or outside the nurse's dates, on a shift the unit no longer works or the nurse may not work, or of a nurse no longer in the month. A request's pin needs no code of its own there, and is kept on re-solve as a manager's is: a solve's roster gets every pin that counts put on top.
- **Leave over an accepted request:** recording leave on its date ends the pin as `leave` through `rosters.pins.end_for_leave`, in `nurses.leave_api._begin`, on every path that adds a date, and the answer names it in `pins_removed`. Look up the request by the ended pin there to give it the new final state and tell the nurse. Accepting a shift request on a leave date is refused like a pin: `rosters.pins.Judge` says why in the words the save uses.
- **The pin's own refusals**, for accepting: a shift the unit does not work, one outside the nurse's allowed shifts, a day outside their dates or on leave, a month that is over. Reuse `Judge`, so a request and a pin cannot disagree. The guards on dropping a shift from the unit rules and on narrowing allowed shifts already count a request's pin, and refuse naming the nurse and date.

**From ticket 15 (2026-11-06).** "Window opened" and "request decided" are yours to emit, and the requests' place on the nurse's own month. Nothing sends either event yet.

- **Window opened:**
  - Add `Event.WINDOW_OPENED` and `sending.window_opened(unit, target_month)`, and call it where the window opens.
  - Tell the unit's nurses of the target month (`membership.placed_in(unit, target_month)`).
- **Request decided** (accepted, rejected, edited, cancelled, and replaced by leave):
  - Tell the nurse who made it, and nobody else.
  - The decision's reason can be shown to her, because it is her own request, but keep it out of the payload and read it from the request when the notification is read.
- **What awaits a manager:** a request made in an open window waits for the manager's decision. Decide whether each one tells the manager, or one notification does when the window closes. Ticket 15 counted only a rejection as what awaits them today.
- **My month:** `routes/_signed-in/my-month.tsx` has a commented slot for "the nurse's requests for this month and their outcomes", between the hours and the leave. `GET /api/rosters/mine/month` (`rosters.reading_api.my_month`) has no requests: add them there or in an endpoint of yours.

How to add an event, the same for each: add it to `notifications.models.Event`, which is a migration only of `choices`. Write a function beside the others in `notifications/sending.py` that works out the recipients and calls `notify(users, Event.X, **payload)`. Call that function inside the change's transaction, after its audit entry. Then give the event its words in `notifications.reading.text_of` and its link in `link_of`, adding a page to `NotificationLink.page` and to `Open` in `routes/_signed-in/notifications.tsx` if it needs one. **A payload holds identifiers only** (`unit_id`, `month`, `by`, and the request's or swap's id): the words are worked out when read, so nothing goes stale and nothing about a person is stored. `text_of` reads `payload["month"]` for every event today, so an event with no month needs its own branch first. `notify` already skips deactivated users and tells each user once.

**From ticket 16 (2026-11-06).** A request accepted, edited or cancelled after its month's roster is approved changes the roster in force: section 5 lists accepted requests among the changes that are new versions. Make it with `rosters.versions.make_version(roster, grid, VersionOrigin.REQUEST, by, reason)` under the roster's row lock, then the audit entry and `notifications.sending.roster_changed`, as `rosters.api.save_version` does. The manager's editor already refuses a pin of origin `request`.

**Implemented on 2026-11-06,** on branch `claude/ticket-19-requests-59645b`. The backend ran under pytest on a throwaway PostgreSQL 18 container of my own, the frontend under Vitest with the real routes and generated client over a stubbed `fetch`.

- Results on the final code: backend 2044 passed, frontend 498 of 498, and `npm run build` clean.
- `makemigrations --check` is clean, and `frontend/openapi.json` is the same as a fresh export.
- **The frontend suite ran alone in this worktree, not in clean exports in parallel.** That is left to the session that brings this into `main`.
- The solver's suite was not run: nothing under `solver/` changed.

What was built:

- **A new app, `requesting`** (not `requests`, which is a well-known HTTP library's import name; section 8 says so). Migrations `requesting.0001_request_windows_and_requests` and `notifications.0003_request_events` (choices only).
  - `RequestWindow`: unit, target month, `opens_on`, `closes_on`, stored state `scheduled`/`open`/`closed`, `opened_at`, `closed_at`, `closed_by` (the manager who closed it early; null when its date did).
  - `Request`: nurse, window, date, shift (null for a day off), state (`pending`, `accepted`, `rejected`, `withdrawn`, `cancelled`, `replaced_by_leave`), and `pin`, the current pinned cell while accepted. A constraint allows one pending or accepted request a nurse and date, and another that only an accepted one holds a pin.
  - `RequestStep`: every step with who, when and the reason given (the nurse's when she made it, the manager's for a decision), and the pin an acceptance or edit made. Nothing is overwritten.
- **The window's clock** (`requesting/windows.py`). `state_today` reads the dates, hospital time through `membership.today()`, for every page and every write. `catch_up` brings the stored state level and tells whoever that tells, under each window's row lock, so whichever comes first does it once.
  - The hourly job `requesting.tasks.open_and_close_request_windows` (minute 10) runs it for every unit. Every write about a unit's windows runs it first for that unit.
  - A worker that is down therefore delays only the notifications, never what a page says or what a nurse may do.
- **The nurse's side** (`requesting/making.py`, `mine_api.py`): `GET/POST /api/requests/mine` and `POST /api/requests/mine/{id}/withdraw`, for staff nurses only.
- **The manager's side** (`requesting/api.py`, `deciding.py`), for the unit's manager only:
  - `GET/POST /api/units/{id}/request-windows`, `.../{window_id}/close` and `.../{window_id}/requests`.
  - `POST /api/units/{id}/requests/{request_id}/accept|reject|edit|cancel`.
- **Shared with pins:**
  - `rosters.pins.Judge.refusal` is now the one set of words for why a pin cannot hold. The draft editor (`DraftEdits.refusal`) and a request's acceptance both use it.
  - `rosters.pins.pin_cell` is the one way a pin is made. It ends whatever pin the nurse held that day, this unit's or one a transfer left behind.
  - `rosters.pins.end` now ends only current rows, so a pin already ended keeps who ended it and why.
  - `end_for_leave` returns every pin it ended, and `leave_api._begin` keeps naming only the unit's. `RemovedPin` gains `origin`.
- **Events:** `WINDOW_OPENED`, `WINDOW_CLOSED_EARLY`, `WINDOW_CLOSED` and `REQUEST_DECIDED`. Each has a sender in `notifications/sending.py`, words in `reading.text_of` and a link in `link_of`. The new pages `my_month` and `requests` were added to `NotificationLink.page` and to `Open`.
- **Pages:**
  - **My month** has a Requests card in ticket 15's slot, for staff nurses only. It shows the window's dates and the cap used, the form (date within their dates, a day off or a shift they may work, and an optional reason), each request with its outcome and the manager's latest reason, and Withdraw on pending ones while the window is open.
  - **Requests** (`/requests`, in the manager's header) has:
    - the form to open a window, and the cap with a link to Unit rules;
    - the windows newest first, with Close early behind a question;
    - each window's requests, with Accept, Reject, Change and Cancel in a dialog with a reason. A pending request that cannot be accepted says why instead of offering Accept, and Accept warns when it replaces your pin.
  - The Leave page says when a pin it replaced was an accepted request. The audit log names the new actions.

Seams:
- `requesting/tests/test_requests.py` (60 tests, some parametrised): the API with the scripted solver and the real worker's code. It covers the window's dates without waiting on a clock (`membership.today` patched, the job called directly), the cap, what may be requested, every state and transition, the decisions on a draft, a submitted and an approved roster, leave over a request, transfers, authorisation, and privacy.
- `requesting/tests/test_two_at_once.py` (5 tests), on real connections with the order forced: two requests at the cap, two acceptances, leave waiting on an acceptance, the hourly job waiting on a write that opened the window, and a decision waiting on a withdrawal.
- `app.test.tsx`: 17 new tests and the new page in the route guards, through `start`. No raised timeout, no fake timers, no wait that proves something did not happen.
- **Honestly: much of the backend came just ahead of its tests, not after a red one.** I broke guards by hand and saw tests fail: the cap check, the window's row lock (the job race tells the nurses twice), the leave hook, a reason put into a payload, the swap refusal, the draft branch and the withdrawal's open check. **One break failed nothing: taking away the nurse's row lock.** The window's row lock, which every request takes, also holds the cap, since a unit has one window open at a time. The nurse's lock stays, for the order with leave and decisions.

**Driven in the built-in browser,** on scratch project `nr-t19`:
- The setup: the production compose file with its own image (`nr-t19-app`), secrets and volumes, and `web` published on `127.0.0.1:18019` under `DJANGO_DEBUG`. There was no Caddy, and the real solver and worker ran. ER was the solver's four-nurse sample with a manager (Mona) and a CNO, seeded by a script, rostering December 2026 on the real clock (6 November).
- **As Mona:**
  - Opening a window that closed on 2 December was refused beside Last day ("choose 30 November 2026 or earlier").
  - A window from 6 to 20 November opened at once, with the status line focused.
- **As Amal:**
  - The bell said "Mona Ali opened requests for the ER roster for December 2026, until 20 November 2026." and led to My month for December.
  - She asked for a day off on 3 December with a reason, Night on 10 December and a day off on 20 December. At 3 of 3 the form gave way to the cap's sentence.
  - She withdrew the 20th, and the form came back. She asked for Day on 15 December.
- **As Badr:** a day off on 3 December. His page showed only his own request.
- **As Mona:**
  - She accepted Amal's 3rd (with a reason) and 10th.
  - Rejecting Badr's with no reason was refused in the dialog, with focus on Why. With a reason it went.
  - The solver input then read "Pinned cells 2". **A real solve of 15 s** (cost 127) kept both: Amal off on the 3rd and Night on the 10th. The grid labels those cells "pinned by an accepted request".
  - She submitted. The Requests page then said Amal's pending 15th "Cannot be accepted: This roster is submitted…".
- **As the CNO:** Requests sent her home, and its API answered 403. She approved December (version 1).
- **As Mona:**
  - Accepting Amal's 15th (Night in the roster) made **version 2, origin `request`**, reason "Amal Saleh's request for Day (D) on 15 December 2026 accepted."
  - **Sick leave for Amal on 10 December** made the Leave page say that the replaced pin "was an accepted request, which stays on record as replaced by leave; its nurse is told", and version 3 took the shift off.
- **The database then held:**
  - The requests: 3rd accepted, Badr's rejected, 10th `replaced_by_leave`, 15th accepted, 20th withdrawn.
  - Every payload held identifiers and a step only.
  - The audit log held `request.made`, `withdrawn`, `accepted` and `rejected` with the nurse as target and nothing else, `request_window.opened` with its dates, and for the leave only `leave.recorded`.
- **Amal's bell:** each decision, "Leave recorded on 10 December 2026 replaced your request for Night (N), as leave wins.", the approval and both changes. Her My month showed each outcome with Mona's reason, and no sideways scroll at 375 px.
- **Badr's bell:** the window, his own rejection ("The reason is on My month."), the approval and two roster changes, and nothing of Amal's requests. His My roster says nothing of requests.
- **The real worker's registry** lists `requesting.tasks.open_and_close_request_windows` at `10 * * * *`.
- That run found one bug, fixed with tests: a shift's name was lowercased inside sentences ("day (d)"). Everything of `nr-t19` has been removed since: containers, volumes, network and image.

What was NOT checked:
- **The Deputy CNO and the System Admin were not signed in** on the scratch stack: no Deputy CNO was seeded, and the System Admin's first login forces a password change. The walk in `test_authorization.py` holds both to 403 on every new endpoint. The manager's bell was seen only as its count; its texts were read from the database.
- **The hourly job firing in the real worker.** No window was left to open or close at minute 10; the job is tested by calling it, and its registration was read from the worker.
- **The manager's Requests page at 375 px, the Change dialog and Close early, in the browser.** Vitest only. **The Cancel dialog has no page test at all**; its endpoint is API-tested.
- **The CNO's and the Deputy CNO's version list showing a request's version** in the browser.
- **A transfer with requests, a cap lowered mid-window, a renamed shift, and the job tests' race, in the browser.** API tests only.
- **Dark mode, 320 px, 200% zoom, RTL, a screen reader, browsers other than the built-in one, and through Caddy.**
- **A large unit.** Each window's request list computes the acceptance refusal for every pending request (one `Judge` a month).

**Decisions taken here:**

- **Worth your review: the manager is told once, when a window closes by its date with requests waiting,** not once a request. Its words count what still waits when read ("…has closed, and 2 requests wait for your decision."). That is what awaits a manager, beside a rejected roster. A window closed early by the manager tells them nothing, and one whose whole span passed with the worker down tells nobody it opened.
- **Worth your review: at most one window of a unit is scheduled or open,** whatever its month: a constraint holds it, and the refusal names the window in the way. Once one has closed, another may target any month, the same one too, and the cap counts across that month's windows.
- **Window dates:**
  - The target month must not have begun.
  - The open date is today or later.
  - The close date is the last day requests are taken, before the month begins.
  - A unit with a cap of 0 cannot open one.
- **Worth your review: closing early tells the nurses who were told it opened,** reading "may close it early; nurses are told" as both. A window that never opened tells nobody.
- **The cap:** pending and accepted requests count, withdrawn, rejected, cancelled and replaced-by-leave ones do not. A cap lowered mid-window keeps the requests made and refuses new ones while the count is at or above it. The count is held under the nurse's row lock and the window's.
- **What a nurse may request:**
  - Only a date of an open window's month, within their dates.
  - A day off, or a shift the unit works that they may work. **The form offers only the shifts they may work, so a nurse can see her allowed shifts** (Worth your review: the glossary says nurses never read their attributes. The alternative is offering every unit shift and refusing at the decision).
  - Not two pending or accepted requests on one date, in any unit.
  - **A date already on leave is refused at the form**, "You are on leave on …, so there is nothing to request that day.", since nothing could accept it.
  - A nurse due to join requests in the new unit's window, and is told when it opens.
  - A manager with a nurse profile makes none: the table gives requests to staff nurses.
- **Transfers:** a nurse transferred out after requesting keeps the request on the old unit's list. Accepting it is refused as a pin would be ("… is not on this unit's roster for …"), and it can be rejected. It counts against the old unit's cap only, but still holds its date.
- **Accepting reuses `Judge`**, in the same words a pin's save uses.
  - **Worth your review: accepting onto a cell the manager pinned replaces that pin** (ended as `replaced`), and the list says so before Accept. An accepted swap's pin refuses it.
  - A draft takes the cell at once, since a draft never disagrees with a pin, and warns that the solve lacked it.
  - **A submitted roster refuses accept, edit and cancel**, and allows a rejection.
  - An approved roster of a month not over takes a changed cell as a version with origin `request`, and its nurses are told the roster changed. A change that alters no cell makes no version and tells nobody but the requesting nurse.
  - A month that is over takes none.
- **Worth your review: an edit changes what the accepted request promises** (another shift, or a day off) and keeps what she asked. **Cancelling ends its pin and changes no cell**, on a draft too, so no version is made after approval. Ticket 16's comment listed a cancel among what makes a version; a cancel that changes no cell cannot, by the user's rule for ticket 16. The next solve, or the manager's edit, is free to change that cell.
- **A reason is required to reject, edit and cancel, and optional to accept** (Worth your review: the ticket says "accepts or rejects each with a reason").
- **Worth your review: leave over a pending request replaces it too**, as `replaced_by_leave`, and the nurse is told. It could never be accepted, and would hold a place under the cap. The user's decision named the accepted case only.
- **Privacy:**
  - A nurse reads only her own requests, through endpoints that take no nurse.
  - Nothing of a request reaches a colleague's My roster, My month, print sheet, a roster file or any notification. A test compares a colleague's whole My month before and after, and searches their print sheet and the manager's CSV.
  - Both reasons stay out of every payload and out of the audit log, whose entries are `request.made|withdrawn|accepted|rejected|edited|cancelled`, target the nurse, and hold no date, shift or reason. Opening and closing a window is audited with the unit and month, its dates for an opening.
  - Leave replacing a request, and a version a request made, have no entry of their own, for the reason ticket 16 gave a leave-made version.
  - **Worth your review: a request's version reason** ("Amal Saleh's request for Day (D) on 15 December 2026 accepted.") is read by the CNO and the Deputy CNO in the version list, as every version reason is. It carries neither reason, but tells them a request was made.

- **My month with no month in its address reads the current month**, its requests too, as its hours and leave do. The request read first defaulted to the next month, which a last check found and a test now holds. A window's notification links to its target month.

`docs/ARCHITECTURE.md` sections 4, 5, 7 and 8 and the glossary's Request, Request window and Notification moved.

**Review.** The `code-review` skill's two axes against `d3b9f5c`.
- Spec found:
  - a pin another unit had ended being overwritten by a cancel;
  - a request left behind by a transfer counting against the new unit's cap;
  - leave over a pending request leaving it pending for good;
  - the lock order's docstring;
  - no file in the colleague privacy test.

  All fixed, with tests. It also raised the cancel making no version, the version reason the approvers read, the form not marking a leave day ahead (the refusal sits beside the date), and the pin-code refactors as scope (kept: they are what lets a request and a pin share their words). Those are recorded above.
- Standards found:
  - lines over 130 characters;
  - missing type hints;
  - duplicated words (what a request asks, a state's words, the cap sentence, month names, shift names in the pages);
  - vague names (`Locked` built without locks, now `Decision`; `found`; `_told`, `_pinned`);
  - an unused helper;
  - the page maps typed as plain strings;
  - one count query a notification and one aggregate a window, now one query each.

  All fixed. Left as judgement calls:
  - `making.nurse_refusal` keeps its own words over `Judge`'s answers, since it speaks to the nurse;
  - `notifications.reading` imports `requesting.models`;
  - `request` for the HTTP request beside `nurse_request`, as the codebase's endpoints have it.

`better-interface` and its domain skills, held by hand against the code and the run:
- Every form field has a label, a description and its error, tied by `aria-describedby`. A refusal goes beside its field with focus on it, or into the dialog as an alert.
- The status line announces each outcome and takes focus. Each table has a scroll region with a name.
- Each action button's name says whose request and which date, and includes its visible word.
- The copy uses the glossary's words: request, request window, pin, roster in force, version, leave.
- No new colour, type or motion.
- `interface-review` is yours to invoke.

**Things later tickets should know:**
- **Swaps (20):**
  - `rosters.pins.pin_cell(unit, nurse, day, shift, PinOrigin.SWAP, by)` is the way to write a swap's pins. It ends whatever pin the nurse held that day, a request's included. A request so ended is left `accepted` with an ended pin, so decide there whether a swap may land on an accepted request's cell; `Judge.refusal` gives the shared words.
  - `requesting/deciding.py` shows the pattern for a version after approval.
- **Month close (21):** a request of a month that is over can no longer be accepted, edited or cancelled (`deciding.MONTH_OVER`), and its pin is read by the close like any pin. A pending request of a month already over stays pending until its manager rejects it.
- **A follow-up for whoever owns the Leave page's copy:** on an approved roster, leave that ends a pin still says "It replaced a pin on the draft… or solve again", which fits a draft only. It predates this ticket.
- **The dev stack was not touched:** no restart, no migration, no login. When this branch reaches `main`, restart `web` and `worker` for `requesting.0001` and `notifications.0003`. Without the restart the pages that read or end pins (Leave, Roster) fail, since `leave_api` imports the new app. **No new dependency.**
