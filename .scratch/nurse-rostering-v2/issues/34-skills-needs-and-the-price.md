# 34: Skill needs among the unit rules, the price among the weights

**What to build:** A unit manager writes skill needs among his unit rules: a shift the unit works, a skill, a weekday minimum and a weekend minimum, several per unit, and one flag making them all hard or soft, hard by default. The CNO sets the skill shortfall weight among the hospital weights, the price per nurse short per shift-day when a unit's needs are soft. What the forms save passes the solver's loader as version 2. A shift a need names cannot be dropped from the unit; a skill a live unit's need names cannot be retired; a skill rename is carried through every unit's needs.

**Blocked by:** 31 Solver: skill rules and solve input version 2; 32 The skill catalogue

**Status:** ready-for-agent

- [x] The unit rules carry `skill_needs` and `skill_needs_hard`; seeded empty and hard; the hospital rules' weights carry `skill_shortfall`, seeded at zero. The test that holds the saved blocks to the solver's own fields covers them.
- [x] A need is refused when it names a shift outside the unit's shifts or a retired skill, or names the same shift and skill twice; minimums are non-negative integers within the solver's parameter limit.
- [x] Dropping a shift from the unit is refused while a need names it, naming the need, as it is while a pin uses it; retiring a skill is refused while a live unit's need names it, naming the units, as retiring a shift is; a skill rename runs through every unit's needs in the same transaction, audited per unit.
- [x] The unit rules page gains a skill needs table (add, edit, remove) and the hard flag beside night rest's; the hospital rules page gains the weight; the CNO and Deputy CNO read a unit's needs read-only as the other rules.
- [x] Audit: unit rule and hospital rule changes keep logging their values; skill needs say nothing about a person.
- [x] The architecture document's unit rules and hospital settings entries name skill needs and the weight.
- [x] Tests at the web API seam for the rules, the refusals, the guards and the rename; frontend tests for the table and the flag through the app test file.

## Comments

**From ticket 31 (2026-11-09), for this ticket to undo.** The solver's blocks gained the version 2 fields before the app's
did, so four backend tests that hold the app's blocks to the solver's own fields subtract a named set,
`VERSION_2_SKILL_FIELDS`, until the app carries them: `hospital/tests/test_rules.py::test_the_rules_are_every_field_of_the_solvers_block_but_the_shift_catalogues`
(`required_skills` and the weight `skill_shortfall`), `units/tests/test_rules_api.py::test_both_schemas_are_every_field_of_the_solvers_block_but_its_name`
(both schemas) and `units/tests/test_unit_rules.py::test_the_rules_are_every_field_of_the_solvers_block_but_the_units_name`
(`skill_needs`, `skill_needs_hard`). Once the hospital and unit blocks carry those fields, delete the set and its
subtraction in each. The solver already refuses a second need for the same shift and skill, a need on a shift the unit
does not work, a minimum outside 0..1000 (`MAX_NURSES`), a skill name listed twice in `required_skills`, and a version 1
input carrying any of the five fields; the app's solve input must be version 2 for its needs to count.

**From the review of ticket 31 (2026-11-09), decided by the user:** fairness should treat a day barred by an expired required skill as leave. Today a barred nurse's Friday share (`fair_weekend`) is not prorated for those days, so she carries a cost she cannot avoid and a lower `friday_balance` into next month. In the solver, count barred days as leave wherever fairness prorates for leave (`nurse_roster.fairness`), with a rule test in the constraint-verifier style. This is a small solver change inside this ticket.

**From ticket 32 (2026-11-09), the catalogue this ticket builds on.** `hospital.models.Skill` and `SkillRename`,
`/api/hospital/skills` in `hospital/catalogue_api.py`. Your two catalogue hooks both go in `update_skill`, after
`differing`, under the `HospitalSettings.load(for_update=True)` lock it already holds: the retire refusal when `"active"`
turns off (as `update_shift` does with `units_using`, naming the units, `refuse((("active",), ...))`), and carrying a rename
through every unit's `skill_needs` when `"name" in new`, beside the `SkillRename` row it already writes, audited per unit as
`_carry_rename_through_the_units` does for a shift. Unit rules store skills by name, so the rename has to be carried; the
rename log is there for stored solve inputs, read on the way out (spec: a map of old to current names applied on read).
No other skill may take a name a skill used to hold (`_refuse_a_taken_name`), so that map is one to one. The audit action
for a catalogue change is `skill.updated` (the ticket's word; every other catalogue uses `.changed`).

**From ticket 33 (2026-11-09):** the catalogue's update action is now `skill.changed` (the user's decision on ticket 32's
review), so read the line above with that name. `update_skill` now also refuses `expires` turned on while a current
`nurses.NurseSkill` of it has no expiry (`_refuse_records_without_expiry`, after `differing`, under the same lock): put the
retire refusal beside it. A nurse's record is keyed by the skill's id, so a rename needs carrying through unit rules only.

