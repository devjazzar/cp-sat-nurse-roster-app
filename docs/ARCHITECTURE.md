# Nurse rostering application: architecture and product rules (v1)

Agreed on 2026-11-04 after a six-round design interview. This document is the shared
understanding the build starts from. Vocabulary is defined in [GLOSSARY.md](../GLOSSARY.md);
the reasons behind the hard-to-reverse choices are in [docs/adr](adr/); the facts the
technology choices rest on are in [docs/research](research/).

## 1. Purpose and scope

One installation serves one hospital. Unit managers generate monthly rosters for their units
with the CP-SAT solver, the Deputy CNO approves them, staff nurses see the approved roster, make
requests for coming months and propose swaps. The hospital's IT runs the installation as a
single `docker compose` stack on one VPS. There is no multi-tenancy, no shared service between
hospitals, and no internet access for the solver.

Out of scope for v1 (designed so they can be added, not built): Arabic or any second language,
LDAP or SSO, email or SMS, push notifications, server-side PDF, soft (unapproved) preferences,
native mobile apps, the solver's reproducible mode in the UI.

## 2. Deployment

### Services

One application image per release. `docker compose` starts five services:

| Service  | Image            | Command             | Network                | Ports            |
|----------|------------------|---------------------|------------------------|------------------|
| `caddy`  | `caddy:2.11`     | stock               | public, frontend       | 80, 443 published |
| `web`    | application      | API + SPA server    | frontend, backend, solver | none published |
| `worker` | application      | Procrastinate worker| backend, solver        | none             |
| `solver` | application      | solver HTTP service | solver                 | none             |
| `db`     | `postgres:18`    | stock               | backend                | none             |

The `solver` network is reachable by `web` and `worker` only. The solver container holds no
database credential and no secret other than the shared solver token. See ADR 0001.

Volumes: `pgdata` (PostgreSQL), `backups` (nightly dumps), `caddy_data` (certificates).

### Configuration (`.env`)

`DOMAIN` (optional; with it Caddy obtains Let's Encrypt certificates, without it Caddy serves a
self-signed certificate via `tls internal`), `SECRET_KEY`, `POSTGRES_PASSWORD`,
`SOLVER_TOKEN`, `TIME_ZONE` (default `Asia/Riyadh`), `INITIAL_ADMIN_PASSWORD` (read once),
`APP_VERSION` (the image tag the hospital pins).

### First start, upgrades, recovery

- First start: `web` runs migrations, seeds the default hospital and unit rule sets (section
  9), and creates the System Admin account from `INITIAL_ADMIN_PASSWORD` with a forced
  password change at first login. The variable is ignored afterwards.
- Upgrade: `docker compose pull && docker compose up -d`; migrations run at `web` start.
- `deploy/reset-admin-password.sh`: resets the System Admin password from the VPS.
- `deploy/restore.sh <backup-file>`: stops the app, restores the database, starts it again.
  Restore is deliberately a script, not a button.
- Nightly backup (02:00 hospital time, kept 30 days) is a worker job; backups are listed and
  downloadable on the System Admin's health page. Off-site copies are the hospital's job and
  are documented in the install guide.

### Image build

One multi-stage `Dockerfile` at the repository root: a `node:26` stage builds the SPA; a
`python:3.14-slim` stage installs the backend and the solver with `uv sync --frozen`; the
final image carries both plus the compiled SPA. The three application containers choose
their command at start. Python 3.14 is the ceiling because OR-Tools 9.15 publishes wheels up
to 3.14.

## 3. Roles and permissions

Every user has exactly one role and optionally a nurse profile (roster membership). A Staff
Nurse always has a profile; a Unit Manager may (the CNO decides). Nobody ever needs two accounts.

