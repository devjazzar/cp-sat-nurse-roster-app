# Skills and credentials per shift-day

Status: ready-for-agent
Type: enhancement
Published: 2026-11-07 by /to-spec

Spec drawn from the grilling of 2026-11-07 (three rounds, fifteen questions, every one answered as recommended). Vocabulary:
`GLOSSARY.md` (skill, expiry, required to work, skill need). Decisions and their reasons: `docs/ARCHITECTURE.md`,
`docs/adr/0002-vendor-the-solver.md` and `docs/adr/0010-skill-rules-in-the-solver.md`. Where this spec and those documents
disagree, the documents win and this spec is wrong.

## Problem Statement

A shift-day today requires a headcount, a team leader and both genders, and nothing else about who is on it. A hospital
rosters by skill: a night in the ICU needs two ICU-certified nurses, an emergency shift needs someone with ACLS, a shift
with students needs a preceptor. Nurses' certificates expire, and nothing in the application knows when. So a unit manager
keeps the skill mix in his head and corrects the solver's roster by hand, a nurse whose BLS lapsed on the 15th is rostered on
the 16th as if nothing had changed, and the CNO learns of an expired certificate when an auditor asks. Timefold, UKG and
Allocate all roster by skill; the 2026 HealthStream survey found that only 34% of hospitals keep a nurse with an expired
credential off the schedule.

## Solution

The CNO keeps a **skill catalogue** beside the shift catalogue and the leave types: each skill has a name, says whether it
expires and whether it is **required to work**, and may be retired. The CNO records each nurse's **skills**, each with its
**expiry** where the catalogue says the kind expires; a nurse reads her own, her unit manager and the Deputy CNO read them,
and they follow her across a transfer. A **skills CSV** (hospital ID, skill, expiry), previewed then confirmed as the nurse
import is, records or renews skills in bulk.

A unit manager writes **skill needs** among the unit rules: on a shift the unit works, at least so many nurses holding a
skill each weekday and each weekend day, counting nurses on exactly that shift. One unit flag makes every skill need hard or
soft, as night rest's does; the price when soft is a hospital weight, **skill shortfall**, the CNO's with the other weights.

The solver honours both: a skill need is a rule of its own, beside team leader and gender, which it generalises; and a nurse
who holds a required-to-work skill that has expired works no shift from the next day, her hours still owed and carried as
debt as for any nurse whose days cannot hold them. A nurse with no record of a required skill is rostered as before: the gap
is the CNO's to fill, not the roster's to punish. Precheck says beforehand when a need cannot be met or an expiry falls in
the month; explain and the draft check name the rule as they name every other; a swap or an edit is judged by the same
code, and a colleague's skills stay behind the same hidden wording as her other facts.

An **expiries page** shows the CNO and the Deputy CNO every unit's skills expired or expiring within 90 days, and every
nurse with no record of a required skill; the CNO's home shows the count; a unit manager sees the same for his own unit.
Nothing rewrites a roster in force when an expiry passes: the Roster page shows the rule it now breaks, a draft is warned
that skills changed since its solve, and the manager edits or re-plans.

## User Stories

### The catalogue (CNO)

