# 32: The skill catalogue

**What to build:** The CNO keeps a skill catalogue beside the shift catalogue and the leave types: each skill has a name, says whether it expires and whether it is required to work, and can be renamed or retired, never deleted. Every signed-in role reads it, since it names no one. Changes go to the audit log with their values. The two refusals that depend on nurses' records and unit rules (turning "expires" on while a record lacks a date; retiring a skill a unit's need names) belong to tickets 33 and 34.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] A catalogue row: name (unique in any case of letters), expires, required to work, active; a rename log as shifts have; nothing deleted.
- [x] API in the shape of the leave types': list for every signed-in role; create, update and retire for the CNO only; a taken name refused.
- [x] A Skills page for the CNO beside Shifts and Leave types, with the two flags and retire; read-only for the other roles who open it, with no link for the System Admin, as for the shift catalogue.
- [x] Audit entries with their values (`skill.created`, `skill.updated`, including a rename and a retire), as shift catalogue changes are logged.
- [x] The glossary's Skill, Expiry and Required to work entries are the words the page uses.
- [x] The architecture document's roles table and domain model name the catalogue and who reads and keeps it.
- [x] Tests at the web API seam for each role, the refusals and the audit entries; frontend tests for the page through the app test file.

## Comments

**Implemented on 2026-11-09,** on branch `claude/ticket-32-skill-catalogue-6f6556`, pull request
MoustafaJazzar/cp-sat-nurse-roster-app#6, from `main` at `7d5b004` (`1cb6b9b`, `c1580df`, `da8d748`, `50a1bf3`, `c6eebde`,
then this comment). The suites, locally:
- the backend under pytest on a throwaway PostgreSQL 18 container of my own (`nr-t32-pytest`), on `c1580df`'s code: 2614 passed and 1
  failed, `accounts/tests/test_authorization.py::test_only_the_named_endpoints_leave_the_role_open`, whose registry of
  endpoints every role may call did not yet name `GET /api/hospital/skills` (GitHub's run found the same). Fixed in
  `c6eebde`; that file alone: 736 passed. `hospital/` again after the review's fixes: 240 passed. `makemigrations --check --dry-run` clean on the head;
- the frontend on the head: `npm test` 626 passed, `npm run build` (with `tsc -b`) clean;
- the OpenAPI document and the generated client regenerated on the head, matching the export;
- the solver untouched; no Playwright file changed; `e2e/ci.sh` and the six parallel frontend runs are GitHub's.

**What the dev stack needs:** a **rebuild** of `web` and `worker` (`docker compose up -d --build`) and the migration
`hospital/0003_skills`, which the stack's start runs. No change to `deploy/compose.yaml`, the `Dockerfile`, the solver or any
dependency.

**What was built, criterion by criterion.**
1. **The catalogue row.** `hospital.models.Skill`: `name` (unique in any case of letters, `Lower(name)` constraint),
   `expires`, `required_to_work`, `active`; UUIDv7 key; ordered by `Lower(name)`. `SkillRename` is the rename log, as
   `ShiftRename` is: skill (`PROTECT`), old name, new name, when, by whom; bigint key (ADR 0007). Nothing deletes either:
   there is no DELETE route (405).
2. **The API**, in `hospital/catalogue_api.py` beside the leave types': `GET /api/hospital/skills` (`listSkills`) for every
   signed-in role, retired skills included, each with its renames oldest first; `POST` (`createSkill`) and
   `PUT /api/hospital/skills/{id}` (`updateSkill`) for the CNO only, 403 otherwise, 401 for a stranger. Retire is `active`
   off, as for shifts and leave types. A strict schema (a typing mistake or an unknown field refused, each flag required).
   Refused, naming the field: a name another skill holds in any case of letters ("ICU is already a skill"), and a name
   another skill used to hold ("BLS is the old name of another skill"). A skill may change only the case of its own name, or
   go back to a name of its own. Writes take the `HospitalSettings` lock every catalogue write takes, so the two checks
   cannot be passed by two writers at once; the constraint stays as a backstop (`save_unless_taken`).
3. **The Skills page** (`/skills`), linked after Leave types in every role's catalogue links but the System Admin's, who may
   open it and has no link, as for Shifts. The CNO gets the table (Name with former names, Expires, Required to work,
   Status, Edit) and the form (Name, Expires, Required to work, Active); the others read the table only, with "Only the CNO
   can change these." and a keyboard-scrollable region. An empty catalogue says "No skills yet."; a failed read says so.
4. **Audit entries:** `skill.created` with every value; `skill.updated` with only what changed, a rename (`{"name": "BLS"}`
   to `{"name": "Basic life support"}`, target the new name) and a retire (`{"active": true}` to `{"active": false}`)
   included. Saving with no change writes no entry and no rename; a refused change writes neither. The audit log page names
   them "Added a skill" and "Changed a skill".
5. **The words:** the page says skill, expiry and required to work as the glossary does, and none of the words it avoids.
   The flags' hints: "Every nurse who holds this skill has an expiry for it, the last day it counts." and "From the day after
   its expiry, a nurse holding this skill works no shift."
6. **Docs and API:** `docs/ARCHITECTURE.md`: the roles table's two catalogue rows (the CNO keeps the skill catalogue, every
   role reads it), a **Skill** entry in the domain model beside Leave type, and section 8's screens. The OpenAPI document,
   the generated client and the route tree regenerated. The migration `hospital/0003_skills`.
