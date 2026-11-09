# 33: A nurse's skills

**What to build:** The CNO records each nurse's skills on the Nurses page, with an expiry where the catalogue says the kind expires, renews one by changing its expiry, and takes one off. Her unit manager (and the manager of a unit she is due to join) and the Deputy CNO read them; she reads her own with their expiries on My month; nobody else does. They follow her across a transfer, stay when she is deactivated or ends, and are the CNO's for a manager with a nurse profile too. The audit log says whose skills changed and by whom, never which skill or date. Turning a catalogue skill's "expires" on is refused, naming the nurses, while a record of it has no date.

**Blocked by:** 32 The skill catalogue

**Status:** ready-for-agent

- [x] A nurse skill row: nurse, skill, expiry (null for a non-expiring kind), recorded by and when, removed by and when; at most one current row a nurse and skill; a correction or removal ends the row, as leave does.
- [x] A record of an expiring kind is refused without an expiry, one of a non-expiring kind with one; a retired skill can be neither recorded nor renewed, but a record of it stays.
- [x] The CNO sets, renews and removes on the nurse's row of the Nurses page; the unit manager reads them on his nurses' rows (his unit, and a nurse due to join), the Deputy CNO on any unit's; a Staff Nurse and a manager with a nurse profile read their own on My month; the System Admin never.
- [x] Changing "expires" from off to on in the catalogue is refused while any current record of that skill lacks an expiry, naming the nurses; off again is allowed and the dates kept.
- [x] Audit: `nurse.skills_changed` with whose and by whom only.
- [x] The architecture document's roles table (CNO sets skills; managers and Deputy CNO read; the nurse reads her own) and the nurse profile entry say so.
- [x] Tests at the web API seam: each role's reading and writing, the refusals, a transfer, a deactivated nurse, the audit entry's shape; frontend tests for the Nurses page controls and My month.

## Comments

**From ticket 32 (2026-11-09), the catalogue this ticket builds on.** `hospital.models.Skill` (`name`, `expires`,
`required_to_work`, `active`) and `SkillRename` (`skill`, `old_name`, `new_name`, `at`, `by`), API under
`/api/hospital/skills` (`listSkills`, `createSkill`, `updateSkill`) in `hospital/catalogue_api.py`. Your refusal of
`expires` off to on goes in `update_skill`, after `differing` and before `_write_skill`, under the
`HospitalSettings.load(for_update=True)` lock every catalogue write already takes (so a nurse skill write that reads the
catalogue's `expires` should take it too, or lock the skill row, for the two not to pass each other). The refusal shape is
`refuse((("expires",), "..."))`; the page already shows a field's refusal beside its checkbox (`showServerErrors`), so the
Skills page needs nothing more for it. `NurseSkill.skill` should be a `PROTECT` foreign key to `Skill`, as `SkillRename`'s
is: nothing deletes a skill. A rename changes `Skill.name` only; a row keyed by the skill's id needs no carrying.

**From the review of ticket 32 (2026-11-09), decided by the user:** rename the skill catalogue's update action from `skill.updated` to `skill.changed`, as `shift.changed` and `leave_type.changed` are: in `hospital/catalogue_api.py`'s `update_skill`, its tests in `hospital/tests/test_skills.py`, the action list in `frontend/src/routes/_signed-in/audit-log.tsx` and `docs/ARCHITECTURE.md`. A small change inside this ticket.

**Implemented on 2026-11-09,** on branch `claude/ticket-33-nurse-skills-b76d9d`, pull request
MoustafaJazzar/cp-sat-nurse-roster-app#7, from `main` at `fdc283a` (`ee8bedb`, `5cd2f90`, `ac51950`, `5abf22b`, then this
comment). The suites, locally:
- the backend under pytest on a throwaway PostgreSQL 18 container of my own (`nr-t33-pytest`): 2678 passed on `ac51950`'s code (the commits after it change the frontend and `.scratch/` only).
  `makemigrations --check --dry-run` clean;
- the frontend on the head: `npm test` 643 passed, `npm run build` (with `tsc -b`) clean;
- the OpenAPI document and the generated client regenerated, matching the export;
- the solver untouched; no Playwright file changed; `e2e/ci.sh` and the six parallel frontend runs are GitHub's.

**What the dev stack needs:** a **rebuild** of `web` and `worker` (`docker compose up -d --build`) and the migration
`nurses/0005_nurse_skills`, which the stack's start runs. No change to `deploy/compose.yaml`, the `Dockerfile`, the solver or any
dependency.

**What was built, criterion by criterion.**
1. **The row.** `nurses.models.NurseSkill`: nurse, skill (`PROTECT` to `hospital.Skill`, keyed by id, so a rename needs no
   carrying), expiry (nullable), recorded by and when, removed by and when; UUIDv7 key. A partial unique constraint
   (`nurses_one_current_skill_a_nurse`) keeps one current row a nurse and skill. A renewal ends the row and begins another; a
   removal ends it; nothing is updated in place or deleted. On the profile, not a placement.
