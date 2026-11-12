# 60: The skills CSV takes Identifier and Issue date

**What to build:** The skills import's file gains two columns, Identifier and Issue date, after Expiry; the template carries the five. A file with last month's three-column header is still read, its two new fields empty on every row, so a licence row in such a file is a problem ("a licence needs its identifier"). The preview names per row, beside the problems it names today: a licence without an identifier, an identifier another nurse's current record of the entry holds, an identifier repeated in the file for one entry on two nurses, an issue date after the expiry or in the future. A row that says what is already recorded, identifier and dates included, is counted unchanged; one that differs in the expiry, the identifier or the issue date is a renewal, ending the old record. Confirm re-judges under the same locks with the same token rule. The nurse import and the staff list are untouched. Spec: `.scratch/nurse-rostering-v2/specs/certificates-and-licences.md`.

**Blocked by:** 59 A record's identifier and issue date, and who reads them

**Status:** ready-for-agent

- [ ] The file's columns are Hospital ID, Skill, Expiry, Identifier, Issue date; the template carries them; the three-column header is still accepted with the two fields empty
- [ ] Per-row problems: a licence row without an identifier (under either header); an identifier held by another nurse's current record of the entry; an identifier repeated in the file for one entry on two different nurses; an issue date after the row's expiry or in the future; the existing problems unchanged
- [ ] A row matching the record in all three fields is unchanged; a difference in any is a renewal through the same rules the API's renewal uses, ending the old row; the preview says which
- [ ] Confirm re-judges the file from the start under the hospital settings' then the nurses' locks; the token stands for the new fields too, so a renewal by hand since the preview is a different preview and nothing is saved
- [ ] `nurse.skills_imported` unchanged: the number of rows and nothing from the file
- [ ] The Import skills page shows the new columns in its preview, grouped as the other tables are, with each problem's words; the nurse import page and the staff list are untouched (a test on each)
- [ ] Tests at the agreed seams: the backend API suite beside ticket 36's import tests, and the frontend's app-level suite (six runs at once); the OpenAPI document and the generated client regenerated if the preview's shape changed

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