- Tests: `hospital/tests/test_skills.py` (43, at the web API seam: each role reading, only the CNO writing, every refusal,
  the rename log, the audit entries' shape); `app.test.tsx` "the skills page" (12: the list with former names and flags,
  add, a refusal before and from the API, rename and retire with focus back, cancel, empty, a failed read, each other role
  read-only, the audit log's names); the routes and every role's links updated for `/skills`.

**What was driven, and how.** Scratch stack `nr-t32` (`E2E_PORT=18320`), seeded, rebuilt on the head's code. Through the API
in the browser pane: as Carla (CNO) the catalogue was empty; BLS (expires, required), ICU and Preceptor added (201 each);
"icu" refused "ICU is already a skill"; BLS renamed "Basic life support", the rename listed with `+03:00`; "bls" then
refused as the old name of another skill; Preceptor retired; DELETE 405. Hala (Deputy CNO), Mona (Unit Manager) and Amal
(Staff Nurse) each read the three and got 403 on a create. As the System Admin, the audit API held three `skill.created` and
two `skill.updated` entries with their values, the audit log page named them "Changed a skill", and `/skills` opened
read-only with no link in the header. As Carla in the browser at 375 px: the table scrolls inside its card with Edit sticky,
no sideways page scroll; ICU edited to required to work through the form, "ICU is saved." and the table updated.

**What was NOT checked:**
- a screen-reader run; the page held against `better-interface`, `better-writing` and `better-accessibility` by hand only
  (names, focus return, live region, words);
- two CNOs saving at once (the lock is the shift catalogue's, and the constraint the leave types'; no concurrency test);
- the six frontend runs at once and the browser suite: GitHub's;
- the dev stack: untouched.

**Decisions taken here:**
- **Worth your review: the update action is `skill.updated`,** as the ticket names it, though every other catalogue logs
  `.changed` (`shift.changed`, `leave_type.changed`). The audit log's action filter therefore lists one `.updated`. The other
  reading, `skill.changed`, is a one-word change in `update_skill`, its tests, `audit-log.tsx` and the architecture
  document.
- **Worth your review: a name another skill used to hold is refused,** as a shift's old code is. The spec names only "a
  name already taken", but it also carries renames through stored inputs by a map of old to current names, which only works
  if an old name means one skill. A skill may take back a name of its own.
- **Worth your review: a change of case alone is a rename,** logged and audited: a stored input names a skill exactly as it
  was spelled.
- **Worth your review: no skill is seeded.** The spec names none, and a hospital's skills are its own; `bootstrap` leaves the
  catalogue empty, and the page says "No skills yet.".
- **Former names on the page** ("Was BLS until 2026-11-09"), as the Shifts page shows former codes. Not asked for; cheap, and
  it explains a name a reader meets on an older page.
- **The two flags start off on a new skill;** Active starts on.
- **Not built, being 33's and 34's:** the refusal of `expires` turned on while a record lacks a date, the retire refusal
  while a live unit's need names the skill, and carrying a rename through unit rules. Each has a note on its ticket saying
  where the hook goes (`update_skill`, after `differing`, under the lock it already holds).

**For tickets 33 to 38:**
- 33 and 34 have notes on their tickets (the model, the API, the hook point, the lock). Store a nurse's skill and a need's
  skill so that a rename reaches them: 33 by the skill's id (nothing to carry), 34 by name, carried in `update_skill`.
- 35 (solving): the solve input's `required_skills` are the active, required-to-work skills' names; a stored input's old
  names map to current ones through `SkillRename` (oldest first, one to one).
- 36 has a note on CSV formula cells: a skill's name may start with `=`, `+`, `-` or `@`.
- 37 (expiries): `required_to_work` and `active` are on the row; a retired skill's records stay.