1. As the CNO, I want a skill catalogue beside the shift catalogue and the leave types, so that the hospital names its skills once and every unit uses the same names.
2. As the CNO, I want to add a skill with a name, so that a unit can require it and a nurse can hold it.
3. As the CNO, I want to say whether a skill expires, so that every nurse's record of it must carry an expiry and the expiries page can watch it.
4. As the CNO, I want to mark a skill as required to work, so that a nurse whose record of it has expired is kept off every shift.
5. As the CNO, I want to rename a skill, so that a wrong or outdated name is corrected everywhere at once, on nurses' records, unit rules and stored inputs read today.
6. As the CNO, I want to retire a skill, so that it is offered no more, while nurses' records of it and past rosters keep it.
7. As the CNO, I want retiring a skill refused, naming the units, while a live unit's skill need names it, so that no unit rule points at nothing.
8. As the CNO, I want a retired skill to count toward no skill need, so that a rule cannot lean on a skill the hospital no longer tracks.
9. As the CNO, I want two skills refused the same name, in any case of letters, so that ICU and icu are not two skills.
10. As the CNO, I want changing a skill from non-expiring to expiring refused, naming the nurses, while a nurse's record of it has no expiry, so that no record is left in an unknown state.
11. As the CNO, I want changing a skill from expiring to non-expiring allowed, with the expiries recorded kept but counting for nothing, so that a hospital decision is not blocked by data.
12. As the CNO, I want unmarking a skill as required to work to take effect at the next solve or check, so that a wrongly marked skill stops barring nurses at once.
13. As any signed-in user, I want to read the skill catalogue, so that the names I meet on my pages are explained; it names no one.
14. As the System Admin, I want each catalogue change in the audit log with its values, so that the hospital can see who changed what, since a skill names no one.

### A nurse's skills (CNO, managers, nurses)

15. As the CNO, I want to record a skill on a nurse, with its expiry where the kind expires, so that the roster knows what she holds.
16. As the CNO, I want a record of an expiring kind refused without an expiry, and one of a non-expiring kind refused with one, so that records match their catalogue entry.
17. As the CNO, I want to renew a skill by changing its expiry, so that a renewed certificate takes effect at the next solve or check.
18. As the CNO, I want to take a skill off a nurse, so that a record made in error is gone, kept in the record of changes.
19. As the CNO, I want a nurse's skills to follow her across a transfer, so that a fact about the person is recorded once.
20. As the CNO, I want a manager with a nurse profile to have skills like any nurse, set by me, so that the rule treats every rostered person alike.
21. As the CNO, I want a deactivated or ended nurse's skills kept, so that a returning nurse has her record and nothing is deleted.
22. As a Unit Manager, I want to read the skills and expiries of my unit's nurses, and of a nurse due to join, so that I know what my skill needs can lean on.
23. As a Unit Manager, I want not to be able to set a nurse's skills, so that nobody can grant a skill to satisfy his own rule; the CNO does.
24. As the Deputy CNO, I want to read every nurse's skills, so that I can judge a submitted roster's skill mix.
25. As a Staff Nurse, I want to read my own skills with their expiries on My month, so that I know what to renew and when.
26. As a Staff Nurse, I want to read nothing of a colleague's skills, so that her records stay hers.
27. As a Unit Manager with a nurse profile, I want to read my own skills where a nurse does, so that I too know what to renew.
28. As the System Admin, I want a change to a nurse's skills in the audit log as whose changed and by whom only, never which skill or date, so that I cannot learn that someone let a licence lapse.

### The skills CSV (CNO)

29. As the CNO, I want a skills CSV import of hospital ID, skill and expiry, so that the hospital's certificate list enters the application in one go.
30. As the CNO, I want a template for it to download, so that the columns are right the first time.
31. As the CNO, I want to preview the import before confirming, row by row, with every problem named (an unknown hospital ID, an unknown or retired skill, a missing or malformed expiry, a date on a non-expiring skill, a row repeated), so that nothing is saved from a file with a mistake.
32. As the CNO, I want a row for a skill a nurse already holds to set its expiry, so that renewals come in bulk too.
33. As the CNO, I want the same encodings, size and row limits, and the same preview-then-confirm with the file sent again, as the nurse import, so that one way of importing is learned.
34. As the CNO, I want the nurse import template unchanged, so that a file made for it last month still works.
35. As the CNO, I want the staff list unchanged, with no skills in it, so that nothing more about a person leaves the system in a file.
36. As the System Admin, I want a confirmed skills import in the audit log as who imported and how many rows, nothing from the file, so that the event is recorded without its contents.

### Skill needs (Unit Manager, CNO, Deputy CNO)

