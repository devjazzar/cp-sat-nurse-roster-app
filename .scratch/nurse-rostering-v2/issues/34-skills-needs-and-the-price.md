# 34: Skill needs among the unit rules, the price among the weights

**What to build:** A unit manager writes skill needs among his unit rules: a shift the unit works, a skill, a weekday minimum and a weekend minimum, several per unit, and one flag making them all hard or soft, hard by default. The CNO sets the skill shortfall weight among the hospital weights, the price per nurse short per shift-day when a unit's needs are soft. What the forms save passes the solver's loader as version 2. A shift a need names cannot be dropped from the unit; a skill a live unit's need names cannot be retired; a skill rename is carried through every unit's needs.

**Blocked by:** 31 Solver: skill rules and solve input version 2; 32 The skill catalogue

**Status:** ready-for-agent

- [ ] The unit rules carry `skill_needs` and `skill_needs_hard`; seeded empty and hard; the hospital rules' weights carry `skill_shortfall`, seeded at zero. The test that holds the saved blocks to the solver's own fields covers them.
- [ ] A need is refused when it names a shift outside the unit's shifts or a retired skill, or names the same shift and skill twice; minimums are non-negative integers within the solver's parameter limit.
- [ ] Dropping a shift from the unit is refused while a need names it, naming the need, as it is while a pin uses it; retiring a skill is refused while a live unit's need names it, naming the units, as retiring a shift is; a skill rename runs through every unit's needs in the same transaction, audited per unit.
- [ ] The unit rules page gains a skill needs table (add, edit, remove) and the hard flag beside night rest's; the hospital rules page gains the weight; the CNO and Deputy CNO read a unit's needs read-only as the other rules.
- [ ] Audit: unit rule and hospital rule changes keep logging their values; skill needs say nothing about a person.
- [ ] The architecture document's unit rules and hospital settings entries name skill needs and the weight.
- [ ] Tests at the web API seam for the rules, the refusals, the guards and the rename; frontend tests for the table and the flag through the app test file.

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
