# Nurse rostering application: architecture and product rules (v1)

Agreed on 2026-11-04 after a six-round design interview. This document is the shared
understanding the build starts from. Vocabulary is defined in [GLOSSARY.md](../GLOSSARY.md);
the reasons behind the hard-to-reverse choices are in [docs/adr](adr/); the facts the
technology choices rest on are in [docs/research](research/).

## 1. Purpose and scope

One installation serves one hospital. Unit managers generate monthly rosters for their units
with the CP-SAT solver, the Deputy CNO approves them, staff nurses see the approved roster, make
requests and preferences for coming months and propose swaps. The hospital's IT runs the installation as a
single `docker compose` stack on one VPS. There is no multi-tenancy, no shared service between
hospitals, and no internet access for the solver.

Out of scope for v1 (designed so they can be added, not built): Arabic or any second language,
LDAP or SSO, email or SMS, push notifications, server-side PDF, native mobile apps, the solver's
reproducible mode in the UI. Soft preferences, once out of scope, are in since ticket 29 (ADR 0013).

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

Volumes: `pgdata` (PostgreSQL), `backups` (the nightly backups, mounted by `worker` and, read-only, by `web`, and by no other
service), `caddy_data` (certificates).

### Configuration (`.env`)

`DOMAIN` (optional; with it Caddy obtains Let's Encrypt certificates, without it Caddy serves a
self-signed certificate via `tls internal`), `SECRET_KEY`, `POSTGRES_PASSWORD`,
`SOLVER_TOKEN`, `TIME_ZONE` (default `Asia/Riyadh`), `INITIAL_ADMIN_PASSWORD` (read once),
`APP_VERSION` (the image tag the hospital pins).

### First start, upgrades, recovery

- First start: `web` runs migrations, seeds the default hospital and unit rule sets (section
  9), and creates the System Admin account from `INITIAL_ADMIN_PASSWORD` with a forced
  password change at first login (`manage.py prepare`, which logs both). The variable is ignored afterwards.
- Upgrade: `docker compose pull && docker compose up -d`; migrations run at `web` start.
- `deploy/reset-admin-password.sh`: resets the System Admin password from the VPS, printed once with a forced change, ends
  the account's sessions and lifts a lock from wrong passwords; audited with no actor, "from the server".
- `deploy/restore.sh <backup name or file>`: stops `web` and `worker`, backs up the database as it stands, restores into a new
  database and only then puts it in the old one's place (the old renamed aside, the new renamed in, the old dropped last), starts them again (`web` migrates an older backup forward).
  Restore is deliberately a script, not a button.
- Nightly backup (02:00 hospital time, kept 30 days, both the System Admin's to change) is a worker job; backups are listed
  and downloadable on the System Admin's health page, each download audited. The files are the record (`ops.backups`): a
  `pg_dump` in its custom format named by its UTC time, readable by the app user only, the newest always kept. Off-site copies
  are the hospital's job and are documented in the install guide, `deploy/INSTALL.md`.

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
| Hospital rules and weights, shift catalogue, leave types, skill catalogue, public holidays, Ramadan dates | | yes | | | |
| Read the hospital rules and weights | | yes | yes | | |
| Read the shift catalogue, leave types, skill catalogue, public holidays, Ramadan dates | yes | yes | yes | yes | yes |
| Create, rename, archive units; assign each unit its manager | | yes | | | |
| Read units | | yes | yes | own unit | |
| Add nurses (form or CSV import), give a unit manager a nurse profile, correct a nurse's gender and start date and a staff nurse's name, transfer, set end dates, export staff list | | yes | | | |
| Read nurses | | yes | | own unit | |
| Record, renew and take off a nurse's skills (a manager with a nurse profile's too) | | yes | | | |
| Read a nurse's skills with their expiries | | yes | yes | own unit | |
| View every unit's rosters, with the per-month state overview and the Day view (one date across every unit) | | yes | yes | | |
| Approve or reject a submitted roster | | yes | yes | | |
| Read an approved roster's versions with their reasons, and compare any two | | yes | yes | own unit | |
| Unit rules; nurses' rostering attributes (gender aside: the CNO sets and corrects it) and opening values | | | | own unit | |
| Read the unit rules, and the rostering attributes and opening values of a unit's nurses | | yes | yes | own unit | |
| Request windows; decide requests; read the unit's preferences; decide swaps; open, offer and withdraw covers; record, correct and remove leave | | | | own unit | |
| Read a unit's leave with its type | | yes | yes | own unit | |
| Solve, edit the draft, submit, edit the approved roster, re-plan, re-close a month | | | | own unit | |
| Exports (CSV, Excel, print page) of any roster version | | yes | yes | own unit | |
| Reset a staff nurse's password (a manager's stays the System Admin's) | | yes | | own unit | |
| Read the name of own unit | | | | | yes |
| View own unit's approved roster (names and shifts only) and own summary | | | | | yes |
| Make and withdraw requests; make and withdraw preferences, or ask for one as a request; propose, accept and reject swaps; accept and decline covers offered to them | | | | | yes |
| Read own leave with its type (a manager with a nurse profile too) | | | | yes | yes |
| Read own skills with their expiries (a manager with a nurse profile too) | | | | yes | yes |

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

