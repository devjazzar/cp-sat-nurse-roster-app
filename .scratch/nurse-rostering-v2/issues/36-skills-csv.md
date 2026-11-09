# 36: The skills CSV

**What to build:** The CNO imports skills in bulk from a CSV of hospital ID, skill and expiry, beside the nurse import and in the same way: download a template, preview the file row by row with every problem named, confirm by sending it again. A row for a skill a nurse already holds sets its expiry, so renewals come in bulk. The nurse import template and the staff list are unchanged.

**Blocked by:** 33 A nurse's skills

**Status:** ready-for-agent

- [x] Template, preview and confirm endpoints beside the nurse import's, with the same encodings (UTF-8 or UTF-16 with a byte order mark, others refused), size and row limits, in-memory handling, preview token and re-judging on confirm.
- [x] Problems named per row: an unknown or inactive hospital ID, an unknown or retired skill, a missing or malformed expiry on an expiring kind, a date on a non-expiring kind, a nurse and skill repeated in the file.
- [x] Confirm records new skills and sets the expiry of held ones under the nurses' row locks, in one transaction; nothing is saved when any row has a problem or the file no longer means what was previewed.
- [x] Audit: `nurse.skills_imported` with who and how many rows, nothing from the file; the template is not logged.
- [x] A Skills import page beside the nurse import, same flow; the nurse import template and the staff list columns unchanged.
- [x] The architecture document's import section gains the skills CSV.
- [x] Tests at the web API seam for the template, each problem, a renewal, the token and the audit entry; frontend tests for the page through the app test file.

## Comments

