# 61: The Deputy CNO records a nurse's skills, certificates and licences

**What to build:** The Deputy CNO records, renews and takes off a nurse's skills, certificates and licences on her row of the Rostering attributes page, where the Deputy already reads them for every unit, with the same forms, fields and refusals the CNO has on the Nurses page; and reaches the Import skills page, linked beside Rostering attributes, to preview and confirm a file as the CNO does. The Deputy's changes are audited with the Deputy as actor, whose record and by whom. The catalogue stays the CNO's: the Deputy reads it and writes nothing to it, and gains no other write about a nurse and no Nurses page. Spec: `.scratch/nurse-rostering-v2/specs/certificates-and-licences.md`; the words: `GLOSSARY.md` (Deputy CNO, Nurse profile).

**Blocked by:** 59 A record's identifier and issue date, and who reads them; 54 Probation on a nurse: the tick, the length and the end (both put controls on the Rostering attributes row)

**Status:** ready-for-agent

- [ ] The record, renew and remove endpoints and the skills import's template, preview and confirm take the CNO and the Deputy CNO; the authorization walk names them so; `createSkill` and `updateSkill`, the nurse import and every other nurse write keep their roles
- [ ] The Deputy's writes take the locks every skill write takes (the hospital settings' then the nurse's) and write `nurse.skills_changed` and `nurse.skills_imported` with the Deputy as actor
- [ ] The Rostering attributes page, for the Deputy CNO only, shows the record, renew and remove controls on each nurse's row with the CNO's forms, fields, grouping and refusals; the unit manager's view of the page is unchanged (a test that his row has no such control)
- [ ] The Import skills page is linked beside Rostering attributes for the Deputy CNO and works for that role end to end; the Nurses page stays the CNO's
- [ ] Tests at the agreed seams: the backend API suite (each endpoint for the Deputy, the audit entries, the roles that stay) and the frontend's app-level suite (the controls for the Deputy, absent for the manager; the import link; six runs at once)
- [ ] `docs/ARCHITECTURE.md` section 3's rows for recording skills and for the skills import name the Deputy CNO, and the roles paragraph says the Deputy writes nurses' records and nothing else about a nurse; section 8's screens name the Deputy's controls and import

## Comments

**From the main session (2026-11-11):** the user confirmed that the CNO and the Deputy CNO both record a nurse's skills,
certificates and licences. `docs/ARCHITECTURE.md` section 3's row for recording skills now reads "yes (from ticket 61)" for
the Deputy CNO, and section 4's Nurse skill entry names the Deputy's controls on Rostering attributes. This ticket still owns
the rest of that criterion: the row for the skills import, the roles paragraph and section 8's screens, and dropping "(from
ticket 61)" once built.