2. **Refusals**, each beside its field: "BLS expires. Enter the last day it counts." (record or renew without a date); "ICU does
   not expire, so it takes no expiry."; "ACLS is retired, so it can no longer be recorded." / "BLS is retired, so it can no
   longer be renewed."; "Amal Saleh already holds ICU. Change or take off the one recorded."; "Choose a skill from the list."
   for an unknown id. A retired skill's record stays and can still be taken off. Renewing or removing one she no longer holds
   is a 409 (the page is out of date), as for leave. An expiry already past is accepted: it is a fact the solver needs.
3. **Who.** `nurses/skills_api.py`: `POST /api/nurses/{id}/skills` (`recordNurseSkill`), `PUT /api/nurses/{id}/skills/{skill_id}`
   (`renewNurseSkill`), `POST /api/nurses/{id}/skills/{skill_id}/remove` (`removeNurseSkill`), the CNO only, each answering with
   her skills as they now are; `GET /api/nurses/my-skills` (`getMySkills`) for a Staff Nurse and a Unit Manager, taking no nurse.
   Readers get `skills` on the rows they already read: `NurseRow` (`listNurses`: the CNO every nurse, a manager his unit and
   those due to join) and `NurseAttributesRow` (`listNurseAttributes`: a manager his unit, the CNO and the Deputy CNO any
   unit). The System Admin reaches none of them. A transfer carries them, a deactivation or an end date leaves them, and a
   manager with a nurse profile has them set by the CNO (403 on his own). Every write takes the hospital settings' lock, then
   the nurse's, as `update_skill` and a transfer do.
   - **Nurses page:** a Skills column ("BLS until 30 Jun 2027", "ICU", "Retired", "None") for the CNO and the manager; for the
     CNO a "Skills" button on each row opening the panel "Skills of Amal Saleh": each skill held with "Expiry of BLS" and
     "Save expiry" (an active kind that expires), "Does not expire", "Retired" with "A retired skill can no longer be
     renewed…", and "Take off"; then "Record a skill" (only active skills not held; the Expiry field appears for a kind that
     expires). The panel stays open through each change and says what it did in the page's status line; taking one off moves
     focus to "Record a skill". An empty catalogue links to Skills.
   - **Rostering attributes:** a read-only Skills column for all three readers; the page says "The CNO sets skills on the
     Nurses page." to the CNO and the Deputy CNO.
   - **My month:** a Skills card (Skill, Counts until: the date or "Does not expire", "Retired"), "No skills are recorded for
     you." when empty, and "The CNO records your skills and changes an expiry when you renew one. Colleagues cannot see them."
4. **The catalogue refusal**, in `update_skill` after `differing`, under the lock it holds: "Amal Saleh and Badr Ali hold ICU
   with no expiry. Take it off them first, then record it again with its expiry.", naming up to four and then "Nurse 0, Nurse
   1, Nurse 2 and 2 more". Off again is allowed; the dates stay and read as null (no expiry) until it is on again.
5. **Audit:** `nurse.skills_changed`, target the hospital ID, actor the CNO, before and after empty, once per write that
   changes something (a renewal to the same date writes none, a refused write none). The audit log page names it "Changed a
   nurse's skills". **`skill.updated` is `skill.changed`** in `update_skill`, `hospital/tests/test_skills.py`, `audit-log.tsx`,
   its test and `docs/ARCHITECTURE.md`.
6. **Docs and API:** `docs/ARCHITECTURE.md`: three rows of the roles table (the CNO records, renews and takes off; the CNO,
   Deputy CNO and own-unit manager read; a nurse and a manager with a profile read their own), the Nurse profile entry and a
   new **Nurse skill** entry, the Skill entry's refusal, and the screens per role. OpenAPI and the client regenerated; the
   migration `nurses/0005_nurse_skills`.
- Tests: `nurses/tests/test_skills.py` (35, at the web API seam: the row, each refusal, each role's reading and writing, a
  manager with a profile, a transfer to a unit she is due to join and after it, a deactivated nurse, the catalogue refusal and
  off-on-off, `skill.changed`, the audit entries' shape and what the System Admin's log does not hold);
  `nurses/tests/test_two_at_once.py` (2: a dateless record and `expires` turned on, each waiting for the other's lock and then
  refused); `app.test.tsx` "a nurse's skills" (13: the column, a manager reading only, record with and without an expiry and
  what is offered, a refusal beside its field, renew with the buttons held while it saves, the body sent, an empty renewal,
  take off and focus, a 409, a retired skill, an empty catalogue, Done and focus back), "the rostering attributes page" (the
  column, the Deputy CNO), "a nurse's own month" (3: the table, empty and failed, a manager with a profile), and the audit
  log's name.

