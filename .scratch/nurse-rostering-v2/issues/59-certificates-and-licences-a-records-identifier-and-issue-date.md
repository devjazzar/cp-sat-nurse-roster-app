# 59: A record's identifier and issue date, and who reads them

**What to build:** The CNO records a certificate or a licence on a nurse with its identifier and its issue date beside its expiry, on the Nurses page as today. The identifier is required on a licence and optional on a certificate or a skill; it is unique among the current records of one catalogue entry, refused naming the other nurse, and the same identifier is allowed on two entries and on an ended record. The issue date is refused when after the expiry or in the future, and nothing reads it. A renewal may set a new identifier and issue date with the new expiry, carrying forward what it does not name; a renewal or a removal still ends the old row. The CNO, the Deputy CNO and the nurse herself (My month) read kind, name, issuing body, identifier, issue date and expiry; a unit manager's reads and the expiries list carry kind, name and expiry and no identifier or issue date. Every table of a nurse's records groups its rows under Skills, Certificates and Licences; the expiries page gains a Kind column and nothing else. Identifiers reach no file, no notification and no audit detail; `nurse.skills_changed` stays whose and by whom. The solve input is unchanged. Spec: `.scratch/nurse-rostering-v2/specs/certificates-and-licences.md`; the words: `GLOSSARY.md` (Identifier, Certificate, Licence).

**Blocked by:** 58 Certificates and licences: the catalogue's kind and issuing body

**Status:** ready-for-agent

- [x] The nurse's skill record gains `identifier` (free text, at most 100 characters, trimmed, nullable) and `issue_date` (nullable); a migration adds them and a partial unique constraint on (skill, identifier) over current rows with an identifier
- [x] Record and renew take both fields; the identifier is required when the entry is a licence; an identifier another nurse's current record of the same entry holds is refused naming her; the same identifier on another entry, or on an ended record, is allowed; the issue date is refused after the expiry or after today on the hospital's clock
- [x] A renewal changes what its body names and carries forward what it does not (identifier, issue date); the ended row keeps what it had
- [x] Ticket 58's kind-change refusal now finds a current record without an identifier and names its nurse
- [x] Row shapes per reader: the CNO's (Nurses page), the Deputy CNO's (Rostering attributes) and the nurse's own (`my-skills`, My month) carry kind, issuing body, identifier and issue date; the unit manager's reads (his nurses and those due to join, on the Nurses page and Rostering attributes) and the expiries list carry kind and no identifier or issue date; the System Admin reads none
- [x] `nurse.skills_changed` is unchanged; the staff list, a roster's CSV, Excel and print page, and every notification carry nothing of it (a before-and-after test on each)
- [x] The solve input, a re-plan's and a close's included, is byte-for-byte what it was for the same month (the four-nurse sample with identifiers and issue dates recorded)
- [x] The Nurses page: Identifier and Issue date columns and fields on the record and renew forms, the identifier marked required when the chosen entry is a licence, refusals beside the field; the records grouped under the three headings; Rostering attributes and My month show the same columns and headings; within the width at 375 px
- [x] The expiries page, and the manager's copy on his Nurses page, gain a Kind column; rows, order, horizon and the home count as ticket 37 left them
- [x] Two at once on real connections: two records of one identifier on one entry, the second refused
- [x] Tests at the agreed seams: the backend API suite (`nurses`, `solves`, the authorization walk) and the frontend's app-level suite (six runs at once); `makemigrations --check` clean; the OpenAPI document and the generated client regenerated
- [x] `docs/ARCHITECTURE.md` section 4's Nurse skill entry carries identifier, issue date and the uniqueness rule; section 3 says who reads identifiers; the security paragraph says they stay off every file and out of the log's detail

