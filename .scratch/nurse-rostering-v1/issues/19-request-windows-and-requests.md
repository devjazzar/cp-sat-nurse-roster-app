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
- **Leave recorded later over an accepted request removes the pin and tells the manager,** which answers "ticket 11's to resolve" above. The request stays on record; which state it then takes is for this ticket, along with what the form says.
