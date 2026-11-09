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

**From ticket 35 (2026-11-09):** every solve, re-plan, draft check, swap and cover judging, submit and approval input now carries
each nurse's `skills` (`nurses.rostering.skills_block`, called by `solves.input.assemble`), so the two rules already reach
everything that checks a grid with the solver's code. What that means for this ticket:
- **Swap judging needed no change to stay hidden.** `swaps.judging._violation_problem` already hides a violation on a colleague
  ("This swap cannot work for <name> on <date>"), says the proposer's own in full, and hides every unit-level rule but
  `headcount` (`SAID_AS_IT_IS`). So `skill_expired` and `skill_need` take the forms the spec asks for. No test pins them yet:
  they are this ticket's.
- **Pins and requests still don't know a barred day,** but a pin can no longer break the solve. `rosters.pins.Judge.day_why` has
  no `barred` reason. Ticket 35 keeps a shift pinned on a barred day out of every input instead
  (`solves.input.without_barred_shifts`, in `assemble` and in the edit check's `rosters.editing.with_edits`), because the
  solver's loader refuses one. The pin row stays, and the grid holds its shift, so the check names the `skill_expired` rule.
  What is left here: the set-aside reason and its words on the draft, and the request refusal. A barred day is every day from
  `solves.input.barred_from`, which mirrors `nurse_roster.problem.barred_days`. Once 38's set-aside lands, drop the filter or
  keep it as the one definition.
- **The Roster page already shows an approved roster's skill rules** among "what the grid breaks on the month as it stands".
  Ticket 35 tested the draft's case and the submit and approval refusals, not the approved roster's.
- **A barred day supersedes a preference** since ticket 35, in the solver and on My month, where it reads "Skill expired".