**Implemented on 2026-11-09,** on branch `claude/ticket-34-skill-needs-df5871`, draft pull request
Nurse-Fold/cp-sat-nurse-roster-app#12, from `main` at `0e6210d`. The commits:
- `f44c754`: the backend, the solver's fairness change, the version 2 sample, the migrations and the regenerated client;
- `7b3c8c8`: the frontend;
- `95f6d14`: the review's points;
- then this comment.

The suites ran locally, one at a time under the heavy-run lock:
- the backend on a throwaway PostgreSQL 18 container of my own: 2787 passed;
- the solver's whole suite with the service tests: 599 passed;
- the frontend: one `npm test` run, 669 passed, and `npm run build` succeeded;
- `makemigrations --check`: "No changes detected";
- the OpenAPI document and the generated client match the export (no diff after regenerating).

GitHub runs the six parallel frontend runs and the browser checks (`e2e/ci.sh`). No Playwright file changed; `e2e/seed.py`
changed by one line (below).

**What the dev stack needs:** a **rebuild** (`docker compose up -d --build`), because the vendored solver changed. Two data
migrations run when `web` starts:
- `units/0005_skill_needs` writes `skill_needs: []` and `skill_needs_hard: true` into every unit's rules, leaving a unit that
  already has them alone;
- `hospital/0005_skill_shortfall_weight` writes `skill_shortfall: 0` into the hospital's weights.

There is no compose, Dockerfile or dependency change.

**What was built, criterion by criterion.**
- **The fields.** `skill_needs` (each `shift`, `skill`, `weekday_min`, `weekend_min`) and `skill_needs_hard` sit in the unit's
  rules in the solver's names, seeded empty and hard (`DEFAULT_UNIT_RULES`, and the migration for existing units). The weights
  gain `skill_shortfall`, seeded 0. The general block a solve input gets also carries `required_skills`: the live skills marked
  required to work, from the catalogue, not from the saved hospital rules.
  - The three `VERSION_2_SKILL_FIELDS` sets and their subtractions are deleted. The hospital's test now subtracts
    `{"shift_hours", "required_skills"}`, both being the catalogues'. New tests hold the need schemas to the solver's
    `SkillNeed`.
  - The "defaults are the reviewed set" tests compare against the ER sample plus the new fields, as ticket 48's do.
- **The refusals.** Each one is said beside its field, all at once, under the catalogue's lock:
  - a need on a shift the unit does not work: "A is not one of this unit's shifts.";
  - a retired or unknown skill, matched exactly by name: "PALS is not an active skill in the catalogue.";
  - the same shift and skill twice, beside the second: "D already has a need for ICU.";
  - a minimum outside 0..1000 (`MAX_NURSES`), a fraction, a string or null;
  - more than 100 needs (`MAX_SKILLS`).

  Both fields are required in a save.
- **The guards.**
  - Taking out a shift a need names is refused beside the shifts, naming the needs: "A skill need names a shift you are
    taking out: ICU on N. Take the need out first." A need on a shift the unit never worked gets the need's own refusal
    instead.
  - Retiring a skill a live unit's need names is refused beside `active`: "ICU is in the skill needs of ER, ICU. The unit's
    manager has to take it out of them first." This is in `update_skill`, beside `_refuse_records_without_expiry`. An
    archived unit does not count, as for shifts.
  - A skill rename runs through every unit's needs, archived units too, in the same transaction. It is audited per changed
    unit as `unit_rules.changed` by the CNO, and the review flag is left alone. The shift rename and the skill rename now
    share one carrier (`_carry_rename_through_the_units`, which takes the transform).
  - A shift rename runs through needs too (`with_shift_codes`), and a need whose shift maps to none is dropped, as a headcount
    is.
