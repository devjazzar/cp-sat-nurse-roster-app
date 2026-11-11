# Security audit (2026-11-11)

A record of the first security audit of this repository: what was checked, what was found and fixed, and what
is still open. Read this before starting the next audit or picking up one of the open leads.

The three files in [`2026-11-11-security-audit/`](2026-11-11-security-audit/) are the audit's own report, kept
as written. They describe the code at `f2492e0`, **before** the fixes, so the five findings they call
"confirmed" are fixed on `main` (see section 2).

| File | What it holds |
|---|---|
| `REPORT.md` | Run facts, the five confirmed findings, the table of leads, hardening notes, coverage summary |
| `FINDINGS-DETAIL.md` | Full source trace, sandbox reproduction and suggested fix for each confirmed finding |
| `NEEDS-VALIDATION.md` | Full source trace, blockers and validation plan for each open lead |

## 1. What was done

- **Audited commit:** `f2492e0`, the whole tracked repository (backend, frontend, solver, deploy, scripts, CI).
- **Tool:** Cloudflare's `security-audit` skill, installed at `.claude/skills/security-audit/`, run in its
  `standard` profile: reconnaissance, three waves of hunters (16 in all), four coverage critics, and two
  independent verification passes on every candidate. 55 agent runs.
- **Evidence bar:** a finding counted as confirmed only when a fresh verifier reproduced it with dummy data in a
  sandbox (a container with no network, the repository mounted read-only, a throwaway PostgreSQL 18). Nothing
  was sent to the dev stack, to a deployed site or to any outside service.
- **Result:** 16 candidates → 5 confirmed (all low severity), 7 leads that need a fact the sandbox could not
  observe, 4 rejected.

The access model held up. No path was found for an anonymous visitor to reach data, or for a nurse or unit
manager to reach another unit's rosters, leave or attributes through the scoped routes. Every route is
authenticated by default, unit scope is enforced in one place (`units.scope`), and no user input reaches raw SQL,
a shell, or unescaped HTML.

## 2. Fixed

Merged to `main` on 2026-11-11 in [PR 4](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/4), one commit
per finding, each with a regression test. After the merge the audit's original reproductions were run again
against the fixed code and none reproduced.

| Commit | Finding | Fix |
|---|---|---|
| `90a8294` | A backup carried every live session; a session key read from a dump signed its holder in as that user. | `pg_dump` runs with `--exclude-table-data=django_session`. A restore now signs everyone out. |
| `fe608ea` | A cover offer's refusal named nurses of other units to a unit manager. | A refused hospital ID is named only if it is on the cover's own roster; any other is said back as sent. |
| `849e3f2` | A unit manager whose nurse profile had ended kept reading the unit's approved rosters after losing the unit. | `rosters.reading_api.in_force` gives no unit for a month that begins after the profile's end date. |
| `62cd1ca` | A far-future month made one request run a query per nurse per month in between (1,219 statements against 19), on a solve start under the hospital settings lock. | `Chain.carry_in` takes a run of months with no approved roster in one step; a solve start is refused before the month is assembled. |
| `5fd83b7` | A staff nurse could propose and withdraw the same swap without limit, pushing a chosen colleague's earlier notices out of the newest 50. | A withdrawal overwrites the recipient's unread notice for that swap; proposing is refused after 5 withdrawals on one roster in a day. |

Choices made in the fixes, kept by the user as product decisions on 2026-11-11 (the swap cap, the swap notice and the end
date):

- **Swap cap.** 5 withdrawals per nurse per roster in a rolling 24 hours (`WITHDRAWALS_A_DAY` in
  `backend/swaps/steps.py`), refused with a 409 that says when she can propose again. The cap counts
  withdrawals, so the number of swaps one nurse has waiting at once is still bounded only by her own cells.
- **Swap notice.** The unread notice is updated in place, not deleted, because only housekeeping deletes
  notifications. Its time moves to the withdrawal.
- **End date.** A staff nurse with an end date still to come can no longer read, or be offered a swap in, a
  month that begins after it.
- **No upper bound on the month.** The audit suggested limiting how far ahead a month may be asked. That was not
  added, because a manager may roster any future month; the work no longer grows with the distance.
- **Not built.** Paging past the newest 50 notifications.

