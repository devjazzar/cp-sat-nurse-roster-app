# 07b: Correct a user's name

**What to build:** The System Admin corrects the full name on the accounts they manage (CNO, Deputy CNO, Unit Manager), from a form on the Users page. Ticket 07a refuses to let the CNO correct a unit manager's name because it is on an account section 3 gives to the System Admin, and ticket 03 gave the System Admin no way to edit one, so nobody could correct it.

**The username still cannot be changed.** It is out of scope here.

**Blocked by:** 03 Management accounts, 07a Correct a nurse's details

**Status:** ready-for-agent

- [x] An endpoint and a form on the Users page correct `full_name` for roles in `MANAGED_ROLES`
- [x] Staff nurses and the System Admin's own account answer 404, as the other endpoints on `/api/users` do
- [x] System Admin only, confirmed in the walking test in `accounts/tests/test_authorization.py`
- [x] Works for a deactivated account, which stays deactivated
- [x] The username stays as it is, and a body that tries to change it is refused
- [x] A manager with a nurse profile shows the new name on the Nurses page; the CNO's refusal says the System Admin can correct it
- [x] The audit entry holds the name before and after under a new action named in `ACTION_NAMES`; a save with no change writes nothing
- [x] The same validation as `FullName`; refusals name their field
- [x] API tests cover the rename, each managed role, both refusals, validation, the no-change save, the audit entry and authorization; frontend tests cover the form

## Comments

Implemented on 2026-11-05. Backend under pytest on real PostgreSQL 18, frontend under Vitest with the real routes and generated client over a stubbed `fetch`. The walking test picked up `PUT /api/users/{user_id}/full-name` by itself, with 7 cases: 403 for each of the four other roles, 401 signed out, 403 during a forced change and 403 without CSRF.

Driven in the built-in browser, **not on the dev overlay's containers**. The only System Admin allowed is the dev stack's `admin`, whose password was not to hand, and resetting it would have changed a test account. So this working tree ran under `runserver` and Vite on the host, with the dev Postgres and a scratch database, dropped afterwards. The dev stack's data was not touched. As the System Admin: a manager renamed, with the new name in the row, the status message and focus back on the row's button; a save with no change, which said so and wrote no entry; a blank name refused beside the field with focus on it; a deactivated Deputy CNO renamed and still deactivated; Cancel with focus back on the row; no sideways page scroll at 375 px with the list and with the form open; a 150-character username wrapping at 320 px; both corrections on the audit log page with their names before and after. As the CNO: the Nurses page showing the new name and hospital ID unchanged, the read-only name with its new description, the new refusal message from the API, and a manager renamed while the form was open still having their gender saved.

What was not checked:

- **The dev overlay's containers and the production compose file through Caddy.** See above. The dev overlay's `web` does serve the new endpoint (403 to a signed-out `PUT`).
- **A refusal from the API on this form in a browser.** The form refuses what the API would first, so only a stubbed test reaches `showServerErrors` here. The API's own refusals are tested.
- **A real keyboard walk and a screen reader.** Focus was read from the DOM after each step, and accessible names from the accessibility tree.
- **Two people at once.** The row lock is by design and no test races it.
- **Dark mode, and browsers other than the app's built-in one.**

Decisions this ticket took:

- **A deactivated user's name can be corrected, and they stay deactivated.** They stay on record and in the log, a manager's nurse profile can outlive their account, and a wrong name does not become right by leaving. Ticket 07a treats an ended nurse the same way.
- **`PUT /api/users/{id}/full-name` refuses any other field (422 on it)**, so asking to change a username fails rather than appearing to work.
- **The action is `user.name_corrected`, "Corrected a user's name",** with `full_name` before and after. A name is neither a roster nor a rostering attribute, so the System Admin may read the values.
- **`full_name` on `PUT /api/nurses/{id}/details` is now optional, and a manager's form leaves it out. Worth your review.** This changes ticket 07a's "takes all three fields". The form used to send the read-only name, so a rename by the System Admin while the CNO's list was stale made every save of that manager's gender or start date a refusal on a field the CNO cannot edit. A staff nurse's form still sends the name, and a different name sent for a manager is still refused. The form may show the old name until it saves; the list then shows the new one.
- **The form takes the place of "Create a user" while open,** in one card as on the Units and Leave types pages, because two "Full name" fields would share an id. A half-typed new user is lost if "Correct name" is clicked. **Worth your review.**
- **A row's actions are now two by two,** as on the Nurses page, so the third button makes the sticky column no wider.

Things a later ticket should know:

- **A renamed person who is signed in** keeps seeing their old name in the header and on their home until the page reloads, because `session.ts` keeps the session until login, logout, a password change or a 401. The API already answers with the new name. Left as it is.
- **Import (08):** `full_name` on an imported manager row is not this ticket's concern, and `create_user` still takes any `FullName`.
- **Audit action added:** `user.name_corrected`, named in `ACTION_NAMES`.

**Review (2026-11-05).** The `code-review` skill's two axes found the stale-name refusal above, fixed; `docs/ARCHITECTURE.md` still giving the CNO every nurse's name in section 3's table, fixed; the `provisioning` docstring claiming every name correction is audited there, fixed; a form-values type named `Name`, renamed; "account" in test names and this ticket's title where the glossary says User, fixed. Left as judgement calls: tickets 03 and 07a have a sentence added in place, because the brief asked for those pointers; this file keeps the name the brief gave it; "unit manager account" stays in the copy, as the glossary's System Admin entry and the Nurses page already say; the `fullName` zod rule stays in `users.tsx` and `nurses.tsx`, as the rule was already in both; `NameCorrectionBody` keeps its own `extra="forbid"` as each app does; the who-is-managed tests stay apart from their POST-only neighbours. `better-accessibility`, `better-layout` and `better-writing` were loaded and held against the form and row action, which found a long username clipped at 320 px, fixed with `wrap-anywhere` on the heading, the username line and the status message. **`better-typography`, `better-colors` and `better-ui` were not loaded,** because the form adds no colour, type or motion of its own; it reuses `FormField`, `Button` and `Card`. `interface-review` was not run, because it is user-invoked. Already so before this ticket and left: at 320 px the sticky actions cover most of the name column, which a sideways scroll of the table reveals.

**Reviewed by the user (2026-11-05), and kept as built:** `full_name` optional for a manager's corrections; a draft of a new user lost when "Correct name" opens; the old name until reload; row buttons two by two; the `07b` ticket name.

**Reviewed by the user (2026-11-06).** From the review of every unsettled item across tickets 01–20, answered as recommended. Kept as built: at 320 px the sticky buttons cover the name column on Users (L50), for ticket 23.
