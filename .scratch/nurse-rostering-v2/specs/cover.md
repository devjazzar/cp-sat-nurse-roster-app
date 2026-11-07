# Cover for a sick call

Status: ready-for-agent
Type: feature
Published: 2026-11-07 by /to-spec
Grilling: sixteen questions in three rounds on 2026-11-07, every one answered as recommended. Decisions: `GLOSSARY.md` (Cover)
and `docs/adr/0011-a-cover-adds-one-nurse-and-the-first-acceptance-wins.md`. Where this spec and `docs/ARCHITECTURE.md`,
`GLOSSARY.md` or an ADR disagree, those win and this spec is wrong.

## Problem Statement

A nurse calls in sick on a day she is rostered to work. The unit manager records the leave, and the app takes her shift off the
roster in force as a new version. The shift-day is now short: of its headcount, of its team leader, or of a gender. The manager
has two ways to fill it, both blind: edit cells by hand, guessing who is off, rested and under their caps, or re-plan from the
date, which moves other cells too and asks nobody first. Nothing lets the manager ask the nurses who could take the shift, and
nothing tells a nurse that a shift is there to take.

## Solution

A **cover**: one more nurse needed on one shift on one date of the roster in force. When leave takes a shift off the roster in
force, a cover opens by itself on the manager's new Covers page, unoffered; the manager may also open one by hand for any
shift-day of the roster in force, today or later, short for any reason. The page lists the unit's staff nurses who could take
the shift without newly breaking a hard rule, judged with the solver's own check as a swap is, ranked by who stands furthest
below her owed hours this month, then least overtime this year, and says what the shift-day still lacks. The manager ticks any
of them and offers, with a note. Each nurse ticked is told, reads the date, the shift and the note on her own Covers page, and
accepts or declines from her phone. The first to accept takes it: a pinned cell of origin `cover` in a new roster version, in
force at once, the way an approved swap lands. The others are told it is taken. A cover not taken expires when its date passes,
is withdrawn by the manager, or is filled when any new version puts one more nurse on its shift-day. A cover is about the
shift-day, never about whose absence made it short: no nurse learns why it was short or who else was asked.

## User Stories

### The manager: covers opening

1. As a Unit Manager, I want a cover to open by itself for every shift that leave takes off the roster in force, so that a sick call leaves me a to-do rather than a cell I must notice.
2. As a Unit Manager, I want the leave form's answer to point me to the cover it opened, so that I go from recording the leave to offering the shift in one step.
3. As a Unit Manager, I want covers opened by leave to wait unoffered until I act, so that annual leave planned weeks ahead, which I will re-plan, sends nobody anything.
4. As a Unit Manager, I want to open a cover by hand for any shift-day of the roster in force, today or later, so that a shift short after a re-plan, an edit, an end date or a transfer can be offered the same way.
5. As a Unit Manager, I want to open a cover from the roster grid's shift-day, so that I need not leave the roster to ask for one more nurse there.
6. As a Unit Manager, I want two absences on one shift-day to be two covers, so that each one more nurse needed is asked for on its own.
7. As a Unit Manager, I want no cover opened for a draft or a submitted roster, so that only the roster in force is offered.
8. As a Unit Manager, I want no cover opened for a date that has passed, so that I am never offered a shift already worked or missed.

### The manager: who could take it