Both GitHub workflows, the browser checks and `deploy/tests/operations.sh` among them, passed on `5fd83b7`, on PR 4 and
again on `main` (corrected 2026-11-11: this line first said they were not run; only a local run was skipped). A restore
with an empty sessions table was checked by reading `deploy/restore.sh` and through `operations.sh` on GitHub. A second
local browser-check run on one long-lived stack within a day could meet the swap cap; CI's stacks are new each run.

## 3. Open leads

Seven leads had a source trace and no verdict: each waits on a fact outside the repository. Leads 5 to 7 have since been
fixed without one (ticket 62), lead 1 (ticket 63) and lead 4 (ticket 67). They carry no
severity. `NEEDS-VALIDATION.md` has the full plan for each; the checks named there are for the owner to make on
their own installation or on a scratch stack, never traffic against a hospital's system.

Five of the seven share one cause: **nothing in the repository limits requests per client** (no limit in
`deploy/Caddyfile`, none in the application). A per-client limit at Caddy on `POST /api/auth/login`, a request
body cap and read timeout, and threaded gunicorn workers would shrink leads 1 to 3 together.

| # | Lead | Where | What is not known | Next step |
|---|---|---|---|---|
| 1 | **Fixed in ticket 63 (`52db6f8`, `a9dcfa6`).** 50 failed logins from one address in 15 minutes throttle it: its logins are refused with 429 before any name's row or password is looked at, so they cost no hash (counted in `accounts/tests/test_throttle.py`). A client with many addresses is still bounded only by the web pool (ADR 0015). Each anonymous login attempt costs a full password hash (0.5 s measured) on one of three sync workers; the lockout is per username, so rotating the username escapes it. | `backend/accounts/login.py` `attempt_login` | Whether it delays other users on a real server: cores, hash time there, and any limit in front of Caddy. | Owner: time one `make_password` in the web container; check for a rate limit in front of Caddy; look for bursts of `auth.login_failed` with many targets. |
| 2 | **Bounded per address in ticket 63; still open** (housekeeping is ticket 65). One address now writes at most about 50 refused-login entries and new names per 15 minutes, plus one `auth.login_throttled`; a refusal during the throttle writes nothing. Refused anonymous logins leave an audit entry and a `LoginAttempts` row that nothing removes; while a name is locked they are written without a hash. | `backend/accounts/login.py`, `backend/audit/log.py` | How fast rows can be written from outside, and the disk and backup headroom. | Owner: the read-only size queries in the plan; on a scratch stack, time 1,000 locked-path logins through Caddy. |
| 3 | A sign-in request whose body has not arrived holds a gunicorn worker (observed in the sandbox with one worker). | `deploy/compose.yaml` (gunicorn `--workers 3 --timeout 300`), `deploy/Caddyfile` | Whether Caddy passes a request upstream before its body is complete. | Scratch stack only: `caddy adapt` to confirm no buffering or read timeout, then the one-connection check in the plan. |
| 4 | **Fixed in ticket 67 (`756f5c5`).** One user may hold any number of push subscriptions, and the single push job sends to each in turn under the installation-wide `push` lock. | `backend/notifications/subscriptions.py` `turn_on`, `backend/notifications/pushes.py` | What a send to a made-up address under an allowed domain costs on the real network. | Owner: count subscriptions per user; read the gaps in `notifications_pushattempt`. Fix direction: cap subscriptions per user and give a job a send budget. |
| 5 | **Fixed in ticket 62 (`d4404f5`).** One unit's manager can queue a solve for every future month to December 2076 ahead of other units' solves, and no role above the unit can cancel them. | `backend/solves/api.py` `start_solve`, `backend/solves/running.py` | How long each such solve holds the queue (no solver ran in the audit), and whether first-come-first-served across units (ADR 0009) is acceptable here. | Scratch stack with the real solver: the three-solve check in the plan. Product decision: a per-unit share of the queue and a cancel for the CNO or System Admin. |
| 6 | **Fixed in ticket 62 (`2b70344`).** No response carries `X-Frame-Options` or a `frame-ancestors` policy, so a page on a same-site origin could frame the signed-in app. | `backend/config/settings.py` `MIDDLEWARE`, `deploy/Caddyfile` | Whether any same-site origin exists that someone other than the app's operators controls; browser behaviour. | Cheap to close without validating: add `XFrameOptionsMiddleware` or a CSP with `frame-ancestors 'none'`. |
| 7 | **Fixed in ticket 62 (`6cda1dd`).** The file download routes are plain GETs, so a page on another site may be able to make a signed-in CNO's browser take the audited staff-list export, or tell that the visitor is the CNO; the System Admin's backup download may be reachable the same way, since a backup's name is predictable. | `backend/nurses/files_api.py`, `backend/ops/api.py` | Whether current browsers attach the Lax session cookie and let the other page tell the two answers apart. | Test installation with dummy accounts: the static-page check in the plan. Fix direction: refuse these GETs when `Sec-Fetch-Site` is `cross-site`. |