**Hospital settings** (one row): the hospital rules (every field of the solver's `general` block including the weights)
with a review flag. Nothing else: no page or rule reads a hospital name, so none is kept; the time zone is `TIME_ZONE` from
the environment (section 2), set at install; and the request cap is each unit's own (below, default 3), with no hospital-wide
default.

**Shift** (catalogue): code (the solver's name), display name, hours, start and end time,
colour, active flag. Hours cannot change while an open month's roster uses the shift (a month not closed: one not over, or
an approved one over that its close will read; a closed month stored the hours it read); the
code may be renamed (each rename is recorded, the app carries the old name through nurses'
histories, and the forbidden successions, every unit's rules and every list of allowed shifts follow
at once, and no other shift may take a code a shift used to hold); a shift a live unit still uses, or
a forbidden succession names, cannot be retired, and the refusal names the units.

**Leave type**: name, active flag. Every type counts the same for hours.

**Skill** (catalogue): name (unique in any case of letters), expires, required to work, active flag. The CNO keeps it and
every role reads it, the System Admin included, since it names no one. Never deleted, only retired: nurses' records of it
and past rosters keep it. The name may be renamed: each rename is recorded (old name, new name, by whom and when), and no
other skill may take a name a skill used to hold, as for a shift's code, so that an old name in a stored solve input
still means one skill. A change goes to the audit log with its values (`skill.created`, `skill.changed`). Turning `expires`
on is refused, naming the nurses, while a current record of the skill has no expiry; turning it off is allowed, and the
expiries recorded stay, counting for nothing until it is on again.

**Public holiday**: date, name. **Ramadan days**: per month, the CNO's fixed dates or range,
else derived from the Umm al-Qura calendar.

**Unit**: name (unique among units not archived), archived flag, manager (a user; none once
archived), the unit rules (every field of the solver's `department` block but its name, which is
the unit's) with a review flag, request cap per nurse per month (default 3), preference cap per nurse per month (default 10,
0 switching preferences off), default time limit.

**User**: username, full name, role, active flag, must-change-password flag.

**Nurse profile** (0..1 per user): hospital ID (= username), gender, start date, end date,
team leader, score, Ramadan-reduced, breastfeeding, opening values (overtime this year, hours balance,
night and weekend fairness balances; editable until her first month closes), whether a manager has ever saved
these, which is how a score at the default is told from one somebody looked at. Her skills are rows of their own (below).

**Nurse skill**: nurse, skill, expiry (null for a kind that does not expire), recorded by and when; removed by and when. At
most one current row a nurse and skill; a renewal or removal ends the row rather than rewriting it, as leave's does, because
the audit log says only whose skills changed and by whom (`nurse.skills_changed`), never which skill or date, since a lapse
says something about a person. The CNO records, renews and takes them off on the nurse's row of the Nurses page, a manager
with a nurse profile's too; her unit's manager (and the manager of a unit she is due to join) reads them on the Nurses page
and Rostering attributes, the Deputy CNO on Rostering attributes for any unit, and she reads her own on My month. The System
Admin reads none. On the profile, not a placement, so they follow her across a transfer and stay when she is deactivated or
ends. A retired skill can be neither recorded nor renewed, and a record of it stays until the CNO takes it off. Every write
takes the hospital settings' lock before the nurse's, as a catalogue change and a transfer do.

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
last restored a result as that grid; a solve replacing it clears that. A submitted or an approved roster is frozen to a solve:
none starts or ends on it and no result is restored onto it (one check, `rosters.drafts.why_frozen`); a re-plan is the way to
solve an approved month again. A submitted one takes no pin either. Leave may still be recorded on it, and ends a pin as ever;
the grid keeps its shift and the approval sees the broken rule. An approved roster of a month not over is edited by its manager
cell by cell, each save a new version (below).

**Submission**: one sending of a draft for a decision: who submitted it and when, what the draft was warned of then, and
the decision, by whom, when and, for a rejection, the comment the manager reads. Nothing is deleted, so every comment is
kept, which the audit log cannot hold, since a comment may name a nurse or their leave.

**Roster version**: the roster's full grid (nurse × date → shift code or off) with who,
when, why and origin (solve, manual edit, re-plan, swap, request, cover), plus the result it came
from when a solve produced it. The latest version of an approved roster is in force. The first approval makes version 1
with origin `solve` and the roster's solve, and its grid is the roster's as approved, hand edits included: the pins and the
solve history say where each cell came from. A version keeps the codes it was saved with, as a stored result does, and is
read under today's. `Roster.grid` is always the latest version's grid under today's codes: every version is made by one
function, `rosters.versions.make_version`, under the roster's row lock, which numbers it. A manager's direct edit needs a
reason, is refused when it changes no cell (a pin alone included), saves even when it breaks a hard rule (the roster in force
has to say what is so, a shift left short included) and makes each edited cell a manager's pin. Leave recorded on a day an
approved roster of a month not over works takes the shift off as a version of its own, origin `edit`, by whoever recorded it,
with a reason that says leave and never the type; removing the leave puts nothing back. The reason, which can say a cell was
leave, is read by the unit's manager, the CNO and the Deputy CNO, in the version list and its comparison of any two versions;
never by a nurse, in a notification or in the audit log, whose entry `roster.changed` says only which version was made and how
many pins and cells changed. A leave-made version has no entry of its own, since one beside the leave's would date that leave
for the System Admin.

**Leave**: nurse, date, leave type, recorded by and when; removed by and when. One row a date, and at most one current row
for a nurse and date. A correction or removal ends the row rather than rewriting it, because the audit log may hold none of
this. A date must lie within the nurse's start and end dates when it is entered; a later correction to those dates leaves
the row, flagged on the unit's list, where it counts for nothing.

**Pinned cell**: unit, nurse, date, shift or off, origin (manager, accepted request, accepted swap, accepted cover), pinned by and when;
removed by, when and why (cleared, replaced, leave). At most one current pin for a nurse and date, and none is deleted. It
belongs to the unit whose month it is, so a transfer leaves it behind. Leave wins over a pin: recording leave on a pinned day
ends the pin and tells the manager, and pinning on a day of leave is refused. A pin that falls out of step with the rest (the
nurse no longer in the unit's month, a day outside their dates or on leave, a shift the unit no longer works or the nurse may
not work) is set aside, not removed: it reaches no solve and the draft says why, and it counts again if that changes. A shift's
hours, a unit's shifts and a nurse's allowed shifts cannot change under a pin that counts in a month not yet over. Nor can a
unit stop working a shift that its submitted or approved roster of a month not yet over holds, pinned or not: a re-plan and
month close give that roster whole to the solver, which refuses a cell on a shift its unit does not work
(`rosters.drafts.frozen_cells_on_shifts_going`).

**Request window**: unit, target month (one not yet begun), open date, close date (the last day requests are taken, before
the month begins; both days on the hospital's clock), state (`scheduled`, `open`, `closed`), who closed it early. The dates
decide whether it is open, for every page and every write; the stored state and who is told follow them in the hourly job or the
next write about the unit, whichever comes first (`requesting.windows`). At most one window of a unit is scheduled or open; once
one has closed, another may target any month, the same one included. A window opens while either the unit's request cap or its
preference cap is above 0; a unit with both at 0 opens none, and is told of both.

**Request**: nurse, window, date, a shift or a day off, state (`pending`, `accepted`, `rejected`, `withdrawn`, `cancelled`,
`replaced_by_leave`, `expired`), and its steps: who made, withdrew, accepted, rejected, edited or cancelled it, when, and the reason given
(the nurse's when she made it, the manager's for a decision), which only she and the unit's manager read. At most one request a
nurse and date is pending or accepted, and those two states count against the unit's cap a nurse a month, across the month's
windows; a cap lowered later stops new requests and leaves those made. Only an accepted request reaches the solver, as a pinned
cell of origin `request`, judged as any pin is (`rosters.pins.Judge`): a manager's pin on its cell is replaced, a swap's refuses
it. An edit changes what the pin promises and keeps what was asked. Leave recorded over an accepted request ends its pin and
makes it `replaced_by_leave`, and its nurse is told. Nothing is deleted: a request the manager cancels after acceptance becomes
`cancelled`, its pin ends and no cell changes. One still pending when its month closes becomes `expired`, with a step of no one's
hand and the same words for everyone ("The month closed before a decision."), and its nurse is told.

**Preference** (ADR 0013): nurse, window, date, kind (`day_off`, or `working_day` of any shift), state (`made`, `withdrawn`,
`asked_instead`), when made, when ended and by whom, and for one asked for instead the request made in its place. Nobody decides
it and it is never a pin; the live ones (`made`) of the unit's windows for the month are the solve input's `undesired_days` and
`desired_days`, which the solver keeps at the two weights' price. A date holds one wish: at most one live preference a nurse and
date, and none where a request of hers is pending or accepted, or the other way round, in any unit's window (a rejected,
withdrawn, cancelled, replaced or expired request frees the date). Live preferences count against the unit's preference cap a
nurse a month, across the month's windows, under the nurse's row lock a request's count takes; a cap lowered later keeps those
made. A leave date or one outside her dates is refused as it is made; leave recorded later leaves it `made` (the solver ignores
a leave day, and whether it is on leave is read, never stored). A nurse transferred out keeps hers on the old unit's record,
counting against that unit's cap and reaching no solve. Nothing is deleted. Only the nurse and her unit's manager read them.

**Swap**: unit, roster, the roster version it was proposed on, proposer, the proposer's note, the set of cell changes (nurse,
date, the shift or off before, the new shift or off, and the pin its approval made), the participants (every colleague whose cells
change, never the proposer) with their answers, state (`pending`, `awaiting_manager`, `approved`, `rejected`, `withdrawn`,
`expired`), who ended it and when, why it expired (a date passed, or a version changed a cell: the manager's to read), the
manager's reason, and the version its approval made. Only staff nurses' cells are swapped, a manager with a nurse profile's
never; a cell is in at most one swap still waiting. A colleague's accepted request on a cell refuses the swap (the request stays her
promise), while a manager's pin, or an earlier swap's, is replaced by the approval.

