# Certificates and licences: kinds of skill, with an identifier and an issue date

Status: ready-for-agent
Type: feature
Published: 2026-11-09 by /to-spec
Decided: the grilling of 2026-11-09 (19 questions, three rounds, every recommendation taken), recorded in `GLOSSARY.md`
(Skill widened, Certificate, Licence, Identifier, Deputy CNO, CNO, Nurse profile). No ADR: nothing here is hard to reverse.
The decisions and the facts they rest on are in the main session's notes as `grill-8-certificates-licences.md`; the
research on how UKG, RLDatix, symplr, HealthStream, Medallion, Verifiable and SCFHS itself model credentials is beside it
as `research-credentials-competitors.md`.

Vocabulary: `GLOSSARY.md`. Decisions and their reasons: `docs/ARCHITECTURE.md` and `docs/adr/`. Where this spec and those
documents disagree, the documents win and this spec is wrong.

## Problem Statement

The hospital must know, for every nurse, that she holds the papers that let her work: her Saudi Commission for Health
Specialties registration, renewed every two years, and the degree her title rests on. Today the skill catalogue holds
abilities and course cards (BLS, ICU) and can already mark one *required to work* and give it an expiry; the solver keeps a
nurse off every shift from the day after a required skill lapses. But a licence has a **number**, which the CNO is asked for
by auditors and by the Commission, and an **issue date**; a degree is held for good and has a certificate number of its own;
and neither has a place in the application, so the CNO keeps them in a spreadsheet beside the app, where nothing reminds
her that a registration ends in sixty days. The Deputy CNO, who in practice keeps these records with the CNO, may read a
nurse's skills but record none.

## Solution

