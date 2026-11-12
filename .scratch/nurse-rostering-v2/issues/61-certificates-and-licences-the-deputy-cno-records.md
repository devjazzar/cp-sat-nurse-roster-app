# 61: The Deputy CNO records a nurse's skills, certificates and licences

**What to build:** The Deputy CNO records, renews and takes off a nurse's skills, certificates and licences on her row of the Rostering attributes page, where the Deputy already reads them for every unit, with the same forms, fields and refusals the CNO has on the Nurses page; and reaches the Import skills page, linked beside Rostering attributes, to preview and confirm a file as the CNO does. The Deputy's changes are audited with the Deputy as actor, whose record and by whom. The catalogue stays the CNO's: the Deputy reads it and writes nothing to it, and gains no other write about a nurse and no Nurses page. Spec: `.scratch/nurse-rostering-v2/specs/certificates-and-licences.md`; the words: `GLOSSARY.md` (Deputy CNO, Nurse profile).

**Blocked by:** 59 A record's identifier and issue date, and who reads them; 54 Probation on a nurse: the tick, the length and the end (both put controls on the Rostering attributes row)

**Status:** ready-for-agent

- [x] The record, renew and remove endpoints and the skills import's template, preview and confirm take the CNO and the Deputy CNO; the authorization walk names them so; `createSkill` and `updateSkill`, the nurse import and every other nurse write keep their roles
- [x] The Deputy's writes take the locks every skill write takes (the hospital settings' then the nurse's) and write `nurse.skills_changed` and `nurse.skills_imported` with the Deputy as actor
- [x] The Rostering attributes page, for the Deputy CNO only, shows the record, renew and remove controls on each nurse's row with the CNO's forms, fields, grouping and refusals; the unit manager's view of the page is unchanged (a test that his row has no such control)
- [x] The Import skills page is linked beside Rostering attributes for the Deputy CNO and works for that role end to end; the Nurses page stays the CNO's
- [x] Tests at the agreed seams: the backend API suite (each endpoint for the Deputy, the audit entries, the roles that stay) and the frontend's app-level suite (the controls for the Deputy, absent for the manager; the import link; six runs at once)
- [x] `docs/ARCHITECTURE.md` section 3's rows for recording skills and for the skills import name the Deputy CNO, and the roles paragraph says the Deputy writes nurses' records and nothing else about a nurse; section 8's screens name the Deputy's controls and import

## Comments

**From the main session (2026-11-11):** the user confirmed that the CNO and the Deputy CNO both record a nurse's skills,
certificates and licences. `docs/ARCHITECTURE.md` section 3's row for recording skills now reads "yes (from ticket 61)" for
the Deputy CNO, and section 4's Nurse skill entry names the Deputy's controls on Rostering attributes. This ticket still owns
the rest of that criterion: the row for the skills import, the roles paragraph and section 8's screens, and dropping "(from
ticket 61)" once built.

**From ticket 54 (2026-11-11).** Ticket 54 has put its controls on the Rostering attributes row.
- **The row:** it gained an "On probation" column, the fifth cell, after Status (`frontend/src/components/probation.tsx`, `ProbationCell`). Its Length, Extend and End buttons show only when the page's `mayChange` is true (the unit manager) and the nurse is not due to join. The questions (`useProbationQuestions`) are rendered only when `mayChange`.
- **The Deputy's view:** it must keep no probation action. When the Deputy gets skill controls, give the row a separate flag for them rather than turning `mayChange` on, or the probation buttons appear too. The Deputy CNO only reads a probation (section 3's new rows).
- **Focus:** after a probation answer, focus goes to the row's "Set attributes" button, by its id `attributes-<nurse id>` (`editButtonId`). Keep that id if the row's buttons change.
- **Tests:** the app-level tests "the CNO / the Deputy CNO reads it and has no action" assert that the row has no button at all for those roles. Ticket 61 will have to narrow that assertion to the probation buttons.

**From ticket 58 (2026-11-12).** The catalogue's write endpoints (`createSkill`, `updateSkill`) stay `auth=cno`; ticket 58
added `kind` and `issuing_body` to them and changed no role. The Rostering attributes row can group a nurse's records with
`byKind` in `frontend/src/lib/skill-kinds.ts` once ticket 59 gives a record its kind.

**From ticket 59 (2026-11-12).** The three write endpoints (`recordNurseSkill`, `renewNurseSkill`, `removeNurseSkill`) answer
with `skills_of(nurse, details=True)`, the full shape: fine for the Deputy CNO too. On Rostering attributes the CNO and the
Deputy CNO now see each nurse's records as a nested `RecordsTable` (`frontend/src/components/nurse-skills.tsx`) in the Skills
cell, grouped by kind with Identifier and Issue date; it takes `actions` (the Nurses page uses it for Renew and Take off, and
shows the renew form under the table, since a row as wide as the table scrolls away on a phone), so your controls can reuse the Nurses page's `HeldSkills`, `RenewForm` and
`RecordSkillForm` (`routes/_signed-in/nurses.tsx`) if you lift them into a component. The page's words "The CNO sets skills on
the Nurses page" and My month's "The CNO records them" need the Deputy then. The renew body's identifier and issue date may be
left out (carried forward); the page always sends all three.

