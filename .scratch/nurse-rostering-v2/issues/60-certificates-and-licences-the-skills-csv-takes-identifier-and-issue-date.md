# 60: The skills CSV takes Identifier and Issue date

**What to build:** The skills import's file gains two columns, Identifier and Issue date, after Expiry; the template carries the five. A file with last month's three-column header is still read, its two new fields empty on every row, so a licence row in such a file is a problem ("a licence needs its identifier"). The preview names per row, beside the problems it names today: a licence without an identifier, an identifier another nurse's current record of the entry holds, an identifier repeated in the file for one entry on two nurses, an issue date after the expiry or in the future. A row that says what is already recorded, identifier and dates included, is counted unchanged; one that differs in the expiry, the identifier or the issue date is a renewal, ending the old record. Confirm re-judges under the same locks with the same token rule. The nurse import and the staff list are untouched. Spec: `.scratch/nurse-rostering-v2/specs/certificates-and-licences.md`.

**Blocked by:** 59 A record's identifier and issue date, and who reads them

**Status:** ready-for-agent

- [x] The file's columns are Hospital ID, Skill, Expiry, Identifier, Issue date; the template carries them; the three-column header is still accepted with the two fields empty
- [x] Per-row problems: a licence row without an identifier (under either header); an identifier held by another nurse's current record of the entry; an identifier repeated in the file for one entry on two different nurses; an issue date after the row's expiry or in the future; the existing problems unchanged
- [x] A row matching the record in all three fields is unchanged; a difference in any is a renewal through the same rules the API's renewal uses, ending the old row; the preview says which
- [x] Confirm re-judges the file from the start under the hospital settings' then the nurses' locks; the token stands for the new fields too, so a renewal by hand since the preview is a different preview and nothing is saved
- [x] `nurse.skills_imported` unchanged: the number of rows and nothing from the file
- [x] The Import skills page shows the new columns in its preview, grouped as the other tables are, with each problem's words; the nurse import page and the staff list are untouched (a test on each)
- [x] Tests at the agreed seams: the backend API suite beside ticket 36's import tests, and the frontend's app-level suite (six runs at once); the OpenAPI document and the generated client regenerated if the preview's shape changed

## Comments

**From ticket 58 (2026-11-12).** A catalogue entry's kind is `hospital.models.Skill.kind` (`Skill.Kind.LICENCE` for a
licence); the import preview can group by it with `byKind` in `frontend/src/lib/skill-kinds.ts`, as the Skills page does.

