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
cell, grouped by kind with Identifier and Issue date; it takes `actions` and `below` (the Nurses page uses them for Renew,
Take off and the renew form under the row), so your controls can reuse the Nurses page's `HeldSkills`, `RenewForm` and
`RecordSkillForm` (`routes/_signed-in/nurses.tsx`) if you lift them into a component. The page's words "The CNO sets skills on
the Nurses page" and My month's "The CNO records them" need the Deputy then. The renew body's identifier and issue date may be
left out (carried forward); the page always sends all three.
