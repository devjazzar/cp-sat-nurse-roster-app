# 58: Certificates and licences: the catalogue's kind and issuing body

**What to build:** Each entry of the skill catalogue is of a kind, a skill, a certificate or a licence, and names the body that issues it. The CNO sets both on the Skills page beside the other marks; the page groups its entries under Skills, Certificates and Licences; every signed-in role reads kind and issuing body in the catalogue's list. A licence always expires: the flag is forced on and disabled on the form, and the API refuses a licence with it off. Changing an entry to a licence is refused, naming the nurses, while a current record of it lacks an identifier or an expiry; changing away from licence is free. Every existing entry becomes a skill with no issuing body. The audit entries carry the two new values. The rename log, the retire rules, "lets a nurse precept" and the skill needs treat every kind alike, and the catalogue stays the CNO's to write. Nothing on a nurse's record changes yet: that is ticket 59, which gives a record the identifier this ticket's refusal names (until then the refusal has no identifier to find, and a test holds it to the expiry alone). Spec: `.scratch/nurse-rostering-v2/specs/certificates-and-licences.md`; the words: `GLOSSARY.md` (Skill, Certificate, Licence).

**Blocked by:** 53 The skill catalogue's "Lets a nurse precept" mark (both change the catalogue's API and its page)

**Status:** ready-for-agent

- [ ] The catalogue row gains `kind` (`skill`, `certificate`, `licence`) and an issuing body (free text, at most 100 characters, may be empty); a migration makes every existing row a skill with no issuing body
- [ ] The catalogue's API carries both on list, create and update; a licence with `expires` off is refused with the field's error; every signed-in role reads them, the CNO alone writes (the authorization walk unchanged in roles)
- [ ] A change to the licence kind is refused, naming the nurses (four at most, then "and N more", as ticket 33's refusal does), while a current record of the entry lacks an expiry, and, once ticket 59 lands, an identifier; a change away from licence is free; a test names the refusal's words
- [ ] `skill.created` and `skill.changed` carry kind and issuing body among their values
- [ ] The Skills page: a Kind choice and an Issuing body field on the form with descriptions in the voice of the other marks; Expires forced on and disabled while the kind is licence; the list grouped under Skills, Certificates and Licences, each heading a row group with its own name, a heading left out when it has no rows; read-only for the other roles as today
- [ ] Renames, retirement, "lets a nurse precept" and skill needs are unchanged for every kind (a test that a need may name a licence)
- [ ] Tests at the agreed seams: the backend API suite (`hospital`) and the frontend's app-level suite (six runs at once); `makemigrations --check` clean; the OpenAPI document and the generated client regenerated
- [ ] `docs/ARCHITECTURE.md` section 4's Skill entry names the kind and the issuing body and that a licence always expires

## Comments

**From ticket 53 (2026-11-11).** The catalogue now has three marks: `expires`, `required_to_work`,
`lets_a_nurse_precept` (`hospital/catalogue_api.py`: `SkillBody`, `SkillSchema`, `_skill_fields`, `_write_skill`; migration
`hospital/0006`). Each is required in the body, so a new field means every test that sends a skill body carries it: `NEW`
and `update` in `hospital/tests/test_skills.py`, `catalogue` in `nurses/tests/test_skills.py` and `test_skills_import.py`,
`icu_skill` in `test_two_at_once.py`, `change_skill` in `units/tests/test_skill_needs.py`. The Skills page's table is Name,
Expires, Required to work, Lets a nurse precept, Status, Edit, and its opening paragraph carries the mark's help line.
