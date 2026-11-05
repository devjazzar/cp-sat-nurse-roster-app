# Nurse rostering web application, v1

Status: ready-for-agent
Type: enhancement
Published: 2026-11-05 by /to-spec


Spec drawn from the design interview of 2026-11-04. Vocabulary: `GLOSSARY.md`. Decisions and
their reasons: `docs/ARCHITECTURE.md` and `docs/adr/`. Where this spec and those documents
disagree, the documents win and this spec is wrong.

## Problem Statement

A hospital's nursing management rosters every unit by hand, month after month: a unit
manager juggles headcounts, team leaders, gender mix, night rest, consecutive-shift limits,
overtime caps, fairness between nurses, Ramadan hours, leave, and the days nurses asked for,
then the Deputy CNO reviews a spreadsheet she cannot verify, and nurses learn their month from
a printout. Changes mid-month (sick leave, a cover, a swap) are re-done by hand and nobody can
tell afterwards who changed what, why, or whether the rules still hold. Every month's
leftovers (hours owed, nights worked, overtime so far this year) are carried in people's heads.

The hospital already has a solver that turns one unit's month, with every rule spelled out,
into a roster and a per-nurse carry-over. What it lacks is the application around it: a place
where the rules, the units, the nurses, the requests and the approvals live, that only the
right people can touch, that any hospital's IT can install on one server without help.

## Solution

A web application, installed with one `docker compose up` on the hospital's own server, in
which:

- the **CNO** sets the hospital rules, the shift catalogue, the leave types, the holidays and
  the Ramadan dates, creates the units, assigns each its manager, and adds the nurses (one at
  a time or from a CSV), each of whom gets an account whose username is her hospital ID;
- each **unit manager** sets his unit's rules and his nurses' rostering attributes, opens a
  request window, decides the requests, records leave, and generates a roster with the
  solver, watching it improve live, editing cells by hand with instant validation, and
  submitting a draft for approval;
- the **Deputy CNO** (or the CNO) sees every submitted roster with its cost, penalties and
  explanations, and approves or rejects it with a comment;
- **staff nurses** see their unit's approved roster on any device, make requests during the
  window, propose swaps that colleagues and the manager accept in-app, and are told when
  their roster is approved or changed;
- the **unit manager** alone handles the month as it unfolds: covers, swaps, leave, re-plans
  from a date, each saved as a new version in force at once, with no further approval;
- the application closes each month automatically, computes every nurse's carry-over from
  what really happened, and starts the next month from it;
- the **system admin** creates the management accounts, sets the technical limits, and sees
  the audit log, the solve history, the health page and the backups, and nothing clinical.

The solver runs in its own container that nothing outside the server can reach.

## User Stories

### Installation and operations (System Admin)

1. As a system admin, I want to install the whole application with one compose file and one
   `.env`, so that a hospital is live in minutes with nothing else to set up.
2. As a system admin, I want the first start to create my account from a password in `.env`
   and force me to change it at first login, so that no default credential survives.
3. As a system admin, I want HTTPS to be automatic when I give a domain and self-signed when
   I don't, so that the installation works both on the internet and on an internal network.
4. As a system admin, I want to create the CNO, Deputy CNO and unit manager accounts and be
   shown each generated password once, so that I can hand it over and it is never stored in
   the clear.
5. As a system admin, I want to deactivate a management account and reset its password, so
   that staff changes in nursing management never need a developer.
6. As a system admin, I want to set the time limit cap, the backup time and retention and the
   month close time, so that the server's resources and schedule are mine to govern.
7. As a system admin, I want an audit log of who changed what, when and from where, with
   filters by user, action and date, so that I can answer any question about a change.
8. As a system admin, I want a solve history across all units with duration, status, cost
   and who asked, so that I can see how the solver is used and whether it struggles.
9. As a system admin, I want a health page showing solver reachability, queue state, disk
   and database size and the last backup, so that I notice trouble before users do.
10. As a system admin, I want nightly backups listed and downloadable, so that off-site copies
    are a download away.
11. As a system admin, I want a documented script to restore a backup and one to reset my own
    password, so that recovery never depends on being logged in.
12. As a system admin, I want upgrades to be a pull and a restart with migrations applied
    automatically, so that updating a hospital is routine.