**What was driven, and how.** Scratch stack `nr-t33` (`E2E_PORT=18330`), seeded, rebuilt on the head's code. Through the API
as each seeded user: Carla (CNO) added BLS (expires, required) and ICU, recorded BLS 2027-06-30 and ICU on Amal and ICU on
Badr (201 each), BLS with no date refused beside `expiry`, ICU on Badr again refused as already held, renewed Amal's BLS to
2028-06-30; ICU's `expires` turned on refused naming "Amal Saleh and Badr Harbi". Mona (ER's manager) read Amal's skills on
`/api/nurses` and got 403 on a record; Hala (Deputy CNO) read them on ER's attributes and got 403 on `/api/nurses`; Omar got
403 on ER's attributes; Amal read her own on `my-skills`; the System Admin got 403 on `my-skills`, and her audit log held five
`nurse.skills_changed` entries, each with the hospital ID only and no before or after. In the browser pane as Carla: the
Nurses page's column, the panel, a renewal to 30 Jun 2029 through "Save expiry of BLS" ("BLS of Amal Saleh now counts until
30 Jun 2029." and the row updated); at 375 px the panel fits with no sideways scroll. As Amal: My month's Skills card read
"BLS 30 Jun 2029" and "ICU Does not expire".

**What was NOT checked:**
- a screen-reader run; the screens held against `better-interface`, `better-writing` and `better-accessibility` by hand only
  (names unique per skill, focus after take off and after Done, the status line, no gendered words in the interface);
- a transfer and a deactivation on the scratch stack (the API tests cover both);
- where focus goes after "Record skill" records the last skill not yet held: the form gives way to a sentence and focus
  falls to the page (not exercised; Amal already held both on the stack);
- the six frontend runs at once and the browser suite: GitHub's;
- the dev stack: untouched.

**Decisions taken here:**
- **Worth your review: the Deputy CNO reads skills on Rostering attributes, not the Nurses page.** The spec says the Nurses
  page, but the roles table gives her no "Read nurses", and the documents win. Rostering attributes is the one place she
  already reads every unit's nurses; the column is there for the manager and the CNO too, read-only. Opening the Nurses page
  to her would show her hospital IDs, end dates and "Password change due" as well.
- **Worth your review: a nurse's own skills are `GET /api/nurses/my-skills`, not part of `getMyMonth`.** The spec says "the
  nurse's own month endpoint", but skills are not of a month and `my-leave` set the precedent; the My month page shows them.
- **Worth your review: removal is `POST …/skills/{skill_id}/remove`,** as leave's is: `test_there_is_no_way_to_delete_a_nurse`
  forbids any DELETE under `/api/nurses`, and a removal ends a row rather than deleting it.
- **Worth your review: turning `expires` on with dateless records means taking them off and recording them again.** A
  renewal with a date on a non-expiring kind is refused (criterion 2), so the refusal says so. Turning it off and on again
  brings the kept dates back, possibly past, with no warning: the spec's "kept but counting for nothing".
- **Worth your review: the refusal names four nurses at most,** then "and N more", so a skill held by a whole ward still
  reads as a sentence.
- **Worth your review: the CNO may record and renew on a deactivated or ended nurse,** so a returning nurse's record is up to
  date. Nothing in the spec refuses it.
- **No "expired" anywhere yet:** each page shows "until <date>" only, since "expired" needs the hospital's today; ticket 37's
  expiries page will say it. Noted on ticket 37.
- The API sends `expiry` null for a kind that does not expire, even with a date kept, so no reader shows a date that counts
  for nothing.
- The Nurses page's other forms now show a 409's or 403's own words where they said "That did not work" (the review merged the
  two alerts into one).

**For tickets 34 to 38:**
- 34: `update_skill` holds the refusal of `expires` turned on (`_refuse_records_without_expiry`); put the retire refusal
  beside it. The action is `skill.changed`. Noted on ticket 34 (and on 53, whose criterion names `skill.updated`).
- 35: the records are `NurseSkill.objects.current()`; read `expiry` only when the skill's `expires` is on; a retired skill's
  records stay current. Noted on ticket 35.
- 36 (CSV): record and renew through the same rules as `skills_api` (`_refuse_expiry`, the retired refusals, ending a row
  to renew), under the same two locks, and audit `nurse.skills_changed` per nurse or the import's own entry as the spec says.
- 37: see above; noted on ticket 37.

**Reviewed by the user (2026-11-09):** all six Worth your review points kept as built: the Deputy CNO reads skills on Rostering attributes; her own skills from `GET /api/nurses/my-skills`; removal by `POST …/remove`; turning `expires` on means taking dateless records off and recording them again; the refusal names four at most; the CNO may record and renew on a deactivated or ended nurse. PR #7 at head `4d3e8fc`, fast-forwarded into `main`; migration `nurses.0005_nurse_skills`; dev stack rebuilt.
