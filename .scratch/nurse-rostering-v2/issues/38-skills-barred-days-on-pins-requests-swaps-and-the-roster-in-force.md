# 38: Barred days on pins, requests, swaps and the roster in force

**What to build:** A day a nurse may not work, because a required skill of hers expired before it, is treated as her leave and her dates are: a pin on it is set aside, not removed, and counts again when the skill is renewed; a shift request for it is refused as she makes it, her own reason in full. A swap is judged by the solver's code as today: a refusal resting on a colleague's expired skill reads "This swap cannot work for <name> on <date>", a skill need left short reads only that the day's shifts would break the unit's rules, the proposer's own expiry is said in full, and the manager reads every reason; approval is refused when a skill change since made the swap break a hard rule. Nothing rewrites an approved roster when an expiry passes: the Roster page shows the skill rule it now breaks, and the manager edits or re-plans.

**Blocked by:** 35 Solving with skills

**Status:** ready-for-agent

- [ ] A pin on a barred day is set aside with a reason of its own in the draft's words, reaches no solve, and counts again when the record is renewed or removed; pinning a shift on a barred day is refused, naming the skill.
- [ ] A shift request on a barred day is refused as made with the nurse's own reason; a day-off request is allowed.
- [ ] Swap judging maps the two rules to the hidden form for a colleague and the full form for the proposer; the manager reads all; approval re-judges.
- [ ] The Roster page's check of an approved roster on the month as it stands shows a skill rule now broken, as it shows any other.
- [ ] The architecture document's pinned cell, request and swap paragraphs say so.
- [ ] Tests at the web API seam: the pin set aside and counting again, the request refusals, each swap wording from the proposer's and the manager's side, an approval refused, the Roster page's check.