37. As a Unit Manager, I want to add a skill need to my unit rules: a shift my unit works, a skill, a weekday minimum and a weekend minimum, so that the solver staffs that shift with that skill.
38. As a Unit Manager, I want several skill needs, including two on one shift for two skills, so that a shift may need an ICU-certified nurse and a preceptor both.
39. As a Unit Manager, I want a skill need refused when it names a shift my unit does not work or a retired skill, so that the solver is not handed a rule it would refuse.
40. As a Unit Manager, I want a skill need to count nurses on exactly its shift that day, so that it works as headcount's anchor shift does.
41. As a Unit Manager, I want one flag making my skill needs hard or soft, hard by default, so that a need I write down is kept unless I choose to pay for it instead.
42. As a Unit Manager, I want to read the skill shortfall weight the CNO set, so that I know the price when my needs are soft.
43. As a Unit Manager, I want dropping a shift from my unit refused while a skill need names it, as it is while a pin uses it, so that no rule points at nothing; I take the need out first.
44. As the CNO, I want the skill shortfall weight among the hospital weights, so that the price of a short skill is the hospital's, as night rest's is.
45. As the CNO or Deputy CNO, I want to read every unit's skill needs with the other unit rules, so that I can judge a roster against them.
46. As the System Admin, I want unit rule changes to skill needs in the audit log with their values, as other unit rules are, so that they say nothing about a person.
47. As a Unit Manager, I want my seeded unit rules to carry no skill needs and the flag at hard, so that a new unit rosters as before until I write a need.

### Solving (Unit Manager)

48. As a Unit Manager, I want every solve of my unit to take my skill needs and my nurses' skills with them, so that the roster meets the needs or pays for each nurse short.
49. As a Unit Manager, I want the solver to keep a nurse off every shift from the day after a required skill of hers expired, so that nobody with a lapsed licence is rostered.
50. As a Unit Manager, I want such a nurse's hours still owed and what her remaining days cannot hold carried over as debt, so that the roster does not credit time the hospital may not pay; I record leave if it does.
51. As a Unit Manager, I want a nurse with no record of a required skill rostered as before, so that marking a skill required does not empty my unit on the day the mark is set.
52. As a Unit Manager, I want an expiry inside the month to count on the days before it and not after, so that a nurse is used while her certificate is valid.
53. As a Unit Manager, I want the precheck to tell me before a solve when a skill need cannot be met (no nurse of mine holds the skill, too few can work the shift, too few for the days), and when a required skill expires in the month, so that I fix the cause rather than read INFEASIBLE.
54. As a Unit Manager, I want the result's explanation to list skill shortfalls per rule like any soft rule, with the shift, the day and how many short, so that I see what the roster paid.
55. As a Unit Manager, I want a hard skill need broken, or a shift on a barred day, reported as a violation like any hard rule, so that the result is read the same way as today.
56. As a Unit Manager, I want the draft check as I edit to name a skill need I break or a barred day I fill, so that a hand edit is judged as the solver judges.
57. As a Unit Manager, I want a draft warned that skills changed since its solve (a skill recorded, renewed, removed or expired, or a need changed), as it is warned for gender or leave, so that I know to solve again.
58. As a Unit Manager, I want a stored result still explained after this change, so that my history is not lost.
59. As a Unit Manager, I want restoring an older result to work as before, checked again on the month as it stands, so that a result from before skills existed is still usable.
60. As a Unit Manager, I want a re-plan to honour skills on the days it plans and treat the earlier days as facts, so that what was worked is not rewritten.

### Rosters in force (Unit Manager, approvers, nurses)

61. As a Unit Manager, I want nothing on an approved roster rewritten when an expiry passes or the CNO corrects a skill, so that a correction cannot change a roster unseen.
62. As a Unit Manager, I want the Roster page to show the skill rule an approved roster now breaks, as it shows a hand edit that breaks one, so that I see where to act.
63. As a Unit Manager, I want to edit or re-plan the roster in force to mend it, so that the fix is mine and recorded as a version.
64. As the CNO or Deputy CNO, I want a submitted roster checked for skills at approval as for every other rule, so that one broken by a skill change while it waited is refused with the reason.
65. As a Unit Manager, I want submit refused when the draft breaks a hard skill need or fills a barred day on the month as it stands, as for any hard rule, so that no such roster reaches the approvers.
66. As a Staff Nurse, I want My roster unchanged in what it shows of colleagues, so that I learn nothing of their skills from it.

