# Preferences: a second, soft kind of request

Status: ready-for-agent
Type: feature
Published: 2026-11-07 by /to-spec
Decided: the grilling of 2026-11-07 (13 questions, two rounds), recorded in `docs/adr/0010-preferences-are-priced-never-pinned.md`
and `GLOSSARY.md` (Preference, Kept)

Vocabulary: `GLOSSARY.md`. Decisions and their reasons: `docs/ARCHITECTURE.md` and `docs/adr/`. Where this spec and those
documents disagree, the documents win and this spec is wrong.

## Problem Statement

A nurse has one way to say what she wants of a coming month: a request, which her unit manager decides and which, accepted,
becomes a pinned cell the solver may not move (ADR 0005). Because every accepted request is a promise, the unit caps them at a
few a month (default 3) and the manager must read and decide each one. A nurse who would simply rather not work the 12th, or
would rather work the Friday her sister is away, has no way to say so: it is either a promise or nothing.

The solver has always been able to take such wishes, as days asked off and days asked to work, kept when it can at a price
set by two hospital-wide weights. The app never fills them: the CNO's weights page says of the two "Nothing reaches this for
now".

Over months, self-scheduling feels fair only when the nurse whose wishes lost last time comes first this time. Nothing in the
app remembers whose wishes lost.

## Solution

**A preference** is a nurse's wish about one date of a coming month, made in the same request window as her requests: a day
off, or a working day of any shift. Nobody decides it. It never becomes a pin. The solver keeps it when it can, at the
weight's price, and the roster in force says whether it was kept.

**Fairness over time.** For a nurse one of whose preferences the month before did not keep, every preference of hers costs
twice the weight this month. The number of her preferences not kept is carried from month to month like her fairness
balances: worked out by the solver's own carry-over, projected from the roster in force and corrected when the month closes.
It remembers one month only.

**A cap of its own.** Each unit caps the preferences a nurse makes a month (default 10; 0 switches preferences off), beside
its request cap, so that nobody can mark the whole month off and hold a doubled price for good.

**One wish a date.** A date holds a request or a preference, never both. While the window is open a nurse may ask for a
preference as a request instead, under the request cap, or withdraw it.

**My month** shows the nurse how many of her preferences the roster in force kept, each one Kept, Not kept or On leave, and
tells her when her preferences count double this month and why.

**The manager** reads the unit's preferences beside its requests and sees what each solve paid for them, as for every soft
rule. He decides nothing on them.

## User Stories

