# 07: Nurses, one at a time

**What to build:** The CNO adds a nurse: hospital ID, full name, gender, unit and start date. Her account is created with the hospital ID as username and a generated password shown once; at first login she must change it and then sees her unit's roster page with "no roster yet". The CNO transfers a nurse to another unit effective from a chosen month, sets an end date to deactivate her, and the CNO or her unit manager resets her password. Nurses are never deleted.

**Blocked by:** 06 Units and managers

**Status:** ready-for-agent

- [x] Add a nurse creates the user, the nurse profile and the password shown once; hospital ID unique
- [x] A unit manager may also be given a nurse profile by the CNO; role stays Unit Manager
- [x] Transfer with an effective month; end date deactivates; no delete endpoint
- [x] Password reset by the CNO for any nurse and by the unit manager for his unit's nurses only
- [x] Staff nurse home shows her unit and 'no roster yet'
- [x] Unit manager sees his unit's nurse list; names and shifts only is enforced for nurses from the start
- [x] Archiving a unit is refused while a nurse belongs to it: `Unit.nurse_count` counts real nurse profiles (see ticket 06's comments)
- [x] A nurse's unit is in `units.scope`, so unit-scoped endpoints resolve it for her (see ticket 06's comments)
- [x] API tests cover creation, uniqueness, transfer, deactivation, resets and scoping

## Comments

Implemented on 2026-11-05. Backend under pytest on real PostgreSQL 18, frontend under Vitest with the real routes and generated client over a stubbed `fetch`.

Driven on the dev overlay in the built-in browser: the CNO adds a nurse, the password dialog with focus back on the opener, a transfer waiting for January 2027 with focus back on the row, no sideways page scroll at 375 px, a reset, that nurse's first login with the forced change and then their home with their unit and "No roster yet.", the manager's list saying "Leaves from January 2027" without naming the other unit, the unit in the address, and clearing an end date into an archived unit refused beside the field with focus on it. Over the API on the same stack: a taken ID in another case, a real refused archive ("2 nurses belong to ER"), another manager's 403 on a reset, `no-store` on both password answers, a nurse's 403s during and after the forced change, and the audit entries as the System Admin reads them. The worker ran `close_ended_nurses` when deferred by hand and, separately, on its own schedule, each deactivating a nurse whose end date had passed, with no actor on the entry. For the second run the minute was set to a few minutes ahead for that test, then put back to `:05`, so `5 * * * *` itself did not fire on the real stack; a test holds that it is what is registered.

What was not checked:

- **Two people at once.** The locks are there by design; no test races them.
- **The production compose file through Caddy.** Only the dev overlay ran, as in tickets 04 to 06.
- **Giving a manager a profile in a browser.** Route tests and API tests only.
- **"Names and shifts only" has nothing to bite on yet.** No roster exists. What holds today: a staff nurse gets 403 on the nurse list and every nurse change, and their one answer is the unit's id and name. Ticket 14 or 15's roster read has to keep to it with its own plain schema.

Decisions this ticket took:

- **Placements, not a unit on the profile.** A transfer takes effect from a chosen month, so `nurses.Placement` holds (nurse, unit, first month); the latest that has begun is in force. This differs from section 4's list, which now says so. There is no stored "current unit" that a job would have to roll forward. A transfer waiting can be replaced, so that row can go; the audit log keeps what it said.
- **"Belongs" (`nurses.membership.belonging_to`):** placed there now or due to join, with an active account and an end date not passed. Deactivated nurses do not count, so the refusal's "Transfer or deactivate them first" is true. A nurse due to leave counts until they have left, so a transfer from next month does not free the unit until then; one from this month does at once.
- **Coming back to an archived unit is refused:** clearing or moving on an end date (422 on `end_date`) and the System Admin reactivating a manager with a profile (409). A deactivated nurse can still be transferred out of an archived unit, so nobody is stuck. Under the unit's row lock, as archiving.
- **An end date:** today or earlier deactivates at once, because ending an account should not wait; a later date stays active through that day, and `close_ended_nurses` closes it within the hour after. Clearing it, or moving it past today, reactivates with the old password. It cancels any transfer after it, recorded in the audit entry. **Worth your review:** login does not check the end date, so a worker that is down leaves an ended nurse able to log in until it is back.
- **An end date may be before the start date only for a nurse who has not started and only when it is today or earlier,** so one added by mistake can be ended; no field can correct a start date (ticket 07a later added one, and keeps to this rule). So there is no database constraint between the two, and **ticket 11 must treat such a nurse as never present.**
- **A transfer may start this month or later,** never a month that is over.
- **A nurse starting later belongs to the unit from now,** so they see it at first login and their manager can prepare. Days before the start date are the solve input's concern.
- **A manager's nurse profile is in the unit they hold, or they hold none.** A manager reaches only that unit, so a roster in another would be one they could not see. It is enforced when giving the profile, transferring it and assigning a manager, and an ended profile counts too, or clearing its end date would bring it back elsewhere. Moving a manager: take them off, transfer from this month, assign. Their hospital ID is the username they already have.
- **An end date on a manager's profile ends the profile, not the account,** and **the CNO and a manager cannot reset a manager's password here.** Section 3 gives manager accounts to the System Admin, and a manager could otherwise bypass their own current password. The ticket says "the CNO for any nurse", so section 3's row now says "a staff nurse's". **Worth your review.**
- **A manager's list includes nurses due to join,** who need rostering in that month, and nothing names another unit: "Joins from" and "Leaves from". They cannot reset a joiner's password until they arrive.
- **Added though no criterion asked:** the CNO's unit filter on the page, in the address per ADR 0008, because a hospital's whole staff would otherwise be one list.
- **The queue's library is behind `ops/queue.py`** per section 7, with `hourly` the first thing in it. A job lives in an app's `tasks.py`, which Procrastinate discovers by name.
- **Not built, because no ticket asks: correcting a nurse's name, gender or start date.** A typo at adding stays for good; gender cannot be fixed by ticket 09 unless it adds it. **Worth your review.** Ticket 07a now builds this, before ticket 08. Also no reactivation button apart from clearing the end date.

Things a later ticket should know:

- **Import (08):** the same rules as `add_nurse`: `create_user`, `_unit_to_join` locks the unit, `_new_profile`. `create_user` hashes one password per row, which is slow on purpose, so a large file may need a long request. Staff list export should read `_with_units` and print `membership.from_now_on(nurse)[0]`.
- **Rostering attributes (09):** add the fields to `NurseProfile`, and keep them out of `record`, as gender is: the System Admin reads the log. A manager's own-unit check for a nurse by id is `unit_in_scope(user, membership.unit_id_now(nurse))`. Allowed shifts need carrying through `_carry_rename_through_the_rules`.
- **Solve input (11):** a unit's nurses in a month are not yet a query here: `on_the_list_of` is for now. Add one month-aware query beside `_unit_in_force`, which reads the latest placement that has begun as of this month. Exclude a nurse whose end date is before the start date.
- **Scope:** `units_in_scope` now answers for a staff nurse, with the unit of this month. A unit-scoped endpoint for them still needs `Role.STAFF_NURSE` in its `SignedIn`, and its own 403 test.
- **`deactivate_many`** is for users who hold no unit, and reads the sessions once. `reactivate` raises `UnitArchived`.
- **Lock order unchanged:** user, then unit. `_locked_nurse` takes the profile and the user together.
- **Audit actions added:** `nurse.added`, `nurse.transferred`, `nurse.end_date_changed`, named in `ACTION_NAMES`. None holds a rostering attribute. `user.deactivated` with no actor means the job.
- **Frontend:** `PasswordDialog` moved to `components/password-dialog.tsx`, and `asDate` and `monthName` to `lib/utils.ts`. The page opens one form at a time above the list through `useEditing<Panel>`, not below it as on Units, because the list can be long. Regenerating the client under a running Vite needs that container restarted.
- **`client_of`** moved to the root `conftest.py`.

**Review (2026-11-05).** The `code-review` skill's two axes found "move" against the glossary, the unit filter out of the address (ADR 0008), the queue's library outside one module (section 7), a table a keyboard could not scroll, a verbless button, an active manager's ended profile able to come back into an archived unit today, a mistaken future nurse who could not be ended, the filter disagreeing with the archive refusal over joiners, wrong "Leaves" copy for a chain of transfers, a wrong message for a manager's end date, and duplicates. All fixed. Left as judgement calls: TanStack Table is named in ADR 0008 but no page uses one yet; `NurseRow`'s `from_month` stays a string; "a manager's account is the System Admin's" is checked in the end date, the reset and the job. The `interface-review` skill itself was not run; the page was held to the `better-*` rules by hand and by that review.

**Reviewed by the user (2026-11-05), and kept as built:** login ignores the end date; manager passwords stay with the System Admin; a manager's nurse profile must be in the unit they hold. TanStack Table is no longer a breach here: ADR 0008 changed on 2026-11-05, so short lists stay plain tables and TanStack Table is for the roster grid and any table that needs sorting or filtering.
