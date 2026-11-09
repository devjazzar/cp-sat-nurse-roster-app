# 53: The skill catalogue's "Lets a nurse precept" mark

**What to build:** A skill in the catalogue gains a third mark beside "expires" and "required to work": "Lets a nurse precept". The CNO sets and clears it on the Skills page, on one skill or several; every role that reads the catalogue reads it; a change is audited with its value, as the other marks are. Nothing yet reads the mark: assigning a preceptor (ticket 55) does. Spec: `.scratch/nurse-rostering-v2/specs/probation.md`; the words: `GLOSSARY.md` (Skill, Preceptor).

**Blocked by:** 33 A nurse's skills (both change the catalogue's API and its page)

**Status:** ready-for-agent

- [ ] The catalogue row gains the mark, off for every existing skill and by default for a new one
- [ ] The catalogue's API carries it: read by every signed-in role, set and cleared by the CNO only
- [ ] The Skills page shows and edits it beside the other two marks, with a description in their voice; read-only for the other roles
- [ ] Audit: the catalogue's `skill.created` and `skill.updated` entries carry the mark's value
- [ ] Clearing the mark while a nurse precepts by that skill is allowed: the skill is checked when a preceptor is assigned only (leave a line in the page's help saying so)
- [ ] Tests at the web API seam for each role and the audit entry; frontend tests for the Skills page through the app test file
- [ ] `docs/ARCHITECTURE.md` names the mark where it names the other two; the OpenAPI document and the generated client regenerated; the migration

## Comments