**From ticket 59 (2026-11-12).** A record has `identifier` and `issue_date` (`nurses.models.NurseSkill`, migration
`nurses/0007`). The rules a record or a renewal keeps are in one place, `nurses.skills.problems_with(nurse, skill, expiry,
identifier, issue_date)`, which answers `(field, words)` pairs; the API and the import both call it. Writes go through
`nurses.skills.record_anew(..., ending=held)`, which ends the old row. Until your columns exist the import (`_judged` in
`nurses/skills_importing.py`) calls it with the held record's identifier and issue date carried, maps a problem onto the
`skill` or `expiry` column, and so: a renewal carries both fields (`test_a_renewal_from_a_file_carries_the_identifier_and_the_issue_date`);
a licence the nurse does not hold is a problem ("SCFHS is a licence, so it needs its identifier. Record it on the Nurses page,
or remove the line."), which your three-column header rule replaces; and a renewal to before the recorded issue date is a
problem on `expiry`. `RowMeaning.change` still compares the expiry alone: yours compares all three. The uniqueness check
excludes her own current record, so a renewal keeps her number; within a file you must also check the other rows. The
grouped table helper for the preview is `byKind` in `frontend/src/lib/skill-kinds.ts`.

**Implemented on 2026-11-12,** on branch `claude/ticket-60-skills-csv-identifier-0d233e` (`27613cb` the backend, `53315a2` the
page and the regenerated client, `4db0a75` the architecture and ticket 61's note, `7c3937a` the code review's points, `43a28cc`
a fix found driving), from `main` at `fca2e29`. Draft pull request
[devjazzar/cp-sat-nurse-roster-app#28](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/28). Built in this session, as
the brief set out.

The suites ran locally under the heavy-run lock, on `4db0a75`:
- the backend on a throwaway PostgreSQL 18 container of my own (`nr-t60-pg`): 3497 passed;
- `makemigrations --check --dry-run`: "No changes detected" (no migration in this ticket);
- the frontend: `npm test` 825 passed; `npm run build` and `tsc -b` clean;
- the OpenAPI document and the generated client regenerated from the export;
- the solver untouched. No Playwright file changed. The six parallel frontend runs and the browser suite are GitHub's.

After `7c3937a` and `43a28cc` (the review's fixes and two cell widths), I reran `test_skills_import.py` (59 passed), the
"importing" Vitest blocks (37 passed) and `tsc -b`. GitHub's CI was green on `4db0a75` before them.

**What the dev stack needs:** a **rebuild** of `web` and `worker` (`docker compose up -d --build`) for the code. No migration,
no change to `deploy/compose.yaml`, the `Dockerfile`, the solver or any dependency.

**What was built, criterion by criterion.**
1. **The file.** `nurses.skills_importing.COLUMNS` is Hospital ID, Skill, Expiry, Identifier, Issue date, and the template writes
   them. The reader's `Layout` gained `together`: the two last columns are left out together or not at all, so a file of last
   month's three columns is read with both fields empty on every row, and a header of four is refused: "… Identifier and Issue
   date may be left out together. Download the template to start from." The nurse import's header rule and words are unchanged
   (`test_files.py` passes unedited).
2. **Per-row problems**, beside today's, each on its own column (`identifier`, `issue_date`):
   - a licence without an identifier, under either header: "SCFHS is a licence, so it needs its identifier. Enter it in the
     Identifier column, as the template has it.";
   - another nurse's current record of the entry holds it: "Amal Saleh already holds SCFHS with this identifier. Check the
     number: each one is one nurse's." (`problems_with`, ticket 59's; exact, not case-folded; her own and ended records do not
     count; another entry may share it);
   - repeated in the file for one entry on two nurses, on both lines: "Line 6 gives Emad this identifier for BSN too. Check the
     number: each one is one nurse's.";
   - an issue date after the expiry or after today (the hospital's clock): ticket 59's words;
   - a cell the record's rules cannot take: "Enter the identifier as its issuing body gave it, in at most 100 characters." (over
     100, or a NUL) and the date words for a malformed issue date.
   Ticket 59's stopgap guards (a licence sent to the Nurses page; the recorded issue date checked against a renewal's expiry)
   are gone: the file now says both fields.
3. **Meaning.** A row says the whole record, an empty cell being none. `RowMeaning.change` compares the counted expiry, the
   identifier and the issue date; equal is unchanged, any difference a renewal through `record_anew(..., ending=held)`, which
   ends the old row as the API's does. A kind that no longer expires keeps its recorded date (`kept_expiry`, as `renew_skill`).
   The preview's rows carry `kind`, `identifier`, `issue_date`, `held_identifier` and `held_issue_date` beside `held_expiry`.
4. **Confirm** re-judges the file from the start under the hospital settings' then the nurses' locks, as before; the token now
   also stands for each row's identifier, issue date and the entry's kind. A renewal of the identifier by hand since the preview
   is a 409 and nothing is saved (tested).
5. **`nurse.skills_imported`** unchanged: actor and `{"count": n}`, nothing from the file (tested with identifiers in the file).
6. **The Import skills page**: Identifier and Issue date columns; the lines grouped under Skills, Certificates and Licences as
   ticket 58's row groups, and last "Other lines" for lines whose skill is no catalogue entry or cannot be read; each problem
   after its column's name ("Identifier: …", "Issue date: …"); the Change cell says what a renewal changes ("Renewal, identifier
   was 21-RN-0412", "Renewal, was until 31 Dec 2026, issue date was 1 Nov 2024", "no issue date before"); column notes for the two
   new columns. The nurse import's template and the staff list are untouched (`test_the_nurse_import_template_names_no_skill`,
   `test_the_staff_list_holds_no_skills`, both run).
7. **Tests**: 22 new or rewritten in `backend/nurses/tests/test_skills_import.py` (the headers, every problem, unchanged against
   each kind of renewal, the token, confirm, the audit), and three in the app-level "importing skills" block. OpenAPI and the
   client regenerated (`SkillImportRow` gained six fields).

Also: `docs/ARCHITECTURE.md` section 8's skills CSV paragraph. `nurses.skills.Identifier` moved from `skills_api.py` so the
import parses a cell as the API parses a body.

**What was driven, and how.** My own stack (`e2e/stack.sh up nr-t60`, seeded), headless Chromium through a throwaway Playwright
spec using the suite's `signIn`, deleted after; the stack taken down. As Carla, at 1280 px and 375 px:
- SCFHS (a licence) and BSN (a certificate) added through the API; SCFHS recorded on Amal (21-RN-0412) and BSN on Badr (KSU-7);
- the template: the five quoted columns;
- a five-column file of six problem lines: Amal's number on Badr, Dana's licence without one, an issue date after today, KSU-9 on
  Dana and Emad (both lines), and an unknown skill under "Other lines", each beside its column, grouped;