| Capability | System Admin | CNO | Deputy CNO | Unit Manager | Staff Nurse |
|---|---|---|---|---|---|
| Create / deactivate CNO, Deputy CNO, Unit Manager accounts; correct the names on them; reset their passwords | yes | | | | |
| Technical settings: time limit cap, backup schedule, close time | yes | | | | |
| Audit log, solve history (all units), health page, backups | yes | | | | |
| Hospital rules and weights, shift catalogue, leave types, public holidays, Ramadan dates | | yes | | | |
| Read the hospital rules and weights | | yes | yes | | |
| Read the shift catalogue, leave types, public holidays, Ramadan dates | yes | yes | yes | yes | yes |
| Create, rename, archive units; assign each unit its manager | | yes | | | |
| Read units | | yes | yes | own unit | |
| Add nurses (form or CSV import), give a unit manager a nurse profile, correct a nurse's gender and start date and a staff nurse's name, transfer, set end dates, export staff list | | yes | | | |
| Read nurses | | yes | | own unit | |
| View every unit's rosters, with the per-month state overview | | yes | yes | | |
| Approve or reject a submitted roster | | yes | yes | | |
| Unit rules; nurses' rostering attributes (gender aside: the CNO sets and corrects it) and opening values | | | | own unit | |
| Read the unit rules, and the rostering attributes and opening values of a unit's nurses | | yes | yes | own unit | |
| Request windows; decide requests; decide swaps; record, correct and remove leave | | | | own unit | |
| Read a unit's leave with its type | | yes | yes | own unit | |
| Solve, edit the draft, submit, edit the approved roster, re-plan, re-close a month | | | | own unit | |
| Exports (CSV, Excel, print page) of any roster version | | yes | yes | own unit | |
| Reset a staff nurse's password (a manager's stays the System Admin's) | | yes | | own unit | |
| Read the name of own unit | | | | | yes |
| View own unit's approved roster (names and shifts only) and own summary | | | | | yes |
| Make and withdraw requests; propose, accept and reject swaps | | | | | yes |
| Read own leave with its type (a manager with a nurse profile too) | | | | yes | yes |

Cardinalities: exactly one active CNO and one active Deputy CNO per hospital (a deactivated one
stays on record, so a successor gets a new account); one Unit Manager per unit and one unit per
manager (a manager account with no unit assigned can log in but do nothing). A unit is created
with or without its manager and waits with none until the CNO assigns one. Deactivating a manager
takes them off their unit at once, because ending an account cannot wait for the CNO, and
reactivating does not give it back; the CNO's home names every unit with no manager. A unit
manager sees nothing of other units. The System Admin sees no roster and no rostering attribute.
A manager's nurse profile is in the unit they hold, if they hold one, because that unit is all they
reach: moving one means taking them off, transferring the profile from this month, and assigning them.
The CNO corrects a manager's gender and start date on their nurse profile. Their name is on the account,
so the System Admin corrects it, as on any account they manage, active or not. A staff nurse's name is the
CNO's to correct. A username cannot be changed, so neither can a nurse's hospital ID, which is the username.
A manager with a nurse profile sets their own attributes, because nobody else may and a nurse has to have them; the CNO
and the Deputy CNO can read the values and the audit log shows whose hand changed them. A nurse's attributes are their
current unit's manager's until they arrive: the manager of a unit they are due to join reads them, and sets only the
allowed shifts there, so that unit can roster the months ahead of them.

A leave's type says something about a person, so only the nurse, the manager of that month, the CNO and the Deputy CNO read
it, the last two every unit's and every month's, and without changing any. A solve input holds dates alone. The System Admin
reads no leave, and colleagues see a day off. The manager of a date is the manager of the unit its month falls under,
whichever unit the nurse is in today. Across a transfer each reaches their own months and sees nothing of the other's: the old unit keeps its past months for late facts, and the new one reaches its
months before the nurse arrives. A manager with a nurse profile records their own, and the audit log shows whose hand it was.

The CNO stands in for an absent Deputy CNO; the CNO reassigns a unit to another manager
account when its manager is unavailable. There is no delegation feature.

## 4. Domain model

Entities, in the glossary's words. Identifiers are UUIDv7 generated by PostgreSQL (ADR 0007)
except for append-only logs.