**Cover** (ADR 0011): unit, roster, the version in force when it was opened (for leave, the version the leave made), date,
shift, how it opened (`leave` or `manager`), the manager's note, state (`open`, `offered`, `taken`, `withdrawn`, `filled`,
`expired`), who withdrew it and when it ended, and for one taken its taker and the version her acceptance made. The absent nurse
is not on the row. Its offers: one per nurse offered (when, her answer `pending`, `accepted` or `declined`, and when she
answered), a nurse at most once, never removed. A cover's pin is a pinned cell of origin `cover`, which the manager's editor
refuses as it refuses a swap's or a request's ("change it there").

**Solve**: unit, month, requested by, time limit, state (`queued`, `running`, `succeeded`,
`failed`, `cancelled`), the queue's job, progress (elapsed, best cost, improvements), the
complete solve input and result as stored, error text, and for a failed one its failure kind: `refused`, `unreachable`, `lost`
(the solver restarted), `overrun` (past the time limit), `solver_error`, `stuck` (an earlier job would not stop), `worker_lost`,
`unexpected`, or `solver` on a row from before the kinds were told apart. A queue position is worked out when asked,
from the solves ahead on the queue, so it cannot be out of date. `succeeded` means the solver ran
to its end, which may have found no roster; `cancelled` may still hold the best roster found, which
becomes the draft; only `failed` means the solver gave no answer. Rules the solver refuses are
`failed` with the failure `refused`, and read as rules to review, not as a failed solve. At most one
solve of a unit's month is active at a time. A re-plan is a solve with the date it plans from, the version it started from, the
manager's reason for the version it makes, and what its end did to the roster in force (`version`, `unchanged`, `outdated`,
`month_over`).

**Month close**: unit, month, closed at, closed by (none for the schedule, or the manager closing it again), the roster version
closed, the input it was worked out on (the roster in force as `published`, the first day after the month as `replan_from`) and
the close result: the month as it happened, what the facts broke and each nurse's hours accounting and carry-over, as a solve's
`nurses` block reads. It is not a solve, so it is in neither solve history. Nothing rewrites it: closing again is a new row, and
the latest of a unit's month is the close in force.

**Carry-over** (per nurse and month): the values and their source (`opening`, `projected`, `closed`). A closed row belongs to its
close and is never rewritten; a projected row is the latest worked out for that month, a record only, since an assembly works the
chain out again; opening values are the nurse profile's and have no row.

**Notification**: user, event, payload, when it was read. The payload holds identifiers only (a unit, a month, a solve, a
version number), and the words are worked out as it is read, from what those name then: a rename or a corrected name leaves
nothing stale, and nothing about a nurse, a leave or a rejection's comment is kept or said. **Audit entry**: actor, action, target,
before and after, IP, time. **Technical settings** (one row): time limit cap (default 300 s),
backup time and retention, close time.

## 5. Lifecycles

### Roster

```
            solve / edit                 submit                  approve
  (none) ──────────────▶ draft ──────────────▶ submitted ───────────────▶ approved
                           ▲                      │                         │
                           └──────── reject ──────┘        edits, re-plans, swaps,
                                 (comment kept)            accepted requests, covers:
                                                           new versions, in force at once
```

- Each solve replaces the draft's grid, unless its result has no roster or `ok` is false, which
  leaves the draft as it was; the solve history keeps every result, and any result
  with a roster can be restored as the draft, unless a solve of that month is queued or running, the month is over, or a shift
  it uses has since been retired or had its hours changed, since its cost and hours would no longer hold (it can still be
  opened, and a rename is carried). The stale-draft warning then compares with the restored solve's input. The draft grid is
  editable by hand: each edit is a pin, the grid it would make is checked as the manager edits, and edits are saved
  together. Every solve and every restore puts the pins that count on top of its roster, so a draft never disagrees with a
  pin; a pin saved since the input was stored, and a pin so put on top, warns like other changes since. Saving while a solve
  of the month is queued or running is allowed and warned of. The solve's own cost holds only for the month it was given, so
  a draft edited or out of date is costed and checked again on the month as it stands. Submitting freezes the draft until
  the decision.