13. As a system admin, I want application logs on the container's standard output and a
    metrics endpoint on the internal network, so that the hospital's own monitoring can
    watch the application.
14. As a system admin, I want to see no roster and no nurse's attributes, so that IT access
    never becomes clinical access.

### Hospital settings (CNO)

15. As a CNO, I want to edit every hospital rule (hours per day, Ramadan and breastfeeding
    reductions, weekend days, forbidden successions, overtime caps) with each field explained,
    so that the policy in the solver is the hospital's policy.
16. As a CNO, I want to edit the weights of the soft rules and understand what each prices,
    so that the solver's trade-offs reflect the hospital's priorities.
17. As a CNO, I want the rules to start from reviewed defaults flagged "review before the
    first solve", so that a new hospital can solve on day one without inventing numbers.
18. As a CNO, I want to maintain the shift catalogue (code, display name, hours, start and
    end time, colour), so that every unit draws on the same shifts.
19. As a CNO, I want to rename a shift's code and have nurses' histories follow, and to be
    refused when retiring a shift a unit still uses or changing the hours of a shift an open
    month uses, so that history and open rosters stay consistent.
20. As a CNO, I want to maintain the leave types, so that leave is recorded in the hospital's
    own categories.
21. As a CNO, I want to enter the public holidays and, after the moon sighting, fix the
    Ramadan dates of a month (otherwise derived from the Umm al-Qura calendar), so that
    hours owed are right.

### Units and nurses (CNO)

22. As a CNO, I want to create, rename and archive units, so that the hospital's structure is
    mine to keep current.
23. As a CNO, I want to assign each unit exactly one unit manager account and reassign it when
    the manager is unavailable, so that every unit is always run by someone.
24. As a CNO, I want to add a nurse (hospital ID, name, gender, unit, start date) and have her
    account created with a generated password shown once, so that onboarding is one step.
25. As a CNO, I want to import nurses from a CSV with a downloadable template and a preview
    that reports every row's problem before anything is saved, and to receive the generated
    passwords as a sheet shown once, so that a hospital's whole staff can be loaded at install.
26. As a CNO, I want to export the current staff list, so that I can reconcile it with HR.
27. As a CNO, I want to transfer a nurse to another unit effective from a chosen month, with
    her carry-over following her, so that moves between units keep her hours honest.
28. As a CNO, I want to deactivate a nurse with an end date rather than delete her, so that
    her past rosters stay intact and she owes nothing after she leaves.
29. As a CNO, I want to reset any nurse's password, so that a locked-out nurse is helped at
    once.
30. As a CNO, I want to see every unit's rosters with a per-month overview of each unit's
    state (no roster, draft, submitted, approved, closed), so that I know where the hospital
    stands.
31. As a CNO, I want to approve or reject submitted rosters exactly as the Deputy CNO can, so
    that approvals never wait for one person.

### Approvals (Deputy CNO)

32. As a Deputy CNO, I want my home page to list every submitted roster waiting for me, so
    that nothing is forgotten.
33. As a Deputy CNO, I want to open a submitted roster and see the grid, the penalties per
    rule, each nurse's hours and cost, the explanation of the largest violations, the precheck
    warnings and the solver's statistics, so that I judge the roster on facts.
34. As a Deputy CNO, I want to approve a roster and have the unit's nurses told at once, so
    that the roster is in force the moment I decide.
35. As a Deputy CNO, I want to reject a roster with a comment that the unit manager sees on
    his draft, so that he knows what to change.
36. As a Deputy CNO, I want to view any unit's roster, past or present, read-only, so that I
    can answer questions without asking the unit.
37. As a Deputy CNO, I want to be notified in-app when a roster is submitted, so that I act
    promptly.

### Running a unit (Unit Manager)

38. As a unit manager, I want to edit every unit rule (shifts used, headcounts, team leader
    and gender requirements, score targets, night rest, run limits, fairness, weekend limits,
    switches) with each field explained and reviewed defaults to start from, so that my unit
    rosters by its own rules.
39. As a unit manager, I want to set each nurse's rostering attributes (team leader, score,
    allowed shifts, Ramadan-reduced, breastfeeding), so that the solver knows my staff.
40. As a unit manager, I want to enter a nurse's opening values when she joins mid-year and
    have them locked once her first month closes, so that her hours and fairness start right
    and are then owned by the carry-over chain.
