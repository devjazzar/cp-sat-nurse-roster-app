# 31: Solver: skill rules and solve input version 2

**What to build:** The vendored solver understands skills. A version 2 solve input carries, per nurse, her skills with the expiry each counts to (or none); in the unit's block, its skill needs (shift, skill, weekday minimum, weekend minimum) and whether they are hard; in the hospital's block, which skills are required to work and the skill shortfall weight. The roster then meets each skill need or pays the weight per nurse short, keeps a nurse off every shift after a required skill of hers expired, and carries the hours she cannot work as debt. Precheck says beforehand what cannot be met; explain and validate name the two rules like every other. A version 1 input still loads as one with no skills, so stored inputs still explain and old months still close. Spec: `.scratch/nurse-rostering-v2/specs/skills-per-shift-day.md`; the reasons: `docs/adr/0010-skill-rules-in-the-solver.md`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] Two rules in the registry: **skill need** (hard or soft by the unit's flag, weight `skill_shortfall`, unit "nurse short of a skill need on a shift-day", active when the unit has any need) and **skill expired** (hard, unit "shift on a day a required skill has expired", active when any nurse in the month holds an expired required skill). Model, validator and explain follow the registry, as for every rule.
- [x] A skill need counts nurses on exactly its shift on each free day against the weekday or weekend minimum; soft, the penalty is the weight per nurse short per shift-day; hard, the count must reach the minimum. Elapsed days are facts, reported apart.
- [x] The bar: from the day after an expired required skill's last day the nurse works no shift. The most hours she can work excludes those days, so the hours her remaining days cannot hold are unreachable, exempt from the avoidable-shortfall floor and carried over as debt, by the existing mechanism. A nurse with no record of a required skill is not barred.
- [x] Request version 2: nurse `skills` (skill name to expiry date or null), department `skill_needs` and `skill_needs_hard`, general `required_skills` and `weights.skill_shortfall`. The expiry is the one dated field accepted before the month; a date after the month is refused; a skill name must be in no list twice; a need must name a shift of the unit. Version 1 loads as version 2 with no skills, no needs, the flag at hard, no required skills and the weight at zero. The result's version is unchanged.
- [x] Precheck lines: a need naming a skill no nurse holds on any free day; a need whose minimum exceeds the nurses who hold the skill and may work the shift, overall and per free day against those not on leave or barred; per nurse, each required skill expiring inside the month, with its last day. Barred days count like leave in the capacity sums.
- [x] The validator's and explain's words give the rule, the shift, the day and the count short, in the solver's day numbering as today.
- [x] Tests at the agreed seam: the rule suite in the constraint-verifier style (hard and soft; a need met, short by one, short by two; the bar with and without a record; an expiry inside the month counting before and not after; the hours carried as debt; elapsed days as facts), precheck lines, explain words, the loader on version 1 and version 2 and its refusals; one service contract test on a version 2 input. The solver's DESIGN notes gain the contract change.

## Comments

**Implemented on 2026-11-09,** on branch `claude/ticket-31-solver-skills-6b2fe1`, pull request
MoustafaJazzar/cp-sat-nurse-roster-app#5, from `main` at `bee0073`. The suites, locally:
- the solver's whole suite with the service tests (`cd solver && uv run --no-sync pytest -q`): 527 passed (57 new in
  `tests/test_skills.py`, one new contract test; existing tests moved to version 2 where they wrote requests);
- the backend under pytest on a throwaway PostgreSQL 18 container of my own: 2554 passed and 4 failed on the solver change
  alone (the field-sync tests, below); with their narrowing, those three files pass (153); no model changed, so no migration;
- no frontend, OpenAPI or Playwright change: those runs are GitHub's, on the pull request.

**What the dev stack needs:** a **rebuild** (`docker compose up -d --build`) after the merge: the vendored solver package
changed. No dependency, migration, compose or Dockerfile change. The app still writes version 1, read as "no skills", so a
solve on the stack prices exactly as before until tickets 34 and 35.