1. As a Staff Nurse, I want to mark a day of a coming month as one I would rather have off, so that the roster leans my way without my using a request.
2. As a Staff Nurse, I want to mark a day as one I would rather work, so that the roster leans towards giving me a shift that day.
3. As a Staff Nurse, I want to make preferences in the same request window as my requests, on My month, so that I plan a month in one place at one time.
4. As a Staff Nurse, I want no reason field on a preference, so that I am not asked to justify a wish nobody decides.
5. As a Staff Nurse, I want to see how many preferences I have made against my unit's cap, so that I know how many are left.
6. As a Staff Nurse, I want to withdraw a preference while the window is open, so that I can change my mind.
7. As a Staff Nurse, I want to ask for a preference as a request instead, while the window is open and under the request cap, so that a wish that has grown important becomes a promise without my re-entering it.
8. As a Staff Nurse, I want a date to hold either a request or a preference, so that I cannot contradict myself on one day.
9. As a Staff Nurse, I want to make a preference on a date whose request was rejected or withdrawn, so that a refused promise can still be a wish.
10. As a Staff Nurse, I want a preference on a leave date refused when I make it, with the reason, so that I do not make one that can count for nothing.
11. As a Staff Nurse, I want a preference on a date outside my start and end dates refused, so that I do not make one for a day I am not on the roster.
12. As a Staff Nurse, I want my preferences fixed once the window closes, so that the roster is solved on what I said in time.
13. As a Staff Nurse, I want to see, once the roster is approved, how many of my preferences it kept, in words like "4 of 5 kept", so that I know how the month treated me.
14. As a Staff Nurse, I want each preference marked Kept, Not kept or On leave, so that I can see which days went my way.
15. As a Staff Nurse, I want a preference on a day I was later put on leave marked On leave and counted neither way, so that leave does not count as a broken wish.
16. As a Staff Nurse, I want to be told when my preferences count double this month, and which month's unkept preference caused it, so that I know the roster owes me.
17. As a Staff Nurse, I want the Preferences card to say "No roster yet" before the roster is approved, so that I do not read a draft's outcome as final.
18. As a Staff Nurse, I want My month of a month that is over to show what the close found kept, so that a late leave or a correction is reflected.
19. As a Staff Nurse, I want no notification about a preference, so that my bell is not filled with news of things nobody decides.
20. As a Staff Nurse, I want only my manager and me to read my preferences, so that colleagues learn nothing of my wishes.
21. As a Staff Nurse, I want nothing of my preferences on a colleague's My roster, print sheet or roster file, so that my wishes stay mine.
22. As a Staff Nurse on a phone, I want the Preferences card to work at 375 px with thumb-sized controls and no sideways scroll, so that I can plan from the ward.
23. As a Staff Nurse using a screen reader, I want each outcome announced and each button named with its date, so that I can act on the right preference.
24. As a Staff Nurse due to join a unit, I want to make preferences in the new unit's window, so that my first month there leans my way too.
25. As a Staff Nurse transferred out after making preferences, I want them left on the old unit's record and counting for nothing there, so that nothing of mine reaches a roster I am not on.
26. As a Unit Manager, I want to read the unit's preferences beside each window's requests, so that I know what the solver is weighing.
27. As a Unit Manager, I want no accept or reject on a preference, so that I am not asked to decide what the solver prices.
28. As a Unit Manager, I want the draft's explanation to show what the solve paid for preferences, as for every soft rule, so that I can see the trade the solver made.
29. As a Unit Manager, I want to set the unit's preference cap on the Unit rules page beside the request cap, so that I decide how many wishes a nurse may make.
30. As a Unit Manager, I want a cap of 0 to switch preferences off for my unit, so that a unit that wants only requests has only requests.
31. As a Unit Manager, I want a cap lowered mid-window to keep the preferences made and refuse new ones above it, so that nobody loses a wish already made.
32. As a Unit Manager, I want to open a request window when either cap is above zero, so that a unit with requests off can still take preferences.
33. As a Unit Manager, I want a re-plan to keep pricing preferences on the days it plans again, so that a mid-month change still leans the nurses' way.
34. As a Unit Manager, I want the draft warned when preferences changed since it was solved, as it is for pins, so that I solve again before submitting on stale wishes.
35. As a Unit Manager, I want a nurse's doubled price to apply in every solve of the month, so that the fairness rule holds however often I solve.
36. As the CNO, I want the two weights on the hospital weights page to say what they now price, and no longer that nothing reaches them, so that I set them knowingly.
37. As the CNO, I want a weight of 0 to switch preferences off hospital-wide, as a weight of 0 does for every soft rule, so that nothing new is needed to turn them off.
38. As the Deputy CNO, I want nothing of preferences in what I read, so that approval stays about the roster.
39. As the System Admin, I want preferences stored in the solve input and the close input as leave already is, so that the solve history stays complete.
40. As a nurse whose month was closed, I want the close to count my unkept preferences from what really happened, so that a leave recorded late corrects it.
41. As a nurse in a month my unit had no roster for, I want zero unkept preferences carried out of it, so that a month nothing was solved for owes me nothing.
42. As a nurse in her first month, I want zero carried, so that nothing is owed from before the app.
43. As a nurse whose carry-over crosses January, I want the unkept count not reset, so that a December loss still counts in January.
44. As a nurse transferred to another unit, I want the count to follow me, so that my new unit's roster still owes me.
45. As a nurse whose month was closed again, I want the count re-worked from the new close, so that the chain stays correct.
46. As a developer, I want every stored solve input and close input from before this change to load, so that nothing of the solve history breaks.
47. As a developer, I want a solve's own carry-over and a close's to agree on the count, so that the chain is one computation.

## Implementation Decisions

### The solver's contract (its first change since ADR 0002, in this repository)

- **A new optional per-nurse input field, the count of her preferences the month before did not keep,** a whole number of
  0 or more, absent meaning 0, so that every stored solve input and close input still loads. The problem's schema version
  notes the change.
- **The price.** When that count is above zero, every entry of hers in the two soft rules (a day asked off, a day asked to
  work) costs twice the weight, in the model's objective and in the validator's explanation alike, so a solve's cost and a
  validation's agree. The explanation's words for such a match say it counted double. The existing lists `undesired_days`
  and `desired_days` are the preferences; nothing else about them changes: a day on leave is ignored, a day listed twice or
  in both lists is refused.
- **The result's carry-over block gains the count,** worked out from the month's facts: her days asked off that were
  worked plus her days asked to work that were off, leave days excluded. It is a carried value like `rest_owed`: one
  month's memory. The precheck and the explanation need no new words beyond the doubled match.
- **The solver's own suite and the service contract tests** cover the loader, the price, the explanation and the carry-over.