41. As a unit manager, I want to record leave (type, dates) for a nurse, so that leave is
    credited and the roster works around it.
42. As a unit manager, I want to open a request window for a target month with open and close
    dates and to close it early, so that requests arrive when I plan.
43. As a unit manager, I want to see each request and accept or reject it with a reason, so
    that every nurse gets an answer.
44. As a unit manager, I want to edit or cancel an accepted request later, so that a changed
    circumstance does not force an impossible month.
45. As a unit manager, I want to be told, before I solve, every reason the month may be
    infeasible or a rule meaningless (the precheck), so that I fix inputs instead of waiting
    for a failed search.
46. As a unit manager, I want to choose a time limit up to the cap the system admin set, so
    that I trade speed for quality knowingly.
47. As a unit manager, I want to start a solve and see my position in the queue, then the best
    cost so far and the number of improving rosters as it runs, so that I know what is
    happening.
48. As a unit manager, I want to stop a running solve and keep the best roster found, so that
    a good-enough roster is never thrown away.
49. As a unit manager, I want the finished solve to show the grid with every penalty per rule,
    each nurse's hours accounting and cost, the explanation of the largest violations, the
    solver's statistics and any recorded facts that broke rules, so that I understand the
    roster before I submit it.
50. As a unit manager, I want the unit's solve history with each result viewable and
    restorable as the draft, so that I can compare runs and go back.
51. As a unit manager, I want to edit the draft's cells by hand (pin a shift, pin off, clear)
    and see hard violations and the cost change instantly, so that my adjustments never
    break a rule unknowingly.
52. As a unit manager, I want a re-solve to keep my pins, so that my decisions survive the
    solver's.
53. As a unit manager, I want to submit the draft and have it frozen until the decision, and
    to see the rejection comment on it if it comes back, so that approval is a clear handoff.
54. As a unit manager, I want to edit the approved roster's cells directly (cover, leave, a
    swap agreed offline) and have the change in force at once as a new version, so that the
    month's realities never wait for approval.
55. As a unit manager, I want to re-plan the approved roster from a date, with earlier days
    kept as facts and the new roster kept close to the current one, and to see what changed,
    so that a mid-month disruption is absorbed with the least upheaval.
56. As a unit manager, I want to decide swaps that all involved nurses have accepted, seeing
    the cells before and after, the validation and the cost change, so that I approve only
    what keeps the roster sound.
57. As a unit manager, I want every roster version listed with who changed it, when and why,
    and any two versions comparable, so that the month's history is explainable.
58. As a unit manager, I want to export any version as CSV and Excel and print it from a
    print-friendly page, so that the roster reaches the ward in the forms it uses.
59. As a unit manager, I want to record late facts after a month ended and re-close it while
    the next month is still open, so that the carry-over reflects the truth.
60. As a unit manager, I want to see each nurse's projected carry-over for the coming month,
    so that I understand the hours and fairness the solver will start from.
61. As a unit manager, I want to reset a nurse's password, so that my staff are never locked
    out for long.
62. As a unit manager, I want in-app notifications when a solve finishes, a request or swap
    awaits me, and a roster is approved or rejected, so that I never poll.
63. As a unit manager, I want to see nothing of other units, so that my view is my unit.

### Living with the roster (Staff Nurse)

64. As a staff nurse, I want to log in with my hospital ID and be forced to change the
    generated password at first login, so that my account is mine from the start.
65. As a staff nurse, I want to see my unit's approved roster for the current and coming
    months, with colleagues' names and shifts only, so that I know when I and my colleagues
    work.
66. As a staff nurse, I want to see my own month: hours worked, overtime, hours balance and
    shift counts, so that I can check what I am owed and what I owe.
67. As a staff nurse, I want to make requests during an open window (a day off, or a specific
    shift on a date), up to my unit's cap, so that my wishes reach the roster.
68. As a staff nurse, I want to withdraw a pending request while the window is open, so that
    I can change my mind.
69. As a staff nurse, I want to see each request's outcome and the manager's reason, so that
    I always know where I stand.
70. As a staff nurse, I want to propose a swap that changes my cells and any colleagues' cells
    needed, and be refused at once with the reason if it breaks a hard rule, so that I only
    propose what can work.