**Hospital settings** (one row): name, time zone, the hospital rules (every field of the
solver's `general` block including the weights), the request cap default.

**Shift** (catalogue): code (the solver's name), display name, hours, start and end time,
colour, active flag. Hours cannot change while an open month's roster uses the shift; the
code may be renamed (each rename is recorded, the app carries the old name through nurses'
histories, and the forbidden successions, every unit's rules and every list of allowed shifts follow
at once, and no other shift may take a code a shift used to hold); a shift a live unit still uses, or
a forbidden succession names, cannot be retired, and the refusal names the units.

**Leave type**: name, active flag. Every type counts the same for hours.

**Public holiday**: date, name. **Ramadan days**: per month, the CNO's fixed dates or range,
else derived from the Umm al-Qura calendar.

**Unit**: name (unique among units not archived), archived flag, manager (a user; none once
archived), the unit rules (every field of the solver's `department` block but its name, which is
the unit's) with a review flag, request cap per nurse per month (default 3), default time limit.

**User**: username, full name, role, active flag, must-change-password flag.

**Nurse profile** (0..1 per user): hospital ID (= username), gender, start date, end date,
team leader, score, Ramadan-reduced, breastfeeding, opening values (overtime this year, hours balance,
night and weekend fairness balances; editable until her first month closes), whether a manager has ever saved
these, which is how a score at the default is told from one somebody looked at.

**Placement**: nurse, unit, first month, allowed shifts. A nurse's allowed shifts are on the placement, not the
profile, because a list means something only in a unit and two units can each roster their own months of one nurse at
once. Empty means any shift the unit works, now or later. A transfer carries the list as far as the new unit works the
same shifts; with none in common it empties, and the new manager is asked to check. A unit that stops working a shift
takes it out of the lists of the nurses placed there or due to join, but is refused, naming them, if a nurse would then
have no shift left. A start date corrected to before the first placement makes that
placement begin in the date's month, so no month after a start date is without a unit. A nurse belongs to the unit of the latest placement that
has begun; a later one is a transfer still to come, which can be replaced. A nurse belongs to a unit,
and so stops it being archived, while placed there or due to join it, with an active account and an
end date not passed.

**Roster** (one per unit and month): state `draft`, `submitted`, `approved`; a rejection
returns it to `draft` with the comment kept. Exactly one draft per unit-month. Its grid is the one in use and
follows a shift's rename, while the solve it came from keeps what it was given and answered. It remembers when a manager
last restored a result as that grid; a solve replacing the grid clears that.

**Roster version**: the roster's full grid (nurse × date → shift code or off) with who,
when, why and origin (solve, manual edit, re-plan, swap, request), plus the result it came
from when a solve produced it. The latest version of an approved roster is in force.

**Leave**: nurse, date, leave type, recorded by and when; removed by and when. One row a date, and at most one current row
for a nurse and date. A correction or removal ends the row rather than rewriting it, because the audit log may hold none of
this. A date must lie within the nurse's start and end dates when it is entered; a later correction to those dates leaves
the row, flagged on the unit's list, where it counts for nothing.

**Pinned cell**: nurse, date, shift or off, origin (manager, accepted request, accepted swap).

**Request window**: unit, target month, open date, close date, state. At most one open per unit.

**Request**: nurse, window, date, kind (`day_off` or `shift` with a shift), state
(`pending`, `accepted`, `rejected`, `withdrawn`, `cancelled`), decided by, reason. Only an
accepted request reaches the solver, as a pinned cell. Nothing is deleted: a request the
manager cancels after acceptance becomes `cancelled`.

**Swap**: unit, the roster version it was proposed on, proposer, the set of cell changes
(nurse, date, new shift or off), the participants with their acceptance, state (`pending`,
`awaiting_manager`, `approved`, `rejected`, `withdrawn`, `expired`), decided by, reason.

**Solve**: unit, month, requested by, time limit, state (`queued`, `running`, `succeeded`,
`failed`, `cancelled`), the queue's job, progress (elapsed, best cost, improvements), the
complete solve input and result as stored, error text. A queue position is worked out when asked,
from the solves ahead on the queue, so it cannot be out of date. `succeeded` means the solver ran
to its end, which may have found no roster; `cancelled` may still hold the best roster found, which
becomes the draft; only `failed` means the solver gave no answer. Rules the solver refuses are
`failed` with the failure `refused`, and read as rules to review, not as a failed solve. At most one
solve of a unit's month is active at a time.

**Month close**: unit, month, closed at, closed by (system or manager), the close result,
and the carry-over per nurse.

**Carry-over** (per nurse and month): the values and their source (`opening`, `projected`,
`closed`).

**Notification**: user, event, payload, read flag. **Audit entry**: actor, action, target,
before and after, IP, time. **Technical settings** (one row): time limit cap (default 300 s),
backup time and retention, close time.

## 5. Lifecycles

### Roster

```
            solve / edit                 submit                  approve
  (none) ──────────────▶ draft ──────────────▶ submitted ───────────────▶ approved
                           ▲                      │                         │
                           └──────── reject ──────┘        edits, re-plans, swaps,
                                 (comment kept)            accepted requests: new
                                                           versions, in force at once
```

- Each solve replaces the draft's grid, unless its result has no roster or `ok` is false, which
  leaves the draft as it was; the solve history keeps every result, and any result
  with a roster can be restored as the draft, unless a solve of that month is queued or running, the month is over, or a shift
  it uses has since been retired or had its hours changed, since its cost and hours would no longer hold (it can still be
  opened, and a rename is carried). The stale-draft warning then compares with the restored solve's input. The draft grid is editable by hand with instant validation;
  a re-solve keeps pins. Submitting freezes the draft until the decision.
- After approval, the unit manager alone changes the roster: direct cell edits, swaps,
  re-plans from a date (earlier days are facts; the `change` weight keeps the new roster
  close). Every change is a new version, in force immediately, and notifies the unit's nurses.
- A month with no approved roster shows "no roster yet" to its nurses; the Deputy CNO's home
  lists submitted rosters waiting.

### Requests

1. The unit manager opens a request window for a target month (open and close dates; may
   close early).
2. Nurses make requests (day off, or a specific shift on a date), up to the unit's cap, and
   may withdraw while the window is open.
3. The manager accepts or rejects each one, with a reason. Rejected requests stay on record.
4. An accepted request is a pinned cell in that month's solve input (ADR 0005). The manager
   may edit or cancel it later; cancelled requests stay on record and reach no solve.

### Swaps

1. On an approved roster, for dates not yet passed, a nurse composes a proposal: a set of
   cell changes on her own cells and on any colleagues' cells needed to make it work.
2. The solver's validate call checks the resulting grid at once; a proposal that breaks a
   hard rule is refused on the spot with the reason.
3. Every colleague whose cells change must accept; one rejection ends the proposal (kept,
   with who rejected). The proposer may withdraw while pending.
4. When all have accepted, the unit manager sees before and after, the re-run validation and
   the cost change, and approves or rejects. He cannot edit a proposal; to change it he
   edits the roster directly.
5. Approval writes the cells as pinned cells in a new roster version. A pending proposal
   expires when any of its dates passes or a new version changes any of its cells. Everyone
   involved is notified at each step.

### Month close and the carry-over chain (ADR 0004)

- The solve input for month M starts from the carry-over of the latest *closed* month,
  projected forward through each approved roster in between by the same computation the
  close uses (the solver with every day recorded). Normally that is one step: M−1's roster in
  force, projected.
- At the close time on the first day after a month (default 00:30 hospital time), the worker
  closes every unit that has an approved roster for it: the roster in force plus every
  recorded leave and pin becomes fact, the solver validates and reports what the facts broke,
  and the carry-over is stored. A unit with no approved roster is skipped; the next month then
  starts from the last closed carry-over with no shift history.
- The unit manager may record late facts and re-close while the following month is not
  closed. A close always takes the previous closed month's carry-over as its input, never a
  projection.
- The carry-over handed into January has overtime-to-date and both fairness balances reset
  to zero.
- Days before a nurse's start date and after her end date are credited like leave in every
  solve input: nothing owed, nothing worked, no debt. A transfer takes effect from a chosen
  month; the carry-over follows the nurse.

## 6. The solver service

A small FastAPI application in the solver container wrapping the vendored `nurse_roster`
package (ADR 0002). Every call carries the shared token. It runs one job at a time and
rejects a second with `409`; the worker guarantees the ordering.

| Call | Purpose |
|---|---|
| `POST /solve` | Start a solve of one solve input; returns a job id. |
| `GET /jobs/{id}` | State, elapsed time, best cost so far, number of improving rosters, the best grid so far, the full result when finished. |
| `POST /jobs/{id}/cancel` | Sets the solver's stop event; the best roster found is kept. |
| `POST /validate` | Hard violations, cost, penalties and the per-rule explanation of a given grid against a solve input. No search. `web` also calls the same code (`solver_service.grid`) in its own process to explain a stored result, since it is in the one image and needs no search: the history reads when the solver is down or busy. |
| `POST /precheck` | Plain-language reasons the month may be infeasible. No search. |
| `GET /health` | Liveness, package version, worker count. |

The worker count defaults to the container's CPU count. The time limit of a solve is chosen
by the unit manager up to the System Admin's cap. The reproducible mode is not exposed.

## 7. The worker and the queue (ADR 0006)

Procrastinate, with its tables in the application database, run by the `worker` container.
Jobs:

- `run_solve(solve_id)`: under a hospital-wide lock, so solves run first come first served
  across units; submits the solve input to the solver, polls progress into the `Solve` row,
  stores the result, relays a cancellation. A failed attempt (solver crash, unreachable) is
  retried once inside the same job, so it keeps its place in line; a second failure is marked
  failed with its reason, and the manager can re-run it. A worker that dies goes on watching the
  job the solver still holds when it comes back.
- `recover_lost_jobs` (every five minutes): puts a dead worker's job back on the queue, which would
  otherwise hold the lock for good, and fails a solve whose job is gone.
- `close_month` (cron, close time on the first of each month) and `project_carry_over` on
  demand.
- `backup` (cron, 02:00) and backup retention.
- `expire_swaps` (hourly).
- `close_ended_nurses` (hourly): deactivates staff nurses whose last day is over. An end date of
  today or earlier deactivates at once. A manager's account stays the System Admin's.

The queue code is one module of ours (enqueue, progress, cancel, schedule) so the library can
be replaced without touching the API, the solver client or the solver.

## 8. The web application

### Backend

Django 6.1 (to 6.2 LTS in April 2027), Django Ninja for the JSON API with an OpenAPI
document, PostgreSQL 18, cookie sessions, CSRF. Django's admin site is not exposed. Apps, one
per domain area: accounts, hospital, units, nurses, rosters, requests, swaps, solves, closes,
notifications, audit, ops. A `solve input` assembler builds the solver JSON from the database
and stores it verbatim with every solve; a `result` reader stores and interprets results.

### Frontend (ADR 0008)

React 19 + TypeScript, Vite 8, shadcn/ui on Base UI with Tailwind 4, TanStack Query, TanStack
Router, TanStack Table (the roster grid and any table that needs sorting or filtering; short lists
stay plain tables) and Virtual (the roster grid), React Hook Form + Zod, Zustand, Recharts via shadcn, TanStack Pacer behind one debounce hook, orval-generated client. One responsive
web app, installable as a PWA; the grid scrolls horizontally on phones. In-app notifications
only. Visual design is decided later; the architecture does not depend on it.

Screens per role, in outline: System Admin (accounts, technical settings, audit log, solve
history, health and backups); CNO (hospital rules and weights, shift catalogue, leave types,
holidays and Ramadan, units and managers, nurses with import and export, each unit's rules, rostering attributes and leave
to read, roster overview and approvals); Deputy CNO (roster overview, approvals, hospital rules and each unit's rules,
rostering attributes and leave to read); Unit Manager (unit rules, rostering attributes, nurses, request
windows and requests, swaps, leave, the roster grid with solve, progress, results and
explanations, submit, versions, exports, month close); Staff Nurse (unit roster, own summary,
requests, swaps, own leave, notifications, password). The Deputy CNO, Unit Manager and Staff Nurse also read
the shift catalogue, leave types, holidays and Ramadan; the System Admin may open those pages
but has no link to them, because nothing in that role's work calls for it.

What a solve shows afterwards: every piece of information the result holds: precheck
warnings, penalties per rule, per-nurse cost and hours accounting, the explanation of the
largest violations per rule, solver statistics, recorded facts that broke rules, and in a
re-plan the comparison with the roster in force. A nurse's carry-over waits for the month close.
A stored result holds the penalties' totals only, so the explanation is worked out when asked.
The solver's words count days from 0, so what the pages show says dates instead.

The System Admin's solve history is unit, month, state, the kind of failure, who asked, when, how
long, the time limit, the attempts and the cost, and only that: the solver's and the worker's words
(`error`, `message`, `precheck`, the explanations) can name a nurse and a date, and no free text
reaches it. The cost was already theirs to read in the audit log.

### Security

Local accounts only, designed so an LDAP or SSO backend can be added as a Django
authentication backend. Generated passwords shown once, forced change at first login.
Minimum length 10 with Django's common-password and similarity checks, lockout for 15
minutes after 5 failed logins, sessions expire after 12 hours of inactivity (polling a solve's
progress is not activity), no two-factor authentication in v1. Every login, failed login and every change to settings, accounts,
rosters, requests and swaps goes to the audit log. So does each taking of the staff list, which holds everyone's gender:
who took it and how many nurses it held, and nothing from the file. Its import template holds no one's data and is not
logged. Nurses see colleagues' names and shifts only. The System Admin reads the log and may see no rostering attribute, so an attribute's change is logged as whose
changed and by whom, without its value or even which one, since a change to a two-way flag gives its value away. Unit
rules are logged with their values, as hospital rules are: they say nothing about a person. Attributes also stay off
the staff list, a file that leaves the system. Leave is logged the same way, as whose changed and by whom: not its type, its
dates or how many, since a long run gives the type away and a date is part of a roster.

### Nurse import and the staff list

A CSV of hospital ID, full name, gender, unit and start date, in UTF-8 or UTF-16 with a byte order mark, at most 500
nurses and 1 MB. Any other encoding is refused rather than guessed. Previewing saves nothing and keeps nothing, so
confirming sends the file again: it is judged again from the start, and with any problem, or when it no longer means what
was previewed, nothing is saved and the answer is the preview as it now stands. One password hash takes about half a second
on purpose, and the passwords may be kept nowhere, so the worker cannot make them and hand them back later. Confirming is
one long request instead: the hashes first, four at a time and holding no lock, then one transaction. The row limit keeps
it inside gunicorn's 300-second timeout (the default of 30 would kill it) even on one core. The password sheet is the
answer to that request and lives only in the page's memory: if the answer is lost after the transaction, the nurses stay and
their passwords are reset one at a time. Uploads stay in memory and never reach a temporary file. In a
staff list every cell is quoted, and one a spreadsheet would run as a formula starts with an apostrophe.

### Observability

JSON logs on stdout for every container; a Prometheus `/metrics` endpoint reachable on the
internal network only; the health page shows solver reachability, disk and database size,
last backup and queue state. Nothing else is bundled.

## 9. Defaults

- Hospital and unit rules are seeded from the reviewed default set the solver was shaped on
  (12-hour day and night shifts, Friday weekend, the standard forbidden successions, overtime
  caps, the weights) and flagged "defaults, review before the first solve". A unit's defaults
  follow the catalogue as it stands when the unit is created: a default shift the CNO renamed
  appears under its new code, and one the CNO retired is left out, which the solver refuses until
  the unit manager has chosen the unit's shifts.
- Time limit cap 300 s; unit default time limit 60 s; request cap 3 per nurse per month;
  backup 02:00 kept 30 days; close 00:30 on the first; time zone `Asia/Riyadh`. All editable
  by the role that owns them.
- A unit manager may roster any future month, not only the next.
- Nothing is hard-deleted: units are archived when they have no nurses, nurses are
  deactivated, requests and swaps keep their final state, leave corrected or removed stays as
  an ended row, every roster version and solve is kept. The exceptions are a public holiday and a month's fixed Ramadan dates, which have no
  history of their own: what a solve used is stored with it and the audit log keeps the rest.

## 10. Repository, build and tests

```
cp-sat-nurse-roster-app/
  backend/      Django project and apps, pytest-django suite
  solver/       vendored nurse_roster package and its tests, the FastAPI service
  frontend/     Vite + React SPA, Vitest suite
  deploy/       compose.yaml, compose.dev.yaml, Caddyfile, .env.example, install guide,
                reset-admin-password.sh, restore.sh
  docs/         this document, adr/, research/
  e2e/          Playwright suite against the compose stack
  Dockerfile    one multi-stage build, one image
  GLOSSARY.md
```

Development runs from `compose.dev.yaml` with hot reload for Django and Vite. GitHub Actions
runs the four suites on every push and, on a version tag, builds the image and pushes it to a
private GitHub Container Registry; each hospital's VPS logs in once with a read-only token
and pins the version in `.env`. The orval client is regenerated in CI from the backend's
OpenAPI document so an incompatible API change fails the build.

## 11. Pinned versions (2026-11-04)

Python 3.14, OR-Tools 9.15, Django 6.1, Django Ninja 1.7, Procrastinate 3.10, PostgreSQL 18,
Caddy 2.11, uv 0.13, Node 26 LTS (build only), Vite 8, Vitest 5, React 19.3, Tailwind 4.3,
TypeScript 6 (7 once the toolchain supports it), TanStack Query 5, Router 1, Table 9,
Virtual 3, React Hook Form 7, Zustand 5, Recharts 3, orval 8, Playwright 1.64.

## 12. Revisit later

The amount of solve information shown (now: everything), TanStack Charts and TanStack Form 2
once mature, Arabic and RTL, LDAP/SSO, email, push notifications, soft preferences, PDF
generation, the Deputy CNO's further responsibilities, the unit manager's further permissions.