**What was built, criterion by criterion.**
- **Two rules in the registry** (`rules.py`). `skill_need`: hard or soft by `department.skill_needs_hard` (as night rest's),
  weight field `skill_shortfall`, unit "nurse short of a skill need on a shift-day", on when the unit has a need.
  `skill_expired`: hard, unit "shift on a day a required skill has expired", on when some nurse holds a required skill
  expiring before the month's last day. The model adds terms and the validator checks exactly when `active()` says so; the
  registry test now holds `{RULES[id].weight}` to the `Weights` fields.
- **The skill need.** Per need and day, the nurses on exactly its shift who hold the skill that day (`problem.holds_skill`:
  recorded, the day not after its expiry) against `SkillNeed.minimum(weekend)`. Hard: `Σ x ≥ min` on free days. Soft:
  `short ≥ min − Σ x`, one term per shift-day at the weight. Elapsed days: a hard shortfall is a fact (`Analysis.elapsed`,
  the result's `elapsed_violations`); a soft one is still priced and marked elapsed, as every soft rule's past is. Tested
  met, one short and two short, hard and soft, the weekend minimum, an expiry inside the month counting before and not after,
  one expired before the month counting on no day, the solver's objective equal to the validated cost, and an unmeetable hard
  need INFEASIBLE.
- **The bar.** `problem.barred_days`: every day after the first expiry of a required skill of hers (-1, before the month:
  all days). The model fixes her off on each free one; the validator reports a shift on one; `max_hours` skips them like
  leave, so what her remaining days cannot hold is `unreachable_hours`, exempt from `avoidable_shortfall` and carried whole
  in `hours_balance`. Tested on seven days: 48 h owed, 24 h reachable, the solver idles her from day 2 at cost 0, 24 h carried;
  without the requirement the same idle days cost 13 h of avoidable shortfall. No record, a skill not required, no expiry, or
  an expiry on the month's last day: no bar. A shift pinned on a barred free day is refused (as on leave); an elapsed one is
  a fact.
- **Request version 2** (`request.py`). Version 2 adds the five fields; the expiry is the one date accepted before the month
  (read as -1) and a date after the month is refused ("is after 2026-06 (a skill that counts all month has no expiry: null)").
  A skill named twice in `required_skills`, a second need for one shift and skill, a need on a shift the unit does not work, a
  minimum out of range are refused. Version 1 loads on copies as version 2 with no skills, no needs, the flag hard, no
  required skills and the weight 0; the stored input is untouched (tested). The result's version stays 1.
- **Reconciling the two versions.** The request goes 1 → 2 and still reads 1; the internal problem's schema goes 4 → 5 (the
  new rule fields required in a problem file, the nurse's `skills` optional) and reads only 5, as 3 → 4 did. They differ on
  purpose: the request is the app's stored history (ADR 0010), the problem file is built by the loader and stored nowhere.
- **Precheck lines.** A need whose skill no nurse holds on any free day; a need whose largest minimum exceeds the holders who
  may work the shift; per free day, a minimum above the holders who may work it that day (not on leave, pinned elsewhere or
  barred); per nurse, each required skill expiring inside the month with its last day. Barred days count like leave in every
  capacity sum (per nurse and per day). When the needs are soft, each need line ends "(soft: each nurse short is priced by
  skill_shortfall)".
- **The words**, in the solver's day numbering: "skill need: day 4 N has 1 holding ICU, needs 2 (1 short)" (amount: nurses
  short) and "skill expired: Dana works N on day 25, BLS is required to work and its last day was day 23" ("was before the
  month" for an earlier one). Through `/validate` the app gets them dated (tested).
- **Tests and docs.** `tests/test_skills.py`; one service contract test on the version 2 sample
  (`service_tests/fixtures/four_nurses_skills.json`: precheck, solve, `/validate`); `solver/DESIGN.md` (request version 2,
  schema 5, the two rules), `solver/how-to.md` (the fields, the weight, the debt) and one paragraph of `docs/ARCHITECTURE.md`
  section 6.

**What was driven, and how.** The CLI on the new sample: `uv run python -m nurse_roster solve
service_tests/fixtures/four_nurses_skills.json --explain`: the precheck line for Dana's BLS (last day day 23), Dana off from
the 25th, `skill_need 100 = 2 x 50` with its two nights short of ICU after Badr's expires, hard rules all met, cost matching
the solver's objective. Nothing in a browser: nothing in the app changed.

**What was NOT checked:**
- A solve on a stack with skills fed: the app writes version 1 until 34 and 35.
- How the soft need's price competes with the fairness weights on a real unit: the CNO's to set.
- Performance on the real ER with many needs (one term per need and shift-day; small next to the headcount's).

**Decisions taken here:**
- **Worth your review: four backend tests narrowed (decided by the main session).** They hold the app's hospital and unit
  blocks to every field of the solver's; the solver now has fields the app gains in ticket 34. Each subtracts
  `VERSION_2_SKILL_FIELDS` with a comment that 34 deletes it; ticket 34's file says so too. No app code changed.
- **Worth your review: the rule ids `skill_need` and `skill_expired`, the weight `skill_shortfall`.** The only rule whose
  weight field is not its id; the result's `penalties` key is `skill_need`. The other choice, id `skill_shortfall`, would
  have named a hard violation after a price.
- **Worth your review: an expiry before the month is read as -1, "before the month",** whatever the date: the words never
  show the real date (the app has it). It keeps the problem's bound simple.
- **Worth your review: the problem's new dataclass fields have Python defaults** (empty, hard, 0), so code building a problem
  by hand need not name them; a problem file must still carry them. The older rule fields have none.
- **Worth your review: refusals the spec did not list:** a version 1 input carrying a version 2 field; a pin of a shift on a
  barred free day (as on leave); at most 100 skills a list (`MAX_SKILLS`). Ticket 34 already refuses a repeated shift and
  skill.
- **Worth your review: when several required skills expired, the bar and the words follow the earliest.**
- **Worth your review: precheck says nothing of a required skill expired before the month,** only of one expiring inside it,
  as the ticket lists; the hours line ("… h owed but at most … fit her free days") shows such a nurse. Nor of one whose last
  day is the month's last (nothing is barred this month).
- **Worth your review: fairness does not treat barred days as leave.** A barred nurse's Friday share is not prorated, so a
  constant `fair_weekend` cost and a lower `friday_balance` may carry; the spec names only `max_hours` and precheck.

**Review:** `code-review` against `bee0073`, both axes. *Standards:* helpers moved beside `holds_skill` in `problem.py`
(`skill_holders`, `expiry_words`), `skill_valid` renamed `holds_skill` (the glossary's verb, not "valid"), the weekday/weekend
minimum is `SkillNeed.minimum`, `READABLE_VERSIONS` named, a split comment and stray blank lines fixed. Kept: the dataclass
defaults and the id/weight split (above); tests of `barred_days` beside the validator's (a small helper the three readers
share, worked by hand). *Spec:* soft needs' precheck lines now say they are priced, not infeasible. Kept: the refusals above.
No adversarial review, by the user's call.

**Things later tickets should know.**
- **32 to 34:** the solver's names: general `required_skills` (names, each once) and `weights.skill_shortfall`; department
  `skill_needs` (`{"shift", "skill", "weekday_min", "weekend_min"}`, mins 0..1000, one a shift and skill) and
  `skill_needs_hard`. Skill names: non-empty, at most 100 characters, no leading `= + - @ '`. 34 deletes
  `VERSION_2_SKILL_FIELDS` from the three test files.
- **35:** write `"version": 2` and every field at once (a version 1 input may carry none of them). A nurse's `skills`:
  `{name: "YYYY-MM-DD" or null}`; null for a skill valid past the month (a later date is refused), its date for one expired
  before (absence means no record). A pin on a barred free day is refused with its date, so drop or set those pins aside
  first (38).
- **36 to 38:** violation rules `skill_need` (department-level, `nurse` null, amount the nurses short) and `skill_expired`
  (per nurse and date). `problem.barred_days` and `holds_skill` are the solver's readings if the app needs them.
- **47:** request version 2 is the version a new field joins; an optional nurse scalar can stay in 2 as
  `preferences_not_kept` did, a new required rule field needs a version 3 and the same reading of 1 and 2.