- last month's three-column file with Amal's SCFHS: the licence's problem;
- a good file: Amal's identifier alone renewed ("Renewal, identifier was 21-RN-0412"), Badr's BSN already recorded, Dana's SCFHS
  new with " 21-RN-0500 " trimmed; saved, "1 skill recorded and 1 skill renewed."; `/api/nurses` then read 21-RN-0413 and
  21-RN-0500; the staff list held no identifier;
- at 375 px the page no wider than the window, the table scrolling inside its region.

**What was found, and fixed.** In the crowded problems table, short skill names and identifiers broke mid-word ("SCF HS",
"21-RN-/0412"); the Skill and Identifier cells now keep a minimum width (`43a28cc`).

**What was NOT checked:**
- `43a28cc`'s widths were not driven again, only typechecked and tested;
- the six frontend runs at once and the browser suite: GitHub's;
- a screen reader's reading of the row groups: only their accessible names, by testing-library;
- `better-interface`, `better-writing` and `better-accessibility` held by hand: the column notes, the problems' words, the row
  groups' names, no gendered words added to the page (the "her record" in the Skill note follows the house's way of naming a
  nurse);
- a file with an identifier in another script (Arabic) was not tried; the cell is kept as the API keeps it;
- the dev stack: untouched.

**Decisions taken here:**
- **A blank cell is none, under either header** (below, the first point for your review).
- **A header of four columns is refused:** the spec names five and three.
- **An identifier another line of the file would free is still refused**, whatever the order: the file is judged against the
  records as they stand, as two renewals by hand would be, and a swap inside one file could otherwise meet the database's partial
  unique constraint mid-save as a 500.
- **"Other lines"** heads the lines that have no kind, so a problem line is never dropped by the grouping.
- **The licence's words name the column and the template**, one wording for both headers, since a line does not know its header.

**Worth your review:**
- **A blank Identifier or Issue date cell takes off the one recorded.** The file says the whole record, which is the only reading
  that agrees with "a licence row under the old header is a problem". The consequence: re-importing last month's three-column
  file renews every certificate and skill that has an identifier or issue date and takes both off; the preview says so on each
  line ("Renewal, identifier was KSU-7"), and nothing is saved until Save. The alternative (blank carries, as the API's renewal
  body carries a key left out) would make an old file harmless; it needs `read_file` to say which header it read, since a line
  does not carry it, and a blank could then never clear a field from a file.
- **How the preview shows a renewal of the identifier alone:** "Renewal, identifier was 21-RN-0412", with the new number in the
  Identifier column; each changed field is named, the expiry as before ("was until …").
- **The problems' words**, quoted under criterion 2, notably "Line 6 gives Emad this identifier for BSN too." for the in-file
  duplicate.
- **"Other lines"** as the last group's heading.

**Review.** `code-review` against `fca2e29`, both axes in fresh sub-agents.
- **Spec** (nothing missing):
  - noted: blank cells clear rather than carry (Worth your review above);
  - fixed: the in-file duplicate compared the written hospital ID in lower case against the parsed one; it now compares the
    parsed one on both sides (`7c3937a`);
  - noted: a swap inside one file refused (a decision above).
- **Standards** (no hard breach):
  - fixed: the column count kept by hand (`COLUMN_COUNT = 8`) now comes from one list of the columns;
  - fixed: `renewalWords`' three fields through one rule;
  - fixed: the template test claimed exact columns and checked a prefix; one test now holds the exact five;
  - kept: `_no_nul` in `nurses/skills.py` copies `hospital.catalogue_api.no_nul`, because importing that module from there is a
    circular import (tried; `rosters.drafts` fails);
  - kept: the row-group heading markup now in two components beside the Skills page's; a shared component is a change to three
    pages for later;
  - kept: (expiry, identifier, issue date) travelling together, as ticket 59 kept them; `Row.kind: Skill.Kind` (the API's
    `SkillKind` is the same enum); the identifier parsed twice per line, which is cheap.

**Things later tickets should know.**
- **61:** noted on 61. The import is the CNO's alone in four places (`auth=cno` and `cno_for_files`, the `Role.CNO` re-check in
  `_save_skills`, `onlyFor(Role.cno)`, and the role tests); the preview's `held_identifier` and `held_issue_date` are fine for the
  Deputy, who reads them.
