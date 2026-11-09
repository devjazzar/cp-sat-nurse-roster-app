# Probation: a newly hired nurse works beside a preceptor and counts toward nothing

Status: ready-for-agent
Type: feature
Published: 2026-11-09 by /to-spec
Decided: the grilling of 2026-11-09 (29 questions, three rounds), recorded in `GLOSSARY.md` (Probation, Nurse on probation,
Preceptor; Skill's third mark) and `docs/adr/0014-a-nurse-on-probation-is-rostered-by-the-solver-and-counts-toward-nothing.md`

Vocabulary: `GLOSSARY.md`. Decisions and their reasons: `docs/ARCHITECTURE.md` and `docs/adr/`. Where this spec and those
documents disagree, the documents win and this spec is wrong.

## Problem Statement

A newly hired nurse is not yet a full member of her unit's staff. For her first months she works day shifts beside an
experienced nurse, her preceptor, and the shift must be safe without her. The application knows none of this. The CNO adds
her and from her first roster she counts toward every headcount, may be the shift's only team leader or its second gender,
is given nights and overtime, and is rostered on days her preceptor is not there. A unit manager who wants it right edits her
row by hand every month, and the headcounts the solver met are then one nurse short on every shift she was counted on.

## Solution

The CNO marks a nurse as on probation when adding her. Her unit manager sets how long it lasts (one to three months, extended
to six at most), assigns her a preceptor who holds a skill the catalogue marks as letting a nurse precept, and may end it
early. While it lasts the solver rosters her itself: day shifts only, on the same shift as her preceptor on the days her
preceptor works one, her other shifts placed freely to fill her hours, no overtime beyond rounding her hours up to a whole
shift, and counted toward nothing about a shift. Her row sits apart on the roster, under "On probation", with her
preceptor's name. When probation ends, on a month's last day, she is rostered like every other nurse from the next month.

## User Stories

### Starting a probation

1. As the CNO, I want to tick "On probation" when I add a nurse on the form, so that a newly hired nurse is never counted as
   full staff by mistake.
2. As the CNO, I want an optional "On probation" column in the nurse import CSV, so that a group of new hires is marked in one
   import.
3. As the CNO, I want the probation to begin on her start date with no other date to enter, so that there is one date to keep
   right.
4. As the CNO, I want to untick "On probation" as a correction, so that a mistake does not hold a nurse back.
5. As the CNO, I want an unticking to apply from the first month whose roster is not yet approved, so that approved rosters
   are not rewritten behind the unit.
6. As the CNO, I want to tick it later for a nurse already added, within six months of her start date, so that a forgotten
   tick can be put right.
7. As the CNO, I want a later tick refused once six months have passed since her start date, so that an established nurse is
   never put on probation by accident.
8. As the CNO, I want the tick refused for a unit manager with a nurse profile, so that only a staff nurse is on probation.
9. As the CNO or Deputy CNO, I want to read who is on probation in each unit, until when and with which preceptor, so that I
   can follow the new hires.
10. As the CNO, I want the staff list to say who is on probation and until when, so that the export matches the application.

### The length and the end

11. As a unit manager, I want to set a nurse's probation to 1, 2 or 3 months, so that it fits the nurse.
12. As a unit manager, I want it to stand at 3 months until I choose, so that a nurse the CNO just added is covered at once.
13. As a unit manager, I want the months counted as whole calendar months, with a month she joined after the 1st not counted,
    so that a probation is never shorter than I set.
14. As a unit manager, I want to see the probation's last day beside its length, so that I need not work it out.
15. As a unit manager, I want to extend a probation one month at a time, up to six in all, so that a nurse who needs longer
    gets it.
16. As a unit manager, I want an extension refused beyond six months, so that no probation runs on without end.
17. As a unit manager, I want to end a probation early at any time, so that a nurse who is ready moves on.
18. As a unit manager, I want an early end to take effect from the first day of the next month, so that the month under way
    keeps its roster.
19. As a unit manager, I want a probation to end by itself on its last day with nothing to confirm, so that nobody is held on
    probation by an oversight.
20. As a unit manager, I want a notification at the start of her last month, so that I can extend it or let it end.
21. As a unit manager, I want an end or extension that touches a month already approved to leave that roster as it is until I
    re-plan it, and the page to say so, so that I decide when the roster changes.
22. As a unit manager, I want every change to a probation in the audit log, so that it says who changed what.
23. As a unit manager of a unit a nurse on probation transfers into, I want her probation to come with her and keep counting
    from her start date, so that a transfer does not reset or cut it.

### The preceptor

24. As the CNO, I want a mark on a catalogue skill, "Lets a nurse precept", so that the hospital says which skills make a
    preceptor.
25. As the CNO, I want to mark more than one skill, so that either of two courses qualifies.
26. As a unit manager, I want to assign a preceptor to a nurse on probation from a chosen month on, so that the change is
    planned like a transfer.
27. As a unit manager, I want to choose the current month only while its roster is not yet approved, so that an approved
    roster is not broken by an assignment.
28. As a unit manager, I want the list to offer only nurses of my unit who hold a marked skill that has not expired, are not
    on probation themselves, and have no other nurse on probation in those months, so that I cannot choose wrongly.
29. As a unit manager with a nurse profile, I want to be offered as a preceptor when I qualify, so that I can precept myself.
30. As a unit manager, I want to change a nurse's preceptor from a chosen month, so that I can react when the pairing does not
    work, and the earlier preceptor to be free for another nurse from that month.
31. As a unit manager, I want the assignment to end with the preceptor's last month in the unit when she transfers or reaches
    her end date, and a notification to choose another, so that the nurse is not left paired with someone who has gone.
32. As a unit manager, I want a preceptor whose skill expires during the probation to stay the preceptor, so that a lapsed
    date does not break the roster mid-probation.
33. As a unit manager, I want the assignment to end when the probation ends, so that the preceptor is free again.
34. As a unit manager of the new unit after her transfer, I want to choose her preceptor there, so that she is paired with one
    of my nurses.
35. As a preceptor, I want a notification when a nurse on probation is assigned to me or taken from me, so that I know.
36. As a nurse on probation, I want a notification when my preceptor is assigned or changed, so that I know who I work beside.

### The roster

37. As a unit manager, I want a nurse on probation rostered on day shifts only, meaning every shift of my unit but its night
    shift, so that she never works a night.
38. As a unit manager, I want her to work the same shift as her preceptor on the days her preceptor works a day shift, so
    that she is supervised.
39. As a unit manager, I want her other shifts placed freely on day shifts when her preceptor is on nights, off or on leave,
    so that she still works the hours she owes.
40. As a unit manager, I want her own rest and run rules to apply to her, so that following her preceptor never overworks her.
41. As a unit manager, I want her to work at most the fewest whole shifts that cover the hours she owes, so that she has no
    overtime beyond rounding up to a whole shift.
42. As a unit manager, I want the hours beyond what she owes recorded as overtime, always less than one shift, so that her
    year's figures are true.
43. As a unit manager, I want her hours to win over following when her preceptor works more day shifts than her hours hold,
    and her to work no day shift apart from her preceptor's while one of her preceptor's is still free to follow, so that she
    is with her preceptor as much as her hours allow.
44. As a unit manager, I want her counted toward no headcount, minimum or maximum, so that every shift is fully staffed
    without her.
45. As a unit manager, I want her to satisfy no team leader, both-genders, score or skill rule, so that no shift leans on
    her.
46. As a unit manager, I want her left out of the unit's fairness figures and the overtime share, so that she does not skew
    her colleagues' shares.
47. As a unit manager, I want the preceptor rostered exactly as before, nights included, so that my night cover does not
    depend on who is precepting.
48. As a unit manager, I want a nurse on probation with no preceptor still rostered, on freely placed day shifts and counted
    toward nothing, with a warning naming her, so that a missing assignment does not stop the solve.
49. As a unit manager, I want her hours debt carried like any nurse's, so that nothing is lost over the month's end.
50. As a unit manager, I want her night and weekend fairness balances and her overtime-share balance to stay at zero through
    probation, so that she starts level with her colleagues when it ends.
51. As a unit manager, I want the draft's explanation to say which of her preceptor's day shifts she did not follow and why,
    so that I can read the roster.
52. As a unit manager, I want her allowed shifts kept as I set them and narrowed by the night shift during probation, so
    that my setting applies in full when it ends.
53. As a unit manager, I want setting her allowed shifts to the night shift alone refused while she is on probation, so that
    she is not left with no shift.
54. As a unit manager, I want her rostered as every other nurse from the month after probation ends, counted, with nights and
    overtime, so that the unit gains her fully.

### After approval

55. As a unit manager, I want a swap or a cover that would take the preceptor off a day shift the nurse on probation follows
    refused, so that she is not left unsupervised by someone else's change.
56. As a unit manager, I want my own edit that breaks it shown as a violation like any hard rule, so that I can move both
    cells together.
57. As a unit manager, I want a re-plan to keep her beside her preceptor, so that a sick call re-plans both.
58. As a unit manager, I want her never offered a cover and never part of a swap, so that she fills no gap.
59. As a unit manager, I want the Day view, the cover list and every headcount the application shows to leave her out, so
    that the numbers are the staffed numbers.

### What she and her colleagues see

60. As a nurse on probation, I want to make requests and preferences like any staff nurse, so that I can ask for a day off.
61. As a nurse on probation, I want an accepted day off to hold over following my preceptor, so that a granted request is
    kept.
62. As a nurse on probation, I want the request form to offer me day shifts only, so that I cannot ask for a night.
63. As a nurse on probation, I want My month to name my preceptor and the last day of my probation, so that I know where I
    stand.
64. As a nurse on probation, I want to be told why I cannot propose a swap, so that the missing action is explained.
65. As a preceptor, I want My month to name the nurse on probation I am paired with, so that I know who follows me.
66. As a staff nurse, I want a nurse on probation's row under an "On probation" heading with her preceptor's name on the
    unit's roster, so that I know she works beside us and does not count.
67. As a unit manager, I want the same heading on the grid, the print page and the Excel file, with headcount totals that
    leave her out, so that the sheet on the wall is right.
68. As the System Admin, I want to read nothing of probation, as I read nothing of rostering attributes, so that the role
    stays technical.

### Stored data

69. As anyone re-solving or closing an old month, I want a solve input stored before this feature to mean no nurse on
    probation, so that every stored solve and close gives what it gave.

## Implementation Decisions

### The words and the counting

- **Probation** begins on her start date and is counted in whole calendar months. A month she joins on the 1st counts; a
  month she joins later does not. Starting 15 December with 3 months, it covers the rest of December, January, February and
  March, and its last day is 31 March. Starting 1 December with 3 months, its last day is 28 February (or 29).
- Its length is 1 to 6. The unit manager may set 1, 2 or 3 while it is 3 or less; from there he may raise it by one at a time
  to 6. Lowering it and ending it early are one act: "End" sets the last day to the last day of the month under way on the
  hospital's clock. An ended probation cannot be extended.
- The CNO's tick is a correction, as her start date is: unticking removes the probation from the first month whose roster
  is not yet approved; ticking a nurse already added is allowed only while six months from her start date, counted the same
  way, have not passed. Only a staff nurse can be on probation.
- "Day shift" means every shift her unit works except the one its unit rules name as the night shift.

### The solver (vendored, `solver/`; ADR 0014)

- The contract gains two optional per-nurse fields: that she is on probation, and her preceptor's id. Absent means not on
  probation and no preceptor, so every stored solve input and close input loads and gives what it gave. The loader refuses a
  preceptor that is not another nurse of the input, one who is herself on probation, one named by two nurses, and a
  preceptor on a nurse not on probation, with the usual `request: <field path>` error. The problem's schema version notes
  the change.
- A nurse on probation is left out of every count about a shift: headcount minimum and maximum (overlapping shifts
  included), team leader, both genders, score target and balance, and skill needs. She is left out of the day and night
  fairness, the weekend fairness and the overtime share, and of the unit's overtime totals; her carried fairness balances
  are zero in and zero out.
- She may work no night shift: her allowed shifts are narrowed by the unit's night shift. A pin of the night shift on a
  free day of hers is refused, as a pin on a leave day is.
- Her hours: she works less than the hours she owes plus the length of her shortest allowed shift, so the excess is always
  under one shift. The excess is overtime on her own record (the month's and the year's). The existing shortfall rule is
  unchanged: she may end under one shift short and carry the debt.
- Following, one hard rule. Let her followable days be the free days on which her preceptor works a day shift she is
  allowed and she is not on leave, outside her dates or pinned. On a followable day she works her preceptor's shift or is
  off, never another shift. If any followable day is left off, she works no free day that is not followable. Pinned cells
  and elapsed days are facts and are not judged; her own rest, run and succession rules apply unchanged. With no preceptor
  there is nothing to follow.
- The validator and the explanation name the rule like every other: the nurse, the day, her preceptor's shift and hers.
  Precheck warns of a nurse on probation with no preceptor. Hours her days cannot hold are reported by the existing hours
  line, with no new one.
- Model, validator, explanation and precheck follow the rule registry, as for every rule.

### The catalogue and the nurse

- The skill catalogue gains a third mark on a skill, "Lets a nurse precept", set by the CNO like the other two, audited
  with the catalogue's entries, and read by every role that reads the catalogue.
- The nurse profile gains her probation: whether she is on one (the CNO's), its length in months and whether it was ended
  early (her unit manager's). Its last day is derived, never stored apart from them. It follows her across a transfer.
- A preceptor assignment says, from a given month on, which nurse precepts her. The latest that has begun is in force, as a
  placement is. It ends with the probation, with the preceptor's last month in the unit (transfer, end date), and with the
  nurse on probation's last month in the unit (her own transfer). Assigning refuses a nurse of another unit in that month,
  one holding no marked skill unexpired on the day of assigning, one on probation in those months, one already precepting
  another nurse in any of those months, and a month whose roster is approved. The skill is checked when assigning only.
- The nurse form and the CSV import gain "On probation" (the column optional, empty meaning no). The staff list gains who
  is on probation and until when.
- The unit manager works on the Rostering attributes page, on her row: the length, the last day, the preceptor, and the
  actions Extend, End and Change preceptor, each behind its question. Setting her allowed shifts to the night shift alone is
  refused while she is on probation.
- Notifications: to the unit manager at the start of her last month ("Layan Alharbi's probation ends on 31 March. Extend it
  or let it end."), and when a preceptor's leaving ends an assignment; to both nurses when a preceptor is assigned or
  changed. Sent by the hourly job that already opens and closes things by the hospital's clock, once each.
- Audit entries for the tick, the length, an extension, an end, and each assignment, with their values, as rostering
  attributes are logged.

### The solve and the roster

- The solve input, a re-plan's and a close's included, marks each nurse on probation in that month and names her preceptor
  when one is in force and in the input. "Changes since" reports a changed probation or preceptor like other inputs.
- An end, an extension or an unticking that touches a month whose roster is approved changes nothing in that roster; the
  roster page says the roster was planned with her on probation (or not) and offers the re-plan.
- Swaps: a nurse on probation cannot propose one or be a colleague in one, and is told why. A swap or cover that would break
  the following rule is refused as any hard rule is, with the proposer told only what My roster would show. Covers: she is
  never listed or offered. A manager's edit shows the violation.
- Every headcount the application itself works out (the approved roster's judging, the cover list, the Day view, the
  sheets' totals) leaves her out, with the solver's own reading.
- The unit's roster, wherever it is read (the manager's grid, My roster, the print page, the Excel file and the CSV), shows
  her row below the counted nurses under an "On probation" heading with her preceptor's name. My month names her preceptor
  and her probation's last day for her, and the nurse on probation for the preceptor.
- Requests and preferences are hers as any staff nurse's; the request form offers her allowed day shifts only.
- The OpenAPI document and the generated client are regenerated. `docs/ARCHITECTURE.md` gains the probation in the roles
  table, the domain model, the solver's contract and the notifications; `GLOSSARY.md`'s Nurse profile entry names it.

## Testing Decisions

A good test exercises the application as a user or a neighbouring system would, through a boundary that will outlive the
implementation, and asserts on what came out: a roster, a response, a stored input, a notification, an audit entry. Expected
values come from a worked example counted by hand, never recomputed the way the code computes them.

- **Seam 1, the solver's own suite and the service contract tests:** in the constraint-verifier style, a small month where
  the rule alone decides the roster. The loader on an input with and without the fields and its refusals; she is on her
  preceptor's shift on every followable day; no night; a headcount met without her and not met with her alone; a team
  leader, gender and skill need she cannot satisfy; fairness figures unchanged by her presence; her hours capped under one
  shift above what she owes, with 12-hour and 8-hour shifts; hours winning over following, and no shift apart from her
  preceptor's while one is unfollowed; a pin and leave holding over following; elapsed days as facts; no preceptor; the
  explanation's and precheck's words; the contract test's sample carrying the fields. Prior art: the skills rule suite, the
  preferences tests, the request and contract tests.
- **Seam 2, the backend API suite** on a throwaway PostgreSQL 18 with the scripted solver: the CNO's tick on the form and
  the CSV, its correction both ways and the six-month refusal; the month counting on worked dates (the 1st, mid-month,
  February, a year's end); the manager's length, extension, end and their refusals; the automatic end; the catalogue mark;
  each refusal of an assignment; the preceptor's transfer and end date; her own transfer; the notifications, once each; the
  solve input, a re-plan's and a close's, month by month across a probation's end; "changes since"; a swap and a cover
  refused; her absence from the cover list and the Day view's counts; the roster reads with her row apart and totals
  without her; My month for both; every role's reading; the audit entries' shape. A few run end to end with the real solver
  in process, as the solve flow tests do. Prior art: the nurse import, attributes, transfer, swap judging, cover, solve
  input and export tests.
- **Seam 3, the frontend's app-level Vitest suite** (through `start` and `hold`): the tick on the nurse form; the Skills
  page's third mark; the Rostering attributes row with its actions and questions; the "On probation" heading on the grid,
  My roster and the print page; My month for both nurses; the swap page's explanation. The local development guide's rules:
  no raised timeout, no fake timers, no wait that proves something did not happen; six runs at once pass.
- **The real thing:** on a scratch stack, a unit with one nurse on probation and a preceptor who works days and nights:
  she is beside her preceptor on every day shift her hours hold, works no night, and every shift's headcount is met without
  her.
- No new Playwright journey.

## Out of Scope

- More than one preceptor for a nurse, or more than one nurse on probation for a preceptor.
- Changing the preceptor's own roster because she precepts, or choosing a preceptor automatically.
- Counting a nurse on probation at a fraction, or toward any rule late in her probation.
- Night shifts under supervision.
- Probation for a unit manager with a nurse profile, or for a nurse who transfers after her probation is over.
- Evaluations, sign-offs, competency checklists or anything a preceptor records about her.
- Pay, contracts and anything a probation means outside the roster.

## Further Notes

- **What this waits for.** A nurse's skills (ticket 33) for the preceptor's check; the solver ticket after ticket 49, since
  both change the solver's input. The skill catalogue (ticket 32) is on `main`.
- **The tickets foreseen** (to be cut by `/to-tickets`, numbered from 52): the solver rosters a nurse on probation; the
  catalogue's "Lets a nurse precept" mark; probation on a nurse (the tick, the length, Extend, End, the automatic end and
  its notification); the preceptor (assigning and changing, the solve input, swaps, covers and requests); what everyone sees
  (the roster reads, the sheets, My month).
- **Worth the user's review when built:** her rounding overtime is on her own record but outside the unit's overtime totals
  (the department cap and the overtime share), so that it does not move her colleagues' shares; and with shifts of several
  lengths the hours bound is her shortest allowed shift, the mirror of the existing shortfall bound.
- A preceptor who works mostly nights leaves the nurse on probation mostly on her own. The application warns of nothing
  there; the unit manager chooses the preceptor and reads the roster.