### What the user decided for the leads (2026-11-11)

- **Leads 5, 6 and 7, and the late approval of section 4:** fixed in ticket 62
  (`.scratch/nurse-rostering-v2/issues/62-audit-follow-ups.md`): one active solve a unit across its months, `X-Frame-Options:
  DENY` and `frame-ancestors 'none'`, the file routes refusing `Sec-Fetch-Site: cross-site`, and no approval once a month is
  over (option A). **Fixed on 2026-11-11** in ticket 62, pull request 5: lead 5 in `d4404f5`, lead 6 in `2b70344`, lead 7 in
  `6cda1dd` and `3b2fc9e`, the late approval in `0cac2f5`. Leads 2 and 3 stay open; leads 1 and 4 are fixed (below). (`NEEDS-VALIDATION.md` numbers its sections differently:
  this table's leads 5, 6 and 7 are its sections 6, 3 and 5.)
- **Lead 1: fixed on 2026-11-11** in ticket 63 (`.scratch/nurse-rostering-v2/issues/63-the-throttle-on-failed-logins.md`), in
  `52db6f8` and `a9dcfa6`: the throttle per client address, before the hash. Lead 2 is bounded per address by it and stays
  open for the housekeeping of ticket 65.
- **Leads 1 to 4, the hardening notes and the restore note of section 4:** one hardening feature, grilled first
  (`/grill-with-docs`), then specced and ticketed: limits per client (Caddy's timeouts and body cap, threaded gunicorn
  workers, a per-IP failed-login throttle before the hash, housekeeping of login-attempt rows), at most a few push
  subscriptions a user, HSTS and a content security policy, and what `restore.sh` should clear and print.
- **Lead 4 and the push hardening notes:** **fixed on 2026-11-11** in ticket 67
  (`.scratch/nurse-rostering-v2/issues/67-ten-devices-a-user-and-a-push-job-that-hands-on.md`), `756f5c5`: at most ten push
  subscriptions a user, an eleventh device ending the earliest turned on; a push job that starts no new send after 30 seconds
  and hands the rest to the next job, behind any push already waiting; the API's `auth` key limit the column's (100), so a
  longer key is 422; and `pushing.send` counting any exception the library raises that is not already sorted as a refusal.
  How long one send to a made-up address takes on a real network stays unmeasured; the cap and the budget bound the delay
  whatever it is.
- **The public health note** (`REPORT.md` section 5, "`GET /api/health` is anonymous and calls the solver on every
  request"): **fixed on 2026-11-11** in ticket 68 (`7e5f7ed`, `77f79f4`). Each web process keeps the public answer five seconds; the
  System Admin's health page and `/metrics` are not kept.
- **The typed username note** (`REPORT.md` section 5, "A failed login stores the submitted username in the audit log"):
  **fixed on 2026-11-11** in ticket 64 (`.scratch/nurse-rostering-v2/issues/64-a-failed-login-names-only-a-real-account.md`),
  `d2043f0`: `auth.login_failed` names the typed username only when an account has it, otherwise its target is empty, with its
  reason and address kept; the lockout still counts by the name typed. Entries written before keep what was typed (the log is
  append-only, ADR 0007). The same ticket put the lockout's time on the hospital's clock (`a68466e`).
- **Known vulnerabilities in dependencies (section 5):** checked with `pip-audit` and `npm audit` on 2026-11-11; the result is
  below in section 5.

## 4. Rejected, and a bug found on the way

Rejected candidates are listed so the next audit does not spend time on them without new evidence.

- **Push host allow-list against the HTTP client's URL parser.** Compared offline; no address passes the
  allow-list and is sent elsewhere.
- **A staff nurse's swap proposal holding the hospital settings lock.** Measured at 50 to 125 ms for a refused
  proposal on a unit of 4 to 24 nurses. A hardening note, not a finding.
- **A restore brings back accounts deactivated and passwords replaced since the backup.** Reproduced, and
  inherent to restoring a database by a trusted operator. Worth adding to `deploy/restore.sh` and
  `deploy/INSTALL.md`: empty the login-attempt table, and print the deactivations, password resets and key
  rotations recorded after the backup's moment before the replaced database is dropped. **Fixed on 2026-11-11** in ticket 66
  (`.scratch/nurse-rostering-v2/issues/66-a-restore-empties-the-login-attempts-and-lists-what-it-undid.md`), `d867d32` and
  `a851c33`: `restore.sh` empties the login attempts and the throttle's addresses in the restored database before the swap,
  and before it drops the replaced one prints, by time, each deactivation, password reset, password change and push key
  rotation recorded there after the restored database's newest audit entry. It re-applies none of them.
- **A roster approved after its month is over.** Not a security finding, because the CNO and Deputy CNO are
  trusted with approval. But it was a **functional bug, reproduced, and fixed in ticket 62 (`0cac2f5`)**: approving now refuses
  a month that is over, as submitting does, and the scenario below is a test in `closes/tests/test_close.py`. As found: a roster left submitted past
  its month can still be approved, and if the month after it has already closed, that unit's month close is then
  refused for good. `backend/rosters/review.py`, `backend/closes/making.py`.

`REPORT.md` section 5 lists the hardening notes (HSTS and a content security policy, limits in the Caddyfile,
the audit log being append-only by convention only, the application's database role being a superuser, images
and actions pinned by tag, and others) and the patterns that held up. Its push note (cap the subscriptions, give a push job a
send budget, align the `auth` key's length, make `pushing.send` never raise) is fixed in ticket 67 (`756f5c5`).

## 5. Not covered

- **Known vulnerabilities in dependencies.** The audit had no network, so the locked versions and base images
  were not checked against advisories. Pinning and integrity were. Run `pip-audit`, `npm audit` or `osv-scanner`
  separately.
  **Checked on 2026-11-11, at `10f18f3`:** `pip-audit` over `uv export --frozen --all-packages` (180 packages, Django
  6.1.3, cryptography 50.0.2, gunicorn 26.2.0 among them): no known vulnerabilities. `npm audit` in `e2e/`: none. In
  `frontend/`: three low, all one advisory, `deepmerge` prototype poisoning (GHSA-gcqx-w48m-w2h4), reached only through the
  `shadcn` CLI package; the SPA imports only that package's `tailwind.css`, so no `deepmerge` code is in the built app.
  `npm audit fix --force` would move `shadcn` to 1.0.0, a downgrade, so it was not run: take the fix when `shadcn` ships a
  release with a fixed `deepmerge`. The base images (`python:3.14-slim`, `node:26`, `postgres:18`, `caddy:2.11`) were not
  scanned.
- **A staff nurse repeating request or preference make-and-withdraw rounds.** Proposed by the last coverage
  critic and not hunted. Nobody is notified and no recipient is chosen, so it is weaker than the swap finding;
  the open question is what the accumulated rows cost the manager's unpaged window lists
  (`backend/requesting/api.py`, `backend/requesting/making.py`).
- The seven leads above are, by definition, not settled.

## 6. Running the next audit

- **How:** ask the agent for a security audit of the codebase; the skill's `SKILL.md` describes the modes. It
  only gives guidance unless asked for a full audit.
- **Prior run:** the skill looks for earlier runs in `~/security-audit-skill/cp-sat-nurse-roster-app/` and
  carries their results forward. Run 1's structured output (`findings.json`, `coverage-ledger.json`, the
  verifiers' harnesses under `agents/*/artifacts/`) is in `run-1/` there, on the machine that ran it, and **not
  in this repository**. Without that folder the next run starts from nothing, and this document is the only
  record of what was rejected.
- **Sandbox:** `run-1/tools/` holds the two wrappers the verifiers used (`sandbox-run.sh` for a no-network
  container, `sandbox-db-run.sh` for one harness against a throwaway PostgreSQL 18). The second takes the
  machine's heavy-work lock. Both need the `nurse-roster-app:dev` and `postgres:18` images present locally.
- **Cost:** the full run took 55 agent runs and met the account's usage limit twice. For a follow-up, a scoped
  run is enough: the files changed since `5fd83b7`, the two areas in section 5, and the fixed findings as
  regression targets.