- **The pages.**
  - **Unit rules** has a "Skill needs" section after "Who a shift needs". It holds the flag "Never break the skill needs",
    worded like night rest's, then one group per need ("Skill need 1"): Shift, Skill, "Weekday, at least" and "Weekend day,
    at least". It also has "Add a skill need" and "Remove this need".
    - A new need takes the first skill and shift with no need yet, and focus moves to its Shift. After a remove, focus
      moves to the add button.
    - The page refuses a repeated pair and a shift taken out under a need before sending.
    - A need on a skill no longer offered shows as itself.
    - With an empty catalogue the add button is off and the page says "The skill catalogue has no skills yet. The CNO adds
      them."
  - **Hospital rules:** the weight is "Short of a skill need", described "Each nurse short of a unit's skill need on a shift
    and day. Applies only in a unit that lets its skill needs be broken.", beside "Day and night switches".
  - **Read-only:** the CNO and the Deputy CNO read "ICU on N: at least 2 on a weekday, 1 on a weekend day" and the flag as
    On or Off.
- **Audit.** A change to the needs is in `unit_rules.changed` with its values, like any unit rule; the weight is in
  `hospital_rules.changed` as `weights.skill_shortfall`. Nothing in either names a person.
- **The solve input is version 2.** `solves.input.assemble` writes version 2, so every new solve, re-plan and close input
  carries the needs, the flag, the weight and the required skills. Stored version 1 inputs still load, as the solver reads them.
- **The solver: fairness counts a barred day as leave** (the user's decision at ticket 31's review). `fairness.weekend_available`
  adds `barred_days` to her leave, so her Friday share is prorated for them, in the model, the validator and the carried
  balance alike (the one place fairness prorates for leave). Tests in `solver/tests/test_skills.py`:
  - barred from the second of two Fridays she is owed 600 thousandths, as a nurse on leave that Friday is, against 1200;
  - barred all month, she is owed 0 and carries no Friday debt;
  - a solve's objective equals the validator's.

  `solver/DESIGN.md` says so.
- **The sample.** `four_nurses.json` is now version 2 with no skills (`required_skills: []`, weight 0, no needs, hard),
  because the backend and `e2e/seed.py` load it as a unit's and the hospital's rules. Its copy in `how-to.md` 2.5 follows.
  - The solver's tests that used it as the version 1 sample now derive one (`tests.er_fixture.version_1`), so version 1
    keeps its coverage.
  - The backend's sample unit and `e2e/seed.py` leave `required_skills` out of the saved hospital rules, as they leave
    `shift_hours`.
- **Docs.** `docs/ARCHITECTURE.md`:
  - section 4's hospital settings, skill and unit entries name the needs, the flag, the weight, the guards and the rename;
  - section 6 says the app writes version 2 since this ticket, and what the barred days do to fairness;
  - section 9 gives the defaults.

**What was driven, and how.** I drove my own scratch stack (`e2e/stack.sh up nr34`, seeded, ports 18340/18743) in the desktop
app's browser. The pane was hidden, so I worked the pages' own forms by script and read what they rendered, and the API where
noted; there are no screenshots. The stack was taken down afterwards. The seed's four real solves ran on version 2 inputs.
- **As Carla (CNO):** I added ICU and BLS (BLS required to work) through the API. On Hospital rules, "Short of a skill need"
  showed 0 with its description, in Weights. I typed 50 into the form and saved: "Saved.", and the audit holds
  `weights.skill_shortfall` 0 → 50.
- **As Mona (ER's manager), on Unit rules:**
  - "Skill needs" came right after "Who a shift needs". "Add a skill need" gave "Skill need 1" at D/BLS with focus on its
    Shift, offering D, N and BLS, ICU.
  - I set it to N, ICU, 1 and 1, turned the flag off and saved: "Saved.", and the audit holds the needs and the flag before
    and after.
  - I unticked N and saved: the page said "A skill need names a shift you are taking out: ICU on N. Take the need out
    first." and sent nothing. The same body sent straight to the API was refused with the same words beside the shifts.
- **As Carla:**
  - Retiring ICU was refused: "ICU is in the skill needs of ER. The unit's manager has to take it out of them first."
  - Renaming it "Critical care" carried the name into ER's need. The audit holds `skill.changed` and a `unit_rules.changed`
    on ER by carla.
  - ER's Unit rules read "Critical care on N: at least 1 on a weekday, 1 on a weekend day" and "Never break the skill needs:
    Off", with no input.
- **The solve input on the stack.** `assemble` for ER, February 2027, gave version 2:
  - the need under its new name, the flag off, `required_skills` ["BLS"] and the weight 50;
  - the solver's precheck said "skill need N/Critical care: no nurse holds Critical care on any free day (soft: each nurse
    short is priced by skill_shortfall)".

**Findings for you, not fixed:**
- **A need written before ticket 35 counts no one.** No nurse's skills reach the solver until ticket 35, so a hard need makes
  every solve of its unit INFEASIBLE, and a soft one is paid in full. The precheck says so before the solve, as above. Nobody
  writes a need on the dev stack until 35 lands, unless you want to see it.
