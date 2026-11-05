# 02: System Admin's first run: login, forced password change, health and technical settings

**What to build:** The System Admin's account is created on first start from the one-time password in the environment. They log in on the SPA's login page, are forced to change the password, and land on their home: the health page (solver reachable, queue state, disk and database size, last backup placeholder) and the technical settings (time limit cap, backup time and retention, month close time) with the agreed defaults. Accounts lock for fifteen minutes after five failed logins, sessions expire after twelve idle hours, and every login and failed login is an audit entry.

**Blocked by:** 01 Foundation

**Status:** ready-for-agent

- [x] First start creates the System Admin from the environment variable with must-change-password set; the variable is ignored on later starts
- [x] Login page, logout, forced password change at first login with the policy (minimum 10, common-password and similarity checks)
- [x] Lockout after 5 failed logins for 15 minutes; sessions expire after 12 idle hours
- [x] Every login and failed login writes an audit entry
- [x] Health page shows solver reachability, queue state, disk and database size
- [x] Technical settings page edits the time limit cap (default 300 s), backup time and retention (02:00, 30 days) and close time (00:30), audited
- [x] API tests cover bootstrap, login, lockout, forced change, settings and that a non-admin cannot read or change technical settings

## Comments

Implemented on 2026-11-05. The suites: solver and backend under pytest, the backend on real PostgreSQL 18, and the frontend under Vitest with the real routes and generated client over a stubbed `fetch`.

Checked on the real compose stack through Caddy with `curl -k`: first start, forced change, policy refusal, health with a live worker and solver, settings with audit entries, logout. Restarting with a different `INITIAL_ADMIN_PASSWORD` kept one user, and neither that value nor the first password logged in. Twelve parallel wrong logins made exactly five password checks. A client's `X-Forwarded-For` is replaced by Caddy, so the audit IP cannot be spoofed.

What was not checked:

- **The pages in a browser through Caddy.** The built-in browser refuses the self-signed certificate. The pages were driven in it on the dev overlay instead (Vite on `localhost:5173`, no Caddy): login, forced change, health, settings, logout, lockout. Through Caddy only the HTML's 200 for `/login` and `/health` and the API were checked. Ticket 24's Playwright suite needs `ignoreHTTPSErrors`.
- **A real twelve-hour wait.** The tests move the session's expiry in the database.

Things a later ticket should know:

- **Username:** the System Admin's is `admin`, fixed in `accounts/management/commands/bootstrap.py`. Ticket 04's seeding belongs in that command, which `web` runs after `migrate` in both compose files.
- **Authorization (03):** every router or endpoint names its roles with `accounts.authz.SignedIn(Role.X, ...)`: 401 when signed out, 403 for the wrong role or a pending forced change, CSRF on unsafe methods. Ninja exempts its views from Django's CSRF middleware, so an endpoint with no `SignedIn` has no CSRF check unless it calls `check_csrf` itself, as login does.
- **One-of-a-kind roles (03):** `accounts_one_system_admin` is a partial unique constraint; the CNO and Deputy CNO can follow the same pattern.
- **Password resets (03, 22):** delete the `LoginAttempts` row for that username, or a locked user stays locked. Set `must_change_password`; changing the hash already ends their sessions.
- **Lockout:** `LoginAttempts` is keyed by the username tried, known or not, so a lock does not reveal which usernames exist. The failure count only resets on success or when a lock runs out. Anyone can lock anyone out for 15 minutes by design, the System Admin included.
- **Audit (03):** actions so far are `user.created`, `auth.login`, `auth.login_failed`, `auth.logout`, `auth.password_changed`, `technical_settings.changed`. Write through `audit.log.record`. Only `at` is indexed, so the filter page may want more.
- **Open decision for ticket 11:** `SESSION_SAVE_EVERY_REQUEST` makes every signed-in request count as activity. Solve progress polling in an open tab would therefore keep a session alive past twelve idle hours. The health page has a Refresh button rather than a timer for this reason. Ticket 11 has to decide whether polling should count.
- **Technical settings:** read them with `ops.models.TechnicalSettings.load()`. Tickets 21 and 22 must honour edited times, so their schedules cannot be fixed at import: nothing reads these values yet.
- **Health:** `last_backup` is always empty until ticket 22, and disk is measured on `BACKUPS_DIR`. The public `/api/health` is unchanged because the compose health check uses it, and it still shows anyone the solver's version and thread count. The System Admin's page uses `/api/ops/health`. Consider trimming the public one in ticket 22.
- **Expired sessions:** nothing runs `clearsessions` yet, so rows accumulate. Ticket 22 should schedule it.
- **Frontend:** routes are files under `src/routes`, with `src/routeTree.gen.ts` committed because `tsc` runs before Vite in the build. Generated calls go through `src/api/fetcher.ts`, which throws `ApiError` on a non-2xx answer, so generated types describe success only and refusal bodies are cast from `error.body`.
- **Dev overlay:** Vite's proxy does not pass the browser's Host on, so `DEBUG` trusts the origin `http://localhost:5173` for CSRF.

**Interface review (2026-11-05).** The `better-*` skills' review of this ticket blocked it on focus contrast and on errors with no way forward; every finding is now fixed. For later pages:

- **Page names:** give a route `staticData: { title }`. `__root.tsx` sets the tab title from it and moves focus to `main[tabindex]` after a client-side navigation. Use `tabIndex={-1}` on any other page's `main` that should take focus.
- **Buttons:** `Button` is `focusableWhenDisabled`, so a disabled one has `aria-disabled` rather than native `disabled`. Test it with `toHaveAttribute("aria-disabled", "true")`, not `toBeDisabled()`.
- **Forms:** use `FormField`, which ties errors to the input. For server refusals, call `setError` with `{ shouldFocus: true }`.
- **Live regions:** render `role="status"` empty first and change its text.
- **Tokens:** `--ring` (4.73:1 on white) and `--input` (3.36:1) now meet 3:1, and destructive fills use `--destructive-foreground` (4.76:1). The dark values are computed only, because nothing can switch the theme yet.

**Reviewed by the user (2026-11-05).** Both open points are decided, not kept: solve progress polling does not count as activity (ticket 11's last comment), and the public `/api/health` is to be trimmed (ticket 22's comment).
