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
