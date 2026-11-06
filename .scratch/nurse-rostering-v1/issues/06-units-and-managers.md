# 06: Units and their managers

**What to build:** The CNO creates units, renames them, archives a unit that has no nurses, and assigns each unit exactly one unit manager account. A unit manager with no unit assigned can log in and sees "no unit assigned"; an assigned manager sees only his unit everywhere. The CNO reassigns a unit when its manager is unavailable.

**Blocked by:** 03 Management accounts

**Status:** ready-for-agent

- [x] Create, rename, archive (refused while nurses belong to it) units; audited
- [x] Assign and reassign exactly one Unit Manager account per unit; a manager account can hold one unit
- [x] Unit manager home shows the unit or 'no unit assigned'; every unit-scoped endpoint resolves the caller's unit and refuses others
- [x] Unit rules row seeded with the reviewed defaults and a review flag when a unit is created
- [x] API tests cover creation, archive guard, assignment cardinality and scoping

## Comments

Implemented on 2026-11-05. Backend under pytest on real PostgreSQL 18, frontend under Vitest with the real routes and generated client over a stubbed `fetch`.

Driven on the dev overlay in the built-in browser: the CNO's home naming a unit with no manager, the Units page, a taken name refused beside its field with focus on it, a rename and assignment in one save with focus back on the row, a manager holding another unit disabled in the select and saying which, archiving with focus on the name field, no sideways page scroll at 375 px, the manager's home with their unit and the review note, the Users page's question before deactivating that manager, and the audit log naming every new action. Over the API on the same stack: a manager reads their unit, gets 403 on another's and on every write, and the System Admin gets 403 on units.

What was not checked:

- **A real refused archive.** No nurse can belong to a unit yet. The guard is tested through `Unit.nurse_count` stubbed to say 1 and 2, so it is proven at the seam only, and it is **not a guard against anything until ticket 07 replaces that method's body**. The criterion is ticked on that footing.
- **A manager with no unit in a browser** is a route test, as is the refused archive's dialog. The API side of no unit was driven.
- **Two people assigning at once.** The locks and the one-to-one field are there by design; no test races them.
- **The production compose file through Caddy.** Only the dev overlay ran, as in tickets 04 and 05.

Decisions this ticket took:

