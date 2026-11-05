# 09: Unit rules and rostering attributes

**What to build:** The unit manager edits his unit's rules (the shifts it works, chosen from the catalogue; headcounts per shift for weekdays and weekends; team leader and gender requirements; score targets; night rest; run limits; fairness; weekend limits; switches; the request cap and default time limit), each explained and seeded with the reviewed defaults. He sets each nurse's rostering attributes (team leader, score, allowed shifts, Ramadan-reduced, breastfeeding) and her opening values. The CNO is refused when retiring a shift a unit still uses.

**Blocked by:** 05 Shift catalogue; 07 Nurses

**Status:** ready-for-agent

- [x] Unit rules form with every field of the solver's unit block, explanations, validation; clears the review flag on save; audited
- [x] Shifts used are a subset of the active catalogue; retiring a shift in use by any unit is refused with the unit named
- [x] A shift's rename carries through every unit's rules in the same transaction (see ticket 06's comments)
- [x] Per-nurse rostering attributes form; allowed shifts restricted to the unit's shifts
- [x] Opening values editable (overtime this year, hours balance, two fairness balances), default zero
- [x] Only the unit's manager edits; CNO and Deputy CNO read; nurses never see attributes
- [x] API tests cover rules, the retire guard, attributes and scoping

## Comments

**From ticket 07a (2026-11-05): gender stays out of this ticket's form.** The CNO sets and corrects it (`nurses.api.correct_details`), and section 3 now says so. It is not on this ticket's list of attributes, though the glossary counts it among them.

Implemented on 2026-11-05. Backend under pytest on real PostgreSQL 18, frontend under Vitest with the real routes and generated client over a stubbed `fetch`.

Driven in the built-in browser, **not on the dev overlay**, whose `admin` password no session knows: a scratch PostgreSQL held a CNO, a Deputy CNO, a System Admin, two managers and their nurses, with `runserver` and Vite on their own ports at `127.0.0.1`. It is dropped. As a manager: the home's link; the form with the flag; a night shift outside the unit's shifts refused by the API beside its field with focus on it; adding a shift and a headcount with focus following; a save clearing the flag and surviving a reload; the unit's shifts refused, naming the nurse who could work none of them, with focus on the list; the attributes form, with a score refused on the client and focus on it, opening values, a save, and focus back on the row; a manager's own form saying who can see it; a manager's form for a nurse due to join, showing only the allowed shifts. As the CNO: retiring D refused, "D is in the unit rules of ER, ICU", beside the switch with focus on it, and both pages read-only with the unit chosen in the address. As the Deputy CNO: both pages with no input or button. As the System Admin: the audit log naming the new actions, unit rule values shown, and attribute changes with no details at all. No sideways page scroll at 375 px on the manager's table, form and rules, and on the CNO's read-only pages. Most of the numbers went in by script, and Save was mostly pressed by script; the score went in by keyboard.

"What the forms save passes the solver's `load_request`" is proven in tests, at the seam, because no solve exists yet: the saved block through `unit_block`, and a nurse through `nurses.rostering.nurse_block`, at the limits of what the API accepts, after a rename and through a transfer. `test_what_the_api_accepts_at_its_limits_the_solver_accepts` is the one to extend.

What was not checked:

- **The dev overlay and the production compose file through Caddy.** See above.
- **A rename in a browser.** API tests only.
- **Two people at once.** The locks are by design and no test races them.
- **Dark mode, and browsers other than the built-in one.**
- **Real clicks on every control.** Many went by script, so a control's own hit area was not tested everywhere.

How the earlier tickets' instructions were handled:

- **Ticket 06, the answer schema:** `UnitRulesAnswer` is a plain `Schema`, and the form starts from blank selects, so a unit seeded with a gap opens. Saving it is refused until the choices are made. Two field lists therefore repeat; a test holds both to the solver's.
- **Ticket 06, renames:** `_carry_rename_through_the_units` sits beside `_carry_rename_through_the_rules` and runs in the same transaction for every unit, archived too, under row locks in id order, audited for each unit it changes, leaving the review flag alone.
- **Ticket 06, the catalogue's lock:** saving rules or attributes takes it first, and checks codes under it.
- **Ticket 06, retirement:** refused in `update_shift` under its lock when a live unit names the code in `shifts`, `night_shift` or `day_shift`. Archived units do not block.
- **Ticket 06, fields:** `request_cap` and `default_time_limit` are on `Unit`, defaults 3 and 60.
- **Ticket 06, the home page:** its review note links to the form.
- **Ticket 05, the hours guard: not built, because there is nothing to check.** No roster exists. `update_shift` says so, and ticket 11 has a comment to add it as a refusal on `hours`.
- **Ticket 07, `record`:** attributes stay out, as below.
- **Ticket 07, a nurse by id:** the path is `/units/{unit}/nurses/{nurse}`: `unit_in_scope`, then the nurse must be on that unit's list, with the same 403 whether they exist or not. This differs from the note's `unit_id_now`, which cannot reach a nurse due to join.
- **Ticket 07, allowed shifts through a rename:** `carry_rename_through_allowed_shifts`, on every placement.
- **Ticket 08, the staff list: attributes stay off it.** It is a file that leaves the system, and a score or a breastfeeding flag has no business on someone's desktop when the CNO can read it here. A test holds it. **Worth your review.**

Decisions this ticket took:

- **Allowed shifts are on the placement, not the profile.** Section 4 and the glossary now say so. A unit may roster any future month, so one list cannot serve a nurse's current unit and the one they join in January at once.
- **When a unit's shifts change:** a list loses a shift the unit stops working, which never widens what a nurse may do. If a nurse placed there or due to join would have none left, the save is refused, naming them, and nothing changes. Past placements narrow too, or a transfer back could bring back a stale list; one left with nothing is emptied and flagged.
- **On a transfer:** the list follows as far as the new unit works the same shifts. With none in common it empties to "any shift", and the new manager sees "To check" and a sentence naming the nurse until they save. **Worth your review:** a restriction with no meaning in the new unit does lift until that manager looks. The solver takes no empty list, and a transfer is the CNO's, who cannot choose.
- **A nurse due to join:** the new unit's manager reads all their attributes and sets only their allowed shifts there. The rest stays with their current unit's manager until they arrive, and a unit with no manager waits for one. **Worth your review:** the wider read is ours; the criterion says only "the unit's manager", and that manager will roster them.
- **A manager with a nurse profile sets their own attributes,** including their score and allowed shifts, because the CNO and the Deputy CNO only read and a nurse has to have them. The form says who can see it, and the log shows `actor` and `target` the same. **Worth your review.**
- **The audit log holds whose attributes changed and by whom, and nothing else:** `nurse.attributes_changed` has no before or after, not even the field's name, because a change to a two-way flag such as breastfeeding gives its value away. This is stricter than `gender_changed`. Narrowing a list writes no entry of its own: the rules' entry shows the shift that went, and an entry or a count beside it would tell the System Admin what a nurse could work.
- **Unit rules are logged with their values,** as hospital rules are, though the System Admin gets 403 on them: they say nothing about a person. **Worth your review.**
- **Score defaults to 0.8, the solver's own default,** and the rest to its defaults too, with opening values at zero. A test holds them to the solver's. **Worth your review:** nothing marks a score nobody has looked at.
- **Stricter than the solver on purpose:** the score ceilings are held above the targets whenever balancing under a ceiling is on, whatever the CNO's weights, because those can change later. The night and day shifts must always be active shifts and differ.
- **Limits of our own:** a request cap of 0 to 31. The default time limit may not exceed the System Admin's cap when saved; lowering the cap later refuses the next save until it is lowered too.
- **A shift with no headcount is allowed,** as the solver allows it, for a shift that only counts towards another. The page says what that leaves out.
- **A deactivated nurse's attributes can still be set,** since a refused save can name one.
- **`nurse_block` is called only from tests,** like `general_block`: it is the seam that proves the attributes reach a solve input.

Things a later ticket should know:

- **Solve input (11):** see the comment there.
- **Request windows (19):** read `Unit.request_cap`.
- **Month close (21):** see the comment there.
- **Lock order:** the catalogue, then the user and the profile, then the unit. `transfer_nurse` now takes the catalogue's lock first, because it copies codes.
- **Audit actions added:** `unit_rules.changed`, `nurse.attributes_changed`, named in `ACTION_NAMES`.
- **Frontend:** `Section`, `ReadOnlyList` and `onOff` moved to `components/rules-section.tsx`. `CodeCheckboxes` picks several shifts. `useChosenUnit` and `UnitPicker` give a page its unit: a manager's own, or one in the address for a hospital-wide role.
- **Test helper:** `make_unit` in `nurses/tests/conftest.py` now seeds real rules, because a rename and a retirement read them.

**Review (2026-11-05).** The `code-review` skill's two axes found a stale list coming back on a transfer into a unit that had since dropped a shift, a transfer copying from the wrong placement, a count of narrowed lists in the log, units locked in a different order from an import's, a 500 when a transfer is cancelled while its nurse is being saved, and duplicates and names. All fixed. The browser also found the row's one action out of reach at the end of fourteen columns, now beside the name. Left as judgement calls: TanStack Table, as in tickets 07 and 08, which ADR 0008 names and no page yet uses, so this list extends a known breach; the shells of the two pages repeat; a new solver field touches both schemas, the form and the read-only view, as ticket 04 left it; `membership.py` now also holds the allowed-shifts rules. A one-shift unit saved while the CNO's `shift_switch` weight is 0 is refused by the solver if that weight later rises, which ticket 11 has to show. `better-interface` and its six domain skills were held against the pages by hand, since `interface-review` is user-invoked.

**Reviewed by the user (2026-11-05), and kept as built:** managers set their own attributes; a joining unit's manager reads all attributes; what the System Admin sees in the log, unit rule values included; the staff list's contents, with attributes off it; allowed shifts narrowing when a unit drops a shift. Two flags are decided rather than kept: a list a transfer emptied now blocks a solve until checked, and scores nobody has reviewed at 0.8 get a count beside the precheck (both in ticket 11's last comment). TanStack Table is no longer a breach here: ADR 0008 changed on 2026-11-05, so short lists stay plain tables and TanStack Table is for the roster grid and any table that needs sorting or filtering.
