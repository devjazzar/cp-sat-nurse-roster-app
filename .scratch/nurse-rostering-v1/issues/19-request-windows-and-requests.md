# 19: Request windows and requests

**What to build:** The unit manager opens a request window for a target month with open and close dates and may close it early; nurses are told. During the window a nurse makes requests (a day off, or a specific shift on a date) up to the unit's cap and may withdraw a pending one. The manager accepts or rejects each with a reason, and may later edit or cancel an accepted one. Accepted requests become pinned cells in that month's solve input; rejected and cancelled ones stay on record and the nurse sees every outcome.

**Blocked by:** 15 Nurse's own month and notifications

**Status:** ready-for-agent

- [ ] Window with target month, open and close dates, close early; at most one open per unit; nurses notified on open
- [ ] Requests of two kinds within the cap; withdraw while open; states pending, accepted, rejected, withdrawn, cancelled
- [ ] Manager decision with reason; edit and cancel of accepted ones; all audited and notified
- [ ] Accepted requests appear as pinned cells with origin 'request' in the solve input and are kept on re-solve
- [ ] Nurse sees her requests and outcomes; manager sees the unit's requests per window
- [ ] API tests cover the window rules, the cap, each state transition, authorization and the solve input

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
