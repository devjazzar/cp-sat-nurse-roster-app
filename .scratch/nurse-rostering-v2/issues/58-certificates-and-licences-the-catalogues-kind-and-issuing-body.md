# 58: Certificates and licences: the catalogue's kind and issuing body

**What to build:** Each entry of the skill catalogue is of a kind, a skill, a certificate or a licence, and names the body that issues it. The CNO sets both on the Skills page beside the other marks; the page groups its entries under Skills, Certificates and Licences; every signed-in role reads kind and issuing body in the catalogue's list. A licence always expires: the flag is forced on and disabled on the form, and the API refuses a licence with it off. Changing an entry to a licence is refused, naming the nurses, while a current record of it lacks an identifier or an expiry; changing away from licence is free. Every existing entry becomes a skill with no issuing body. The audit entries carry the two new values. The rename log, the retire rules, "lets a nurse precept" and the skill needs treat every kind alike, and the catalogue stays the CNO's to write. Nothing on a nurse's record changes yet: that is ticket 59, which gives a record the identifier this ticket's refusal names (until then the refusal has no identifier to find, and a test holds it to the expiry alone). Spec: `.scratch/nurse-rostering-v2/specs/certificates-and-licences.md`; the words: `GLOSSARY.md` (Skill, Certificate, Licence).

**Blocked by:** 53 The skill catalogue's "Lets a nurse precept" mark (both change the catalogue's API and its page)

**Status:** ready-for-agent

