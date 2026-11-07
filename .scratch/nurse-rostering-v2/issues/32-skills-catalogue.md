# 32: The skill catalogue

**What to build:** The CNO keeps a skill catalogue beside the shift catalogue and the leave types: each skill has a name, says whether it expires and whether it is required to work, and can be renamed or retired, never deleted. Every signed-in role reads it, since it names no one. Changes go to the audit log with their values. The two refusals that depend on nurses' records and unit rules (turning "expires" on while a record lacks a date; retiring a skill a unit's need names) belong to tickets 33 and 34.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] A catalogue row: name (unique in any case of letters), expires, required to work, active; a rename log as shifts have; nothing deleted.
- [ ] API in the shape of the leave types': list for every signed-in role; create, update and retire for the CNO only; a taken name refused.
- [ ] A Skills page for the CNO beside Shifts and Leave types, with the two flags and retire; read-only for the other roles who open it, with no link for the System Admin, as for the shift catalogue.
- [ ] Audit entries with their values (`skill.created`, `skill.updated`, including a rename and a retire), as shift catalogue changes are logged.
- [ ] The glossary's Skill, Expiry and Required to work entries are the words the page uses.
- [ ] The architecture document's roles table and domain model name the catalogue and who reads and keeps it.
- [ ] Tests at the web API seam for each role, the refusals and the audit entries; frontend tests for the page through the app test file.