### Pins, requests and swaps

67. As a Unit Manager, I want a pin on a day a nurse may not work set aside, not removed, as a pin on a leave day is, so that it counts again if her skill is renewed.
68. As a Staff Nurse, I want a shift request for a day I may not work refused as I make it, with my own reason said in full, so that I do not ask for what cannot be given.
69. As a Staff Nurse, I want a swap refused on a colleague's expired required skill to read "This swap cannot work for <name> on <date>", so that I learn nothing of her records.
70. As a Staff Nurse, I want a swap leaving a skill need short to read only that the day's shifts would break the unit's rules, as team leader and gender read, so that no rule or count about others reaches me.
71. As a Staff Nurse, I want my own expired skill said in full when it refuses my swap, so that I know what to renew.
72. As a Unit Manager, I want every swap reason in full, skills included, so that I judge the swap as I judge an edit.
73. As a Unit Manager, I want a swap's approval refused when a skill change since made it break a hard rule, so that the roster in force is not broken by a stale proposal.

### Expiries (CNO, Deputy CNO, Unit Manager)

74. As the CNO, I want an expiries page listing every skill expired or expiring within 90 days, with the nurse, her unit, the skill and the date, so that renewals are chased in time.
75. As the CNO, I want every nurse with no record of a required skill listed there too, so that the gaps that a required mark exposes are filled.
76. As the CNO, I want the list to leave out deactivated nurses and those past their end date, so that it shows only what the roster can touch.
77. As the CNO, I want my home to show how many entries the expiries page has, beside the units with no manager, so that I see at a glance whether anything waits.
78. As the Deputy CNO, I want to read the expiries page for every unit, so that I know the hospital's standing before I approve a roster.
79. As a Unit Manager, I want the same list for my own unit on my nurses page, so that I know whose certificates are about to lapse before I solve.
80. As the CNO, I want the horizon fixed at 90 days, so that there is one meaning of "expiring" across the hospital.
81. As any user, I want no bell notification for an expiry, so that the bell is not drowned; the page is the reminder, and a nurse reads her own dates on My month.

### Month close

82. As a Unit Manager, I want the close to report a shift worked on a barred day or a skill need the month left short as a fact that broke a rule, never to refuse it, so that what happened is recorded as it happened.
83. As a Unit Manager, I want a month closed before this change re-closed exactly as before, so that the carry-over chain is not disturbed.

## Implementation Decisions

### Solver (the vendored package)