- **Deactivating a manager takes them off their unit** (`units.assignment.release_managed_unit`, called in `accounts.provisioning.deactivate`'s transaction, audited as `unit.changed` with the System Admin as actor). Refusing would make cutting off an account wait for a CNO, and the System Admin never touches assignments. Keeping them on the unit would leave a unit nobody can run, looking as though it had a manager. Reactivating does not give the unit back, because the CNO may have assigned another. The Users page says this in its question, and the CNO's home names every unit with no manager; there is no notification yet (15).
- **"Exactly one" is at most one in the database, with the gap made visible.** A unit is created with or without a manager, because the System Admin may not have made the account yet, and deactivating opens the same gap. `docs/ARCHITECTURE.md` section 3 now says so.
- **A manager already holding a unit is refused, not moved.** Moving would silently empty the other unit. So the CNO can also take a manager off (`manager_id: null`), which is how two managers change places.
- **Name, manager, one save.** `PUT /api/units/{id}` takes both, as the other lists' forms do, so a rename and a reassignment are one audited change: `unit.changed`, with only what differs.
- **Names are unique in any case among units not archived.** A hospital can close a unit and open another under its name; the old row stays on record.
- **Archiving has no way back, and lets the manager go.** `units_archived_unit_has_no_manager` makes this a database rule, so a manager's unit is always a live one and `units.scope` needs no archived check. A mistaken archive means a new unit under the same name with fresh defaults. An unarchive endpoint would be small; no ticket asks for one. **Worth your review.**
- **A manager's refusal is the same 403 whether the unit exists or not**, since "a unit manager sees nothing of other units". The CNO and Deputy CNO get 404.
- **The Deputy CNO may read units over the API** with no page yet. Section 3 gives that role every unit's rosters and now has a row for reading units, and `units.scope` has to answer for them for ticket 09's read access. `GET /api/units/{id}` likewise has no page calling it: it is the endpoint that proves scoping over HTTP, and later tickets' pages can use it.
- **Seeding when the catalogue has moved (`units.rules.seeded_rules`).** A default code means one shift for good, because no other shift may take a code one held. So a renamed D seeds under its current code, and the block still passes the solver's `load_request`. A retired D is left out of `shifts`, `headcounts` and `fair_shifts`, and `day_shift` becomes `""`; if both are retired, `shifts` is empty. The unit is still created, with the flag up. It does not refuse (a hospital that retired D could otherwise make no unit) and does not substitute another shift (hours and meaning would be a guess). The solver refuses that block, so the gap cannot reach a roster unnoticed. **Worth your review.**
- **`rules` holds no `name`.** `unit_block(unit)` adds the unit's name, so a rename touches one place.
- **The manager's home shows the review flag as a statement only**, because the form to clear it is ticket 09's. It is not shown to the CNO, who does not own unit rules.
- **A row's actions are not sticky on the Units page**, against ticket 03's advice and as on the holidays page: at 375 px two sticky buttons would cover the name and manager, which are what the row is for. The table scrolls inside its card.
- **The System Admin sees unit names** on the Users page and in the audit log. A unit's name is neither a roster nor a rostering attribute. Default rule values are not written to the audit log.

Things a later ticket should know:

- **Scoping (all later tickets):** an endpoint names roles with `SignedIn`, then calls `units.scope.unit_in_scope(request.user, unit_id, for_update=...)` for one unit or `units_in_scope(request.user)` for a list. The walking test cannot see this, so **each unit-scoped endpoint needs its own test that another unit's manager gets 403**. Put the unit id in the path. For a resource reached by its own id, such as a nurse or a roster, load it and then call `unit_in_scope` with its unit. The role decides what a CNO may do, so an edit only the manager may make needs `SignedIn(Role.UNIT_MANAGER)` as well as this.
- **What ticket 07 must add:**
  - The body of `Unit.nurse_count`, which returns 0 today, counting real nurse profiles, with a test that replaces the two stubbed ones in `units/tests/test_units.py`. Decide there whether a nurse past her end date still belongs.
  - Lock the unit's row (`select_for_update`) when adding or transferring a nurse into it. `archive_unit` counts under that same lock, so the two cannot interleave.
  - What "belongs" means, and the refusal's wording with it. It says "Transfer or deactivate them first", so deactivated nurses must not count, or the advice is false since nurses are never deleted. Then reactivating a nurse, or a transfer into the unit effective in a later month, must be refused while the unit is archived, or she lands in one. Choose otherwise only with the message changed.
  - A staff nurse's branch in `units_in_scope`, which returns nothing for her today, with `test_other_roles_have_nothing_in_scope` changed to match. `HOSPITAL_WIDE` must stay out of it. Refuse adding a nurse to an archived unit.
  - A manager with a nurse profile: this ticket's scope is the unit they hold, so either require their profile to be in that unit or decide otherwise.
  - Taking a manager off a unit does not touch any nurse profile they have.
- **What ticket 09 must add:**
  - The form and schema, in the shape of ticket 04: `StrictSchema`, `field_validator`s, solver field names, saving clears `rules_need_review`. `night_shift` and `day_shift` may hold `""` and `shifts` may be empty, so **the answer schema must be a plain `Schema`** and the form must start from a blank select, or a retired-at-seeding unit cannot be opened.
  - **Renames:** in `_carry_rename_through_the_rules` in `hospital/catalogue_api.py`, for every unit including archived ones, read the row with `select_for_update`, set `unit.rules = with_shift_codes(unit.rules, {old: new})` and audit it, leaving the review flag alone. That function already knows every place the block names a shift. `create_unit` seeds under the same lock, so nothing slips between. The row lock matters because `update_unit` saves the whole row. Allowed-shifts lists need carrying there too.
  - **Saving the rules takes the catalogue's lock too** (`HospitalSettings.load(for_update=True)`, as `update_rules` does), before checking its codes against the active catalogue, or a manager's save can write a code the CNO is retiring or renaming at that moment.
  - **Retirement:** in `update_shift`, under its lock, `refuse((("active",), ...))` naming the unit when any unit not archived names the code in `rules["shifts"]`, `night_shift` or `day_shift`. The last two count because the solver only requires them to be in `shifts` while the night rules are on, so a saved block can name one outside it. Archived units do not block.
  - **Stale rows:** nothing carries a rename through `Unit.rules` until then, so a row seeded and then renamed on a development database will name the old code. No installation is live, so no migration is planned. Add one if that changes.
  - **Fields:** `request_cap` (default 3) and `default_time_limit` (default 60 s) from section 4 and 9 are not on `Unit` yet. Add them with those defaults in a migration; no criterion here reads them. The hospital-wide request cap default in section 4 still does not exist.
  - The Home page's review note should link to the form once it exists.
- **Solve input (11):** build the block with `unit_block(unit)`. It raises in the solver for a unit left with a gap by seeding, so show that as "review the unit rules" rather than a failed solve.
- **Lock order:** `HospitalSettings` (the catalogue), then the user's row, then the unit's; a step may be skipped. `release_managed_unit` runs inside `deactivate`'s user lock, and `_manager_to_assign` takes the user's before `update_unit` takes the unit's.
- **Moved:** `save_unless_taken` is now public in `hospital/api.py`.
- **Audit actions added:** `unit.created`, `unit.changed`, `unit.archived`, all named in `ACTION_NAMES`.
- **Frontend:** `routes/_signed-in/units.tsx` is CNO only. A manager finds their unit's id with `useListUnits` (zero or one row), and a later manager page should do the same. `ManagedUser` now has `unit`.

**Review (2026-11-05).** The `code-review` skill's two axes found the CNO's home hiding a failed read (so a unit with no manager could go unnoticed), `GLOSSARY.md` contradicting the new rule on managers, a hint not tied to its select, the home page no longer forcing a new role to have a home, an untested claim that the solver refuses a block with no shifts, three copies of the same comparison, and gaps in the hand-over to tickets 07 and 09 (what "belongs" means, the lock on saving unit rules, `night_shift` and `day_shift` in the retire guard). All fixed. Left as judgement calls: `UnitBody` is not strict because ids are strings in JSON, with a test that a number is refused as a name; `save_unless_taken` would report any constraint on a unit as a taken name, which only the name's can reach because `_manager_to_assign` holds the account's lock; `hospital/api.py` holds generic helpers beside the rules; `units.tsx` finds the name field by `FormField`'s id, as `holidays.tsx` does. The `interface-review` skill itself was not run; the pages were held to the `better-*` rules by hand and by that review.

**Reviewed by the user (2026-11-05), and kept as built:** the manager assignment rules; no unarchive; a unit seeded with a gap, which ticket 11 shows as "review the unit rules".

**Reviewed by the user (2026-11-06).** From the review of every unsettled item across tickets 01–20, answered as recommended. Kept as built: the same 403 for a unit that does not exist (L36); the Deputy CNO reads units over the API only (L37); the review flag as text only on the manager's home (L40); row buttons not pinned on Units (L41).