**From ticket 60 (2026-11-12).** The skills import is still the CNO's alone, in four places to widen together:
`auth=cno` on `previewSkillsImport` and `confirmSkillsImport` and `auth=cno_for_files` on the template
(`nurses/files_api.py`); the `Role.CNO` re-check inside `_save_skills`, which a confirm makes under the locks; `onlyFor(Role.cno)`
on the route (`routes/_signed-in/nurses_.import-skills.tsx`); and `test_only_the_cno_imports_skills` in
`nurses/tests/test_skills_import.py`, with "sends a unit manager home" in the app-level suite. The file now carries Identifier and
Issue date, and the preview's rows carry the record's `held_identifier` and `held_issue_date`: fine for the Deputy, who reads them
(ticket 59). The audit entry `nurse.skills_imported` carries the actor, so the Deputy's import would show as the Deputy's.

**From ticket 55 (2026-11-12).** The Rostering attributes row's probation cell (`components/probation.tsx`, `ProbationCell`) now
has a fourth action, "Choose preceptor" or "Change preceptor" (`ProbationAction` "preceptor"). It shows behind `mayChange` too, and
unlike the other three it also shows for a nurse due to join, since the unit she joins chooses her preceptor there. Keep the
Deputy CNO's controls on a flag of their own, as ticket 54 asked: the Deputy CNO reads the preceptor (`probation.preceptors`) and
assigns none (`PUT …/preceptor` is the unit manager's). Ticket 55's question puts focus back on the row's `attributes-<id>`
button afterwards, as the others do.

**Implemented on 2026-11-12,** on branch `claude/ticket-61-deputy-records-74be89` (`011a86a` the backend and the regenerated
client, `dce4ced` the pages, `4c01f59` the architecture, `9b159e2` the code review's points), from `main` at `8c83302`. Draft
pull request [devjazzar/cp-sat-nurse-roster-app#31](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/31). Built in this
session, as the brief set out (no implementer worktrees).

The suites ran locally under the heavy-run lock, on `4c01f59`:
- the backend on a throwaway PostgreSQL 18 container of my own (`nr-t61-pg`): 3616 passed;
- `makemigrations --check --dry-run`: "No changes detected" (no migration);
- the frontend: `npm test` 854 passed; `npm run build` and `tsc -b` clean;
- the OpenAPI document and the generated client regenerated from the export (one field description changed:
  `NurseAttributesRow.skills`);
- the solver untouched (GitHub's run green). No Playwright file changed. The six parallel frontend runs and the browser suite
  are GitHub's. After `9b159e2` (copy and names), `tsc -b` and the touched Vitest blocks (85) were run again, and the stack was
  rebuilt on it before driving.

**What the dev stack needs:** a **rebuild** of `web` and `worker` (`docker compose up -d --build`) for the code. No migration,
no change to `deploy/compose.yaml`, the `Dockerfile`, the solver or any dependency.

**What was built, criterion by criterion.**
1. **The endpoints.** `recordNurseSkill`, `renewNurseSkill`, `removeNurseSkill` (`nurses/skills_api.py`) and the skills import's
   template, preview and confirm (`nurses/files_api.py`) take `recorders = SignedIn(Role.CNO, Role.DEPUTY_CNO)` (the template
   through `for_a_file`, so ticket 62's cross-site refusal holds for the Deputy too). The nurse import, the staff list and every
   other nurse write keep `cno`; `createSkill` and `updateSkill` stay `auth=cno`. The authorization walk gained a closed list,
   `NURSE_WRITE_ROLES`: every write under `/api/nurses` and `/api/units/{unit_id}/nurses`, the three file downloads and the two
   catalogue writes, each with its roles, so a later write about a nurse must be named there.
2. **Locks and audit.** Nothing new to take: the Deputy goes through the same code under the hospital settings' lock then the
   nurse's; `_save_skills`' re-check under the locks is now `role__in=recorders.roles`. Tests: the Deputy's record, renewal and
   removal each write `nurse.skills_changed` with `hala` as actor and nothing more; her import writes `nurse.skills_imported`
   with her as actor; a record by the Deputy waits on the CNO's open record of the same identifier and is refused naming the
   nurse (`test_two_at_once.py`, real connections); a Deputy deactivated since the preview saves nothing.
3. **Rostering attributes, for the Deputy CNO only.** A Skills button beside each nurse's name ("Skills of Amal Saleh") opens a
   panel above the list, as the CNO's Skills panel on the Nurses page: the same `SkillsPanel`, now in
   `frontend/src/components/skill-records.tsx` with `HeldSkills`, `RenewForm`, `RecordSkillForm` and `RecordDetailFields`
   lifted out of `nurses.tsx`, so the forms, fields, grouping (Skills, Certificates, Licences) and refusals are one code. The
   renew form stays under the records table. The panel reads the nurse from the list as it refreshes; focus goes to its heading
   on opening and back to the row's button on Done. The flag is `mayRecord` (`role === deputy_cno`), never `mayChange`: the
   probation's Length, Extend, End and Choose/Change preceptor stay the unit manager's, and `attributes-<id>` is untouched. The
   CNO's view of this page has no button at all, as before. The unit manager's row has no Skills button (tested).
4. **Import skills** is linked in the Deputy CNO's header right after Rostering attributes; its route takes `onlyFor(Role.cno,
   Role.deputy_cno)`. For the Deputy the page's back link is Rostering attributes and the Hospital ID note "As on Rostering
   attributes."; for the CNO both stay Nurses. The CNO's header does not gain the link (she reaches it from Nurses, as before).
   The Nurses page stays the CNO's and the unit manager's.
5. **Tests.** Backend: `test_only_the_cno_and_the_deputy_cno_write`, `test_the_deputy_cno_records_renews_and_takes_off_as_the_cno_does`,
   `test_the_deputy_cno_meets_the_cnos_refusals`, `test_the_deputy_cno_writes_nothing_to_the_catalogue`, the audit test, the
   import's role test widened (`test_only_the_cno_and_the_deputy_cno_import_skills`), the Deputy's template, preview and confirm,
   the walk's closed list, the two-at-once test. App-level: a block "the Deputy CNO's records (ticket 61)" (opening and Done,
   recording a licence with the identifier refusal and the fresh list on her row, the API's refusal beside its field, renewing,
   taking off and the 409, the empty catalogue's words); the CNO's and Deputy's probation tests narrowed to the probation's
   buttons, plus one with an open probation for the Deputy; the manager's row has no Skills button; the header for each role;
   the import reached from the Deputy's header and saved; the CNO's import page unchanged.
6. **`docs/ARCHITECTURE.md`.** Section 3: the recording row now reads "Record, renew and take off a nurse's skills, certificates
   and licences …, by hand or from the skills import" with yes for the Deputy (one row for both, since the import is a way of
   recording; "(from ticket 61)" gone), and a roles paragraph: the Deputy writes nurses' records and nothing else about a nurse.
   Section 4's Nurse skill entry and section 8's skills CSV paragraph and the Deputy's screens name her controls and import.

Also the words that named the CNO alone: Rostering attributes' line for each role, My month's "The CNO and the Deputy CNO record
them", the manager's Nurses page line, the Expiries page and the manager's expiries (each saying who records and where), the
import's "No nurse has this hospital ID. Use the one the Nurses page or Rostering attributes shows.", and the attributes row's
OpenAPI description.

**What was driven, and how.** My own stack (`e2e/stack.sh up nr-t61`, seeded, rebuilt on `9b159e2`), headless Chromium through
a throwaway Playwright spec using the suite's `signIn`, deleted after; the stack taken down. A licence (SCFHS) added by Carla
through the API. As Hala, at 1280 px:
- the header: "… Unit rules | Rostering attributes | Import skills | Expiries …";
- Rostering attributes, ER: a Skills button beside each name and no probation or Set button; Skills of Amal Saleh opened with
  focus on its heading; SCFHS without an identifier refused beside the field, then recorded with 21-RN-0612 and an issue date;
  renewed to 31 Mar 2030 with focus back on Renew SCFHS; her row's records table then read 21-RN-0612; taken off; Done put
  focus back on her Skills button;
- at 375 px: nothing wider than the window, the panel's records table scrolling inside the card;
- Import skills from the header: the template's five columns; a file with an unknown hospital ID showed the new words; a good
  file saved "1 skill recorded.";
- the audit log as the System Admin read it: three `nurse.skills_changed` and one `nurse.skills_imported` with actor `hala`,
  target only, nothing from the record or the file;
- as Mona, Rostering attributes had no Skills button.

**What was found, and fixed.** Nothing in the code. The drive's own selectors needed `exact` labels, since the row buttons'
names start with "Skills".

**Findings for you, not fixed:**
- Right after a record, the panel can show the list as it was for a moment until the refetch lands (the screenshot caught "No
  skills are recorded" beside "SCFHS is recorded"); the CNO's Nurses page does the same, since both refresh by refetching the list
  rather than taking the answer. Not changed here, as the shared component behaves as the CNO's always has.
- A write refreshes the page's own list, not the expiries query; the Expiries page reads afresh when opened, as for the CNO.
- The Deputy's page is per unit, so a nurse with no current unit (ended, deactivated without a placement in view) is reachable
  by the Deputy only through the import, whereas the CNO's Nurses page lists everyone.

**What was NOT checked:**
- the six frontend runs at once and the browser suite: GitHub's (`roles.spec.ts` and `narrow.spec.ts` walk every header page
  of the Deputy, so they open Import skills on a desktop and a phone);
- a screen reader's reading of the panel: only its accessible names, by testing-library;
- `better-interface`, `better-writing` and `better-accessibility` held by hand: the button's name ("Skills of …", as the CNO's),
  the panel's heading taking focus, the region rule (the table is no keyboard-scrolled region once it holds buttons), the copy;
- the solver's suite locally (untouched; GitHub's);
- the dev stack: untouched.

**Decisions taken here:**
- **A panel above the list, not controls inline in the row.** Ticket 59's taller rows stay as the read view (the records table
  in the Skills cell); the forms open in a card above the table from a Skills button beside the name, as the CNO's do on the
  Nurses page. A form in a row as wide as this table (17 columns) would scroll away on a phone, and a record form per row would
  repeat ids.
- **One header link, the Deputy's**, after Rostering attributes; the CNO keeps reaching the import from Nurses.
- **The section 3 row covers the import** ("by hand or from the skills import") rather than a second row.
- **The empty catalogue's words for the Deputy** name the CNO and link nowhere: "The skill catalogue is empty. The CNO adds
  skills, certificates and licences to it under Skills."

**Worth your review:**
- **How the controls sit:** a Skills button beside the name opening a panel above the list (above), with the row's records table
  kept for reading. The alternative, Renew and Take off inline in the row's records table with the record form under it, keeps
  everything on the row but grows each row further and scrolls away on a phone.
- **The new words:** Rostering attributes, for the Deputy: "Only the unit's manager can change these, but for skills, certificates
  and licences, which you record here and the CNO on the Nurses page."; for the CNO: "Only the unit's manager can change these.
  You record skills, certificates and licences on the Nurses page, and the Deputy CNO records them here."; for the manager:
  "Gender and whether a nurse is on probation are the CNO's to set, and skills the CNO's and the Deputy CNO's to record; you set
  how long a probation lasts. …". My month: "The CNO and the Deputy CNO record them and change one when you renew it." The
  Expiries page per role, and the manager's: "The CNO records and renews skills on the Nurses page, and the Deputy CNO on
  Rostering attributes."
- **What the Deputy sees on Import skills that the CNO does not:** the back link and the Hospital ID note name Rostering
  attributes; everything else, the problems' words included, is the same page. The import's unknown-ID words now name both pages
  for both roles.

**The code review.** `code-review` against `8c83302`, both axes in fresh sub-agents.
- Spec (no blocking gap):
  - noted: section 3 has one row for recording and the import (a decision above);
  - "six runs at once": GitHub's, on the pull request;
  - noted: the manager's line on Rostering attributes changed in words only (his controls are unchanged and tested);
  - noted: the expiries query not refreshed after a write (a finding above);
  - kept: the Skills button on a nurse due to join's row too, since a record follows the profile.
- Standards (no hard breach):
  - fixed: the manager's expiries line now says where, as the docstring of `ExpiriesList` asks (`9b159e2`);
  - fixed: `files_api.py`'s docstring wrapped; one style for the role on Rostering attributes; `recordsOf` renamed `skillsPanel`
    with a comment, `Holder` renamed `NurseWithRecords`;
  - kept: `Unexpected` and `COULD_NOT_SAVE` copied in `skill-records.tsx` (`nurses.tsx` still uses its own for its other forms;
    every page keeps its own copy today, `probation.tsx` and `rostering-attributes.tsx` too); a shared one is a change to many
    pages;
  - kept: the role branches on copy in three pages: each says something different in its own words, so one map would hold
    sentences rather than a rule;
  - kept: `keepsCatalogue`, a boolean for one sentence, as the simplest thing;
  - kept: `recorders` defined in both API modules, as `approver` is in the rosters' (per-module guards are the house pattern);
  - kept: the deactivated Deputy's `in (401, 403)`, as the CNO's test beside it has.

**Things later tickets should know.**
- The record forms live in `frontend/src/components/skill-records.tsx` (`SkillsPanel`, taking the nurse, a `refresh` and
  `keepsCatalogue`); the Nurses page and Rostering attributes both use it.
- A new write about a nurse must be added to `NURSE_WRITE_ROLES` in `backend/accounts/tests/test_authorization.py`.
