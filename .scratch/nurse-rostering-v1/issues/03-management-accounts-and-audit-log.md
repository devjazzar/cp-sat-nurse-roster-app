# 03: Management accounts and the audit log

**What to build:** The System Admin creates the CNO, the Deputy CNO and unit manager accounts, each shown its generated password exactly once, deactivates accounts and resets passwords. Exactly one CNO and one Deputy CNO can exist. Every role lands on a navigation scoped to what it may do, and every API endpoint checks the caller's role through one authorization layer that later tickets reuse. The System Admin reads the audit log with filters by user, action and date.

**Blocked by:** 02 System Admin's first run

**Status:** ready-for-agent

- [x] Create CNO, Deputy CNO, Unit Manager accounts; generated password shown once; forced change at first login; a second CNO or Deputy CNO is refused
- [x] Deactivate and reactivate an account; reset its password (shown once)
- [x] Role-scoped navigation and home page for every role; the System Admin creates no nurse and sees no roster
- [x] One authorization layer applied to every endpoint, with API tests that each role gets 403 where it has no business
- [x] Audit log page with filters by user, action and date; every account change is audited
- [x] API tests cover account creation, cardinality, deactivation, reset and the audit log

## Comments

Implemented on 2026-11-05. Backend under pytest on real PostgreSQL 18, frontend under Vitest with the real routes and generated client over a stubbed `fetch`.

Driven on the dev overlay in the built-in browser: create a CNO, the password dialog (Escape does not close it, Done does, nothing left on the page), deactivate, reactivate, reset, focus back on the row's button, the audit log and its filters with no page-level sideways scroll at 375 px, then logging in as that CNO with the generated password, the forced change, the CNO's home, 403 from all four admin APIs and `/users` redirecting home. Checked through Caddy with `curl -k` on the production compose file: creation, a second CNO's 409, deactivation, the audit entry, 401 signed out, and the HTML of both new pages.

What was not checked:

- **A successful copy to the clipboard in a real browser.** The built-in browser refuses clipboard access, so only the fallback (the password is selected in its box) was seen working. The success path is a stubbed test.
- **The reload prompt with a real person.** `beforeunload` is confirmed to be cancelled while a password shows, but browsers skip the prompt without a user gesture.
- **Deputy CNO, Unit Manager and Staff Nurse homes in a browser.** They are route tests; only the CNO's was driven.
- **The new pages in a browser through Caddy**, for the reason in ticket 02.

Decisions this ticket took:

- **"One CNO" means one active CNO** (`accounts_one_active_cno`, `accounts_one_active_deputy_cno`, and `docs/ARCHITECTURE.md` section 3 now says so). Accounts are never deleted and a username cannot be reassigned, so counting deactivated rows would leave a hospital unable to replace its CNO. Reactivating while a successor holds the role is a 409.
- **The code says User, per `GLOSSARY.md`**: `/api/users`, the Users page. The app is still called `accounts`.
- **Usernames are unique in any case** (`accounts_username_any_case`) and limited to letters, digits, `.`, `_` and `-` on this API. Login stays case-sensitive.
- **The audit log's user filter** is an exact username in any case, matching actor or target, so typing `ali` does not bring up `khalid`. The field suggests known usernames.
- **Times on the audit log and the users table are hospital time**: the API sends them with the hospital's offset and `hospitalTime` in `lib/utils.ts` prints them as sent. Other new pages should do the same.

Things a later ticket should know:

- **Authorization (all):** `NinjaAPI(auth=SignedIn())` now makes every endpoint signed-in by default; a public one must say `auth=None`. `accounts/tests/test_authorization.py` walks every endpoint and fails on a new public or any-role one until it is named there, and it tests each restricted endpoint automatically for 403 per wrong role, 401 signed out, 403 during a forced change and 403 without CSRF. New endpoints get this for free. It uses Ninja's private `_get_bound_routers`, because only bound routers show inherited auth.
- **Own-unit scoping (06 onward):** `SignedIn` checks the role only. "His own unit" is not expressed yet and needs its own check, which the walking test cannot see.
- **Creating users and resets (07):** use `accounts.provisioning`: `create_user`, `reset_password`, `deactivate`, `reactivate`. Each audits in its own transaction, and `reset_password` lifts a lock. The role limit lives in `accounts/api.py` (`MANAGED_ROLES`, which also 404s nurses and the System Admin on these endpoints), so nurses need their own guarded endpoints. Answers holding a password set `Cache-Control: no-store`; do the same, and use `gcTime: 0` on the mutation.
- **Deactivating (06, 07):** `deactivate` deletes the user's sessions by reading all live ones, so a reactivated user is not let back into an old browser. Fine for rare admin actions; an end date deactivating many nurses at once should not call it in a loop. Nothing yet stops deactivating a manager who has a unit: ticket 06 has to say what happens to that unit.
- **The System Admin reads every audit entry (09, 13 onward):** they "see no roster and no rostering attribute", so before and after values of roster cells or rostering attributes must not go into an entry as they are, or the audit page shows them. Record what changed, not the values, or decide otherwise deliberately.
- **Audit actions added:** `user.created` (now with an actor), `user.deactivated`, `user.reactivated`, `user.password_reset`. A new action shows as its code on the page until it gets a name in `ACTION_NAMES` in `audit-log.tsx`. `action` is indexed; the user filter uses `iexact`, which indexes do not help, so watch it if the log grows large.
- **Navigation (all):** add a role's pages to `NAVIGATION` in `src/roles.ts`, guard the route with `beforeLoad: onlyFor(Role.x)`, and replace that role's line on the home page. `<main>` no longer limits width, so each page sets its own `max-w-*`.
- **Tables:** `Table` takes `container` props. A table with no focusable content needs `tabIndex={0}`, `role="region"` and a label so a keyboard can scroll it; put a row's actions in a sticky last column.
- **Dialogs:** `AlertDialog` has no exit animation, deliberately, because its content comes from state that goes null at close. `useBlocker` is on while a password shows. Its navigation promise never settles, so a test cannot await it.
- **A user's `full_name` and `username` cannot be edited yet.** No ticket asked for it. Later: ticket 07b let the System Admin correct `full_name` on the users they manage; `username` still cannot be changed.

**Interface review (2026-11-05).** The `better-*` review blocked on the dialog's zoom ignoring reduced motion and on tables a keyboard could not scroll. Those and its smaller findings are fixed: voice-control labels, the blocker, hospital time, the selectable password box, no repeated "Loading…" on a window-focus refetch, dropping hand-edited bad dates from the address, and text size on selects.

**Reviewed by the user (2026-11-06).** From the review of every unsettled item across tickets 01–20, answered as recommended. Kept as built: one CNO means one active CNO (L31); usernames unique in any case, with limited characters (L33); the audit log's user filter is an exact username (L34), which ticket 22 times on the real database at first install; times shown in hospital time (L35).
