# 59: A record's identifier and issue date, and who reads them

**What to build:** The CNO records a certificate or a licence on a nurse with its identifier and its issue date beside its expiry, on the Nurses page as today. The identifier is required on a licence and optional on a certificate or a skill; it is unique among the current records of one catalogue entry, refused naming the other nurse, and the same identifier is allowed on two entries and on an ended record. The issue date is refused when after the expiry or in the future, and nothing reads it. A renewal may set a new identifier and issue date with the new expiry, carrying forward what it does not name; a renewal or a removal still ends the old row. The CNO, the Deputy CNO and the nurse herself (My month) read kind, name, issuing body, identifier, issue date and expiry; a unit manager's reads and the expiries list carry kind, name and expiry and no identifier or issue date. Every table of a nurse's records groups its rows under Skills, Certificates and Licences; the expiries page gains a Kind column and nothing else. Identifiers reach no file, no notification and no audit detail; `nurse.skills_changed` stays whose and by whom. The solve input is unchanged. Spec: `.scratch/nurse-rostering-v2/specs/certificates-and-licences.md`; the words: `GLOSSARY.md` (Identifier, Certificate, Licence).

**Blocked by:** 58 Certificates and licences: the catalogue's kind and issuing body

**Status:** ready-for-agent

- [ ] The nurse's skill record gains `identifier` (free text, at most 100 characters, trimmed, nullable) and `issue_date` (nullable); a migration adds them and a partial unique constraint on (skill, identifier) over current rows with an identifier
- [ ] Record and renew take both fields; the identifier is required when the entry is a licence; an identifier another nurse's current record of the same entry holds is refused naming her; the same identifier on another entry, or on an ended record, is allowed; the issue date is refused after the expiry or after today on the hospital's clock
- [ ] A renewal changes what its body names and carries forward what it does not (identifier, issue date); the ended row keeps what it had
- [ ] Ticket 58's kind-change refusal now finds a current record without an identifier and names its nurse
- [ ] Row shapes per reader: the CNO's (Nurses page), the Deputy CNO's (Rostering attributes) and the nurse's own (`my-skills`, My month) carry kind, issuing body, identifier and issue date; the unit manager's reads (his nurses and those due to join, on the Nurses page and Rostering attributes) and the expiries list carry kind and no identifier or issue date; the System Admin reads none
- [ ] `nurse.skills_changed` is unchanged; the staff list, a roster's CSV, Excel and print page, and every notification carry nothing of it (a before-and-after test on each)
- [ ] The solve input, a re-plan's and a close's included, is byte-for-byte what it was for the same month (the four-nurse sample with identifiers and issue dates recorded)
- [ ] The Nurses page: Identifier and Issue date columns and fields on the record and renew forms, the identifier marked required when the chosen entry is a licence, refusals beside the field; the records grouped under the three headings; Rostering attributes and My month show the same columns and headings; within the width at 375 px
- [ ] The expiries page, and the manager's copy on his Nurses page, gain a Kind column; rows, order, horizon and the home count as ticket 37 left them
- [ ] Two at once on real connections: two records of one identifier on one entry, the second refused
- [ ] Tests at the agreed seams: the backend API suite (`nurses`, `solves`, the authorization walk) and the frontend's app-level suite (six runs at once); `makemigrations --check` clean; the OpenAPI document and the generated client regenerated
- [ ] `docs/ARCHITECTURE.md` section 4's Nurse skill entry carries identifier, issue date and the uniqueness rule; section 3 says who reads identifiers; the security paragraph says they stay off every file and out of the log's detail

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