- Submitting checks the grid again on the month as it stands with the solver's own code, always: a draft out of date or
  edited by hand goes with its warning, and is refused only if it breaks a hard rule or cannot be checked. It is refused while
  a solve of the month is queued or running. The CNO or the Deputy CNO approves it, checked again the same way since leave
  may have been recorded while it waited, or rejects it with a comment. Approving takes the catalogue's lock, then the
  month's nurses' (the lock a leave write takes), then the unit's, so neither leave nor a second approver passes between the
  check and the decision. A draft is the unit management's alone: the CNO and the Deputy CNO see that one exists, and read a
  submitted or approved roster with its solve's details. The locks on nurses' and users' rows are `FOR NO KEY UPDATE`: they serialise
  those writes as `FOR UPDATE` would, but let another transaction's foreign key to the row (a notification's, checked at
  commit) through, which `FOR UPDATE` did not, deadlocking a leave against an edit. Every new such lock is taken the same way.
- After approval, the unit manager alone changes the roster: direct cell edits, swaps,
  re-plans from a date (earlier days are facts; the `change` weight keeps the new roster
  close), and covers, which the manager offers and the first nurse to accept puts in force as a version of her own making.
  Every change is a new version, in force immediately, and notifies the unit's nurses of the month, except whoever
  made it, that the roster changed: never why, which cells or whose.
- A re-plan (`solves.replans`) is a solve of an approved month that has not ended, from a date that is today or later and in
  the month: the month's first day only while it is still to come, never the first day after it, which is month close. A draft
  is solved again instead, and a submitted roster waits for its decision. It goes through the same queue as a solve, one active
  a unit's month, with the same progress, stop and retry. Its input holds the roster in force as `published` and the date as
  `replan_from`, and the solver makes every earlier day a fact: a pin that counts, of any origin, then leave and the days outside
  a nurse's dates, then the roster in force; a pin set aside is no fact. A nurse no longer in the month is left out, and one who
  joined since worked nothing before the date. Its end takes the locks an approval takes, and its roster becomes a version with
  origin `replan`, the manager's reason or one naming the date, and the roster's solve set to it, only while the version it
  started from is still in force and the month's nurses, leave and pins are as its input holds them; otherwise it would undo
  what came since, so it is kept in the history and the manager re-plans again. A rename is no change. A roster that changes no
  cell makes no version and tells no nurse; no roster, or one breaking a hard rule, leaves the roster in force as it was. A
  stopped re-plan's best roster goes in force like a finished one's. Its result shows the comparison with the roster in force it
  started from: the cells changed, the cost of each on the re-plan's input, rule by rule, and the facts that broke rules. A nurse reads the roster in force on My roster and no
  version list. Leave recorded late is such a change too (section 4). A month already over cannot be edited; its close reads
  leave and pins itself.
- A month with no approved roster shows "no roster yet" to its nurses; the CNO's and the Deputy CNO's homes
  list submitted rosters waiting, oldest first. A nurse sees their unit's approved roster for this month and later, the unit
  being the one each month falls under for them: names and shifts only, a colleague's leave the same empty cell as a day off,
  and their own leave as leave.

### Requests

1. The unit manager opens a request window for a target month (open and close dates; may
   close early). Its nurses of that month, one due to join included, are told when it opens, and
   again if it closes early.
2. Nurses make requests (day off, or a specific shift on a date), up to the unit's cap, and
   may withdraw a pending one while the window is open. A request that could never be accepted (a
   day on their leave or outside their dates, a shift the unit does not work or they may not) is
   refused as it is made.
3. The manager accepts or rejects each one, with a reason, required to reject. Rejected requests stay on record. A window
   that closes by its date with requests waiting tells the manager once, how many still wait worked out when read.
4. An accepted request is a pinned cell in that month's solve input (ADR 0005). The manager
   may edit or cancel it later; cancelled requests stay on record and reach no solve. Accepting or editing puts the pin's
   cell on a draft at once; a submitted roster takes neither, nor a cancel, until its decision; on an approved roster of a
   month not over, a changed cell is a new version with origin `request`, telling the unit's nurses, and one that changes no
   cell makes no version. Each decision tells the nurse who made the request, and nobody else.
5. In the same window a staff nurse makes preferences (a day off or a working day, no reason), up to the unit's preference
   cap; while it is open she may withdraw one, or ask for it as a request instead: the request is made under the request cap
   and the window's rules (for a working day, the shift she chooses), the preference ends as `asked_instead`, and a refusal
   of the request leaves the preference as it was. Once the window closes they are fixed. Nobody decides them and nobody is
   told of them; the manager reads each window's beneath its requests. Each solve and re-plan of the month lists the live ones,
   and a draft solved before one was made or ended warns "preferences changed".

### Swaps