71. As a staff nurse, I want to accept or reject a swap a colleague proposed that changes my
    cells, so that nothing about my shifts changes without my consent.
72. As a staff nurse, I want to withdraw my own pending proposal, so that I can retract it.
73. As a staff nurse, I want to see each swap's status (waiting for whom, approved, rejected
    and by whom, expired) so that I know what will happen.
74. As a staff nurse, I want an in-app notification when my roster is approved or changed, a
    request is decided, a swap moves a step, or a window opens, so that I never miss news
    that affects my days.
75. As a staff nurse, I want the application to work on my phone and be installable to the
    home screen, so that my roster is in my pocket.
76. As a staff nurse, I want to change my own password, so that my account stays secure.

### What the application does on its own

77. As the application, I take a nightly backup at the configured time and keep the
    configured number of days, so that the hospital can recover.
78. As the application, I close every unit's month at the close time on the first day after
    it, from the roster in force plus recorded leave and pins, and store each nurse's
    carry-over, so that the next month starts from facts.
79. As the application, I build each month's solve input from the latest closed carry-over,
    projected through the approved rosters in between, reset the year-to-date values for
    January, and credit the days outside a nurse's start and end dates, so that hours and
    fairness are right across months, years and transfers.
80. As the application, I expire a pending swap when one of its dates passes or a new version
    changes one of its cells, so that stale proposals never reach the roster.
81. As the application, I retry a failed solve once and report the reason, so that a hiccup
    in the solver does not cost the manager a run.
82. As the application, I write an audit entry for every login, failed login and every change
    to settings, accounts, rosters, requests and swaps, so that every question has an answer.
83. As the application, I lock an account for fifteen minutes after five failed logins and
    expire sessions after twelve idle hours, so that accounts are protected without
    two-factor authentication.

## Implementation Decisions

### Topology and delivery

- One application image per release, started by compose as three containers (`web`,
  `worker`, `solver`) next to stock PostgreSQL 18 and Caddy 2.11. The solver container
  publishes no port, holds no database credential, and sits on a network only `web` and
  `worker` can reach (ADR 0001).
- Configuration through `.env`: optional domain (automatic Let's Encrypt, else Caddy's
  internal self-signed issuer), secret key, database password, solver token, time zone
  (default Asia/Riyadh), one-time initial admin password, pinned image version.
- First start runs migrations, seeds the default rule sets, creates the System Admin.
  Upgrades are pull and restart. A restore script and an admin password reset script run on
  the server; restore is deliberately not a button.
- One multi-stage Dockerfile: a Node 26 stage builds the SPA, a Python 3.14 stage installs
  backend and solver with uv; Python 3.14 is the ceiling set by OR-Tools 9.15's wheels.
- The solver package and its tests are vendored from the original repository, which is
  frozen (ADR 0002).

### Backend

- Django 6.1 with Django Ninja for the JSON API and its OpenAPI document; PostgreSQL 18;
  cookie sessions and CSRF; Django's admin site not exposed (ADR 0003).
- Apps by domain area: accounts, hospital, units, nurses, rosters, requests, swaps, solves,
  closes, notifications, audit, ops. Two central modules: the solve input assembler (database
  to solver JSON, stored verbatim with every solve) and the result reader.
- UUIDv7 primary keys generated by PostgreSQL for every domain table; bigint identity for
  append-only logs (ADR 0007).
- Procrastinate, with its tables in the application database, run by the `worker` container,
  behind one queue module of ours. Jobs: run a solve under a hospital-wide lock (first come,
  first served across units; progress written to the solve row; cancellation relayed; one
  automatic retry), close months (cron), project carry-over, nightly backup and retention,
  expire swaps (hourly) (ADR 0006).
- Local authentication only, structured so an LDAP or SSO backend can be added as a Django
  authentication backend. Generated passwords shown once; forced change at first login;
  minimum length 10 with common-password and similarity checks; lockout 5/15 min; sessions
  12 idle hours.

### Solver service

- A small FastAPI application in the solver container wrapping the vendored package; every
  call carries the shared token; one job at a time, a second is refused with 409 (the worker
  guarantees ordering). Calls: start a solve, read a job (state, elapsed, best cost,
  improvements, best grid so far, full result when done), cancel (keeps the best found),
  validate (violations, cost, penalties, explanation of a grid against an input; no search),
  precheck (plain-language infeasibility reasons; no search), health. Worker threads default
  to the container's CPU count. Reproducible mode not exposed.