### The app's model

- **`Preference`, in the `requesting` app**, beside `Request`: nurse, window, date, kind (a day off or a working day),
  state (`made`, `withdrawn`, `asked_instead`), when made, when ended and by whom. Nothing is deleted. A unique constraint
  holds one live preference a nurse and date. Whether a date is on leave is read, never stored, since leave may be removed.
- **One wish a date, across requests and preferences:** making a preference is refused where a pending or accepted request
  holds the date, and making a request where a live preference does, with words naming the other. A rejected, withdrawn,
  cancelled, replaced or expired request frees the date.
- **The unit's preference cap** is one more field of the unit (0 to 31, default 10), set on the Unit rules page beside the
  request cap and audited like it. Live preferences (`made`) count against it, a month, across the month's windows. A cap
  lowered keeps those made and refuses new ones at or above it. Counting is under the same locks a request's count takes.
- **The window** opens when the unit's request cap or its preference cap is above zero. The refusal for a unit with both at
  zero names both caps.
- **Who makes them:** staff nurses only, as with requests; a manager with a nurse profile makes none. A nurse due to join a
  unit makes them in that unit's window. A nurse transferred out keeps hers on the old unit's record; she is not in that
  unit's month, so they reach no solve input and count against the old unit's cap only.
- **What may be preferred:** a date of the open window's month, within the nurse's dates, not on her leave (refused at the
  form, as a request is). Leave recorded later over a preference leaves it `made`; every reading of its outcome then says
  On leave, and the solver already ignores it.

### The nurse's side

- **Endpoints beside the request ones, taking no nurse:** read the month's preferences with the window and the cap, make
  one, withdraw one, ask for one as a request instead. The last makes the request under the request cap and the window's
  rules, ends the preference as `asked_instead`, and fails as a whole if the request is refused.
- **The read answer** carries, for each preference, its date, kind, state and outcome: `kept`, `not_kept`, `on_leave`, or
  none while no roster is approved. The outcome is read from the roster in force (the version in force on the month as it
  stands, as My month's hours are) and, once the month is closed, from the close in force's facts. It also carries the count
  kept and the count that could be kept, and whether her preferences count double this month, with the month that caused it.
- **Counting double is read from the chain:** the carried value her month starts from, through the same reading the solve
  input takes, so My month and the solve input never disagree.
- **The Preferences card on My month**, for staff nurses, beside the Requests card: the window's sentence ("You have 3 of 10
  preferences."), the form (date within her dates; "A day off" or "A working day"; no reason), each preference with its
  outcome and, while the window is open, Withdraw and "Ask for it as a request" behind a question that names the request
  cap. Once the roster is approved the card's heading says "4 of 5 kept"; before, "No roster yet"; and when it applies, a
  line reading "One of your preferences was not kept in May, so this month yours count double." The outcome words are
  "Kept", "Not kept" and "On leave". No notification is sent for anything here.
- **Privacy:** only the nurse and her unit's manager read preferences. Nothing of them reaches a colleague's My roster, My
  month, print sheet, a roster file, a notification or the audit log's detail (the audit entries are `preference.made`,
  `preference.withdrawn` and `preference.asked_instead`, targeting the nurse, with no date or kind). The solve input and the
  close input hold the days, as they hold leave, and the System Admin reads them there as today.

### The solve input and the chain

- **The solve input** fills each nurse's `undesired_days` with her live day-off preferences and `desired_days` with her
  live working-day preferences for the unit's month, and her carried count from the chain. A preference on a day she is on
  leave or outside her dates is left in: the solver ignores it. A re-plan's input carries the same; the solver prices only
  the days it plans again.
- **The chain carries the count** as one more carried field, from the result's carry-over block, so a projection from the
  roster in force and a close compute it the same way. A month with no roster for her hands on 0, like the shift history;
  her opening values carry 0 and need no field; January does not reset it. A re-close re-works it.
- **Changes since a solve:** the draft's warning lists a nurse whose preferences changed since the input was stored, as it
  lists pins, as "preferences".

### The manager's side

- **The Requests page** lists each window's preferences beneath its requests: nurse, date, kind, state, read-only.
- **The draft's explanation** already shows each soft rule's cost; the two preference rules now show real numbers and the
  per-nurse explanation says which matches counted double. No new page.
- **The Unit rules page** gains "Preferences per nurse per month" beside the request cap, with the same description style
  and the same refusal on an open window.

### The CNO's side

- **The hospital weights page's two descriptions** drop "Nothing reaches this for now" and say: "Each day a nurse preferred
  to have off but works; twice that for a nurse whose preference last month was not kept." and its mirror for days preferred
  to work. The weights' names and defaults do not change.