9. As a Unit Manager, I want the cover's page to list the month's staff nurses who could take the shift, so that I ask only those who can.
10. As a Unit Manager, I want the list to hold only nurses off that day (no leave, within their dates, no shift that day) who may work the shift, so that nobody is asked to be in two places.
11. As a Unit Manager, I want the list to leave out anyone whose taking the shift would newly break a hard rule (rest, run, succession, a forbidden pair, an overtime cap, the shift-day's maximum headcount), judged with the solver's own check, so that an acceptance never breaks the roster.
12. As a Unit Manager, I want a hard rule the roster in force already breaks not to count against a nurse, so that a shift-day already short does not empty its own list.
13. As a Unit Manager, I want a nurse whose accepted request holds that day off left out, so that a promise the hospital made to her is kept.
14. As a Unit Manager, I want a nurse I pinned off that day, or whom an approved swap pinned off, still listed, with the pin replaced if she takes the cover, so that an earlier pin does not stop my offer.
15. As a Unit Manager with a nurse profile, I want myself not listed, so that I take a shift by editing the roster, never by offering it to myself.
16. As a Unit Manager, I want the list ranked by who stands furthest below her owed hours this month, then by least overtime this year, so that the fairest choice is at the top.
17. As a Unit Manager, I want each nurse's hours against her owed hours this month and her overtime this year shown beside her name, so that I can explain the order to anyone.
18. As a Unit Manager, I want the page to say what the shift-day still lacks (below its minimum headcount, no team leader, not both genders), so that I know whether one more nurse makes it whole.
19. As a Unit Manager, I want a mark on each nurse whose taking the shift makes the shift-day whole, so that I can tick a team leader when a team leader is what is missing.
20. As a Unit Manager, I want a shift-day at its maximum headcount that lacks a team leader to list nobody and say why, so that I know a cover cannot help and an edit is needed.
21. As a Unit Manager, I want the list worked out on the month as it stands when I open the page, so that leave recorded a minute ago is already counted.

### The manager: offering

22. As a Unit Manager, I want to tick any of the listed nurses, all ticked by default, and offer the cover with an optional note, so that one tap asks everyone who could.
23. As a Unit Manager, I want to add nurses from the list to a cover already offered, so that I can widen the offer without withdrawing it.
24. As a Unit Manager, I want never to take a nurse off an offer, so that nobody told of an offer finds it silently gone.
25. As a Unit Manager, I want to withdraw a cover, offered or not, so that one I no longer need, or filled by my own edit, stops asking.
26. As a Unit Manager, I want to be told at each decline and at the acceptance, so that I know where the cover stands without watching the page.
27. As a Unit Manager, I want to see who accepted, who declined and who has not answered, so that I can add nurses or withdraw when everyone has declined.
28. As a Unit Manager, I want a cover everyone declined to stay offered with nobody left, so that nothing ends it but my own hand or its date.
29. As a Unit Manager, I want the Covers page to show the month's covers, open, offered and ended, newest first, so that I can read what happened to each.
30. As a Unit Manager, I want a cover's page to read what its shift-day lacks and who could take it again each time I open it, so that it is never stale.

### The manager: what an acceptance does

31. As a Unit Manager, I want the first acceptance to take the cover and make the pinned cell and the version at once, so that a sick call is answered without a second round of mine.
32. As a Unit Manager, I want the acceptance judged again on the month as it stands, so that a nurse who could no longer take it (leave recorded since, a rule now broken) is refused rather than pinned.
33. As a Unit Manager, I want the version's reason to name the taker, the shift and the date, never the absent nurse, so that the version list and its comparison say what happened without dating anyone's leave.
34. As a Unit Manager, I want the pin of origin `cover` to count like any pin in every solve, re-plan and month close, so that the promise holds.
35. As a Unit Manager, I want an acceptance during a re-plan of the month to make the re-plan end outdated, so that the re-plan never undoes the shift a nurse just took.
36. As a Unit Manager, I want my editor to refuse to change a cell a cover's pin holds, as it refuses a swap's, so that I change it on the cover's page or by a reason I give.

### The manager: how a cover ends

37. As a Unit Manager, I want a cover not taken to expire when its date has passed on the hospital's clock, so that nobody is offered a shift already gone.
38. As a Unit Manager, I want every page to read a cover's date itself, so that an expiry shows at once even when the worker is down.
39. As a Unit Manager, I want a new version that puts one more nurse on a cover's shift-day, whatever made it, to end one waiting cover of that shift-day as filled, so that my edit, a re-plan or an approved swap does not leave an offer open for a need already met.
40. As a Unit Manager, I want a leave removed later to put nothing back and end no cover, so that the cover stays until I fill or withdraw it, as the shift does.
41. As a Unit Manager, I want ended covers kept with who ended them, when and how, so that nothing is deleted.

### The nurse

42. As a Staff Nurse, I want to be told when a cover is offered to me, so that I can take a shift from my phone.
43. As a Staff Nurse, I want a Covers page beside Swaps with the offers waiting for me and those I took or declined, so that I find them in one place.
44. As a Staff Nurse, I want to read the date, the shift, its hours and the manager's note, so that I know what I am asked.
45. As a Staff Nurse, I want nothing of why the shift is short or who else was asked, so that no colleague's leave reaches me.
46. As a Staff Nurse, I want to accept with one tap, 44 px tall, so that it works with a thumb.
47. As a Staff Nurse, I want my acceptance to put the shift in my cell on My roster at once, so that I see it is mine.
48. As a Staff Nurse, I want to be told, in my own words, when I can no longer take it (my leave recorded since, a rule it would break for me), so that I know why I was refused.
49. As a Staff Nurse, I want to be told when a cover offered to me is taken by someone else, withdrawn, filled or expired, so that I stop waiting on it.
50. As a Staff Nurse, I want to decline, so that the manager knows not to wait for me.
51. As a Staff Nurse, I want My month to count a shift I took, so that my hours and overtime are right.
52. As a Staff Nurse, I want a cover's shift on My roster to look like any shift of mine, so that nothing marks a colleague's absence.
53. As a Staff Nurse, I want to be offered two covers of one shift-day and take at most one, so that I am never on the shift twice.
54. As a Staff Nurse, I want the notification to link to my Covers page, so that one tap takes me to the offer.

### Everyone else

55. As the CNO or the Deputy CNO, I want to read a cover only through the version it made and its reason, as with swaps, so that nothing new is mine to decide.
56. As the System Admin, I want the audit log to say that a cover was offered, withdrawn, accepted or declined, never a date, a shift or a note, so that nothing in it dates a nurse's leave.
57. As a colleague on the unit, I want to be told the roster changed when a cover is taken, as for every version, and nothing more, so that I read my own row on My roster.
58. As a nurse of another unit, I want to see nothing of this unit's covers, so that a cover never crosses a unit.

### Phones and access

59. As a Staff Nurse on a phone, I want Covers in the Menu, so that I reach it as I reach Swaps.
60. As a screen reader user, I want each outcome announced and each cover's actions named with its date and shift, so that I can act on the right one.
61. As a keyboard user, I want focus on the refusal or the outcome after each action, so that I read it without hunting.

## Implementation Decisions

- **A new app, `covers`,** shaped on `swaps`. ARCHITECTURE sections 3, 4, 5, 7 and 8 and the glossary carry the cover as they
  carry the swap; the implementer writes those paragraphs.
- **The Cover row:** unit, roster, the version in force when it was opened, date, shift, how it opened (`leave`, with the
  leave-made version, or `manager`), the manager's note, state, who ended it and when, the version its acceptance made, and the
  nurse who took it. The absent nurse is not on the row: the version that opened it is enough for the manager, who reads that
  version's reason anyway.
- **States:** `open` (unoffered), `offered`, `taken`, `withdrawn`, `filled`, `expired`. Waiting means `open` or `offered`.
  Expiry has no reason field: a date passing is the only cause. `filled` is nobody's act, like an expiry.
- **The offer rows:** one per nurse offered (nurse, offered at, answer `pending`, `accepted`, `declined`, answered at). A nurse
  is in a cover at most once. The acceptance that won is the taker; a later acceptance is refused as taken.
- **Opening by leave:** the one function that takes a shift off the roster in force for leave opens a cover per shift taken off,
  in the same transaction, after the version. The leave endpoints' answer lists the covers opened beside the shifts taken off.
  No notification and no audit entry for the opening.
- **Opening by hand:** a manager's endpoint on the unit, taking a date today or later in a month whose roster is in force and
  one of the unit's shifts, refused for anything else; refused for a draft or a submitted roster.
- **Who could take it, and the ranking,** in one judging module, the one place a cover is judged and worded, as swaps have:
  - the month's staff nurses (not a manager with a nurse profile) whose cell that day is empty, whose day the pin judge allows
    (in the month, within dates, not on leave) and whose placement allows the shift; a current pin of origin `request` on the
    day leaves her out; a manager's pin, or a swap's, is noted as replaced, as a swap's approval replaces both; a cell in a
    waiting swap is left in (the swap expires if she takes the cover, as any version expires it);
  - for each, the grid with her cell set to the shift, the cell put in as a pin, checked in `web`'s process with the solver's
    own code against the solve input of the month as it stands; a hard violation not already in the roster in force's own
    check leaves her out; a grid or rules the loader refuses is an answer shown, not an error;
  - the shift-day's lack is read from the roster in force's own check: its hard violations on that date and shift (headcount,
    team leader, gender), in words from the solver's text with dates instead of day numbers; a nurse "makes it whole" when her
    grid leaves no hard violation on that shift-day;
  - ranking by (hours worked − owed hours) this month ascending, then overtime this year (the carry-over's year-to-date plus
    this month's) ascending, then name; the figures from the solver package's per-nurse accounting on the roster in force,
    the same arithmetic My month uses. Nurses whom the shift would push over a cap are already out by the hard check.
  - The whole list is read when the page asks; nothing of it is stored.
- **Offering:** the manager's endpoint takes the nurse ids to offer, each one in the list as judged now (refused by name
  otherwise), and the note; on an `open` cover it makes it `offered`; on an `offered` cover it adds those not yet in it. It
  tells the nurses added. The audit entry `cover.offered` has the manager as actor and the unit as target.
- **Accepting,** by a nurse offered it, under the locks an approval takes in their order (the catalogue's, the nurse's
  `FOR NO KEY UPDATE`, the unit's, the roster's, the cover's): the cover's date read first (expired is refused), the state
  (taken, withdrawn, filled are refused with the state's words), then judged again for her alone; refused in her own words
  ("You are on leave on …", "This breaks a rule for you: …"), the cover staying offered. Then her answer, the pin through the
  one way a pin is made with origin `cover`, the version with origin `cover` and the reason "Cover taken by {name}: {shift}
  on {date}.", the cover `taken` with the taker and the version, the audit entries `cover.accepted` (actor the nurse, target
  her hospital ID) and `roster.changed` (version, one pin, one cell), then the unit's nurses told the roster changed and the
  cover's other nurses told it was taken. The nurse's own acceptance tells the manager.
- **Declining,** by a nurse offered it, under the cover's lock only: her answer and `cover.declined` (actor the nurse, target
  her hospital ID); the manager told. A nurse who declined is not asked again by an add.
- **Withdrawing,** by the manager, open or offered: `withdrawn`, `cover.withdrawn` (actor the manager, target the unit), the
  nurses offered it told.
- **Filled:** in the one function that makes a version, under the roster's row lock, after the swaps' hook: for each
  shift-day on which the new grid holds more nurses than the grid before, one waiting cover of that shift-day, oldest first,
  per nurse added, becomes `filled`; its nurses offered are told. A version of origin `cover` fills nothing: it changes one
  cell, its taker's, which its own cover accounts for, so a second cover of the same shift-day stays offered. No audit entry.
- **Expiry:** a waiting cover whose date is before today on the hospital's clock reads as expired on every page and in every
  write about it first; the hourly job `expire_covers` (minute 20, beside `expire_swaps` at 15) stores it and tells the nurses
  offered it. No audit entry.
- **Re-plans:** nothing new. A cover's version is a version, so a re-plan in flight ends `outdated`; a pin of origin `cover`
  before the re-plan's date is a fact, after it a pin the re-plan keeps.
- **The manager's editor** refuses a cell a cover's pin holds with "change it there", as for a swap's pin.
- **Pins and versions:** `PinOrigin.COVER` and `VersionOrigin.COVER`, migrations of choices only.
- **Notifications:** one event `COVER_STEP` with the step in the payload (`offered`, `declined`, `accepted`, `taken`,
  `withdrawn`, `filled`, `expired`) and the cover's id; recipients as the user stories say, never whoever took the step; the
  words read the cover when shown and never say why it was short, who else was asked or why it ended; links to the new pages
  `covers` (the nurse's) and `unit_covers` (the manager's). The month close tells nothing of covers.
- **Endpoints:**
  - the manager's, on the unit: list the month's covers; read one (its state, its shift-day's lack, the list of who could with
    the figures and the mark, the nurses offered with their answers); open by hand; offer or add; withdraw;
  - the nurse's: list mine (waiting first, then ended, with the cover's date, shift, hours, note, my answer and its state);
    accept; decline. A cover not offered to her is the same 404 as none.
  - Every other role is 403, the CNO, the Deputy CNO and the System Admin included. The OpenAPI export and the generated
    client are regenerated.