- **A preference on a barred day.** Preferences treat leave as superseding them; a barred day does not, so a "work this day"
  preference on a barred day costs its weight unavoidably. The cost is constant, so the roster is the same; only the cost
  and the count of preferences not kept move. That is ticket 35's or the solver's, if anyone's.

**What was NOT checked:**
- The pages at phone width, and with a screen reader. The app suite checks the accessible names, the groups, the
  descriptions and where focus goes.
- A solve, re-plan or close actually run on the stack with a need. The seed's solves ran on version 2 inputs with no needs.
  The solver's own tests decide a month by a need.
- The six parallel frontend runs and the browser checks locally: they are GitHub's, on the pull request.
- The screens were held against `better-interface`, `better-writing` and `better-accessibility` by hand, not by running
  them:
  - every input has a label, and a group's name says which need;
  - the flag's words follow night rest's;
  - the weight's description follows its neighbours' "Each … Applies only in a unit that lets …";
  - a refusal takes focus;
  - the add and remove buttons say which need.

**Decisions taken here, and Worth your review:**
- **Worth your review: the flag sits in a "Skill needs" section of its own,** after "Who a shift needs", with the table
  under it, rather than inside "Night rest". I read "beside night rest's" as worded and behaving like night rest's; the
  needs generalise team leader and gender, so they sit next to those.
- **Worth your review: the general block carries `required_skills` from now on** (the live skills marked required to work).
  Version 2 requires the field, and with no nurse's skills sent it bars nobody. A retired required skill is left out, so it
  bars nobody once ticket 35 sends skills. Ticket 35 may revisit that.
- **Worth your review: the four-nurse sample is version 2,** with empty skills. Ticket 48's lesson was that the sample must
  carry a new required field, and a version 1 input may not carry these. The solver's version 1 tests derive their input
  from it.
- **Worth your review: the page refuses a shift taken out under a need before saving,** naming the need, rather than
  dropping the need the way it drops a headcount. That follows the spec's "I take the need out first".
- **Worth your review: a new need starts at the first skill and shift with no need yet,** with both minimums at 1.
- Skill names in needs are matched exactly, case included: the catalogue already forbids two skills differing only in case,
  and the page only offers the catalogue's names.
- The migration tests run the migration's own function against today's app registry, as ticket 48's do.

**Review:** `code-review` against `0e6210d`, both axes.
- **Standards:** no hard violation. Fixed:
  - the shift and skill renames now share one carrier, where the second was a near-copy;
  - a need's key is one helper (`needKey`), no longer a space-joined string built three times;
  - `needed` is renamed `stranded`.

  Kept:
  - the live-skill query twice in `rules_api.py`: each is one line;
  - the page and the API both holding the shift-guard and repeated-pair words: the page refuses before sending, as it does
    for headcounts;
  - a second focus effect beside the headcounts' rather than a shared hook;
  - `version_2(...)` wrapping at each test call site rather than changing each file's `er_request()`, which other tests
    use as the version 1 sample.
- **Spec:** nothing missing. Its points:
  - the flag's place (above);
  - `required_skills` (above);
  - the shift rename through needs, which `with_shift_codes` owes them;
  - a repeated pair on a retired skill gets only the retired refusal on the second row (the save is still refused);
  - the page's wording for a need on a shift that was never the unit's ("taking out");
  - an archived unit's need on a retired skill blocks that unit's next save until removed, as for shifts.

No adversarial review, by the brief.

**Things later tickets should know.**
- **35 (solving with skills):**
  - The input is already version 2 with the needs, the flag, the weight and `required_skills`. What is left is the nurses'
    `skills`, changes since, the rename on read of stored inputs, and the words in dates.
  - `required_skills` comes from `hospital.rules.required_skills()`, live skills only; change it there if retired ones
    should bar.
  - `tests.er_fixture.version_1` in the solver makes a version 1 input from a version 2 one.
  - A backend test pairing the version 1 ER sample with today's blocks needs `"version": 2` and the department's two skill
    fields: `hospital.tests.test_rules.version_2` does it.
- **Anyone adding a required unit-rule field:** the sample is version 2 now, so a version 2 field goes straight into it.

**Reviewed by the user (2026-11-09):** all five points kept as recommended.
- The flag in its own "Skill needs" section.
- `required_skills` carried in the general block, live skills only.
- The four-nurse sample in version 2.
- A shift taken out under a need refused, naming it.
- A new need's starting pair and minimums of 1.
- A "work this day" preference on a barred day is left to ticket 35.