- [x] The catalogue row gains `kind` (`skill`, `certificate`, `licence`) and an issuing body (free text, at most 100 characters, may be empty); a migration makes every existing row a skill with no issuing body
- [x] The catalogue's API carries both on list, create and update; a licence with `expires` off is refused with the field's error; every signed-in role reads them, the CNO alone writes (the authorization walk unchanged in roles)
- [x] A change to the licence kind is refused, naming the nurses (four at most, then "and N more", as ticket 33's refusal does), while a current record of the entry lacks an expiry, and, once ticket 59 lands, an identifier; a change away from licence is free; a test names the refusal's words
- [x] `skill.created` and `skill.changed` carry kind and issuing body among their values
- [x] The Skills page: a Kind choice and an Issuing body field on the form with descriptions in the voice of the other marks; Expires forced on and disabled while the kind is licence; the list grouped under Skills, Certificates and Licences, each heading a row group with its own name, a heading left out when it has no rows; read-only for the other roles as today
- [x] Renames, retirement, "lets a nurse precept" and skill needs are unchanged for every kind (a test that a need may name a licence)
- [x] Tests at the agreed seams: the backend API suite (`hospital`) and the frontend's app-level suite (six runs at once); `makemigrations --check` clean; the OpenAPI document and the generated client regenerated
- [x] `docs/ARCHITECTURE.md` section 4's Skill entry names the kind and the issuing body and that a licence always expires

## Comments

**From ticket 53 (2026-11-11).** The catalogue now has three marks: `expires`, `required_to_work`,
`lets_a_nurse_precept` (`hospital/catalogue_api.py`: `SkillBody`, `SkillSchema`, `_skill_fields`, `_write_skill`; migration
`hospital/0006`). Each is required in the body, so a new field means every test that sends a skill body carries it: `NEW`
and `update` in `hospital/tests/test_skills.py`, `catalogue` in `nurses/tests/test_skills.py` and `test_skills_import.py`,
`icu_skill` in `test_two_at_once.py`, `change_skill` in `units/tests/test_skill_needs.py`. The Skills page's table is Name,
Expires, Required to work, Lets a nurse precept, Status, Edit, and its opening paragraph carries the mark's help line.
`test_every_skill_there_was_before_the_mark_has_it_off` migrates `hospital` back to `0005` and forward again, so your
`hospital/0007` must reverse (a `RunPython` with its reverse, as `0004` and `0005` have).

**Implemented on 2026-11-12,** on branch `claude/ticket-58-kind-and-issuing-body-1f32de` (`87d0605`, `916248f`, `43088a8`,
`9eefee3`, then this comment), from `main` at `3579d76`. Draft pull request
[devjazzar/cp-sat-nurse-roster-app#19](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/19). Built in this session,
not by implementer subagents: one ticket on its own integration branch, as the brief set out (it overrides
`/implement-spec`'s subagent per ticket).

The suites ran locally on `43088a8` under the heavy-run lock (`9eefee3` only lets one table cell wrap, and the Skills page
block of the Vitest suite was run again on it, 19 passed):
- the backend on a throwaway PostgreSQL 18 container of my own (`nr-t58-pg`): 3361 passed;
- `makemigrations --check --dry-run`: "No changes detected";
- the frontend: `npm test` 798 passed, `npm run build` (with `tsc -b`) clean;
- the OpenAPI document and the generated client regenerated, matching the export;
- the solver untouched; no Playwright file changed. The six parallel frontend runs and the browser suite are GitHub's, on the
  pull request.

**What the dev stack needs:** a **rebuild** of `web` and `worker` (`docker compose up -d --build`) and the migration
`hospital/0007_skill_kind_and_issuing_body`, which the stack's start runs. No change to `deploy/compose.yaml`, the
`Dockerfile`, the solver or any dependency.

**What was built, criterion by criterion.**
1. **The row.** `hospital.models.Skill` gains `kind` (`Skill.Kind`: `skill`, `certificate`, `licence`, default `skill`) and
   `issuing_body` (at most 100 characters, default empty). Migration `0007` adds both with their defaults, so every existing
   entry is a skill with no issuing body, plus a check constraint `hospital_skill_a_licence_expires`. Every step reverses by
   itself (`AddField` and `AddConstraint`), so there is no `RunPython`. Ticket 53's test still goes back to `0005` and
   forward. A new test goes back to `0006`, which undoes `0007`, writes a skill as that release did, goes forward, and reads
   `("skill", "")` through the API.
2. **The API.** `kind` and `issuing_body` are on `SkillSchema` (`listSkills`, every signed-in role) and `SkillBody`
   (`createSkill` and `updateSkill`, the CNO only).
   - Both are **required** in the body, as the marks are (53's rule, kept by the user).
   - `kind` is a closed list.
   - The issuing body is trimmed, at most 100 characters, may be empty, and has no NUL.
   - A licence with `expires` off is refused beside `expires` with "A licence always expires.", on create and on update.
   - Every role reads; every other role gets 403 on both writes, with nothing written and no entry. The authorization walk
     (`accounts/tests/test_authorization.py`) passes unchanged.
3. **A change to licence.** It is refused **beside `kind`** while a current record has no expiry, naming the nurses through
   ticket 33's helper (all four when there are four; three and "and N more" past that). The words:
   "Amal Saleh and Badr Ali hold ICU with no expiry, and a licence always expires. Take it off them first, then record it
   again with its expiry." A change to licence where every record has its expiry passes. That test,
   `test_a_change_to_licence_passes_when_every_record_has_its_expiry`, holds it to the expiry alone until ticket 59. A change
   away from licence is free, `expires` off included.
4. **Audit.** `skill.created` carries every value, kind and issuing body among them. `skill.changed` carries what changed,
   for example `{"kind": "skill", "issuing_body": ""}` → `{"kind": "certificate", "issuing_body": "American Heart Association"}`.
5. **The Skills page.**
   - The form gains a Kind select (Skill, Certificate, Licence) after Name, then an Issuing body field. Their descriptions:
     - Kind: "A skill is an ability, such as triage. A certificate attests something a nurse has earned, such as a degree or a
       course. A licence permits a nurse to practise and always expires."
     - Issuing body: "Who issues it, such as the Saudi Commission for Health Specialties or a university. Leave it empty when no
       one does."
   - While the kind is licence, Expires is checked and disabled, and its description starts "A licence always expires." The
     body still sends `expires: true`, which a test checks.
   - The table gains an Issuing body column after Name. Its rows are grouped under Skills, Certificates and Licences, each a
     `<tbody aria-labelledby>` whose first row is a `<th scope="rowgroup">` heading spanning the columns, and a heading with
     no rows is left out.
   - The other roles read the same table and no form, as before.
6. **Unchanged for every kind.** A licence is renamed, retired and marked "lets a nurse precept" as any skill. A skill need
   names a licence, and a change of kind leaves the needs and the solve input as they were
   (`units/tests/test_skill_needs.py`).
7. **Tests.** They are at the agreed seams: `hospital/tests/test_skills.py` for the catalogue and the Skills page block of
   `app.test.tsx`. Every other body helper carries the two fields (`nurses` and `units` tests). `makemigrations --check` is
   clean, and the OpenAPI document and client are regenerated.
8. **`docs/ARCHITECTURE.md`** section 4's Skill entry names the kind, the issuing body, that a licence always expires (API and
   constraint), and the refusal beside the kind.

**What was driven, and how.** A seeded scratch stack `nr-t58` (`e2e/stack.sh up`, ports 18580 and 18958), driven in Chromium
by a throwaway Playwright file, since deleted:
- **As Carla, the CNO:**
  - She added a licence "SCFHS registration" (Expires checked and disabled), a certificate "BSc Nursing", a skill
    "ICU course" with no issuing body, and "BLS" from the American Heart Association. The table showed three headings in
    order.
  - "ICU course" was recorded on Amal with no expiry through the API, then changed to Licence on the page. It was refused
    with focus on Kind and the words beside it, read with the field.
  - At 375 px the page does not scroll sideways. The table scrolls inside its card, with Edit held in place.
- **As Hala, the Deputy CNO:** the same grouped table, "Only the CNO can change these.", and no form.
- **Found and fixed while driving:** at 1280 px the new column pushed Status under the sticky Edit button. The issuing body now
  wraps in its cell (`9eefee3`).
- **Afterwards:** the stack is down, and my PostgreSQL container is stopped.

**What was NOT checked:**
- the six frontend runs at once and the browser suite: GitHub's;
- the read-only page in the browser as a unit manager, a staff nurse or the System Admin: the Vitest suite covers all four;
- `better-interface`, `better-writing` and `better-accessibility` were held by hand only: the select's and the field's names
  and descriptions, the headings as named row groups, the disabled checkbox's reason in its own description, and no gendered
  words;
- a screen reader's reading of the row groups: only the accessible names were checked, by testing-library and in the DOM;
- the dev stack: untouched.

**Decisions taken here:**
- **The refusal of a change to licence sits beside `kind`, not `expires`.** On the page Expires is disabled while the kind is
  licence, and focus cannot reach it. The same helper names the nurses, with ", and a licence always expires" added. Turning
  `expires` on alone is refused beside `expires` as before.
- **A check constraint** holds "a licence always expires" in the database as well as the API. It is small, reverses, and
  catches a write that skips the API.
- **`kind` is a select, not a radio group**, since `SelectField` is the house's choice control. It sits after Name, with the
  issuing body after it, both before the marks.
- **Expires stays checked when the kind changes away from licence.** The CNO unchecks it if the entry no longer expires.
- **The grouping helper** (`frontend/src/lib/skill-kinds.ts`: `KINDS`, `byKind`) is shared, for the tables that tickets 59
  and 60 group.

**Worth your review:**
- **Kind and issuing body are required in the API body with no default**, as 53's marks are. An older client's PUT cannot
  turn a licence back into a skill by leaving the field out. A create without them is refused naming the field.
- **The Kind control and its words:** a select (Skill, Certificate, Licence), described as above. The alternative was a radio
  group of three, which shows all three at once but takes four lines.
- **No Kind column:** the kind is the group heading. The spec's "the list shows kind and issuing body" is read as the heading
  and a column for the issuing body. A Kind column would repeat the heading on every row.
- **The headings' order and look:** Skills, Certificates, Licences, as the spec says, each a shaded row spanning the table.
  Within a group the order is alphabetical, as today.
- **The refusal beside Kind** (a decision above) and its words: "… hold ICU with no expiry, and a licence always expires.
  Take it off them first, then record it again with its expiry."
- **The database constraint**, which the spec did not ask for.

**Review.** `code-review` against `3579d76`, both axes in fresh sub-agents.
- **Standards.** No hard violation.
  - Fixed in `43088a8`:
    - two lines far past the files' width;
    - the migration test missing its comment;
    - the model comment using "registration", a word the glossary says to avoid;
    - the column count repeated by hand, now one list of columns;
    - the zod enum, now built from the generated kind.
  - Kept:
    - the skill's fields listed by hand in each test helper, as ticket 53 kept them;
    - the shared refusal helper taking its field and an added clause;
    - a hospital test of the "and N more" count, which goes through the kind path;
    - `byKind` with one caller for now, which 59 and 60 will use.
- **Spec.** Nothing missing.
  - Noted: the Kind column (above), the constraint (above), and Expires staying checked after a licence (a decision above).
  - Also noted: a body that turns a non-expiring entry into a licence with `expires` off gets "A licence always expires."
    first, and the names only once `expires` is on. The page always sends it on.

**Things later tickets should know.**
- **59:** the second refusal of a change to licence (a current record with no identifier) goes in `update_skill` beside the
  first, where the comment says, also on `kind`. `test_a_change_to_licence_passes_when_every_record_has_its_expiry` should
  gain a record without an identifier and be refused. `NurseSkillRow` does not carry the kind yet; grouping a nurse's records
  needs it. Noted on 59.
- **60 and 61:** `byKind` in `frontend/src/lib/skill-kinds.ts` groups any rows by kind. The catalogue's writes stay the
  CNO's. Noted on 60 and 61.