- **Pages:**
  - **Covers** (`/unit-covers`, the manager's header beside Swaps): the month's covers with state, date, shift, how opened and
    who took it; a cover's page with the lack, the ranked list with a tick a nurse (all ticked), the figures, the mark, the
    note field and Offer (or Add on an offered one), the answers so far, and Withdraw behind a question. An "Open a cover"
    form: date and shift. The leave form's answer links each cover opened; the roster grid's shift-day offers "Open a cover".
  - **Covers** (`/covers`, the staff nurse's header beside Swaps, in the phone Menu): offers waiting for her, each with
    Accept and Decline (decline behind a question), then those she took or declined and those that ended, with the state's
    words. Both pages take `month` in the address as Swaps do.
- **Privacy:** the nurse's rows carry no field about why the cover opened, no version number, no list of who was offered,
  no count. A refusal at acceptance uses her own words only, worked out in the judging module as swaps' are.
- **No change to leave's own rules,** to how a draft or a submitted roster treats leave, or to re-plans.

## Testing Decisions

- **What a good test is here:** it drives the API or the app as a user does and checks what that user gets: the list and its
  order, the refusal's words, the roster in force, who was told, the audit entries. It never checks how the judging is wired
  or which lock was taken, only what two writes at once end up as.
- **Seam 1, the API** (backend pytest, the scripted solver on the four-nurse June sample, the scene the swap tests use):
  - leave on a worked day opens a cover, unoffered, listed in the leave answer; leave on a day off opens none; a draft or
    submitted roster opens none; a date passed opens none;
  - open by hand: refused for a date passed, a shift the unit does not work, a month with no roster in force;
  - who could: off that day only; leave, dates, allowed shifts, an accepted request for the day off keep a nurse out; a
    manager's pin and a swap's are noted replaced; a manager with a nurse profile absent; a hard rule newly broken keeps her out and one
    already broken does not; the lack read as the roster's check says; the mark on those who make it whole; a shift-day at
    its maximum lists nobody;
  - ranking: below owed first, then least overtime, then name, on a scene where the figures differ;
  - offer: `open` to `offered`, those ticked told, the entry; add on an offered one tells only those added; a nurse not in the
    list refused by name;
  - accept: the first takes it (pin of origin `cover`, version of origin `cover` with its reason, `roster.changed`, the unit's
    nurses told, the others told taken, the manager told); the second is refused as taken; a nurse refused in her own words
    when leave was recorded since; a cover expired by date refused; a withdrawn one refused;
  - decline: the answer, the entry, the manager told; an add does not ask her again;
  - withdraw: open and offered; told; the entry;
  - filled: a manager's edit putting a nurse on the shift-day fills one cover, oldest first; two covers on one shift-day, one
    edit, one filled; an approved swap and a re-plan fill the same way; the cover's own version fills nothing: two covers on
    one shift-day, one taken, the other stays offered;
  - expiry: the page reads it, the job stores and tells; no entry;
  - the role walk in the authorization test for every endpoint;
  - two at once, on real connections: the last two acceptances, the second refused as taken; an acceptance against leave on
    the taker's day, refused; an acceptance against a withdrawal, refused;
  - with a re-plan: a cover accepted while a re-plan runs makes it end `outdated`; a re-plan's version fills a waiting cover.
- **Seam 2, the frontend's app-level Vitest suite** through `start`, as the swap pages are tested: both pages in the route
  guards and the header, wide and in the phone Menu; the manager's list, a cover's page with its lack, list, ticks, figures,
  Offer, Add and Withdraw; the "Open a cover" form; the nurse's page with Accept and Decline, each outcome's words, a
  refusal as an alert with focus; notification words and links for each step. No raised timeout, no fake timers, no wait that
  proves something did not happen.
- **Seam 3, Playwright,** `e2e/tests/cover.spec.ts` beside `swap.spec.ts`, on the seeded stack: a finder like `sound_swap.py`
  picks a worked cell of a staff nurse from tomorrow on and a colleague the judging lists for it; the manager records sick
  leave for that nurse on the desktop, opens the cover from the leave answer and offers it; the colleague accepts on her phone
  (`anotherPhone`); My roster shows her cell. The check leaves the stack usable: the manager removes the leave and edits the
  two cells back, or the stack is reset as `stack.sh` provides. `layout.spec.ts` gains the Covers link for both roles. Run
  with `e2e/ci.sh`.
- **Prior art:** `swaps/tests` (the API scene, the two-at-once tests, the re-plan tests), the swap sections of the frontend's
  app-level suite, `e2e/tests/swap.spec.ts` and `e2e/sound_swap.py`, `accounts/tests/test_authorization.py`.

## Out of Scope

- A nurse reporting sick in the app; leave stays the manager's to record.
- Push notifications for an offer (another grilling's subject); the bell is the only channel here.
- A cover that replaces a nurse rather than adds one, or that removes anyone; the manager edits for that.
- The manager choosing among several acceptors, or a deadline earlier than the date.
- Covers for the CNO's or the Deputy CNO's reading, or a count of open covers on any home page.
- Covers on a draft or a submitted roster.
- Arabic, email, SMS.

## Further Notes

- The judging checks one grid per candidate in `web`'s process, about 8 ms each on the 25-nurse sample; a unit of 40 nurses
  is under a second. The page reads the list each time it opens; nothing is cached.
- After this reaches `main` the dev stack needs `web` and `worker` restarted: new migrations (`covers`, `notifications`,
  `rosters` choices), the one function that makes a version imports the new app, and the worker needs the new hourly job.
  No new dependency is expected.
- Removing a leave puts no shift back (unchanged), so a cover opened by a leave recorded by mistake stays open until the
  manager's edit fills it or the manager withdraws it.