- The solver's own vocabulary is translated at this boundary only: the app's Approved roster
  is the solver's `published`; accepted requests, accepted swaps and manual edits are the
  solver's `pinned`; days outside a nurse's start and end dates are credited like leave; the
  app never uses the solver's soft day requests (ADR 0005).

### Domain model

- Hospital settings (one row: name, time zone, hospital rules with weights, request cap
  default); shift catalogue (code, display name, hours, start and end time, colour, active;
  hours frozen while an open month uses the shift; code rename carried through histories;
  retirement refused while a unit uses it); leave types; public holidays; Ramadan days per
  month (fixed by the CNO or derived from Umm al-Qura).
- Unit (name, archived, manager, unit rules, request cap, default time limit). Exactly one
  manager per unit, one CNO and one Deputy CNO per hospital.
- User (username, full name, role, active, must-change-password) with an optional nurse
  profile (hospital ID = username, gender, unit, start and end dates, team leader, score,
  allowed shifts, Ramadan-reduced, breastfeeding, opening values editable until the first
  close). Every Staff Nurse has a profile; a Unit Manager may.
- Roster, one per unit and month, with state and exactly one draft; roster versions each
  holding the full grid, author, time, reason and origin (solve, edit, re-plan, swap,
  request) and the result they came from; leave; pinned cells with origin; request windows;
  requests; swaps with their change set and participants; solves with stored input, result,
  progress and queue position; month closes with the carry-over per nurse; carry-over rows
  with source (opening, projected, closed); notifications; audit entries; technical settings.
- Nothing is hard-deleted: units archive, nurses deactivate, requests and swaps keep their
  final state (a cancelled accepted request becomes `cancelled`), every version and solve is
  kept.

### State machines

Roster: `draft` → (submit) → `submitted` → (approve) → `approved`; `submitted` → (reject,
comment kept) → `draft`. Each solve or manual edit of a draft replaces its grid. After
`approved`, every edit, re-plan, accepted swap or accepted request creates a new version in
force immediately; there is no further approval state.

Request: `pending` → `accepted` | `rejected` | `withdrawn` (by the nurse while the window is
open); `accepted` → `cancelled` (by the manager). Only `accepted` reaches a solve, as a pin.

Swap: `pending` (participants deciding) → `awaiting_manager` (all accepted) → `approved`
(written as pins in a new version) | `rejected`; `pending` → `rejected` (one participant) |
`withdrawn` (proposer); `pending`/`awaiting_manager` → `expired` (a date passed or a cell
changed). The resulting grid is validated at proposal, at each acceptance and at the
manager's decision; a hard violation refuses the step with its reason.

Month close and carry-over (ADR 0004): a month's input starts from the latest closed month's
carry-over projected through each approved roster in between; the close on the first day
after the month takes the previous closed month's carry-over as input, never a projection;
re-close allowed until the next month closes; a unit with no approved roster is skipped; the
carry-over into January resets overtime-to-date and both fairness balances.

### Frontend

- React 19 + TypeScript, Vite 8, shadcn/ui on Base UI with Tailwind 4, TanStack Query,
  TanStack Router (unit, month and filters in typed search params), TanStack Table for
  the roster grid and any table that needs sorting or filtering (short lists stay plain tables)
  and Virtual for the grid, React Hook Form + Zod, Zustand for the little
  client-only state, Recharts via shadcn, TanStack Pacer behind one debounce hook, an
  orval-generated client from the OpenAPI document regenerated in CI (ADR 0008).
- One responsive web app installable as a PWA; the grid scrolls horizontally on phones;
  in-app notifications only.
- Role-scoped screens as outlined in the architecture document; nurses see colleagues' names
  and shifts only.

### Observability and defaults

- JSON logs on stdout; a Prometheus metrics endpoint on the internal network; a health page
  with solver reachability, queue, disk, database size, last backup; audit log; solve history.
- Defaults: time limit cap 300 s, unit time limit 60 s, request cap 3, backup 02:00 kept 30
  days, close 00:30 on the first, time zone Asia/Riyadh, rule sets seeded from the reviewed
  defaults and flagged for review.

## Testing Decisions