1. On an approved roster, for dates not yet passed (today included, on the hospital's clock), a staff nurse composes a
   proposal: a set of cell changes on her own cells, at least one, and on any colleagues' cells needed to make it work, at most
   62 cells in all (a month of her own and of one colleague's). One of only her own cells needs no colleague and goes to the
   manager at once.
2. The solver's own code checks the resulting grid at once, on the month as it stands, with the swap's cells as pins (so a
   manager's pin there does not count against it); a proposal is refused on the spot, with every reason, when a cell cannot
   hold its change or the grid newly breaks a hard rule (one the roster in force already breaks, which an edit may save, is not
   the swap's). The proposer learns nothing about a colleague that My roster would not show: every reason resting on a
   colleague's facts (leave, dates, unit, allowed shifts, hours, an accepted request, another swap) reads "This swap cannot work
   for Badr on 5 June", and is checked only after what My roster shows, so leave asked for as a day off reads "already a day
   off" like any day off; a shift-day left without a team leader or both genders reads only that that day's shifts would break the unit's
   rules, and the proposer reads no rule, solver text or cost about anyone else. Her own reasons are said in full, and so is
   anything My roster shows (a cell's shift, a date passed, a headcount). The manager reads every reason in full
   (`swaps.judging`).
3. Every colleague whose cells change must accept; one rejection ends the proposal (kept,
   with who rejected). The proposer may withdraw while it waits for its colleagues or the manager.
4. When all have accepted, the unit manager sees before and after, the re-run validation and
   the cost change, and approves or rejects, a reason required to reject, which everyone in it reads. He cannot edit a
   proposal; to change it he edits the roster directly. Approval is refused, with the reasons in full, when the month moved
   since in a way the swap can no longer hold (leave, a transfer, a hard rule it would now newly break).
5. Approval writes the cells as pinned cells of origin `swap` (`rosters.pins.pin_cell`) in a new roster version of origin
   `swap`, in force at once, telling the unit's nurses the roster changed. A proposal still waiting expires when any of its dates passes
   (every page reads the dates; the hourly job and the next write about it store it and tell its people) or a new version
   changes any of its cells, whatever made it (`rosters.versions.make_version`). A swap approved while a re-plan of its month
   runs makes the re-plan end `outdated`. Everyone involved is notified at each step: its colleagues when proposed, the
   proposer at each acceptance, the manager when all have accepted, and the proposer and every colleague at a rejection, a
   withdrawal, an expiry and an approval (the manager too for a withdrawal or an expiry of one awaiting him), never whoever took
   the step, and never why one expired.

### Covers

1. Leave that takes a shift off the roster in force, on a day today or later, opens a cover for it, unoffered and told to
   nobody; the manager opens one by hand for any shift-day of the roster in force, today or later. Two absences on one
   shift-day are two covers.
2. Its page judges, each time it is read, who could take it: the month's staff nurses off that day (in the month, within their
   dates, not on leave, allowed the shift, no accepted request holding the day) whose grid with the shift, as a pin, newly
   breaks no hard rule on the month as it stands, with the solver's own code; a headcount already broken counts only when
   broken further, as for a swap. Ranked furthest below owed hours first, then least overtime this year (`covers.judging`).
3. The manager ticks any of them and offers it, with a note: it becomes `offered` and each nurse ticked is told. An add on an
   offered cover asks only those not yet in it; a nurse who declined is in it and is not asked again. A nurse not in the list
   as judged then is refused by name.
4. A nurse offered it reads its date, shift, hours and note on Covers, never why it opened or who else was asked, and accepts or
   declines. A decline takes the cover's lock only and tells the manager; a cover everyone declined stays offered.
5. The first acceptance takes it, under the locks an approval takes (the catalogue's, hers, the unit's, the roster's, the
   cover's): its date read first, then its state, then judged again for her alone and refused in her own words. Her cell is a
   pin of origin `cover` in a new version of origin `cover`, "Cover taken by {name}: {shift} on {date}.", in force at once;
   the unit's nurses are told the roster changed, the others offered it that it is taken, the manager that she accepted. A
   later acceptance is refused as taken. An acceptance while a re-plan of the month runs makes the re-plan end `outdated`.
6. A waiting cover ends by the manager's withdrawal, by its date passing (every page reads the date; the hourly job and the
   next write about it store it), or filled when a new version, whatever made it, puts one more nurse on its shift-day, one
   cover per nurse added, oldest first; a cover's own version fills none. The nurses offered it are told it ended, never why.

### Month close and the carry-over chain (ADR 0004)

- The solve input for month M starts from the carry-over of the latest *closed* month,
  projected forward through each approved roster in between by the same computation the
  close uses (the solver package's carry-over of a month with every day recorded, worked out with no
  search in the worker's own process, ADR 0009). Normally that is one step: M−1's roster in
  force, projected.
- At the close time on the first day after a month (default 00:30 hospital time), the worker
  closes every unit that has an approved roster for it, whether or not a solve is running (ADR 0009): the roster in force plus every
  recorded leave and pin becomes fact, the solver validates and reports what the facts broke,
  and the carry-over is stored. A unit with no approved roster is skipped; the next month then
  starts from the last closed carry-over with no shift history.
- What becomes fact (`closes.making`): the solver's own loader with every day elapsed makes a pin that counts a fact, then
  leave and the days outside a nurse's dates, then the roster in force. The pins are `rosters.pins.month_pins` with the month's
  facts: a pin set aside for its day counts for nothing, one on a shift since dropped or no longer allowed was worked and
  counts. A shift the roster or a pin holds that the unit has since stopped working, or that was retired, counts as worked (the
  user's decision): the close lists it among the unit's shifts for its own input, with the hours it had. The solver reports
  what the facts broke (`elapsed_violations`); a close never refuses them. Requests of the month still pending expire. The
  schedule's close tells the unit's manager, with how many hard rules broke read when shown; the audit log says only which
  version closed and whether again.
- The unit manager may record late facts (leave, and corrections to a nurse's dates) and close again, on the Roster page,
  while the following month is not closed; the page says when the facts read now differ from the close's. Pins and hand edits
  of a month over stay closed. Once the month after has closed the month is fixed for good: its leave, and a start or end date
  that would change which of its days counted (with a first placement reaching back into it), are refused, naming it. A
  nurse's opening values lock at her first close, refused on their own fields. A close always takes the previous closed
  month's carry-over as its input, never a projection; months with no approved roster in between hand on what came in, with no
  shift history. A shift renamed since is mapped into histories (`renamed_shifts`).
- A draft solved before the month before it closed warns that the month before has closed since (`closed` among its changes),
  and is checked again on the month as it stands, as at submit. A re-plan is never made outdated by a close.
- The carry-over handed into January has overtime-to-date and both fairness balances reset
  to zero.
- Days before a nurse's start date and after her end date are credited like leave in every
  solve input: nothing owed, nothing worked, no debt. A transfer takes effect from a chosen
  month; the carry-over follows the nurse.

## 6. The solver service

A small FastAPI application in the solver container wrapping the vendored `nurse_roster`
package (ADR 0002). Every call carries the shared token. It runs one job at a time and
rejects a second with `409`; the worker guarantees the ordering, and `run_solve` is the only
caller of `POST /solve` (ADR 0009).

| Call | Purpose |
|---|---|
| `POST /solve` | Start a solve of one solve input; returns a job id. |
| `GET /jobs/{id}` | State, elapsed time, best cost so far, number of improving rosters, the best grid so far, the full result when finished. |
| `POST /jobs/{id}/cancel` | Sets the solver's stop event; the best roster found is kept. |
| `POST /validate` | Hard violations, cost, penalties and the per-rule explanation of a given grid against a solve input. No search. `web` also calls the same code (`solver_service.grid`) in its own process to explain a stored result and to check a draft as the manager edits it, since it is in the one image and needs no search: both answer when the solver is down or busy, and faster (measured on the 25-nurse ER sample: about 8 ms idle and 20 ms during a search, against 29 ms and 91 ms through the call). |
| `POST /precheck` | Plain-language reasons the month may be infeasible. No search. |
| `GET /health` | Liveness, package version, worker count. |

The worker count defaults to the container's CPU count. The time limit of a solve is chosen
by the unit manager up to the System Admin's cap. The reproducible mode is not exposed.

Preferences changed the solve input's contract (ADR 0013; the solver's problem schema 4, the solve input still version 1):
each nurse may carry `preferences_not_kept`, how many of her preferences (`undesired_days`, `desired_days`) the month
before did not keep, absent meaning 0 so every stored solve input and close input still loads. Above 0, each of her
preferences costs twice its weight, in the search and in the explanation, whose match says it "counts double". A result's
`carry_over` block carries the same field for next month, counted from the month's facts with leave days left out.
The app fills it in every solve input, a re-plan's and a close's included, from the carry-over chain (section 7), and fills
the two lists from her live preferences of the unit's windows. My month reads what was kept with the package's own reading of
"not kept" (`nurse_roster.validate.unkept_days`), on the version in force as the month stands or on the close in force's
facts, so the outcomes she reads add up to the count the next month is priced on, whatever the two weights; and it reads
whether hers count double from the same chain value the solve input takes (`rosters.own_month`).

Skills changed it again (ADR 0010; the solver's problem schema 5, the solve input version 2). Version 2 adds the nurse's
`skills` (skill name to its expiry, the last day it counts, or null; a skill expired before the month sent with its date,
absence meaning no record), the department's `skill_needs` and `skill_needs_hard`, and the general `required_skills` and
`weights.skill_shortfall`. The solver reads a version 1 input as version 2 with none of them (no skills, no needs, the needs
hard, no required skills, the weight 0), so every stored solve input and close input still loads, explains and closes; the
result's version is unchanged. Until the app writes version 2 (the skills tickets), it writes version 1 and nothing changes.

Full runs changed it once more (the solver's problem schema 6; the solve input's version unchanged). The department gains
`max_full_runs`, the most full runs a nurse may work in the month (a whole number 0 to 31; absent or null means no cap), and
the weights gain `excess_full_run`, the price of each full run beyond it (absent means 0); both are optional in either
version, so every stored solve input and close input still loads and gives what it gave. A full run is a run of exactly the
longest run (`max_consecutive_shifts`), leave ending a run as a day off does; it counts in the month that holds its last day,
one reaching the month's last day included (ticket 48: it cannot grow, as the next month reads it as history). The rule, `excess_full_run`, is priced only, never refused; its match
names the nurse, her count and the cap, and the per-nurse explanation carries it as it carries weekends above the most. Until
the app fills the two fields (ticket 48), nothing changes.

## 7. The worker and the queue (ADR 0006)

Procrastinate, with its tables in the application database, run by the `worker` container at
concurrency 4 (`manage.py queue worker --concurrency 4` in `deploy/compose.yaml`, `queue` being Procrastinate's command with
what it prints logged as JSON), so a scheduled job never waits behind a
running solve (ADR 0009). Every job takes a lock: solves share the hospital-wide one, and each
periodic job takes one under its own name, so a waiting job takes no slot, no kind of job holds more
than one, and no job runs beside its own previous run. A new job that can run longer than about a
minute takes a lock of its own. Jobs:

- `run_solve(solve_id)`: under a hospital-wide lock, so solves run first come first served
  across units; submits the solve input to the solver, polls progress into the `Solve` row,
  stores the result, relays a cancellation. A failed attempt (solver crash, unreachable) is
  retried once inside the same job, so it keeps its place in line; a second failure is marked
  failed with its reason, and the manager can re-run it. A worker that dies goes on watching the
  job the solver still holds when it comes back.
- `recover_lost_jobs` (every five minutes): puts a dead worker's job back on the queue, which would
  otherwise hold the lock for good, and fails a solve whose job is gone. A dead run of a periodic job whose next run already
  waits ends as failed instead, since it could not take its queueing lock back (a restore brings back the backup that was
  running as that backup was taken).
- `close_month` (hourly, minute 30): closes every unit's month whose close time has passed on the hospital's clock and
  is not closed, oldest month first across units, so a worker that was down catches up; and `project_carry_over` on demand,
  after every new roster version and every close, under its own lock, which stores the projected carry-over of an approved
  month and of the unit's approved months after it. Neither calls the solver
  service: the carry-over is worked out in the worker's process by `solver_service.grid`. The chain carries each field of the
  result's `carry_over` block (`closes.chain.CARRIED`), the count of preferences not kept among them (ticket 30): projected
  from the roster in force, corrected at the close and re-worked at a re-close, 0 through a month with no roster for her and
  out of her opening values (which have no field for it), not reset in January, and following her across a transfer. It
  remembers one month only, so a nurse's preferences count double in the month after one was not kept, and not after that
  unless another was not. A close stored before the count existed hands on 0. A solve of a later month
  that is queued or running goes on, and its draft is warned of as older than the close.
- `backup` (every five minutes): takes the nightly backup once the backup time has passed on the hospital's clock and none
  was taken since, so a worker that was down catches up, then removes those past the days kept, never the newest. Its own lock
  (`backup`) keeps a run of minutes to one slot.
- Retention, daily at a fixed UTC time, a day missed caught up by the next: `remove_ended_jobs` (queue rows and their events of
  jobs that ended well or were stopped more than seven days ago, and of failed jobs more than thirty days ago, so the health
  page counts the last month's failures),
  `remove_old_notifications` (older than a year, read or not), `clear_expired_sessions` (Django's `clearsessions`).
- `expire_swaps` (hourly, minute 15): expires each waiting swap one of whose dates has passed, telling its people. Every page reads
  the dates itself and every write about a swap does the same for it first, so a worker that is down delays only who is told.
- `expire_covers` (hourly, minute 20): stores each waiting cover whose date has passed as expired and tells the nurses offered
  it. Every page reads the date itself and every write about a cover does the same for it first.
- `open_and_close_request_windows` (hourly): opens each request window whose open date has come and closes each whose close
  date has passed, telling whoever that tells. Every write about a unit's windows does the same first, so a worker that is down
  delays only the notifications.
- `close_ended_nurses` (hourly): deactivates staff nurses whose last day is over. An end date of
  today or earlier deactivates at once. A manager's account stays the System Admin's.

The queue code is one module of ours (enqueue, progress, cancel, schedule) so the library can
be replaced without touching the API, the solver client or the solver.

## 8. The web application

### Backend

Django 6.1 (to 6.2 LTS in April 2027), Django Ninja for the JSON API with an OpenAPI
document, PostgreSQL 18, cookie sessions, CSRF. Django's admin site is not exposed. Apps, one
per domain area: accounts, hospital, units, nurses, rosters, requests (`requesting`, since `requests` is a well-known
library's import name), swaps, covers, solves, closes, notifications, audit, ops. A `solve input` assembler builds the solver JSON from the database
and stores it verbatim with every solve; a `result` reader stores and interprets results.

### Frontend (ADR 0008)

React 19 + TypeScript, Vite 8, shadcn/ui on Base UI with Tailwind 4, TanStack Query, TanStack
Router, TanStack Table (the roster grid and any table that needs sorting or filtering; short lists
stay plain tables) and Virtual (the roster grid), React Hook Form + Zod, Zustand, Recharts via shadcn, TanStack Pacer behind one debounce hook, orval-generated client. One responsive
web app, installable as a PWA; the grid scrolls horizontally on phones. The nurse's pages are made for a phone first (320 px
at the narrowest): below 640 px the header is the name, the bell and a Menu button, and on a touch screen every control is
44 px tall; the managers' and the System Admin's pages only keep within the width. The PWA is a web app manifest, icons and a
service worker that handles no request (`frontend/public/sw.js`, no `fetch` listener): nothing is kept offline, no push, so
the API, a roster's files and print sheets, backups and `/metrics` reach the network as they would without it. Every file
with a fixed name (the page, the worker, the manifest, the icons) answers `no-cache`, so a deploy is what loads next; only
the build's hashed assets are cached for good. They come from `frontend/public` at the site's root: WhiteNoise in `web`
sets the headers (`config.settings`) and Caddy passes them through unchanged; in development Vite serves the same files
with the same headers. The worker's scope is `/`. A tab opened before a deploy that asks for a page's code by its old name
loads again once (`lib/stale-build.ts`). In-app notifications
only: every role's header has a bell with the unread count, which polls and does not count as activity, and leads to the
Notifications page. Who is told of what is in one place, `notifications.sending`, called inside the transaction of the
change. A notification links to the reader's own page for it, by what they hold when they read it. Visual design is decided later; the architecture does not depend on it.

Screens per role, in outline: System Admin (accounts, technical settings, audit log, solve
history, health and backups); CNO (hospital rules and weights, shift catalogue, leave types, skills,
holidays and Ramadan, units and managers, nurses with import and export and their skills, each unit's rules, rostering attributes and leave
to read, roster overview, the Day view and approvals); Deputy CNO (roster overview, the Day view, approvals, hospital rules and each unit's rules,
rostering attributes with nurses' skills, and leave, to read); Unit Manager (unit rules, rostering attributes, nurses, request
windows, requests and the unit's preferences (read-only), swaps, covers, leave, the roster grid with solve, progress, results and
explanations, submit, versions, exports, month close; with a nurse profile, also their own roster and month, as a Staff
Nurse reads them, but no requests, swaps or covers of their own); Staff Nurse (unit roster, own month: hours, overtime, what
is carried, shift counts, her skills with their expiries and leave with its type, requests, a Preferences card beside them ("4 of 5 kept" once the roster
is approved, "No roster yet" before, each one Kept, Not kept or On leave, and when hers count double this month, the month
that caused it), swaps, covers offered to them,
notifications, password). A nurse's own hours are
worked out from the version in force on the month as it stands, with the solver's own arithmetic, for this month and later;
a month already over shows its leave only. Every role has the bell and Change password. The Deputy CNO, Unit Manager and Staff Nurse also read
the shift catalogue, leave types, skills, holidays and Ramadan; the System Admin may open those pages
but has no link to them, because nothing in that role's work calls for it. A session that ends behind the user's back (the
idle limit, a deactivation, a password changed elsewhere: any 401 while the app believes someone is signed in) goes straight
to the login page from any page, without the roster page's unsaved-changes question, since staying could save nothing. The
login page says "You were signed out. Changes you had not saved are lost. Sign in to carry on.", only then, and signing in
again goes back to the page the user was on (an address in the app, carried in the login page's address), which sends a role
that may no longer open it home. Nothing of unsaved edits is kept in the browser.

What a solve shows afterwards: every piece of information the result holds: precheck
warnings, penalties per rule, per-nurse cost and hours accounting, the explanation of the
largest violations per rule, solver statistics, recorded facts that broke rules, and in a
re-plan the comparison with the roster in force. A nurse's carry-over waits for the month close.
A stored result holds the penalties' totals only, so the explanation is worked out when asked.
The solver's words count days from 0, so what the pages show says dates instead.

The System Admin's solve history is unit, month, state, the failure kind (in fixed words naming no one), who asked, when, how
long, the time limit, the attempts and the cost, and only that (not even whether a solve was a re-plan, whose date is about a
roster): the solver's and the worker's words
(`error`, `message`, `precheck`, the explanations) can name a nurse and a date, and no free text
reaches it. The cost was already theirs to read in the audit log.

### Security

Local accounts only, designed so an LDAP or SSO backend can be added as a Django
authentication backend. Generated passwords shown once, forced change at first login.
Minimum length 10 with Django's common-password and similarity checks, lockout for 15
minutes after 5 failed logins, sessions expire after 12 hours of inactivity (polling a solve's
progress is not activity), no two-factor authentication in v1. Every login, failed login and every change to settings, accounts,
rosters, requests, swaps and covers goes to the audit log. So does each taking of the staff list, which holds everyone's gender:
who took it and how many nurses it held, and nothing from the file. Its import template holds no one's data and is not
logged. So does each taking of a roster version's CSV or Excel file (`roster.exported`): who took which unit's month, which
version and which format, and nothing from the file. A roster's print page makes no file and shows only what its reader can
already read, so it is not logged. Nurses see colleagues' names and shifts only. The System Admin reads the log and may see no rostering attribute, so an attribute's change is logged as whose
changed and by whom, without its value or even which one, since a change to a two-way flag gives its value away. Unit
rules are logged with their values, as hospital rules are: they say nothing about a person. Attributes also stay off
the staff list, a file that leaves the system. Leave is logged the same way, as whose changed and by whom: not its type, its
dates or how many, since a long run gives the type away and a date is part of a roster. So is a request: whose it is, who moved it and how (made, withdrawn,
accepted, rejected, edited, cancelled), never its date, its shift or either reason, which can be about someone's health. A
request that leave replaced, and a version a request made, have no entry of their own, since one beside the leave's or the
request's would date it. So is a preference: `preference.made`, `withdrawn` and `asked_instead`, the nurse acting and her
hospital ID as target, never its date or kind; no notification is sent for one. So is a swap: whose it is (the proposer's) and who moved it how (`swap.proposed`, `accepted`, `rejected`,
`withdrawn`, `approved`), never its cells, dates, note or reasons; an approval also writes `roster.changed`. An expiry has no
entry: it is nobody's act, and one beside the version that caused it could date a colleague's leave. A cover is logged as who moved it how:
`cover.offered` and `cover.withdrawn` (the manager, the unit as target) and `cover.accepted` and `cover.declined` (the nurse, her
hospital ID as target), never its date, shift or note; an acceptance also writes `roster.changed`. Its opening, by leave or by
hand, its filling and its expiry have no entry, since one beside the leave's would date it.

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

### Roster files and the print page

Any version of an approved roster, not only the one in force, downloads as CSV and as an Excel workbook and opens as a print
page, all one table (`rosters.sheets`): a row a nurse by name, a column a date, then the hours of its shifts and a count of each shift.
The unit's manager takes them for their unit, the CNO and the Deputy CNO for any unit while its month is submitted or approved;
a draft is not a version and has none. A nurse takes no file, and prints only their own unit's roster in force, from My
roster. A file and a printout leave the system, so a cell is the version's shift or nothing: a day of leave reads as a day off
in every one, as it does to a colleague, and no leave's type is ever in one; only a nurse's own row on their own print page may
say leave. Hours are therefore those of the shifts on the row, at the hours the version's solve was given, and never what a
month owes or the overtime, which would say how much leave someone had. Cells and codes are under today's codes. The CSV is the
staff list's (byte order mark, every cell quoted, an apostrophe before a cell that opens like a formula); the workbook writes
text as text, numbers as numbers and dates as dates, marks text that opens like a formula as text the way Excel does, and is
built in memory with XlsxWriter. Both answer `no-store`. The print page is laid out for A4 landscape, a 31-day month across one
page and the header row repeated on each.

### Observability

JSON logs on stdout for `web`, `worker` and `solver` (Caddy logs JSON of its own, PostgreSQL its own format): one formatter (`solver_service.logs`) for Django's `LOGGING`, gunicorn's own and
access lines (`config/gunicorn.py`) and the solver's uvicorn (`solver_service/logging.json`); Docker rotates them at 10 MB,
five files. The worker's can name a nurse and a date, so the install guide treats them as personal data. A Prometheus `/metrics`
endpoint on `web`, with no sign-in, reachable on the internal network only: Caddy refuses the path and `web` refuses anything
Caddy passed on (`X-Forwarded-For`); its gauges are worked out at each scrape from what the health page reads, plus how many
solves there are in each state. The health page
shows solver reachability and version, disk and database size, the backups with the last one's time, and queue state; the
public `/api/health` says only whether the database and the solver answer. Nothing else is bundled.

## 9. Defaults

- Hospital and unit rules are seeded from the reviewed default set the solver was shaped on
  (12-hour day and night shifts, Friday weekend, the standard forbidden successions, overtime
  caps, the weights) and flagged "defaults, review before the first solve". A unit's defaults
  follow the catalogue as it stands when the unit is created: a default shift the CNO renamed
  appears under its new code, and one the CNO retired is left out, which the solver refuses until
  the unit manager has chosen the unit's shifts.
- Time limit cap 300 s; unit default time limit 60 s; a new unit's request cap 3 and preference cap 10 per nurse per month;
  backup 02:00 kept 30 days; close 00:30 on the first. All editable by the role that owns them. The time
  zone, `Asia/Riyadh` by default, is the environment's `TIME_ZONE`, set at install rather than on a page.
- A unit manager may roster any future month, not only the next.
- Nothing is hard-deleted: units are archived when they have no nurses, nurses are
  deactivated, requests and swaps keep their final state, leave corrected or removed stays as
  an ended row, every roster version and solve is kept. The exceptions are a public holiday and a month's fixed Ramadan dates, which have no
  history of their own: what a solve used is stored with it and the audit log keeps the rest. Housekeeping removes only what is
  no one's record (section 7): a notification after a year, an expired session, and the queue's rows of jobs that ended;
  backups go after the days the System Admin keeps them.

## 10. Repository, build and tests

```
cp-sat-nurse-roster-app/
  backend/      Django project and apps, pytest-django suite
  solver/       vendored nurse_roster package and its tests, the FastAPI service
  frontend/     Vite + React SPA, Vitest suite
  deploy/       compose.yaml, compose.dev.yaml, Caddyfile, .env.example, INSTALL.md,
                reset-admin-password.sh, restore.sh, tests/operations.sh (the compose-level test)
  docs/         this document, adr/, research/
  e2e/          Playwright suite against stacks of its own (stack.sh builds, seeds, resets and removes them; ci.sh is CI)
  .github/      workflows/browser-checks.yml, which runs e2e/ci.sh
  Dockerfile    one multi-stage build, one image
  GLOSSARY.md
```

Development runs from `compose.dev.yaml` with hot reload for Django and Vite.

The browser checks (`e2e/`, ticket 24) run against stacks of their own built from the checkout: a seeded one for every role's
pages and the operations, and an empty one for the journey from the System Admin's first login, emptied again before each run.
A stack's hospital date can be moved for them (`e2e/stack.sh clock`): `nurses.membership.today` adds the days in the file
`E2E_CLOCK_FILE` names, a variable only `e2e/compose.e2e.yaml` passes, which `deploy/compose.yaml` gives no service and which
has no URL. The hourly jobs are then run at once by the stack's own worker (`e2e/stack.sh fire`).

CI is GitHub Actions on the private repository, on every pull request and on `main` (since 2026-11-08; ticket 26 was the last
verified on a local copy): `.github/workflows/ci.yml` runs the solver's, the backend's (on a PostgreSQL 18 service, with
`makemigrations --check`) and the frontend's suites, the frontend's six times at once, checks that the orval client and
`openapi.json` match the backend's export so an incompatible API change fails the build, and builds the image;
`.github/workflows/browser-checks.yml` runs `e2e/ci.sh`: the image, both stacks, every Playwright project and
`deploy/tests/operations.sh`. A ticket branch is checked through its pull request; `main` is fast-forwarded to it and pushed
(`docs/guides/local-development.md`). Planned: on a version tag, build the image and push it to a private GitHub Container
Registry; each hospital's VPS logs in once with a read-only token and pins the version in `.env`.

## 11. Pinned versions (2026-11-04)

Python 3.14, OR-Tools 9.15, Django 6.1, Django Ninja 1.7, Procrastinate 3.10, PostgreSQL 18,
Caddy 2.11, uv 0.13, Node 26 LTS (build only), Vite 8, Vitest 5, React 19.3, Tailwind 4.3,
TypeScript 6 (7 once the toolchain supports it), TanStack Query 5, Router 1, Table 9,
Virtual 3, Pacer 0.24, React Hook Form 7, Zustand 5, Recharts 3, orval 8, Playwright 1.64.

## 12. Revisit later

The amount of solve information shown (now: everything), TanStack Charts and TanStack Form 2
once mature, Arabic and RTL, LDAP/SSO, email, push notifications, PDF
generation, the Deputy CNO's further responsibilities, the unit manager's further permissions.