The skill catalogue gains a **kind** per entry: a *skill* (the plain kind: an ability, BLS), a *certificate* (a degree, a
diploma, a course certificate) or a *licence* (the SCFHS registration), and names the **body that issues it**. A nurse's
record of a certificate or licence carries its **identifier** and its **issue date** beside the expiry it already has; the
identifier is required on a licence and unique among one entry's current records, so a number typed onto the wrong nurse is
caught. A licence always expires; the other marks (required to work, lets a nurse precept) and the skill needs stay free for
every kind. Nothing changes in the solver: a required licence reaches it as one more required skill, and a lapse bars her as
a lapsed skill does. The **Deputy CNO records** what a nurse holds beside the CNO, on the Rostering attributes page where
the Deputy already reads it, and reaches the skills import; the catalogue itself stays the CNO's. Every table that lists
skills (the catalogue, a nurse's row, the expiries page, My month, the import preview) groups them under three headings.
The paper or PDF stays in HR's files: the application keeps no document, and the record is the record.

## User Stories

### The catalogue (CNO)

1. As the CNO, I want each catalogue entry to be a skill, a certificate or a licence, so that the hospital's licences and
   degrees are kept in the one catalogue beside its skills and read by the same rules.
2. As the CNO, I want the catalogue page to show its entries under three headings, Skills, Certificates and Licences, so
   that the page reads as the three things they are.
3. As the CNO, I want to name the body that issues an entry (the Saudi Commission for Health Specialties, a university),
   so that a record says where its number comes from.
4. As the CNO, I want a licence to always expire, so that no registration can be recorded without the day it ends.
5. As the CNO, I want a certificate and a skill to expire or not as I choose, so that a BLS card expires and a degree does
   not.
6. As the CNO, I want required to work, lets a nurse precept and the skill needs free for every kind, so that a licence
   bars a nurse when it lapses and a degree is required on file, with the marks I already know.
7. As the CNO, I want a bachelor's, a master's and a PhD to be three entries, so that the hospital names exactly what it
   requires and nothing orders them.
8. As the CNO, I want to change an entry's kind, so that a card I filed as a skill becomes the certificate it is.
9. As the CNO, I want a change to the licence kind refused, naming the nurses, while a current record of the entry lacks
   an identifier or an expiry, so that no licence record is left half recorded.
10. As the CNO, I want every existing entry to be a skill after the change, with no issuing body, so that nothing I
    recorded changes meaning.
11. As the CNO, I want a catalogue change audited with its values, kind and issuing body included, so that the log says
    who changed what, since an entry names no one.
12. As any signed-in user, I want to read the catalogue with its kinds and issuing bodies, so that the names I meet on my
    pages are explained; it names no one.

### A nurse's records (CNO, Deputy CNO)

13. As the CNO, I want to record a certificate or a licence on a nurse with its identifier and its issue date beside its
    expiry, so that the number the Commission and the auditors ask for is in the application.
14. As the CNO, I want the identifier required on a licence and optional on a certificate or a skill, so that a licence is
    never recorded without its number and a course card needs none.
15. As the CNO, I want an identifier refused, naming the other nurse, when another current record of the same entry holds
    it, so that one nurse's number typed onto another's record is caught.
16. As the CNO, I want the same identifier allowed on two different entries, so that a body that numbers two documents
    alike does not block a record.
17. As the CNO, I want an issue date refused when it is after the expiry or in the future, so that a slip is caught before
    anything is saved.
18. As the CNO, I want the issue date to be informational, read by nothing, so that recording it wrongly never moves a
    roster; the expiry is what the roster reads.
19. As the CNO, I want a renewal to set a new expiry and, in the same act, a new issue date and a new identifier when the
    body gave one, so that a renewed registration is recorded as it was renewed.
20. As the CNO, I want a renewal or a removal to end the old record rather than rewrite it, as today, so that what was
    there stays on record.
21. As the CNO, I want a nurse's certificates and licences to follow her across a transfer and stay when she is deactivated
    or ends, so that a fact about the person is recorded once.
22. As the Deputy CNO, I want to record, renew and take off a nurse's skills, certificates and licences on her row of the
    Rostering attributes page, where I already read them, so that the two of us keep the records.
23. As the Deputy CNO, I want the skills import beside the CNO, so that a bulk renewal is not the CNO's alone.
24. As the Deputy CNO, I want no catalogue access beyond reading it, so that recording what a nurse holds does not make me
    the keeper of the catalogue.
25. As the CNO, I want the Deputy's changes audited as mine are, whose record and by whom, so that the log shows whose
    hand it was.

### Who reads what

26. As the CNO or the Deputy CNO, I want a nurse's records grouped under Skills, Certificates and Licences with the
    identifier and the issue date beside each, so that a licence number is one glance away.
27. As a Staff Nurse, I want to read my own certificates and licences on My month with their identifiers, issue dates and
    expiries, so that I know my registration number and when to renew.
28. As a Unit Manager with a nurse profile, I want to read my own the same way, so that I too know what to renew.
29. As a Unit Manager, I want to read my nurses' skills, certificates and licences by kind, name and expiry, and no
    identifier or issue date, so that I know what my skill needs can lean on and nothing more of a person's papers.
30. As a Staff Nurse, I want to read nothing of a colleague's certificates and licences, so that her records stay hers.
31. As the System Admin, I want to read none of it, so that the role stays technical.
32. As the CNO, I want identifiers, issue dates and expiries kept off the staff list, every roster file, every print page
    and every notification, so that nothing more about a person leaves the system.
33. As the System Admin, I want a change to a nurse's records in the audit log as whose changed and by whom only, never
    which entry, which number or which date, so that I cannot learn that someone let a licence lapse.

### The expiries page

34. As the CNO or the Deputy CNO, I want the expiries page to list expired and expiring licences and certificates beside
    skills, each row with its kind, so that a registration ending in sixty days is seen in time.
35. As the CNO, I want a nurse with no record of a required degree listed as a gap, nobody barred, so that a missing paper is
    chased and no roster is touched for it.
36. As the CNO, I want the horizon to stay 90 days for every kind, so that "expiring" means one thing across the hospital;
    the Commission's renewal window opens about three months before the end.
37. As the CNO, I want the home count unchanged in meaning, so that it still says how many rows the page has.
38. As a Unit Manager, I want my own unit's list to show the kind too, so that I know whether a lapse is a card or a
    licence.
39. As any user, I want no bell or push for an expiring licence, so that ticket 37's decision holds: the page is the
    reminder.

### The import

40. As the CNO, I want the skills CSV to take Identifier and Issue date as two more columns, so that a licence list comes in
    bulk with its numbers.
41. As the CNO, I want a row for a licence refused without an identifier, named per row in the preview, so that a licence is
    never imported half recorded.
42. As the CNO, I want a file with last month's three-column header still read, so that an old file works; a licence row in
    such a file is a problem, since it has nowhere to put its number.
43. As the CNO, I want the identifier's uniqueness judged in the preview, against the records and against the other rows of
    the file, so that nothing is saved from a file with a duplicated number.
44. As the CNO, I want a row that says what is already recorded, number and dates included, counted unchanged, so that a
    full re-import is harmless.
45. As the CNO, I want the template to carry the five columns, so that a new file is right the first time.
46. As the CNO, I want the nurse import template and the staff list unchanged, so that nothing else learns of skills.

### The roster

47. As a Unit Manager, I want a lapsed licence to bar a nurse as a lapsed required skill does, from the day after, so that
    nobody with a lapsed registration is rostered; nothing in the solver changes.
48. As a Unit Manager, I want a skill need free to count any kind, so that a shift may need two ICU-certified nurses or, if
    the hospital wants it, two licensed specialists.
49. As anyone re-solving or closing an old month, I want every stored solve input and close input to give what it gave, so
    that the kinds are the catalogue's business and the solver's input is unchanged.

### Phones and access

50. As the CNO on a phone, I want the three headings and the new columns to keep within the width, so that the Nurses page
    stays usable where it was.
51. As a screen reader user, I want each heading to name its group and each control to name the entry it acts on, so that I
    record the right thing.

## Implementation Decisions

### The catalogue

- The catalogue entry gains **kind** (`skill`, `certificate`, `licence`) and **issuing body** (free text, at most 100
  characters, may be empty). Every existing entry becomes kind `skill` with no issuing body, by migration. The CNO sets
  both on the Skills page as the other marks are set; every signed-in role reads them in the catalogue's list.
- **A licence always expires:** the API refuses a licence with `expires` off, and the page fixes the flag on and disables it
  while the kind is licence. The other marks, and whether a skill need may name the entry, are unchanged for every kind.
- **A kind change** is one more edit of the entry. Changing to licence runs two refusals, each naming the nurses: the
  existing one for current records without an expiry (since licence turns `expires` on), and a new one for current records
  without an identifier. Changing away from licence is free. A kind change is audited as any catalogue change, with the
  values; the entries `skill.created` and `skill.changed` carry kind and issuing body.
- The rename log, the retire rules, the "lets a nurse precept" mark (ticket 53) and the skill needs are untouched: a
  rename, a retirement and a need treat every kind alike.
- **The catalogue stays the CNO's to write.** The Deputy CNO's widening (below) is to what a nurse holds, never to the
  catalogue: `createSkill` and `updateSkill` keep their roles.

### A nurse's record

- The nurse's skill record gains **identifier** (free text, at most 100 characters, trimmed, may be null) and **issue date**
  (a date, may be null). Both may be set on a record of any kind; the identifier is **required on a licence** and refused
  with the field's error when missing. The issue date is refused when after the expiry or after today on the hospital's
  clock. Nothing reads the issue date.
- **The identifier is unique among the current records of one catalogue entry**, compared exactly after trimming (not
  case-folded): a record or a renewal that would repeat another nurse's current identifier on the same entry is refused,
  naming that nurse. Ended records do not count, and the same identifier on two different entries is allowed. A partial
  unique constraint holds it in the database beside the check in the API, so two writes at once cannot both pass.
- **Recording, renewing and removing** stay the three acts they are, ending a row rather than rewriting it. A renewal takes
  the new expiry and may take a new identifier and a new issue date in the same body; what it does not name is carried from
  the record it ends. The "record and renew through the same rules" promise of the CSV holds for the new fields.
- The audit entry `nurse.skills_changed` is unchanged: whose record and by whom, never the entry, the identifier or a date.
- The record stays on the profile, so a transfer carries it and a deactivation or an end date keeps it, as today.

### Who writes and who reads

- **The Deputy CNO records.** The three nurse-record endpoints (record, renew, remove) and the two skills-import endpoints
  (preview, confirm) and its template take the CNO and the Deputy CNO; the authorization walk names them so. The Deputy's
  entries carry the Deputy as actor. The locks are those every skill write takes: the hospital settings' then the nurse's.
- **Where the Deputy works:** the record, renew and remove controls appear on the nurse's row of the Rostering attributes
  page for the Deputy CNO (the page already lists every unit's nurses and their skills for that role), and the Import
  skills page is linked beside it. The CNO's controls stay on the Nurses page. The Deputy does not gain the Nurses page.
- **The row shape readers get:** the CNO, the Deputy CNO and the nurse herself (My month, `my-skills`) read kind, name,
  issuing body, identifier, issue date and expiry. A unit manager's reads (his unit's nurses and those due to join, on the
  Nurses page and Rostering attributes) and the expiries list carry kind, name and expiry and **no identifier or issue
  date**: the manager's reason to read is what his skill needs lean on. This is a decision the spec took beyond the grilling
  (see Further Notes). The System Admin reads none, as today.
- Identifiers, issue dates and expiries reach no file (the staff list, a roster's CSV, Excel or print page), no
  notification and no audit detail. The solve input holds skill names and expiries as before and gains nothing.

### The pages

- **One grouping rule, three headings:** every table that lists catalogue entries or a nurse's records (the Skills page,
  a nurse's row on the Nurses page and on Rostering attributes, My month's skills, the expiries page, the import preview)
  groups its rows under Skills, Certificates and Licences in that order, each heading a row group with its own name, a
  heading left out when it has no rows. Within a group the order is as today.
- **The Skills page** gains a Kind choice and an Issuing body field on its form, with a description in the voice of the
  other marks; the kind forces and disables Expires when licence; the list shows kind and issuing body.
- **A nurse's records** (Nurses page, Rostering attributes, My month) gain Identifier and Issue date columns; the record and
  renew forms gain the two fields, the identifier marked required when the chosen entry is a licence, with the refusals
  beside the field. On a phone the tables keep within the width and scroll inside themselves where they must.
- **The expiries page** gains a Kind column and nothing else; its rows, its order, its 90-day horizon and the home count
  are as ticket 37 left them. The unit manager's copy on his Nurses page gains the same column.
- **The import:** the skills CSV's columns are Hospital ID, Skill, Expiry, Identifier, Issue date. The header check accepts
  the five-column header and the old three-column one; with the old header the two fields are empty for every row, and a
  licence row is then a problem ("a licence needs its identifier"). The preview names per row: a missing identifier on a
  licence, an identifier another nurse's current record of the entry holds, an identifier repeated in the file for the
  same entry on two nurses, an issue date after the expiry or in the future, as it names the existing problems. A row that
  says what is recorded, identifier and dates included, is unchanged; a row that differs in any of the three is a renewal,
  ending the old record. The confirm re-judges under the same locks with the same token rule. The template carries the five
  columns and nothing else. The nurse import and the staff list are untouched.

### Documents

- `docs/ARCHITECTURE.md`: section 3's rows for recording skills name the Deputy CNO and the kinds; section 4's Skill and
  Nurse skill entries carry kind, issuing body, identifier and issue date and the uniqueness rule; the roles paragraph says
  the Deputy CNO writes nurses' records and nothing else about a nurse; section 8's screens name the Deputy's controls and
  the headings; the security paragraph says identifiers stay off every file and out of the log's detail. `GLOSSARY.md` is
  already written. The OpenAPI document and the generated client are regenerated.

## Testing Decisions

A good test drives a public interface and checks what a user or a caller sees: an endpoint's answer, a page's words by
their accessible names, the rows a write leaves, an audit entry's shape. Expected values come from a worked example, never
from the code that produced them. The seams are the three every v2 feature uses; none is new, and no Playwright journey
is added.

- **Seam 1, the backend API suite** on a throwaway PostgreSQL 18 with the scripted solver:
  - `hospital`: the catalogue's kind and issuing body on create, update and list; a licence with `expires` off refused; a
    change to licence refused naming the nurses for a missing identifier and for a missing expiry, allowed when every
    record has both; a change away from licence free; the migration's effect (every existing row a skill); the audit
    entries' values; every role reading, the CNO alone writing (the authorization walk).
  - `nurses`: a record with identifier and issue date; the identifier required on a licence and optional elsewhere; the
    uniqueness refusal naming the other nurse, the same identifier allowed on two entries and on an ended record; the issue
    date's two refusals; a renewal carrying what it does not name and changing what it does; the Deputy CNO recording,
    renewing and removing with the Deputy as actor; the row shapes per reader (the manager's and the expiries list without
    identifier or issue date; the nurse's own with them); the audit entry still naming nothing; two at once on real
    connections, two records of one identifier on one entry, the second refused.
  - the skills CSV: the five-column and the three-column headers; a licence row without an identifier, under either header;
    a duplicate within the file and against the records; an issue date refused; a row unchanged versus a renewal; the
    Deputy CNO previewing and confirming; the template's columns; the nurse import template and the staff list unchanged.
  - `solves`: the solve input unchanged by kind, issuing body, identifier and issue date (a before-and-after on the
    four-nurse sample); a required licence barring as a required skill does, through the existing tests' pattern.
  - the expiries list's kind column and unchanged rows, horizon and count.
- **Seam 2, the frontend's app-level Vitest suite** (`app.test.tsx` through `start` and `hold`): the Skills page's kind
  and issuing body, the Expires flag forced for a licence, the three headings; the Nurses page's columns and the forms'
  identifier requirement and refusals; the Deputy's controls on Rostering attributes and the import link; My month's
  columns; the expiries page's kind column; the import page's new columns and problems. Ticket 11's rules: no raised
  timeout, no fake timers, no wait that proves something did not happen; six runs at once.
- **Seam 3, the solver's own suite:** nothing changes; it runs as for every ticket and must stay green.
- **Prior art:** `hospital/tests` for the catalogue and its refusals (tickets 32 to 34), `nurses/tests` for skills, the
  attributes reads and the CSV (tickets 33, 36, 37), `accounts/tests/test_authorization.py`, the skills blocks of the
  frontend's app-level suite.

## Out of Scope

- Attachments: a scanned licence, a PDF or any file. The application keeps no files; a backup is a copy of the database and
  a restore would lose them. A feature of its own, with the backup question answered first, if the hospital asks.
- A verification status, method or verifier on a record; primary-source verification against the Commission or DataFlow.
- A notification or push for an expiring licence; a horizon other than 90 days; a horizon per kind.
- A level or ordering between degrees; a classification or professional title field on a licence; a list of issuing bodies.
- CPD hours, renewal steps or anything the Commission asks of a nurse beyond the dates.
- A second catalogue, a second import or a second page for certificates and licences.
- Any change to the solver, its contract or the solve input.
- Identifiers on the staff list or any file that leaves the system; the unit manager reading identifiers.
- Arabic names for the kinds.

## Further Notes

- **Decisions this spec took beyond the grilling**, each the user's to veto: the unit manager's reads and the expiries list
  carry no identifier or issue date (the glossary's Identifier entry names the CNO, the Deputy CNO and the nurse as its
  readers, and the manager's reason to read a skill is his needs); a renewal carries forward the fields it does not name; a
  partial unique constraint in the database beside the API's check; a licence row under the old three-column header is a
  problem rather than a silent skip; the issuing body may be empty.
- **Ticket order.** The catalogue ticket touches the Skills page and its API as open ticket 53 ("lets a nurse precept")
  does, so it runs after 53. The Deputy's controls on the Rostering attributes row share that row with tickets 54 and 55
  (probation), so that ticket runs after 54 at least.
- **The research** (`research-credentials-competitors.md`) found every public vendor schema separating a type catalogue from
  the per-person record with identifier, issue and expiry dates (Verifiable, Medallion, UKG, RLDatix's NMC registration "as
  a skill with Certificate Number, Valid From, Valid To", symplr); degrees non-expiring and verified once; lead times of 30
  to 90 days. SCFHS: registration lasts two years, renewal needs CPD hours and an employer letter, the window opens about
  three months before, nursing has two titles (Nurse Technician, Nurse Specialist), the degree is verified once through
  DataFlow, and no employer-side verification service is public. BLS is an employer requirement, not the Commission's.
- After the tickets land the dev stack needs `docker compose up -d --build` for the two migrations (the catalogue's kind and
  issuing body; the record's identifier and issue date with its constraint). No new dependency is expected.