**Worth your review, already known:** the unit manager reads no identifier (the spec's decision beyond the grilling); say in the comment if the manager's page would be better with it.

## Comments

**From ticket 58 (2026-11-12).** The catalogue row has `kind` (`Skill.Kind`: `skill`, `certificate`, `licence`) and
`issuing_body`; `SkillSchema` carries both. A change to licence runs its refusal in `update_skill`
(`hospital/catalogue_api.py`) where the comment "Ticket 59 adds the second refusal here" sits: today it is
`_refuse_records_without_expiry(skill, "kind", ", and a licence always expires")`, beside `kind`, naming four at most and then
"and N more". Add the identifier's refusal beside it, also on `kind`. `test_a_change_to_licence_passes_when_every_record_has_its_expiry`
in `hospital/tests/test_skills.py` holds the change to the expiry alone; it should gain a record without an identifier and
be refused. A licence with `expires` off is refused in the API and by the constraint `hospital_skill_a_licence_expires`. For
the grouped tables: `frontend/src/lib/skill-kinds.ts` has `KINDS` (order and headings) and `byKind(rows, kindOf)`; the
Skills page (`routes/_signed-in/skills.tsx`) shows the pattern, a `<tbody aria-labelledby>` per kind whose first row is a
`<th scope="rowgroup">` heading spanning the columns. A nurse's skill row (`NurseSkillRow`) does not carry the kind yet.

**Implemented on 2026-11-12,** on branch `claude/ticket-59-identifier-and-issue-date-ce7e52` (`38cdfae`, `8414baf`, `3a6f4c8`,
`0ce03fc` the code review's fixes, `e71870f` a fix found driving at 375 px, `2ad5b24` a merge of `main` with tickets 52 and 72,
then this comment, then a merge of `main` with ticket 50, which renumbered my migration `0008` and put
the Overtime balance column before Skills on Rostering attributes), from `main` at `d759f0d`. Draft pull request
[devjazzar/cp-sat-nurse-roster-app#27](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/27). Built in this session, as
the brief set out (it overrides `/implement-spec`'s subagent per ticket).

The suites ran locally under the heavy-run lock:
- the backend on a throwaway PostgreSQL 18 container of my own (`nr-t59-pg`), on `0ce03fc`: 3457 passed (`e71870f` and the
  merge change no backend code of mine);
- `makemigrations --check --dry-run`: "No changes detected", before and after each merge;
- after the merge of ticket 50: the touched backend files (`nurses` skills, attributes, two at once, expiries, the import;
  `hospital` skills; `solves` input), 350 passed, and the Vitest blocks of Rostering attributes and the Nurses page's skills;
- the frontend: `npm test` 822 passed on `e71870f`; `npm run build` and `tsc -b` clean, `tsc -b` again after the merge;
- the OpenAPI document and the generated client regenerated, matching the export, before and after the merge;
- the solver untouched. No Playwright file changed. The six parallel frontend runs and the browser suite are GitHub's.

**What the dev stack needs:** a **rebuild** of `web` and `worker` (`docker compose up -d --build`) and the migration
`nurses/0008_identifier_and_issue_date`, which the stack's start runs. No change to `deploy/compose.yaml`, the `Dockerfile`,
the solver or any dependency.

**What was built, criterion by criterion.**
1. **The row.** `NurseSkill` gains `identifier` (at most 100 characters, nullable) and `issue_date` (nullable). Migration `0008`
   (it was `0007` until ticket 50's `0007_opening_overtime_balance` reached `main` first) adds both and the partial unique constraint `nurses_one_current_identifier_a_skill` on (skill, identifier) where the row is
   current and has an identifier. Every step reverses by itself.
2. **Record and renew.** Both bodies take `identifier` and `issue_date`. The identifier is trimmed; an empty one is none; more
   than 100 characters or a NUL is refused beside it. The rules live in one place, `nurses.skills.problems_with`, which the API
   and the import call:
   - a licence without an identifier: "SCFHS is a licence, so it needs its identifier.";
   - another nurse's current record of the same entry with it: "Badr Ali already holds SCFHS with this identifier. Check the
     number: each one is one nurse's." Compared exactly, not case-folded. Her own record, an ended record and another entry
     do not count;
   - "The issue date cannot be after the expiry." and "The issue date cannot be after today." (the hospital's clock).
3. **A renewal** names what changes: `identifier` and `issue_date` may be left out of its body and are then carried from the row
   it ends; null clears one (refused on a licence). The ended row keeps what it had. A renewal that says what is recorded
   changes nothing and logs nothing. Renew is now offered for an entry that does not expire, so a degree's identifier can be
   corrected, and a date kept from when the kind expired is carried through such a correction.
4. **Ticket 58's refusal** of a change to licence now also finds a current record without an identifier, beside `kind`. When
   both halves apply, one message names both, since the page shows one error beside a field. 58's
   `test_a_change_to_licence_passes_when_every_record_has_its_expiry` became
   `test_a_change_to_licence_is_refused_naming_the_nurses_whose_record_has_no_identifier`, which renews the record with an
   identifier and then passes.
5. **Row shapes per reader.** `NurseSkillRow` gains `kind` and `details` (`issuing_body`, `identifier`, `issue_date`).
   `details` is set for the CNO (Nurses page, and her writes' answers), the CNO and the Deputy CNO (Rostering attributes) and
   the nurse herself (`my-skills`), and null for a unit manager everywhere (his Nurses page, Rostering attributes, his writes'
   answers, the password reset's answer). Each caller of `skills_of` / `as_rows` must say `details=`, so none gives them away
   by default. The expiries' rows carry `kind` and nothing more. The System Admin reads none, as before.
6. **Nothing leaves.** `nurse.skills_changed` is unchanged: a test reads the System Admin's log after a record, a renewal with a
   new identifier and a removal, and finds no entry, identifier or date. A before-and-after test in `rosters/tests/test_exports.py`
   takes the roster's CSV, Excel (its cells), the print sheet (the manager's and the CNO's), the staff list and every
   notification row, records a licence and a certificate with identifiers and issue dates on all four nurses, takes them again,
   and finds them equal.
7. **The solve input.** `solves/tests/test_input.py::TestCertificatesAndLicences` builds the four-nurse sample's input, a close's
   (`facts=True`) and a re-plan's, then changes the kinds and issuing bodies and renews every record with an identifier and an
   issue date, and builds them again: byte for byte the same.
8. **The pages.** One component, `RecordsTable` (`components/nurse-skills.tsx`): Name, Expiry, Identifier, Issue date, grouped
   under Skills, Certificates and Licences as ticket 58's row groups.
   - The Nurses page's panel is that table with Renew and Take off on each row. Renew opens a form under the table (Expiry,
     Identifier, Issue date, filled with what is recorded; Save, Cancel; focus back on the row's button). The record form
     gains Identifier and Issue date once an entry is chosen; the identifier is labelled "Identifier" with `aria-required` for
     a licence and "Identifier (optional)" otherwise, as the house marks the optional. The skill select groups its entries by
     kind. API refusals land beside their fields.
   - Rostering attributes: the CNO and the Deputy CNO see the same table in each nurse's Skills cell; a manager sees the list
     as before, grouped under the three headings.
   - My month: the table, under "Skills, certificates and licences".
   - The Nurses page's list keeps a short list in its Skills cell, now grouped, without identifiers.
9. **The expiries page** and the manager's copy gain a Kind column (Skill, Certificate, Licence). Rows, order, horizon and the
   home count are unchanged.
10. **Two at once** (`nurses/tests/test_two_at_once.py`): a record of 21-RN-0412 on Amal stays open; Badr's record of it waits on
    the hospital settings' lock, as every skill write takes it, and is refused naming Amal once the first commits. The database
    constraint stands behind it.
11. **Tests** at the agreed seams: `nurses` (skills, two at once, expiries, the import), `hospital` (the kind change), `solves`
    (the input), `rosters` (files), the authorization walk run unchanged (no role changed), and the app-level suite (the Nurses
    page, Rostering attributes, My month, the expiries page). OpenAPI and client regenerated.
12. **`docs/ARCHITECTURE.md`**: section 3's table (who reads a record's identifier and issue date; the expiries' kind), section
    4's Nurse skill entry (the fields, the uniqueness rule, the carry-forward, the readers), and the security paragraph (off every
    file, every notification and the log's detail).

**What was driven, and how.** My own stack (`e2e/stack.sh up nr-t59`, seeded), headless Chromium through a throwaway Playwright
spec using the suite's `signIn`, at 1280 px and 375 px (deleted after):
- as the CNO: a licence (SCFHS) and a certificate added on the Skills page; SCFHS recorded on Amal, first refused without an
  identifier, then with " 21-RN-0412 " (trimmed) and an issue date; the same number on Badr refused naming Amal; a future issue
  date refused; Badr's renewed to a new expiry with his identifier carried, focus back on Renew; a licence expiring in December
  shown on the expiries page with Kind "Licence" and no identifier; Rostering attributes showing Amal's identifier; the staff
  list without it;
- as the Deputy CNO: Rostering attributes with the identifiers;
- as the unit manager: the Nurses page and Rostering attributes with SCFHS by kind and no identifier, in the page and in
  `/api/nurses`;
- as Amal: My month with her licence under Licences, identifier and issue date;
- at 375 px: the CNO's panel with a renewal open, Rostering attributes, the expiries page and My month, none wider than the
  window, and the renew form's labels inside it.

**What was found, and fixed.** At 375 px the renew form sat in a row spanning the records table, as wide as the table; focus on
its first field scrolled the table sideways and cut its labels off. It now sits under the table (`e71870f`), and the drive
checked its labels are in view.

**What was NOT checked:**
- the six frontend runs at once and the browser suite: GitHub's;
- a screen reader's reading of the row groups and the select's groups: only the accessible names, by testing-library and in the
  browser;
- `better-interface`, `better-writing` and `better-accessibility` were held by hand: the labels and their descriptions, the
  required mark, the row groups' names, the focus after Save and Cancel, no gendered words on the pages;
- a case-insensitive near-duplicate (rn-0412 against RN-0412) is allowed, as the spec says ("compared exactly"), and was not
  driven;
- the dev stack: untouched.

**Decisions taken here:**
- **`details`, one nested object, null for a reader who may not read it,** rather than two schemas or nullable fields at the
  top: null `identifier` then always means "none recorded", never "not yours to read".
- **Record's body requires both keys** (nullable), as `expiry` is and as 58's rule keeps the catalogue's; **the renewal's body
  may leave them out**, the one body where a missing key means "carry it".
- **The renewal form is under the table,** opened by a Renew button on each row, rather than one form per record always open.
- **The import, ahead of ticket 60:** a renewal from a file carries the record's identifier and issue date (it would otherwise
  silently drop a licence's number), a licence the nurse does not hold is a problem on its line ("… Record it on the Nurses page,
  or remove the line."), and a renewal to before the recorded issue date is a problem on the expiry.
- **`SkillKind` moved** beside `Skill` in `hospital/models.py`, since `nurses/skills.py` could not import the catalogue's API.

**Worth your review:**
- **The unit manager reads no identifier or issue date** (the spec's decision beyond the grilling). Built so. I think his page is
  right without them: his reason to read a record is what his skill needs lean on, and the kind and the expiry tell him that; a
  manager who must chase a registration number sends the nurse to the CNO. If he should read them, it is one `details=` at
  two callers and the page's choice follows the API.
- **Rostering attributes for the CNO and the Deputy:** each nurse's records are a small table in the Skills cell, so rows with
  records are several lines tall. The alternative was the short list with the number after each name, which is not the
  spec's "columns". Ticket 61 adds the Deputy's controls to that row and may want a panel as the Nurses page has.
- **The import's guards above,** which run ahead of ticket 60 and which 60 replaces with its columns.
- **My month's card is titled "Skills, certificates and licences"** and its line says the manager sees no identifier or issue
  date.
- **The identifier is accepted on a plain skill too,** as the spec says ("Both may be set on a record of any kind"); the
  glossary's Identifier names certificates and licences.

**Review.** `code-review` against `d759f0d`, both axes in fresh sub-agents.
- **Spec:**
  - fixed: a correction of a non-expiring record dropped its kept expiry (now carried, with a test);
  - fixed: the two refusals of a change to licence did not show together (one message now, with a test);
  - fixed: Rostering attributes chose the table by "not a manager" rather than by what the API gave (now `details` present);
  - noted: the import's guards and the select's groups beyond the ask (decisions above); 375 px unchecked by then (driven since);
    the authorization walk untouched (no role changed; it ran).
- **Standards** (no hard breach):
  - fixed: a long line and an import out of order in `skills_api.py`; `SkillKind` imported from its new home;
  - fixed: the carry-forward spelled three times, now `nurses.skills.carried`; the import's problem mapping now explicit per
    field; `Expiry.kind` typed; `_named` renamed `_who_holds_it_without`; the coined "papers" renamed to the API's "details";
  - kept: the frontend's long lines (the files had 43 before); `(expiry, identifier, issue_date)` travelling together, three
    values not worth a type; `details=` said at each caller, deliberately, so none reveals by default.

**Things later tickets should know.**
- **60:** noted on 60. `problems_with`, `carried` and `record_anew` in `nurses/skills.py`; `RowMeaning.change` still compares the
  expiry alone.
- **61:** noted on 61. `RecordsTable` takes `actions`; the Nurses page's `HeldSkills`, `RenewForm` and `RecordSkillForm` can be
  lifted for the Deputy's row; two lines of page copy still say the CNO alone records.