- Two rules enter the rule registry (ADR 0010). **Skill need**: level hard or soft by a new department flag (as night rest's), weight field `skill_shortfall` in the hospital weights, unit "nurse short of a skill need on a shift-day"; enabled when the department has any skill need. **Skill expired** (the bar): hard, unit "shift on a day a required skill has expired"; enabled when any nurse carries an expired required skill in the month. The model adds the constraints or penalty terms, the validator the matches, exactly when the registry says the rule is active, as for every other rule, so model, validator, explain and the tests stay in step.
- The skill need counts nurses on exactly its shift on each free day, against the weekday or weekend minimum, as a headcount anchor does; the shortfall is a non-negative integer per shift-day (the minimum minus those holding the skill, floored at zero) and the penalty is the weight per nurse short. Hard: the count must reach the minimum. Elapsed days are facts, reported apart as every rule's are.
- The bar: on each day after an expired required skill's last day, the nurse's shift variables are fixed off. `max_hours` excludes barred days so that the hours her remaining days cannot hold are unreachable, exempt from the avoidable-shortfall floor and carried over as debt, the existing mechanism. Precheck treats barred days like leave in its per-nurse and per-day capacity sums.
- Department block gains `skill_needs` (list of shift, skill, weekday_min, weekend_min) and `skill_needs_hard`; the general block gains `required_skills` (the catalogue's required-to-work skill names) and `weights.skill_shortfall`. Nurse block gains `skills`: a map of skill name to expiry date or null (held all month or non-expiring). A skill expired before the month is sent with its past expiry; absence means no record (ADR 0010). The expiry is the one dated field the loader accepts before the month; a date after the month is refused, since the app sends null there.
- Request version 2. The loader reads version 1 as version 2 with no skills, no needs, the flag at hard, no required skills and the weight at zero; the result keeps its version. The solve input the app writes is version 2 only. Contract tests cover both versions.
- Precheck gains: a skill need naming a skill no nurse in the month holds (valid on any free day), a need whose minimum exceeds the nurses who hold the skill and may work the shift, per free day the same against those not on leave or barred, and per nurse each required skill expiring inside the month with its last day.
- Explain and validate words name the rule, the shift, the day and the count short, in the solver's words that the app turns into dates as today.
- Renamed skills: the app carries a rename through stored inputs when it reads them, as it carries shift renames (a map of old to current names applied on read), so the solver needs no `renamed_skills`; a stored input keeps the names it was given.

### Backend

- Hospital app: a `Skill` catalogue row (name unique in any case of letters, `expires`, `required_to_work`, `active`), never deleted, with a rename log as shifts have; the hospital rules' weights gain `skill_shortfall` (default 0, which switches the price off until the CNO sets one; a unit's hard flag needs no weight). The catalogue API follows the leave types' and shifts' shape: list for every signed-in role, create and update for the CNO, retire by the active flag. Refusals: retiring while a live unit's skill need names it (naming the units); turning `expires` on while any nurse's record lacks an expiry (naming the nurses); a name already taken.
- Nurses app: a `NurseSkill` row (nurse, skill, expiry nullable, recorded by and when, removed by and when), at most one current row a nurse and skill, ended rather than rewritten as leave is. The CNO sets and corrects them on the nurse's row in the Nurses page; the unit manager (own unit and a nurse due to join) and the Deputy CNO read them. The nurse's own month endpoint returns her skills with expiries. Audit: `nurse.skills_changed` with whose and by whom only.
- Skills CSV: template, preview and confirm beside the nurse import, same encodings, limits, token and re-judging on confirm, same in-memory handling; columns Hospital ID, Skill, Expiry (ISO date, empty for a non-expiring skill). Confirm writes under the nurses' row locks and audits who and how many rows.
- Units app: the unit rules' JSON gains `skill_needs` and `skill_needs_hard` (seeded empty and true); the schema validator refuses a need naming a shift outside the unit's shifts or a retired skill, and the shift-drop guard refuses dropping a shift a need names. A skill rename is carried through every unit's needs as a shift rename is.
- Solve input assembly: the nurse block gains `skills` as ADR 0010 says (clamped per month: expired before the month sent with its date, valid past the month sent as null, not held absent); the general block gains `required_skills` and the weight; the department block its needs and flag. `changes_since` gains the kind `skills`: a nurse's skills as the month would see them differ from the stored input's, or the needs or required skills differ.
- Pins: a pin on a day a nurse may not work (a required skill of hers expired before it) is set aside with a reason of its own, as a pin on leave or outside her dates is, and counts again when the skill is renewed.
- Requests: a shift request on such a day is refused as made, the nurse's own reason in full.
- Swap judging: the two new rules map to the hidden form: a violation of the bar on a colleague reads "This swap cannot work for <name> on <date>", a skill need short reads the existing "that day's shifts would break the unit's rules"; the proposer's own bar is said in full; the manager reads everything.
- Expiries: one read endpoint, scoped by role (CNO and Deputy CNO all units, a manager his unit), returning expired, expiring within 90 days and no-record-of-a-required-skill rows for nurses active and not past their end date, each with nurse, unit, skill, state and date; the CNO's home data gains the count. No job and no notification.
- Roster in force: no new write. The Roster page's existing "what the grid breaks on the month as it stands" covers an approved roster whose skills changed; a hand edit saves with the warning as today.
- Month close: unchanged in shape; the solver's close input carries skills like any input, and the facts that broke a skill rule are reported as elapsed matches.
- API change: the OpenAPI document and the generated client are regenerated and committed.

### Frontend

- Skill catalogue page for the CNO (read for others), beside Shifts and Leave types, with the two flags and retire.
- Nurses page: the CNO records, renews and removes a nurse's skills on her row; managers and the Deputy CNO read them.
- Skills import page beside the nurse import, same preview-then-confirm flow.
- Unit rules page: a skill needs table (shift, skill, weekday min, weekend min, add and remove) and the hard flag; Hospital rules page: the skill shortfall weight.
- Expiries page for the CNO and Deputy CNO; the same list on the manager's Nurses page; the count on the CNO's home.
- My month: the nurse's own skills with expiries.
- Roster page: the existing check and changes-since displays show the new rule names and the new change kind in the page's words, dates not day indices.

## Testing Decisions

A good test exercises the application as a user or a neighbouring system would, through a boundary that will outlive the
implementation, and asserts on what came out: a response, a stored input, a roster, an audit entry. It never asserts on
which functions were called. Expected values come from an independent source (a worked example, the spec, the solver's
fixture), never recomputed the way the code computes them.

### Seams (agreed with the user, 2026-11-07)

1. **The solver package's own rule suite** and its request contract tests: each new rule in the constraint-verifier style of
   the existing rule tests (a small month where the rule alone decides the roster; hard and soft; elapsed days as facts;
   the bar with and without a record; the hours carried as debt), the precheck lines, the explain words, and the loader
   reading version 1 as "no skills" and version 2 with them, refusing a date after the month and accepting one before it
   only for an expiry. One service contract test on a version 2 input.
2. **The web API over HTTP** with a real PostgreSQL and a signed-in user of each role, the solver scripted at the client's
   boundary as today: the catalogue and its refusals; a nurse's skills and who may set or read them; the skills CSV;
   the expiries endpoint and the home count; skill needs among the unit rules and the shift-drop guard; the solve input
   carrying skills, needs, required skills and the weight, clamped per month; `skills` among a draft's changes since; the
   pin set aside; the request refused; the swap's hidden wording; the audit entries' shape. A few run end to end with the
   real solver in process, as the solve flow tests do now.
3. **Frontend Vitest** through the app test file's `start` and `hold`, for the new pages and the unit rules form, under
   the rules in the local development guide (six parallel runs pass; no waits that prove an absence).

No new Playwright journey: the browser suite's role journeys stay as they are.

### Prior art

The solver's per-rule tests and the request contract tests; the leave types and shift catalogue API tests (including the
retire refusals); the nurse import tests for the CSV; the attributes tests for who may set and read; the solve input tests
for assembly and changes since; the swap judging tests for the hidden wording.

## Out of Scope

- Notifications or email about expiries; a configurable horizon.
- Skills on the nurse import template or the staff list; an export of the expiries page.
- Skill needs counting a shift's `also_counts` shifts, or maximums; a skill need per nurse count other than a minimum.
- Moving team leader or gender into the catalogue.
- Automatic rewriting of a roster in force when a skill expires.
- Crediting a barred day's hours (the manager records leave if the hospital credits it).
- A nurse recording or renewing her own skills; proof documents or attachments.
- Any change to the browser (Playwright) suite beyond keeping it green.

## Further Notes

- ADR 0002 permits the solver change: it froze the original repository, not the package. ADR 0010 records the choice to
  read version 1 inputs, a deliberate departure from the solver's earlier refusal of older schemas.
- The nurse's skills are not "rostering attributes" in the glossary's sense (those are the manager's to set); the glossary's
  Nurse profile entry names them apart, and the nurse's reading of them is the second exception beside allowed shifts.
- A precedent followed throughout: unknown rostering data blocks (a catalogue change that would leave records dateless is
  refused); known data is modelled (an expiry in the month is a precheck warning, never a block).