### Documents

- `docs/ARCHITECTURE.md`: section 1 and section 12 no longer list soft preferences as out of scope; section 4 gains the
  Preference entity and the unit's preference cap; section 5's Requests lifecycle gains the preference steps; section 6
  notes the solver contract's new field; section 7's chain paragraph names the carried count; section 8's screens name the
  Preferences card and the manager's read-only list. ADR 0010 and the glossary are already written.
- `frontend/openapi.json` and the generated client are regenerated.

## Testing Decisions

- **What a good test is here:** it drives a public interface and checks what a user or a caller sees: an endpoint's answer,
  a page's words by their accessible names, a solve input's nurse block, a close's carried values. Expected numbers come
  from an independent source: a roster whose kept and unkept days are counted by hand, a weight multiplied on paper. No test
  of the chain's internals, the model's literals or a component's state.
- **Seam 1, the solver's own suite and the service contract tests** (`solver/tests`, `solver/service_tests`): the loader
  accepts the new field, defaults it to 0 and refuses a negative or non-integer; a problem with the count above zero costs
  twice the weight for that nurse and once for another, in the model's cost and the validator's; the explanation's match
  says it counted double; the carry-over block counts unkept preferences from a known grid, leave days excluded; the
  contract test's sample request and result carry the field. Prior art: `test_request.py`, `test_rules.py`,
  `test_carry_over.py`, `test_contract.py`.
- **Seam 2, the backend API suite** on a throwaway PostgreSQL 18 with the scripted solver and the real worker's code:
  - `requesting`: make, withdraw, ask instead (under the request cap, and refused as a whole when the request is), the
    preference cap and its lowering, one wish a date both ways, a leave date refused, a date outside her dates refused, the
    window's open and closed states, a window opening on the preference cap alone, a nurse due to join, a transfer, a
    manager with a nurse profile refused, the manager's read-only list, the audit entries' content, and privacy (a
    colleague's whole My month, print sheet and file unchanged), after the pattern of `test_requests.py`; two at once at the
    cap, after `test_two_at_once.py`.
  - `solves`: the solve input's nurse block carries the two lists and the carried count; a re-plan's input too; `changes
    since` reports changed preferences (`test_input.py`, `test_replan.py`).
  - `closes`: the count projected from the roster in force, corrected at the close from facts with late leave, zero through
    a month with no roster, zero for a first month, not reset across January, following a transfer, re-worked on a re-close
    (`test_close.py`).
  - `rosters`: My month's preference outcomes and counts from the version in force and from a close, the doubled line and
    its month, with expected values counted by hand on `sound_rosters.json` (`test_own_month.py`).
  - `units`: the cap's range and audit; `accounts/tests/test_authorization.py` names every new endpoint's roles.
- **Seam 3, the frontend's app-level Vitest suite** (`app.test.tsx` through `start` and `hold`): the Preferences card's
  sentence, form, outcomes, "No roster yet", the doubled line, Withdraw and Ask-instead behind their questions, the cap
  reached; the Unit rules page's new field and its refusal; the Requests page's read-only list; the weights page's new
  descriptions; the route guards for any new page. Ticket 11's rules: no raised timeout, no fake timers, no wait that proves
  something did not happen; six runs at once must pass.
- **Seam 4, one Playwright check** beside `request.spec.ts`: on the phone, a nurse makes a day-off preference, asks for it
  as a request, withdraws the request, makes the preference again and withdraws it, leaving the stack as it was. Thumb-sized
  controls, the outcome in view. Run with `e2e/ci.sh`.

## Out of Scope

- A preferred shift on a day: the solver prices a day, and a specific shift stays a request.
- A multiplier by the count unkept, a longer memory than one month, or a price that differs by unit: ADR 0010 rejected them.
- A manager's decision on preferences, a notification for them, or a reason on them.
- Preferences for a manager with a nurse profile; swaps touching preferences in any way.
- Showing the nurse the solver's cost or any colleague's preferences.
- Arabic, dark mode, and whatever earlier tickets listed as not checked.

## Further Notes

- The solver package changes, so the dev stack needs a **rebuild** of `web`, `worker` and `solver` after the merge, and a
  restart for the migration (the preference table and the unit's cap). The solver's suite must run.
- The hospital weights page keeps the defaults 2 and 1; whether they are the right price against the fairness weights is
  the CNO's to judge after a real month, not this feature's.
- The carried count's name in the solver's contract is the implementer's, in the solver's own style (`rest_owed`,
  `last_shift_kind`); the glossary's word for the nurse is "not kept".