A good test exercises the application as a user or a neighbouring system would, through a
boundary that will outlive the implementation, and asserts on what came out: a response, a
stored roster, a notification, an audit entry. It never asserts on which functions were
called or how a table is shaped.

### Seams

Three seams, from highest to lowest; the first carries almost everything.

1. **The web API** (new). Tests drive the Ninja API over HTTP with a real PostgreSQL and a
   logged-in user of a given role, and exercise whole flows: add a nurse and log in as her,
   open a window, make and decide requests, solve, edit, submit, approve, propose and decide a
   swap, close a month, check the carry-over handed to the next. The solver is replaced at
   the solver client's boundary (the same interface the HTTP client implements) by a scripted
   fake that returns prepared results, reports progress and honours cancellation, so these
   tests are fast and deterministic. Authorization is tested here too: every endpoint, every
   role, the unit scoping of unit managers, the nurse-only view of nurses.
2. **The solver service** (new, small). Contract tests over HTTP against the real FastAPI
   service and the real solver on the four-nurse sample from the solver's how-to (proven
   optimal in under a second): start, poll, finish, cancel, validate, precheck, the token
   check, the 409 on a second job. A few API tests also run end to end with this real service
   on the same sample, so the fake can never drift from the contract.
3. **The browser** (new, few). Playwright smoke journeys against the compose stack for each
   role's main path: log in and change password, generate and submit a roster, approve it,
   see it as a nurse, make a request, propose and accept a swap, on desktop and phone sizes.

The solver package keeps its existing seam and suite unchanged: per-rule tests in the style
of a constraint verifier, regression tests from the audit passes, the ER fixture; these are
the prior art for how to test a rule in isolation, and the solver's request/result contract
tests are the prior art for contract tests.

### What is tested where

- Backend domain logic without the API (solve input assembly, carry-over projection and
  chain, year reset, start and end date crediting, swap validation and expiry rules, request
  caps and windows, shift rename and retire guards) is tested through the API seam wherever a
  request can reach it; only the assembler and the carry-over chain get direct unit tests in
  addition, because their inputs are large and their edge cases many.
- Frontend: Vitest for the roster grid's pure logic (selection, pending edits, diff display)
  and the debounce hook; everything else through the browser seam. The generated client
  compiling against the current OpenAPI document is itself a test, run in CI.
- Queue and scheduled jobs: tested through the API seam with the worker run inline in tests
  (Procrastinate's in-process mode), plus one real-worker test per job in the compose-based
  end-to-end run.

## Out of Scope

Arabic or any second language and RTL; LDAP, Active Directory or SSO; email and SMS; push
notifications; server-side PDF generation (the print page suffices); soft, unapproved
preferences (the solver's `desired_days`/`undesired_days`); native mobile apps; the solver's
reproducible mode in the UI; two-factor authentication; delegation of a role during absence
(the CNO stands in for the Deputy, the CNO reassigns a unit's manager); per-date headcount
exceptions; any change to the solver's rules or contract; a visual design system (decided
later, independent of this architecture); the Deputy CNO's and unit manager's further
responsibilities the owner has deferred.

## Further Notes

- Build order, each step shippable and tested at its seam: (1) repository skeleton, vendored
  solver, solver service with its contract tests, Dockerfile and compose with Caddy and
  PostgreSQL; (2) accounts, roles, authorization, audit, first-start bootstrap; (3) hospital
  settings, shift catalogue, units, nurses with import and export; (4) solve input assembly,
  queue and worker, solves with progress and cancellation, drafts and solve history;
  (5) submission and approval, versions, manual edits with validation, re-plan, exports;
  (6) request windows and requests; (7) swaps and expiry; (8) month close, carry-over chain,
  opening values, year reset; (9) notifications, health page, backups, metrics; (10) the
  SPA, screen by screen in the same order, with the browser smoke journeys last.
- One reconciliation was made silently during design and is worth a glance: the owner first
  said a cancelled accepted request is removed, then accepted that nothing is hard-deleted;
  the spec keeps cancelled requests as records.
- The amount of solve information shown to managers and approvers is "everything the result
  holds" for now and will be revisited once real users have seen it.
- Deferred technology to re-evaluate in a year: TanStack Charts and TanStack Form 2 once
  mature, TypeScript 7 once Vite and Vitest run on it, Django 6.2 LTS in April 2027.
