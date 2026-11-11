# 53: The skill catalogue's "Lets a nurse precept" mark

**What to build:** A skill in the catalogue gains a third mark beside "expires" and "required to work": "Lets a nurse precept". The CNO sets and clears it on the Skills page, on one skill or several; every role that reads the catalogue reads it; a change is audited with its value, as the other marks are. Nothing yet reads the mark: assigning a preceptor (ticket 55) does. Spec: `.scratch/nurse-rostering-v2/specs/probation.md`; the words: `GLOSSARY.md` (Skill, Preceptor).

**Blocked by:** 33 A nurse's skills (both change the catalogue's API and its page)

**Status:** ready-for-agent

- [x] The catalogue row gains the mark, off for every existing skill and by default for a new one
- [x] The catalogue's API carries it: read by every signed-in role, set and cleared by the CNO only
- [x] The Skills page shows and edits it beside the other two marks, with a description in their voice; read-only for the other roles
- [x] Audit: the catalogue's `skill.created` and `skill.updated` entries carry the mark's value
- [x] Clearing the mark while a nurse precepts by that skill is allowed: the skill is checked when a preceptor is assigned only (leave a line in the page's help saying so)
- [x] Tests at the web API seam for each role and the audit entry; frontend tests for the Skills page through the app test file
- [x] `docs/ARCHITECTURE.md` names the mark where it names the other two; the OpenAPI document and the generated client regenerated; the migration

## Comments

**From ticket 33 (2026-11-09):** the catalogue's update action is `skill.changed` now, not `skill.updated` (the user's
decision on ticket 32's review); the criterion's `skill.updated` means that entry.

**Implemented on 2026-11-11,** on branch `claude/ticket-53-precept-mark-89b4c9` (`ca2308a`, `692bd50`, merges of `main`
`5d41fea` and `aa22210`, then this comment), from `main` at `e8b1308`. Draft pull request
[devjazzar/cp-sat-nurse-roster-app#16](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/16). Built here in this
session, not by implementer subagents: one small ticket on its own integration branch, as the brief set out.

The suites ran locally on `aa22210` (tickets 44, 65 and 70 merged in) under the heavy-run lock:
- the backend on a throwaway PostgreSQL 18 container of my own (`nr-t53-pytest`): 3262 passed;
- `makemigrations --check --dry-run`: "No changes detected";
- the frontend: `npm test` 782 passed, `npm run build` (with `tsc -b`) clean;
- the OpenAPI document and the generated client regenerated after each merge, matching the export;
- the solver untouched; no Playwright file changed; the six parallel frontend runs and the browser suite are GitHub's (both
  workflows), green on the head that reached `main` (the final report names it). The local suites ran on `aa22210`; the
  commits after it are the migration test's comment and `.scratch/` notes.

**What the dev stack needs:** a **rebuild** of `web` and `worker` (`docker compose up -d --build`) and the migration
`hospital/0006_skill_lets_a_nurse_precept`, which the stack's start runs. No change to `deploy/compose.yaml`, the
`Dockerfile`, the solver or any dependency.

**What was built, criterion by criterion.**
1. **The row.** `hospital.models.Skill.lets_a_nurse_precept`, a boolean with `default=False`; the migration
   `hospital/0006_skill_lets_a_nurse_precept` adds it, so every existing skill has it off. A test runs the migration itself:
   back to `0005`, a skill written as that release did, forward again, and the API reads the mark off.
2. **The API.** `lets_a_nurse_precept` on `SkillSchema` (`listSkills`, every signed-in role, the System Admin included) and on
   `SkillBody` (`createSkill`, `updateSkill`, the CNO only; 403 for every other role, nothing written and no entry). It is
   **required** in the body, as the other flags are (ticket 32's strict schema): a body without it is refused naming it, so
   an older client's PUT cannot clear the mark by leaving it out. The page sends it off for a new skill.
3. **The Skills page.** A column "Lets a nurse precept" after "Required to work" and before Status, Yes or No, for every
   reader; for the CNO a checkbox "Lets a nurse precept" after "Required to work" in the form, described as "A nurse holding
   this skill can be assigned as the preceptor of a nurse on probation, unless it has expired." Set and cleared one skill at
   a time, as the other marks are; any number of skills may carry it. The other roles see the column and no form.
4. **Audit.** `skill.created` carries every value, the mark among them; `skill.changed` (the criterion's `skill.updated`, as
   ticket 33's comment says) carries only what changed, so the mark appears there when it changed:
   `{"lets_a_nurse_precept": false}` to `{"lets_a_nurse_precept": true}`. The audit log page shows it as it shows the others.
5. **Clearing while a nurse precepts.** Nothing refuses it (unlike turning `expires` on). The page's help, which every role
   reads, now says: "A skill that lets a nurse precept is checked only when a preceptor is assigned, so turning that off later
   changes no preceptor already assigned." No preceptor exists before ticket 55, so the test shows a skill held by a nurse
   cleared, not a skill a nurse precepts by.
6. **Tests.** `hospital/tests/test_skills.py` (8 new and the existing ones carrying the field: the migration, a new skill
   off, set on two skills and cleared, cleared while held, each role reading, each other role refused with nothing written,
   both audit entries' shape, the field required and typed). `app.test.tsx` "the skills page" (2 new, 4 changed: the column
   for the CNO, set on one skill and cleared on another with the bodies sent, a new skill added marked, the description, the
   help line, and the column read-only for the four other roles with no checkbox). Other test files that send a skill body
   carry the field (`nurses/tests/test_skills.py`, `test_skills_import.py`, `test_two_at_once.py`,
   `units/tests/test_skill_needs.py`).
7. **Docs and API.** `docs/ARCHITECTURE.md` section 4's Skill entry names the mark beside the other two and says it is read
   when a preceptor is assigned only, so clearing it is allowed. The OpenAPI document and the generated client regenerated.

**What was driven, and how.** Scratch stack `nr-t53` (`E2E_PORT=18530`), seeded, built from `aa22210`. Through the API as
each seeded user: Carla (CNO) added "Preceptor course" marked and "T53 ICU" unmarked (201 each), set the mark on T53 ICU and
cleared it on Preceptor course (200), and a PUT without the field was refused (422). Hala (Deputy CNO), Mona (Unit Manager),
`icu01` (Staff Nurse) and the System Admin each read T53 ICU as the one marked skill and got 403 setting it. In the browser
pane as Carla: the column and the help line, Preceptor course marked through Edit ("Preceptor course is saved.", both skills
then Yes), T53 ICU cleared ("T53 ICU is saved.", No); at 375 px the page has no sideways scroll (scroll width 375), and the
table scrolls inside its card with Edit sticky. As the System Admin: the audit log showed both "Added a skill" entries with
`lets_a_nurse_precept`, and each "Changed a skill" as `lets_a_nurse_precept: false → true` or `true → false`; `/skills`
read-only with the column and no checkbox. The stack, its volumes and image, and my PostgreSQL container are gone.

**What was NOT checked:**
- the new tests seen red: they were written before the code, but run only after it (the Vitest ones were seen red);
- clearing the mark while a nurse actually precepts by the skill: there are no preceptors before ticket 55;
- a screen-reader run; the page held against `better-interface`, `better-writing` and `better-accessibility` by hand only
  (the checkbox's name and description, the column header's words, the help line where every role reads it, no gendered
  words, nothing new to focus);
- the read-only page in the browser as the Deputy CNO, a manager or a nurse: they were driven through the API, and the
  System Admin's page in the browser; the Vitest suite covers the four;
- the six frontend runs at once and the browser suite: GitHub's;
- the dev stack: untouched.

**Decisions taken here:**
- **The field's name is `lets_a_nurse_precept`,** the mark's words, as `required_to_work` is "Required to work".
- **"One skill or several"** read as story 25: more than one skill may carry the mark, each set on its own form as the other
  marks are. No control for several at once.
**Worth your review:**
- **The mark is required in the API's body,** as the other flags are, so "off by default for a new one" holds in the
  migration, the model and the form, not in the API: a create without the field is refused. The other reading, a default of
  off in `SkillBody`, would let an older client's PUT clear the mark by leaving it out.
- **The description on the form:** "A nurse holding this skill can be assigned as the preceptor of a nurse on probation,
  unless it has expired." It follows the spec's "unexpired on the day of assigning" and the other two descriptions' voice;
  "unless it has expired" reads naturally for a skill that never expires too.
- **The help line in the page's opening paragraph,** read by every role, rather than in the CNO's form only: a unit manager,
  who assigns a preceptor, reads the catalogue and not the form. It lengthens the paragraph by a sentence.
- **The column's place,** after "Required to work" and before Status. At 375 px it is one more column to scroll to inside the
  card; the Edit button stays sticky.
- **Nothing else shows the mark.** A nurse's skills (the Nurses page, Rostering attributes, My month, `my-skills`) do not
  say which of hers lets her precept. Ticket 55's list of preceptors is where it matters; I left the rest as it was.

**Review.** `code-review` against `e8b1308`, both axes in fresh sub-agents.
- Standards: no hard violation. Judgement calls fixed in `692bd50`: the "existing skills" test exercised the ORM default
  and not the migration (now it runs the migration and reads through the API); "chosen" and "assigned" mixed across the
  page, the API description and the model (now "assigned" throughout); the column index repeated in two Vitest tests (one
  helper). Kept: the skill's fields listed by hand in each test helper and on the page (as before this ticket; a shared
  helper across apps' tests is a refactor of its own), and `hospital/tests/test_skills.py` importing the nurse helpers from
  `nurses/tests/conftest.py` to add a nurse through the API.
- Spec: no missing criterion. The help line was in the CNO's form only, where the readers never see it: moved into the
  page's paragraph (`692bd50`). Noted, not changed: the API requires the field (a decision above); the test of clearing
  shows a held skill, not a precepted one (ticket 55's).

**Things later tickets should know.**
- **55:** read `hospital.models.Skill.lets_a_nurse_precept` through a nurse's current `NurseSkill` rows
  (`NurseSkill.objects.current()`), with the expiry counting only when the skill's `expires` is on (ticket 33's rule), on the
  day of assigning. Nothing refuses clearing the mark, and nothing should end an assignment when it is cleared. Noted on 55.
- **58:** the form and the table now hold three marks; the kind and issuing body go beside them, and every catalogue body
  test helper lists the fields by hand (`NEW` and `update` in `hospital/tests/test_skills.py`, `catalogue` and
  `change_skill` in the nurses and units tests). The migration test goes back to `hospital/0005` and forward, so `0007` must
  reverse (a `RunPython` with its reverse, as `0004` and `0005` have). Noted on 58.