**From ticket 32 (2026-11-09).** A skill's name is any 1 to 100 characters (stripped, no NUL), unlike a shift's code,
which must start with a letter or digit so a spreadsheet does not read it as a formula. A CSV this app writes with skill
names in it (the template's example rows, or an export later) should guard a cell starting with `=`, `+`, `-` or `@`,
or the catalogue should refuse such a name: your call. Matching a file's skill to the catalogue is case-insensitive at most
(the name is unique in any case of letters); a former name (`SkillRename.old_name`) is not a current skill.

**Implemented on 2026-11-09,** on branch `claude/ticket-36-skills-csv-e1504b`, draft pull request
Nurse-Fold/cp-sat-nurse-roster-app#24, from `main` at `3588b1d`. The commits:
- `7f960bd`: the backend, the shared reader and its tests;
- `ac44ad5`: the Skills import page, the shared file form, and the regenerated client;
- `5ff709a`: the architecture document;
- `9c73803`: the review's points;
- `1956118`: the preview's column wording;
- then this comment.

The suites ran locally, one at a time under the heavy-run lock, on a throwaway PostgreSQL 18 container of my own:
- the backend: 2878 passed, on `5ff709a`;
- the frontend: one `npm test` run, 681 passed, and `npm run build` succeeded;
- `makemigrations --check`: "No changes detected";
- the OpenAPI document and the generated client were regenerated from the export.

After `9c73803` and `1956118`, I reran the whole frontend suite (681 passed) and the build, and the backend's `nurses`,
`accounts`, `audit` and `hospital` tests (1706 passed). The rest of the backend is untouched by those commits. GitHub runs the
six parallel frontend runs and the browser checks. No Playwright file changed.

**What the dev stack needs:** a **rebuild** (`docker compose up -d --build`), for the new endpoints and page. There is no
migration, and no change to compose, the `Dockerfile`, the solver or any dependency.

**What was built, criterion by criterion.**
- **The endpoints**, beside the nurse import's, the CNO only:
  - `GET /api/nurses/skills-import/template` (`downloadSkillsImportTemplate`): the header `"Hospital ID","Skill","Expiry"`
    with Excel's byte order mark;
  - `POST /api/nurses/skills-import/preview` (`previewSkillsImport`);
  - `POST /api/nurses/skills-import/confirm` (`confirmSkillsImport`): 200 with counts recorded, renewed and unchanged, or 409
    with the preview as it now stands.

  Preview and confirm answer `no-store`.
- **One reader for both imports.** `nurses.importing.read_file` now takes a `Layout`: the columns, and the words its refusals
  use for a line ("nurses", "skills"). The skills import reads its file through it, so the encodings (UTF-8, or UTF-16 with a
  byte order mark, others refused), 500 lines, 1 MB, the in-memory upload, Excel's padding, the three separators and the
  header in any case are the nurse import's own code. The nurse import's words are unchanged, and `test_files.py` passes
  as it was.
- **The problems, per row, beside their column** (`nurses.skills_importing`):
  - the hospital ID: malformed, the nurse import's words; unknown, "No nurse has this hospital ID. Use the one on the
    Nurses page." (a user with no nurse profile is unknown); deactivated, "Amal Saleh is deactivated. Record their skills on the
    Nurses page, or remove the line.";
  - the skill: unknown, "There is no such skill. Use its name on the Skills page."; retired, "ACLS is retired, so it can no
    longer be recorded or renewed.";
  - the expiry: missing on an expiring kind, "BLS expires. Enter the last day it counts, as YYYY-MM-DD."; malformed, the nurse
    import's date words; on a non-expiring kind, "ICU does not expire, so leave its expiry empty.";
  - a nurse and skill twice, in any case of letters, on both lines: "BLS of Emad is also on line 9. Keep one line for each
    nurse's skill.";
  - a line of the wrong number of cells, once for the line.

  The skill is matched case-insensitively on its current name only, and a former name is no skill. A date already past is
  accepted, as by hand (ticket 33).
- **What a row does.** A skill she does not hold is recorded. One she holds takes the row's expiry, ending the old row as a
  renewal by hand does. One that says what is already recorded changes nothing; that is `renew_skill`'s reading, so a kind that
  no longer expires, held with a kept date, is "already recorded" with no date. The preview says which for every row, and the
  page's column "Change" reads "New", "Renewal, was until 31 Dec 2026" or "Already recorded".
- **Confirm.** One transaction:
  - the CNO checked still active;
  - the hospital settings' lock;
  - the named nurses' rows by key, `of=("self", "user")`, no key;
  - then the file judged again under those locks, and saved only when the token still matches.

  The token stands for each row's nurse, skill (name and `expires`), expiry and the record a renewal would end. So a renewal by
  hand, a rename, a retirement or a deactivation since the preview means nothing is saved, and the answer is 409 with the
  preview as it now stands. Nothing is saved when any row has a problem, whatever token is sent.
- **Audit.** One `nurse.skills_imported` entry: the actor and `{"count": <rows>}`, with no target and nothing from the file.
  The template writes nothing, and neither do a preview or a refused confirm.
- **The page.** Import skills at `/nurses/import-skills`, for the CNO only (a manager is sent home). It is linked from the Nurses
  page as "Import skills from a file", beside "Import nurses from a file" (renamed from "Import from a file", so the two
  read apart). It has the nurse import's flow: the template, the column notes, Check file, only the lines with problems shown
  when there are any, then "4 lines ready to save", "Saving records 1 skill and renews 2 skills…" and "Save 3 skills". A file that
  changes nothing offers no button. A 409 shows "Something changed since the last check…", and an unknown outcome says "It is
  not known whether these skills were saved…".

  The file form, the problem list and their words are shared with the nurse import (`components/csv-import.tsx`). There is no
  password sheet, no leave guard and no slow-request words: this confirm returns no passwords and is quick.
- **Unchanged:** the nurse import's template, and the staff list's columns. A test holds each.
- **Docs.** `docs/ARCHITECTURE.md` section 8 ("Nurse import and the staff list") gains the skills CSV, and the Nurse skill
  entry points there. The audit log page names `nurse.skills_imported` "Imported skills".
- **Tests.**
  - `backend/nurses/tests/test_skills_import.py` (38):
    - the template, and that it is not logged;
    - only the CNO;
    - the preview of a record, a renewal and a no-change;
    - every problem, a deactivated nurse, a retired held skill, a former name, a repeat, a past date, the cell count and a NUL;
    - UTF-16, a refused encoding, the file refusals, the limits and the in-memory upload;
    - confirm records and renews;
    - a kind that no longer expires;
    - a file with a problem, another file, a renewal by hand since, a rename since, and a change caught under the locks;
    - twice, a failure mid-way, and a CNO deactivated;
    - the audit entry's shape, and the preview writing none;
    - the staff list unchanged, and the skills read on the Nurses page.
  - `frontend/src/app.test.tsx`, "importing skills" (10): the template link, a manager sent home, a large file refused in the
    skills' words, a file refused beside the field, the problems, the table's words and the bytes and token sent, nothing to
    save, a 409, an unknown outcome, and the buttons held while saving. Also the Nurses page's two links and the audit log's
    name.

**What was driven, and how.** I drove my own scratch stack, `e2e/stack.sh up nr36` (ports 18360/18763), rebuilt on
`9c73803`, in the desktop app's browser pane. The setup went through the API as Carla:
- I added BLS (expires, required to work), ICU (does not expire) and ACLS (expires), then retired ACLS;
- I recorded BLS until 30 June 2027 and ICU on Amal, and BLS until 31 December 2026 on Badr;
- I gave icu16 an end date of yesterday, which deactivated them.

The stack was taken down afterwards.
- **The template**, from the page's link: 200, `text/csv`, `skills-import-template.csv`, the three quoted columns.
- **A file with every problem**: "9 of 10 lines have a problem", each named beside its column on its line. The problems were a
  malformed ID, an unknown skill and a bad date on one line; an unknown ID; a date on ICU; BLS without a date; retired ACLS;
  Emad's BLS twice (both lines); four cells; and deactivated "ICU Nurse 16".
- **A clean file**: "4 lines ready to save". The rows were Amal's BLS (Renewal, was until 30 Jun 2027), Amal's ICU (Already
  recorded), Badr's BLS (Renewal, was until 31 Dec 2026) and icu01's ICU (New). "Save 3 skills" said "1 skill recorded and 2
  skills renewed." and moved focus to the heading. The Nurses page then read Amal "BLS until 30 Jun 2028, ICU", Badr "BLS
  until 31 Dec 2027" and icu01 "ICU".
- **The audit log**, as the System Admin through the API: one `nurse.skills_imported` entry, actor carla, no target, `{"count":
  4}`.
- **Encodings**: a UTF-16 file with a byte order mark checked as "1 line ready to save"; a Windows-1256 file was refused beside
  the field ("This is not a CSV file in UTF-8…") with focus on it.
- **At 375 px wide**: no sideways scroll; the problems table scrolls inside its region.

The file was put into the field by script (a `DataTransfer`), since the pane has no file picker I can drive. The rest was clicks
and reading the page.

**What was found, and fixed.** Only on the page: the preview's column read "When saved" with "Recorded" and "Renewed". That
reads like a time and a past event, so it is now "Change" with "New", "Renewal, was until …" and "Already recorded".

**What was NOT checked:**
- a screen-reader run. The page was held against `better-interface`, `better-writing` and `better-accessibility` by hand only:
  focus goes to the preview's heading and, after saving, to the page heading; the status line is always rendered; the page
  uses no gendered words;
- downloading the template through the browser's own save dialog: I fetched it from the page's link instead;
- two imports at once on the real database (no `test_two_at_once` case). The re-judging under the locks is tested by a change
  made inside the transaction before the locks;
- the six parallel frontend runs and the browser checks, locally: they are GitHub's, on the pull request.

**Decisions taken here, and Worth your review:**
- **Worth your review, 1: the formula guard is the template's, not a new catalogue refusal.** Ticket 35 already made the
  catalogue refuse a name starting `=`, `+`, `-`, `@` or `'`, or with a line break. It does not refuse the full-width `＝ ＋ －
  ＠` that some spreadsheets also run, nor a name stored before ticket 35.
  - The template is its header alone, as the nurse import's is, so it writes no skill name.
  - Every CSV cell this application writes goes through `nurses.spreadsheets.safe_cell`, which covers the full-width forms.
    So any later export with skill names is guarded too.
  - A catalogue refusal would add nothing for this ticket and would refuse names a hospital may use, such as "-".
- **Worth your review, 2: a deactivated nurse is a problem in the file, though the CNO may record and renew on one by hand.**
  The ticket names "an unknown or inactive hospital ID", and the documents won over ticket 33's decision for the bulk path. A
  certificate list from elsewhere can name people who have left, and the problem says to use the Nurses page for one who is
  coming back.
- **Worth your review, 3: the audit log has the import's one entry only, not a `nurse.skills_changed` per nurse.** The ticket
  says "nothing from the file", and whose skills changed comes from the file's hospital IDs. The review found the first build
  wrote both, and that is undone. The cost: an import's renewals cannot be traced to a nurse from the log, only from the
  rows' `recorded_by` and `recorded_at`.
- **Worth your review, 4: the Nurses page's button "Import from a file" is now "Import nurses from a file",** beside "Import
  skills from a file", so the two read apart.
- **Worth your review, 5: a row that says what is already recorded is fine, not a problem.** It is counted "unchanged". A
  file of nothing but such rows offers no button.
- **Worth your review, 6: the preview shows the nurse's full name beside the hospital ID.** The CNO reads every nurse's name
  on the Nurses page already, and it lets her see a wrong ID before saving.
- The skills import's limits are the nurse import's, 500 lines and 1 MB, though it hashes no passwords. One way of importing is
  one set of limits (story 33).
- Confirm answers 200 with counts, not 201: it may create nothing.

**Review:** `code-review` against `3588b1d`, both axes.
- **Standards:** no hard violation. Fixed:
  - `change` is a `StrEnum` (`SkillImportChange`), and the API types it as that enum;
  - `SkillLine` became `RowMeaning`, the expiry helper `counted_expiry`, and the shared form's `adding` became `confirming`;
  - `nurse_ids` uses the shared `wrong_cell_count`.

  Kept:
  - the two pages' tables and preview cards are near-copies, because their columns, words and confirm differ (a password
    sheet against counts); the form and the problem list are what is truly shared;
  - the frontend's `lines="skills"` restates the backend's word, as the nurse page's limits already did, for the size refusal
    before sending;
  - `Layout.split_by` holds a sentence fragment so the nurse import's words stay byte-identical;
  - `_save_skills` lives beside `_create`, as the nurse import splits judging from saving;
  - `importing.py` holds the shared reader and the nurse judging, as its docstring says.
- **Spec:** nothing missing. Not asked for:
  - the per-nurse entries, removed (above);
  - the renamed button, kept (above).

  Flagged:
  - the deactivated asymmetry (above);
  - skill names matched with Python's `lower()`, where uniqueness is PostgreSQL's `LOWER`. They can differ only for a few
    non-ASCII letters; the nurse import matches unit names the same way. Kept.

  It confirmed the locking order, the token, the re-judging, and the template and staff list unchanged.

**Things later tickets should know.**
- **Another import:** give `nurses.importing.read_file` a `Layout`, and reuse `wrong_cell_count`, `parsed` and `HOSPITAL_ID`; on
  the page, `components/csv-import.tsx`.
- **An export with skill names** (none is planned): write it through `nurses.spreadsheets.csv_response`, whose `safe_cell` is the
  formula guard (decision 1).

