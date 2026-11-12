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
LDAP or SSO, email or SMS, server-side PDF, native mobile apps, the solver's
reproducible mode in the UI. Soft preferences, once out of scope, are in since ticket 29 (ADR 0013), and so is Web Push, for
the six notifications with a deadline and nothing else, since tickets 40 to 42 (ADR 0012).

## 2. Deployment

### Services

One application image per release. `docker compose` starts five services:

| Service  | Image            | Command             | Network                | Ports            |
|----------|------------------|---------------------|------------------------|------------------|
| `caddy`  | `caddy:2.11`     | stock               | public, frontend       | 80, 443 published |
| `web`    | application      | API + SPA server    | frontend, backend, solver | none published |
| `worker` | application      | Procrastinate worker| backend, solver, egress | none            |
| `solver` | application      | solver HTTP service | solver                 | none             |
| `db`     | `postgres:18`    | stock               | backend                | none             |

The `solver` network is reachable by `web` and `worker` only. The solver container holds no
database credential and no secret other than the shared solver token. See ADR 0001.

`egress` is the only network of an application service that is not internal: the worker's alone, its way out, which it uses
for the browsers' push services and nothing else (ADR 0012). The network itself is open; what keeps the worker to those hosts
is `notifications.subscriptions`'s list, checked at turn-on and before each send, and the hospital's firewall, for which
`deploy/INSTALL.md` names them. `web`, `db` and the solver are on internal networks only and reach nothing outside; only
Caddy is on `public`. A hospital that lets nothing out loses pushes and nothing else.

What Caddy limits (`deploy/Caddyfile`, stock handlers only, ADR 0015): a request body over 2 MB (2,000,000 bytes) is refused
with 413, from its `Content-Length` before any of it is read, which is above the nurse import's 1 MiB file and its multipart.
Caddy reads a body whole before it opens the request to `web`, so a web worker never waits on a client. A body that stalls for
a minute, or averages under 10 kB/s from its start (each byte adding a tenth of a millisecond to the minute), is dropped by
Caddy. Nothing bounds a whole request's time: once its body is in, a long nurse import's confirmation or a backup's download
runs to its end. The other timeouts are Caddy's defaults (headers 1 minute, idle connections 5 minutes, a stalled write 1
minute), with no write timeout. Caddy has no rate limit (ADR 0015); the limit on failed logins is the application's.

`web`'s command (`deploy/compose.yaml`, ticket 71): `prepare`, then gunicorn with `--worker-class gthread --workers 3
--threads 4 --keep-alive 10` and `--timeout` at gunicorn's default. Each of the twelve threads serves one request at a time, so
a login's hash or a long nurse import's confirmation holds one thread, not a third of the pool. Under `gthread` the timeout is
only how long a worker's main loop may go silent: no request is killed for its length. A connection from Caddy stays open 10 s
after an answer, and Caddy closes an idle one to `web` after 2 s (`keepalive` in the Caddyfile's `reverse_proxy`), so it
never sends a request down one gunicorn has just closed. Database connections: each thread opens at most one and closes it
at the request's end (no `CONN_MAX_AGE`), so `web` holds at most 12, beside the worker's 9 (ADR 0009), against PostgreSQL's
100. The application keeps no mutable state in a module that a request changes; the public health answer held five seconds is
shared by a process's threads under a lock (`ops.public_health`).

Volumes: `pgdata` (PostgreSQL), `backups` (the nightly backups, mounted by `worker` and, read-only, by `web`, and by no other
service), `caddy_data` (certificates).

### Configuration (`.env`)

`DOMAIN` (optional; with it Caddy obtains Let's Encrypt certificates, without it Caddy serves a
self-signed certificate via `tls internal`), `SECRET_KEY`, `POSTGRES_PASSWORD`,
`SOLVER_TOKEN`, `TIME_ZONE` (default `Asia/Riyadh`), `INITIAL_ADMIN_PASSWORD` (read once),
`APP_VERSION` (the image tag the hospital pins), `TRUSTED_PROXIES` (optional, empty by default; the hospital's
own proxies in front of Caddy, given to Caddy alone, section 8).

### First start, upgrades, recovery

- First start: `web` runs migrations, seeds the default hospital and unit rule sets (section
  9), and creates the System Admin account from `INITIAL_ADMIN_PASSWORD` with a forced
  password change at first login (`manage.py prepare`, which logs both). The variable is ignored afterwards. It also makes
  the installation's push key pair, once, and logs that it did: the pair names the installation to the push services, every
  push subscription is bound to its public key, and it lives in the database so that a backup brings it back with them
  (ADR 0012). There is no variable for it and no step of the hospital's.
- Upgrade: `docker compose pull && docker compose up -d`; migrations run at `web` start.
- `deploy/reset-admin-password.sh`: resets the System Admin password from the VPS, printed once with a forced change, ends
  the account's sessions and lifts a lock from wrong passwords; audited with no actor, "from the server".
- `manage.py rotate_push_keys`: replaces the push key pair after a compromise, audited the same way (`push.keys_rotated`). It
  deletes no push subscription: sends to a device still bound to the old key are refused until it opens the app again, when
  it subscribes with the new key without being asked. Each refusal counts toward the ten that end a subscription, so a
  device not opened in that time is turned off and its user turns it on again. There is no scheduled rotation.
- `deploy/restore.sh <backup name or file>`: stops `web` and `worker`, backs up the database as it stands, restores into a new
  database and empties its login attempts and the throttle's addresses there, so no lockout or throttle comes back, and only then
  puts it in the old one's place (the old renamed aside, the new renamed in, the old dropped last). Before it drops the old
  one it prints from it, by time and not id, each deactivation, password reset, password change and push key rotation
  recorded after the restored database's newest audit entry (action, user, time on the hospital's clock), to be done again
  by hand; it re-applies none, and a failure to print does not stop it. Then it starts them again (`web` migrates an older
  backup forward).
  Restore is deliberately a script, not a button.
- Nightly backup (02:00 hospital time, kept 30 days, both the System Admin's to change) is a worker job; backups are listed
  and downloadable on the System Admin's health page, each download audited. The files are the record (`ops.backups`): a
  `pg_dump` in its custom format named by its UTC time, readable by the app user only, the newest always kept. The sessions'
  table goes in empty, since a session's key is a working login: a restore signs everyone out. Off-site copies
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
| Put a staff nurse on probation, on adding her or later as a correction, and take her off it (ticket 54) | | yes | | | |
| A nurse's probation: its length, Extend, End (ticket 54) | | | | own unit | |
| Read who is on probation and until when | | yes | yes | own unit | |
| Read nurses | | yes | | own unit | |
| Record, renew and take off a nurse's skills (a manager with a nurse profile's too) | | yes | yes (from ticket 61) | | |
| Read a nurse's skills, certificates and licences with their kinds and expiries | | yes | yes | own unit | |
| Read a record's identifier and issue date, with the issuing body (ticket 59) | | yes | yes | | |
| Read the expiries: skills expired or expiring within 90 days, and skills required to work with no record, each with its kind and no identifier | | yes | yes | own unit | |
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
| Read own skills, certificates and licences with their expiries, identifiers and issue dates (a manager with a nurse profile too) | | | | yes | yes |

Cardinalities: exactly one active CNO and one active Deputy CNO per hospital (a deactivated one
stays on record, so a successor gets a new account); one Unit Manager per unit and one unit per
manager (a manager account with no unit assigned can log in but do nothing). A unit is created
with or without its manager and waits with none until the CNO assigns one. Deactivating a manager
takes them off their unit at once, because ending an account cannot wait for the CNO, and
reactivating does not give it back; the CNO's home names every unit with no manager. A unit
manager sees nothing of other units. The System Admin sees no roster and no rostering attribute; of a probation, only what
the audit log's entries carry, with their values, as the user decided on 2026-11-11 (ticket 54).
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

**Hospital settings** (one row): the hospital rules (every field of the solver's `general` block including the weights, but
`shift_hours` and `required_skills`, which a solve input takes from the shift catalogue and the skill catalogue) with a review
flag. Among the weights is the skill shortfall (ticket 34), the price per nurse a soft skill need is short on a shift-day,
default 0, which switches the price off until the CNO sets one. Nothing else: no page or rule reads a hospital name, so none is kept; the time zone is `TIME_ZONE` from
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

**Skill** (catalogue): name (unique in any case of letters), kind (a skill, a certificate or a licence), issuing body (free
text, at most 100 characters, may be empty), expires, required to work, lets a nurse precept, active flag. A licence always
expires: a licence with `expires` off is refused, and a check constraint holds it in the database. Changing an entry to a
licence is refused beside its kind, naming the nurses, while a current record of it has no expiry; changing away from
licence is free. Every other rule here treats every kind alike, the skill needs included; the Skills page lists the entries
under Skills, Certificates and Licences. The CNO keeps it and every role reads it, the System Admin included, since it names
no one. Never deleted, only retired: nurses' records of it and past rosters keep it. The name may be renamed: each rename is
recorded (old name, new name, by whom and when), and no other skill may take a name a skill used to hold, as for a shift's
code, so that an old name in a stored solve input still means one skill. A change goes to the audit log with its values
(`skill.created`, `skill.changed`). Turning `expires` on is refused, naming the nurses, while a current record of the skill
has no expiry; turning it off is allowed, and the expiries recorded stay, counting for nothing until it is on again.
Retiring it is refused, naming the units, while a live unit's skill need names it; a new name is carried through every
unit's skill needs in the same transaction, archived units too, each changed unit audited as `unit_rules.changed` (ticket
34). The live skills marked required to work are a solve input's `required_skills`; a retired one bars nobody. A nurse
holding a skill marked as letting a nurse precept, unexpired on the day of assigning, may be assigned as a preceptor (ticket
55); the mark is read then only, so clearing it while a nurse precepts by that skill is allowed and takes no preceptor away
(ticket 53).

**Public holiday**: date, name. **Ramadan days**: per month, the CNO's fixed dates or range,
else derived from the Umm al-Qura calendar. A write that moves a month's days, Ramadan's or a holiday's (the per-month fix, "Use
the calendar", a Ramadan confirmed, a holiday created, moved or removed), tells the manager of every unit with a roster in that
month, draft, submitted or approved, once a month and never the CNO who made it (`month_dates_changed`, ticket 46); one that
leaves the days as they were (fixing a month to the calendar's own days, a holiday renamed) tells nobody. Nothing else moves:
approved cells, versions and pins stay, and the next solve or re-plan reads the days as they stand.

**Unit**: name (unique among units not archived), archived flag, manager (a user; none once
archived), the unit rules (every field of the solver's `department` block but its name, which is
the unit's) with a review flag, request cap per nurse per month (default 3), preference cap per nurse per month (default 10,
0 switching preferences off), default time limit. Among the unit rules are the skill needs (ticket 34): each a shift the unit
works, a skill, a weekday minimum and a weekend minimum (0 to 1000), at most one a shift and skill, at most 100; and one flag
making them all hard or soft, hard by default, as night rest's does. A need naming a retired skill or a shift outside the unit's
is refused, and so is taking out a shift a need names, naming the need, as a pin's shift is: the manager takes the need out
first. The CNO and the Deputy CNO read them as the other rules; a change is audited with its values, since a need names no
one.

**User**: username, full name, role, active flag, must-change-password flag.

**Nurse profile** (0..1 per user): hospital ID (= username), gender, start date, end date,
team leader, score, Ramadan-reduced, breastfeeding, opening values (overtime this year, hours balance,
night and weekend fairness balances, and the overtime balance, her overtime above (+) or below (−) her overtime share so far
this year, in hours within the solver's ±1 000 000, ticket 50; editable until her first month closes), whether a manager has ever saved
these, which is how a score at the default is told from one somebody looked at. Her skills are rows of their own (below).

**Nurse skill**: nurse, skill, expiry (null for a kind that does not expire), identifier (the number or code the issuing body
gave it: free text, at most 100 characters, trimmed, may be empty), issue date (may be empty), recorded by and when; removed by
and when (ticket 59 added the identifier and the issue date). The identifier is required when the skill is a licence, and is
unique among one skill's current records, compared exactly: a record or renewal repeating another nurse's is refused naming
her, beside a partial unique constraint (`nurses_one_current_identifier_a_skill`), while an ended record and another skill may
hold the same one. The issue date is neither after the expiry nor after today on the hospital's clock, and nothing reads it:
the expiry is what a roster reads. A renewal takes a new expiry and may take a new identifier and issue date; what it does not
name is carried from the row it ends. The CNO, the Deputy CNO and the nurse herself read the identifier, the issue date and
the issuing body; a unit manager's reads and the expiries carry kind, name and expiry only. At
most one current row a nurse and skill; a renewal or removal ends the row rather than rewriting it, as leave's does, because
the audit log says only whose skills changed and by whom (`nurse.skills_changed`), never which skill or date, since a lapse
says something about a person. The CNO records, renews and takes them off on the nurse's row of the Nurses page, a manager
with a nurse profile's too, and so does the Deputy CNO, on her row of Rostering attributes (ticket 61); her unit's manager (and the manager of a unit she is due to join) reads them on the Nurses page
and Rostering attributes, the Deputy CNO on Rostering attributes for any unit, and she reads her own on My month. The System
Admin reads none. On the profile, not a placement, so they follow her across a transfer and stay when she is deactivated or
ends. A retired skill can be neither recorded nor renewed, and a record of it stays until the CNO takes it off. The
expiries (ticket 37, `nurses.expiries`) are worked out when read, on the hospital's clock: each skill of a nurse with an active
account and an end date not passed whose expiry has passed or falls within 90 days, and each skill required to work she has no
record of, read as a solve input reads them (a retired skill is no record, a kind that does not expire has no expiry). The CNO
and the Deputy CNO read every unit's on the Expiries page, a unit manager his unit's and those due to join it on his Nurses
page, and the CNO's home shows how many there are. Nothing is sent about an expiry: the page is the reminder. Every write
takes the hospital settings' lock before the nurse's, as a catalogue change and a transfer do. The skills CSV records and
renews them in bulk (section 8, "Nurse import and the staff list").

**Probation** (ticket 54; ADR 0014), on the nurse profile, so a transfer carries it: whether she is on one (`on_probation`, the
CNO's tick, a staff nurse's only), its length in months (`probation_months`, her unit manager's: 1, 2 or 3, standing at 3 until he
chooses, then extended a month at a time to 6) and an early end (`probation_ended_in`, a month). Its last day is derived, never
entered (`nurses.probation`): whole calendar months from her start date, the month she joins counting only when she joins on the
1st, so a start on 15 December with 3 months ends on 31 March, and a corrected start date moves it; an early end makes it the last
day of that month. End sets it to the month under way on the hospital's clock, and is refused before the month she starts in; an
ended probation cannot be extended or its length changed; Length is refused once extended, and for a length that would have ended
it before the month under way. The CNO's untick removes it from the first month whose roster, in the unit that month falls under,
is not approved, keeping the months before as an early end would; a later tick is refused once six months from her start date,
counted the same way, have passed, and while her allowed shifts are her unit's night shift alone, and it starts again at 3
months. While it is not over, her allowed shifts cannot be set to the night shift alone. It ends by itself on its last day, with no
job; the hourly job tells her unit's manager once in her last month, from its first hour ("Layan Alharbi's probation ends on 31
March. Extend it or let it end."), and again in a new last month after an extension (`probation_notified_for`), and never of one
ended early. The CNO, the Deputy CNO and her unit's manager read it, on the Nurses list, Rostering attributes and the staff list;
the System Admin reads none of it but the audit log, whose entries (`nurse.probation_ticked`, `nurse.probation_unticked`,
`nurse.probation_length_set`, `nurse.probation_extended`, `nurse.probation_ended`) carry its values before and after, unlike
every other rostering attribute: the user's decision of 2026-11-11. Tickets 55 and 56 bring it into a solve and onto the roster.

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

**Submission**: one sending of a draft for a decision: who submitted it and when, what the draft was warned of then (the
month's nurses, and since ticket 46 its Ramadan days and public holidays, null on a submission from before, which compares
none), and the decision, by whom, when and, for a rejection, the comment the manager reads. Nothing is deleted, so every comment is
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
ends the pin and tells the manager, and pinning on a day of leave is refused. A day an expired required skill bars a nurse from
(`solves.input.barred_from`, as the solver's `barred_days`) is treated as leave for a shift, ticket 38: pinning a shift there is
refused, naming the skill ("Amal's BLS, required to work, counted until 20 June 2026, so Amal can work no shift on 25 June
2026."), and a day off may still be pinned. A pin that falls out of step with the rest (the nurse no longer in the unit's month,
a day outside their dates or on leave, a shift the unit no longer works or the nurse may not work, a shift on a barred day) is
set aside, not removed: it reaches no solve and the draft says why, and it counts again if that changes, as when the skill is
renewed or its record taken off. A barred pin is set aside before a re-plan's date too, so the roster in force holds that day
as for any pin set aside, and a month's close, which reads its pins as facts, counts a shift pinned on a barred day as worked
and reports the rule it broke. A shift's
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
solve of a unit is active at a time, whatever its month (ticket 62): a start while one of another month is queued or running is
refused naming that month, so one unit cannot hold every other unit's solve behind a month for each month ahead. The database
holds one a unit's month; the start routes hold the unit's row while they check the rest. A re-plan is a solve with the date it plans from, the version it started from, the
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
nothing stale, and nothing about a nurse, a leave or a rejection's comment is kept or said, but for a probation ending, which
names the nurse to her unit's manager by her profile's identifier, with her last month as its month. **Audit entry**: actor, action, target,
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
  leaves the draft as it was; the solve history keeps every result, any two of a month's results holding a roster compare
  side by side for the manager alone, with what differed between their inputs named, and any result
  with a roster can be restored as the draft, unless a solve of that month is queued or running, the month is over, or a shift
  it uses has since been retired or had its hours changed, since its cost and hours would no longer hold (it can still be
  opened, and a rename is carried). The stale-draft warning then compares with the restored solve's input. The draft grid is
  editable by hand: each edit is a pin, the grid it would make is checked as the manager edits, and edits are saved
  together. Every solve and every restore puts the pins that count on top of its roster, so a draft never disagrees with a
  pin; a pin saved since the input was stored, and a pin so put on top, warns like other changes since. So do the month's
  Ramadan days and public holidays when they differ from the input's, as changes of the month's with no nurse (ticket 46);
  they block nothing, and do not make a re-plan outdated. Saving while a solve
  of the month is queued or running is allowed and warned of. The solve's own cost holds only for the month it was given, so
  a draft edited or out of date is costed and checked again on the month as it stands. Submitting freezes the draft until
  the decision.
- Submitting checks the grid again on the month as it stands with the solver's own code, always: a draft out of date or
  edited by hand goes with its warning, and is refused only if it breaks a hard rule or cannot be checked. It is refused while
  a solve of the month is queued or running. The CNO or the Deputy CNO approves it, checked again the same way since leave
  may have been recorded while it waited, or rejects it with a comment. A month that is over can no longer be approved, as it
  can no longer be submitted (ticket 62): approved after the month after it had closed, it would be an approved month no close
  could reach, and every later close of the unit would wait on it for good. Rejecting it stays allowed, and the month, with no
  approved roster, is skipped by the close. Approving takes the catalogue's lock, then the
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
  a unit whatever the month, with the same progress, stop and retry. Its input holds the roster in force as `published` and the date as
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
  being the one each month falls under for them (none for a month that begins after their end date, a manager's included,
  whose account outlives the profile): names and shifts only, a colleague's leave the same empty cell as a day off,
  and their own leave as leave.

### Requests

1. The unit manager opens a request window for a target month (open and close dates; may
   close early). Its nurses of that month, one due to join included, are told when it opens, and
   again if it closes early.
2. Nurses make requests (day off, or a specific shift on a date), up to the unit's cap, and
   may withdraw a pending one while the window is open. A request that could never be accepted (a
   day on their leave or outside their dates, a shift the unit does not work or they may not, a shift on a day an expired
   required skill bars them from) is refused as it is made, in their own words: their own skill is theirs to read, so a barred
   day names it ("Your BLS, required to work, counted until 15 June 2026, so you can work no shift on 20 June 2026. You can
   still ask for the day off."). A day off there is a request like any other (ticket 38). One accepted before the skill
   expired is set aside with its pin, and the manager's acceptance of one after it is refused, naming the skill.
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
   colleague's facts (leave, dates, unit, allowed shifts, hours, an accepted request, another swap, a required skill expired)
   reads "This swap cannot work for Badr on 5 June", and is checked only after what My roster shows, so leave asked for as a day
   off reads "already a day off" like any day off; a shift-day left without a team leader or both genders, or short of a skill
   need, reads only that that day's shifts would break the unit's rules, and the proposer reads no rule, solver text or cost
   about anyone else. Her own reasons are said in full, her own expired skill among them (ticket 38), and so is
   anything My roster shows (a cell's shift, a date passed, a headcount). The manager reads every reason in full
   (`swaps.judging`).
3. Every colleague whose cells change must accept; one rejection ends the proposal (kept,
   with who rejected). The proposer may withdraw while it waits for its colleagues or the manager. A withdrawal frees its
   cells, so a nurse who has withdrawn five of hers on one roster in the last day (`swaps.steps.WITHDRAWALS_A_DAY`) proposes no
   more on it until the first of those is a day old, refused with the time she may again: her rounds cannot tell a colleague
   or the manager without end.
4. When all have accepted, the unit manager sees before and after, the re-run validation and
   the cost change, and approves or rejects, a reason required to reject, which everyone in it reads. He cannot edit a
   proposal; to change it he edits the roster directly. Approval is refused, with the reasons in full, when the month moved
   since in a way the swap can no longer hold (leave, a transfer, a required skill expired or a skill need changed, a hard rule
   it would now newly break).
5. Approval writes the cells as pinned cells of origin `swap` (`rosters.pins.pin_cell`) in a new roster version of origin
   `swap`, in force at once, telling the unit's nurses the roster changed. A proposal still waiting expires when any of its dates passes
   (every page reads the dates; the hourly job and the next write about it store it and tell its people) or a new version
   changes any of its cells, whatever made it (`rosters.versions.make_version`). A swap approved while a re-plan of its month
   runs makes the re-plan end `outdated`. Everyone involved is notified at each step: its colleagues when proposed, the
   proposer at each acceptance, the manager when all have accepted, and the proposer and every colleague at a rejection, a
   withdrawal, an expiry and an approval (the manager too for a withdrawal or an expiry of one awaiting him), never whoever took
   the step, and never why one expired. A withdrawal is told in place of a person's notice of the swap still unread, that it was
   proposed or awaits him, so a round leaves each one notice of it; one already read stays, and the withdrawal is a new one.

### Covers

1. Leave that takes a shift off the roster in force, on a day today or later, opens a cover for it, unoffered and told to
   nobody; the manager opens one by hand for any shift-day of the roster in force, today or later. Two absences on one
   shift-day are two covers.
2. Its page judges, each time it is read, who could take it: the month's staff nurses off that day (in the month, within their
   dates, not on leave or barred by an expired required skill, allowed the shift, no accepted request holding the day) whose grid with the shift, as a pin, newly
   breaks no hard rule on the month as it stands, with the solver's own code; a headcount already broken counts only when
   broken further, as for a swap. Ranked furthest below owed hours first, then least overtime this year (`covers.judging`).
3. The manager ticks any of them and offers it, with a note: it becomes `offered` and each nurse ticked is told. An add on an
   offered cover asks only those not yet in it; a nurse who declined is in it and is not asked again. A nurse not in the list
   as judged then is refused by name, if she is on the cover's roster; any other ID is said back as sent, the same for a nurse
   of another unit as for no such nurse.
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
- A draft solved before a nurse's skills changed as the month sees them (a skill recorded, renewed, taken off, retired or expired
  into the month) warns `skills` for her, and one solved before the unit's skill needs or their flag, the skills required to work or
  the skill shortfall's price changed warns `skills` as a change of the unit's (ticket 35); a rename is no change. A stored input
  of version 1 had no skills, so a nurse who has some since is a change. A submission keeps each nurse's skills, so a skill change
  while it waits is news to the approver, and a re-plan whose month's skills changed while it ran ends `outdated`. Submit and
  approval refuse a grid that breaks a hard skill need or fills a barred day on the month as it stands, as any hard rule; the
  close reports a barred day worked or a need left short among what the facts broke and never refuses. Nothing rewrites an
  approved roster when an expiry passes or a skill is corrected (ticket 38): the Roster page's check of the month as it stands
  names the rule it now breaks, as for any rule, and the manager edits or re-plans.
- The carry-over handed into January has overtime-to-date and the three fairness balances (nights, weekend days and the
  overtime balance) reset to zero. The reset is applied as January's input is built, so December's stored carry-over keeps
  what December handed on.
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
result's version is unchanged. The app writes version 2 since ticket 34: the unit's skill needs and flag, the hospital's skill
shortfall weight and the catalogue's required skills reach every new solve, re-plan and close input as the other rules do.
Each nurse carries her `skills` since ticket 35, clamped to the month by the assembler (`nurses.rostering.skills_block`): a
current record of a live skill by its name, with its expiry when that falls in the month or before it, and null when it is valid
past the month's last day or its kind does not expire (an expiry kept while `expires` was off counts for nothing). A nurse with no
record of a skill has no entry for it, and a retired skill is no record: it counts toward no need and bars nobody, as it is left
out of `required_skills`. The solver counts a day barred by an expired required skill as leave in fairness (ticket 34, the user's
decision): her fair share of weekend days is prorated for it, so she pays no `fair_weekend` and carries no lower
`friday_balance` for a Friday she could not work. Such a day also supersedes a preference, as leave does (ticket 35): a wish to
work it costs nothing and is no preference not kept, in the search, the explanation and the carry-over alike
(`nurse_roster.problem.superseding`), and My month marks it "Skill expired", counted neither way. A stored input keeps the skill
names it was given and is read under today's (`solves.input.in_current_skill_names`, through the rename log) where the solver's
code explains or compares it: a result's explanation, a re-plan's comparison and a draft's changes since. A skill name the solver
would refuse (one a spreadsheet reads as a formula, or with a line break) is refused by the catalogue.

Full runs changed it once more (the solver's problem schema 6; the solve input's version unchanged). The department gains
`max_full_runs`, the most full runs a nurse may work in the month (a whole number 0 to 31; absent or null means no cap), and
the weights gain `excess_full_run`, the price of each full run beyond it (absent means 0); both are optional in either
version, so every stored solve input and close input still loads and gives what it gave. A full run is a run of exactly the
longest run (`max_consecutive_shifts`), leave ending a run as a day off does; it counts in the month that holds its last day,
one reaching the month's last day included (ticket 48: it cannot grow, as the next month reads it as history). The rule,
`excess_full_run`, is priced only, never refused; its match names the nurse, her count and the cap, and the per-nurse
explanation carries it as it carries weekends above the most. In the app (ticket 48) the cap is a unit rule, "Most full runs in
a month", among the run rules beside the longest run and the rest after two runs, shown on Unit rules only while the longest
run is above 1 and kept while hidden; the weight, "Full run above the most", is the CNO's beside the other weights, 0
switching it off hospital-wide. Every new solve, re-plan and close input carries both, as the unit rules and the weights are
carried; a stored one without them reads as no cap. Hand edits, swaps, covers and requests are never refused for it, and no
nurse page shows it.

The overtime share changed it again (ticket 49; the solver's problem schema 7; the solve input's version unchanged). The
department gains `share_overtime` (the unit shares its overtime), `overtime_tolerance` (hours a nurse may stand above her target
for free) and `overtime_carry_cap` (the most her carried balance moves her target), the two numbers whole hours 0 to 744; the
weights gain `overtime_above_share`, the price of each whole hour above; each nurse gains `overtime_balance`, the hours her
overtime has stood above (+) or below (−) her overtime share so far this year. All five are optional in either version, absent
meaning the rule off, 0 hours and a balance of 0, so every stored solve input and close input still loads and gives what it gave.
Her share is the month's overtime in the input times the hours she owes over the hours every nurse of the input owes; her target
is the share less her balance, held within the limit, when the unit carries fairness between months; her overtime above it,
beyond the tolerance, is priced in whole hours rounded down and never more than her overtime, so a nurse with no overtime, or
owing none, costs nothing. The rule, `overtime_above_share`, is soft only and active while the unit's switch, the weight and the
hours rule are all on; its match names the nurse, her overtime, her share and the hours priced, and the per-nurse explanation
carries it. A result's `carry_over` carries her balance for next month, in + overtime − share, moving while the switch and the
hours rule are on and handed on unchanged otherwise. The chain carries it (`closes.chain.CARRIED`, ticket 50) from her opening
value, 0 by default, and 0 out of a close stored before it; it resets in January with the other two balances. Until the unit
rules and the weight reach the solve input (ticket 51) the solver hands every balance on unchanged.

Probation changed it again (ticket 52, ADR 0014; the solver's problem schema 8; the solve input's version unchanged). Each nurse
gains `on_probation` (absent = false) and `preceptor`, the id of another nurse of the input she follows (absent or null = none),
both optional in either version, so every stored solve input and close input still loads and gives what it gave. Refused with
the field's path: a preceptor that is not another nurse of the input, one herself on probation, one named by two nurses, and a
preceptor on a nurse not on probation. A nurse on probation counts toward nothing about a shift (headcount minimum and maximum,
team leader, both genders, score target and balance, skill needs), is left out of the day and night fairness, the weekend
fairness, the overtime share and the unit's overtime totals, with her three fairness balances 0 out; works no night shift (her
allowed shifts narrowed by the unit's night shift, a night pin on a free day refused); and works less than what she owes plus
her shortest allowed shift, the excess her own overtime for the month and the year. The hard rule `following`: on a free day her
preceptor works a shift she is allowed, not on leave or pinned, she works that shift or is off, and once such a day is left off
she works no other free day; its match names the nurse, the day, her preceptor's shift and hers. Precheck names a nurse on
probation with no preceptor. The app writes neither field until ticket 55.

## 7. The worker and the queue (ADR 0006)

Procrastinate, with its tables in the application database, run by the `worker` container at
concurrency 4 (`manage.py queue worker --concurrency 4` in `deploy/compose.yaml`, `queue` being Procrastinate's command with
what it prints logged as JSON), so a scheduled job never waits behind a
running solve (ADR 0009). Every job takes a lock: solves share the hospital-wide one, and each
periodic job takes one under its own name, so a waiting job takes no slot, no kind of job holds more
than one, and no job runs beside its own previous run. A new job that can run longer than about a
minute takes a lock of its own. Jobs:

- `run_solve(solve_id)`: under a hospital-wide lock, so solves run first come first served
  across units, a unit having one queued or running at a time (section 4); submits the solve input to the solver, polls progress into the `Solve` row,
  stores the result, relays a cancellation. A failed attempt (solver crash, unreachable) is
  retried once inside the same job, so it keeps its place in line; a second failure is marked
  failed with its reason, and the manager can re-run it. A worker that dies goes on watching the
  job the solver still holds when it comes back.
- `recover_lost_jobs` (every five minutes): puts a dead worker's job back on the queue, which would
  otherwise hold the lock for good, and fails a solve whose job is gone. A dead run of a periodic job whose next run already
  waits ends as failed instead, since it could not take its queueing lock back (a restore brings back the backup that was
  running as that backup was taken).
- `tell_probations_ending` (hourly, minute 25, ticket 54): tells the unit's manager, once, in the last month of each probation
  not ended early, from its first hour; one per last month (`probation_notified_for`), so a worker that was down still tells
  that month, and an extension tells again in the new one. A probation needs no job to end: its last day is read.
- `close_month` (hourly, minute 30): closes every unit's month whose close time has passed on the hospital's clock and
  is not closed, oldest month first across units, so a worker that was down catches up; and `project_carry_over` on demand,
  after every new roster version and every close, under its own lock, which stores the projected carry-over of an approved
  month and of the unit's approved months after it. Neither calls the solver
  service: the carry-over is worked out in the worker's process by `solver_service.grid`. The chain carries each field of the
  result's `carry_over` block (`closes.chain.CARRIED`), the overtime balance among them (ticket 50): projected from the roster in
  force, corrected at the close and re-worked at a re-close, carried unchanged through a month with no roster for her, as the
  night and weekend balances are, out of her opening value at first, reset in January with them, following her across a
  transfer, and 0 out of a close stored before it existed, nothing worked back through earlier months. So is the count of
  preferences not kept (ticket 30): projected
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
  `remove_old_notifications` (older than a year, read or not), `remove_old_push_attempts` (older than seven days, whatever
  came of them; the health page reads the last 24 hours), `clear_expired_sessions` (Django's `clearsessions`), and last, at
  22:50, before a nightly backup at 02:00 in Riyadh, `remove_old_login_failures` (ticket 65: each username's count of failed
  logins, `LoginAttempts`, a day after its last failure or when that time is unknown, unless the name is locked now, and each
  address's throttle window, `AddressFailures`, once it has ended; a name or an address removed counts afresh from its next
  failure, and the audit entries of the failures stay).
- `expire_swaps` (hourly, minute 15): expires each waiting swap one of whose dates has passed, telling its people. Every page reads
  the dates itself and every write about a swap does the same for it first, so a worker that is down delays only who is told.
- `expire_covers` (hourly, minute 20): stores each waiting cover whose date has passed as expired and tells the nurses offered
  it. Every page reads the date itself and every write about a cover does the same for it first.
- `open_and_close_request_windows` (hourly): opens each request window whose open date has come and closes each whose close
  date has passed, telling whoever that tells. Every write about a unit's windows does the same first, so a worker that is down
  delays only the notifications.
- `close_ended_nurses` (hourly): deactivates staff nurses whose last day is over. An end date of
  today or earlier deactivates at once. A manager's account stays the System Admin's.
- `push(notification_ids)` (ADR 0012): deferred by `notifications.sending.notify` in the transaction that writes the
  notifications, one job a call however many it tells, and only when their event has one of the six kinds with a deadline.
  Under its own lock, `push`, so pushes go one job at a time. For each notification, to each push subscription of its reader,
  it first reads that the thing still waits and that the reader still has a page for it, then sends the kind code alone
  (`notifications.pushing`, the one module that knows the protocol and its library). Every send is one row of
  `PushAttempt`: when, and `sent`, `gone`, `refused` or `unreachable`, nothing of the user or the device. A success resets
  the subscription's failures; `gone` (404 or 410) ends it at once; a refusal counts one failure; an unreachable service is
  tried again after 1, 3 and 6 minutes, for the subscriptions that failed alone, and counts one failure after the last; ten
  failures in a row end a subscription. A try again is deferred at priority −1, so one waiting for its time holds back no
  new push. A job starts no new send once it has run 30 seconds, and hands the sends it has not made to a new push job at the
  normal priority with the same try number, so they wait behind any push already waiting and a first try stays one; the next
  job reads again that the thing still waits and whose the subscription is. So no job holds the others back by more than
  about 30 seconds and one send, and nothing is dropped. A user holds at most ten subscriptions (ticket 67), which bounds the
  sends one reader costs.

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
service worker that handles no request (`frontend/public/sw.js`, no `fetch` listener): nothing is kept offline, so
the API, a roster's files and print sheets, backups and `/metrics` reach the network as they would without it. Every file
with a fixed name (the page, the worker, the manifest, the icons) answers `no-cache`, so a deploy is what loads next; only
the build's hashed assets are cached for good. They come from `frontend/public` at the site's root: WhiteNoise in `web`
sets the headers (`config.settings`) and Caddy passes them through unchanged; in development Vite serves the same files
with the same headers. The worker's scope is `/`. A tab opened before a deploy that asks for a page's code by its old name
loads again once (`lib/stale-build.ts`). Every notification is in the app: every role's header has a bell with the unread count, which polls and does not count as activity, and leads to the
Notifications page. Who is told of what is in one place, `notifications.sending`, called inside the transaction of the
change. A notification links to the reader's own page for it, by what they hold when they read it. Visual design is decided later; the architecture does not depend on it.

Six of them, those with a deadline, are also pushed to the devices their reader turned on (ADR 0012; GLOSSARY, **Push**): a
swap to answer, a swap awaiting the manager, a request window opened, a window closed with requests waiting, a roster
submitted and a roster rejected. Everything else stays on the bell alone. A push carries its kind code and nothing more; the
service worker holds each kind's words and page, always shows a notification titled "Nurse roster" tagged by its kind
(`push`; an unknown kind shows the title alone), and on a tap (`notificationclick`) focuses an open window and has the app's own router go to the kind's page, with
no month, so a roster with unsaved changes still asks first, or opens a window there when none is open. A third listener for pushes,
`pushsubscriptionchange`, subscribes again when the browser renews an address and tells the server which one it replaces.
A device opts in on the Notifications page, in "On this device": Turn on asks the browser's permission inside the tap and
subscribes with the installation's public key (on an iPhone or iPad only from the app on the Home Screen, which the page
says); Turn off ends this device's push subscription, Turn off on every device all of the user's. Pressing Log out turns
this device off first; a session that expires on its own does not, since reaching someone who is not using the app is the
point. A deactivation ends every subscription of the account, beside its sessions. So does the push service saying an
address is gone, and ten failed sends in a row. A user holds at most ten: turning pushes on for an eleventh device, or
taking over one of another user's, ends the user's earliest turned on, with no entry of its own; a browser's renewal is no
new device. At each start the app replaces, unasked, a subscription bound to a key the
server no longer uses. An address is accepted only on a push service's own host, at turn-on and again at each send, so the
worker posts nowhere else.

Screens per role, in outline: System Admin (accounts, technical settings, audit log, solve
history, health and backups); CNO (hospital rules and weights, shift catalogue, leave types, skills,
holidays and Ramadan, units and managers, nurses with import and export and their skills, the expiries, each unit's rules, rostering attributes and leave
to read, roster overview, the Day view and approvals); Deputy CNO (roster overview, the Day view, approvals, hospital rules and each unit's rules,
rostering attributes with nurses' skills, the expiries, and leave, to read); Unit Manager (unit rules, rostering attributes, nurses with the unit's expiries, request
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
re-plan the comparison with the roster in force. Any two of a month's results that hold a roster also compare side by side,
for the unit's manager only (ticket 43): what differed between their solve inputs (hospital and unit rules field by field in
the audit log's words, the time limit, the calendar, and for each nurse only the kind of change), each soft rule's amount,
weight and penalty with each result costed on its own input, the cells that differ, each nurse's hours, the violations and
facts in both or in one only, and the solver's statistics. Nothing is priced on the other's input, and nothing is restored
from it. A nurse's carry-over waits for the month close.
A stored result holds the penalties' totals only, so the explanation is worked out when asked.
The solver's words count days from 0, so what the pages show says dates instead. The two skill rules read as the others do: a
skill need short, per shift and day with how many short, under the skill shortfall weight's name, "Short of a skill need", when
soft, and as a violation when hard; a shift on a barred day as a violation on her, saying the skill and its last day (ticket 35).

The System Admin's solve history is unit, month, state, the failure kind (in fixed words naming no one), who asked, when, how
long, the time limit, the attempts and the cost, and only that (not even whether a solve was a re-plan, whose date is about a
roster): the solver's and the worker's words
(`error`, `message`, `precheck`, the explanations) can name a nurse and a date, and no free text
reaches it. The cost was already theirs to read in the audit log.

### Security

Local accounts only, designed so an LDAP or SSO backend can be added as a Django
authentication backend. Generated passwords shown once, forced change at first login.
Minimum length 10 with Django's common-password and similarity checks, lockout for 15
minutes after 5 failed logins (whether or not an account has the username, so the answer never says which names exist; the
login page shows when it ends on the hospital's clock), sessions expire after 12 hours of inactivity (polling a solve's
progress is not activity), no two-factor authentication in v1. Beside the lockout per username, a **throttle** per client
address (ADR 0015, `accounts.login`): 50 failed logins from one address in a 15-minute window refuse every login from it for
the rest of the window, whatever the username, with 429, the time it may try again on the hospital's clock and `Retry-After`.
The check comes before the username's row is touched or any password looked at, so a throttled login costs no hash. A wrong
password, a refusal while the name is locked and a wrong current password on Change password each count one failure; a success
counts nothing and clears nothing. Change password is refused the same way while its address is throttled, before the current
password is checked. An IPv6 address counts by its /64; a request with no address (development without Caddy) is never
throttled. The address is the one the audit log reads (`audit.log.client_ip`), so everyone behind one address shares its
budget. Caddy works it out and always sends it to `web` in `X-Client-IP`, replacing any a client sent; `client_ip` reads that
header, and the peer only without Caddy (development), never `X-Forwarded-For`. Caddy takes the peer as the client unless the
peer is one of `TRUSTED_PROXIES` (empty by default: no one), whose `X-Forwarded-For` it then reads strictly from the right,
skipping only trusted hops, so the address is the one the nearest untrusted hop was seen at. Without the variable, behind a
hospital's proxy, every client is the proxy and shares its throttle. The address's row is not held across the hash, so a
burst of parallel tries may pass the 50 by at most what the web pool serves at once. Every login the server checked, failed or not, goes to the audit log, and so does each throttle, once,
when an address reaches it (`auth.login_throttled`: no actor, no target, the address and the window's end); a request a
throttle refused is not, since its password was never looked at. A failed login (`auth.login_failed`) names the username
typed as its target only when an account has it; at any other name its target is empty, with its reason and address, so a
password typed into the username box is never kept where the System Admin reads it. Every change to settings, accounts,
rosters, requests, swaps and covers goes there too. So does each taking of the staff list, which holds everyone's gender:
who took it and how many nurses it held, and nothing from the file. Its import template holds no one's data and is not
logged. So does each taking of a roster version's CSV or Excel file (`roster.exported`): who took which unit's month, which
version and which format, and nothing from the file. A roster's print page makes no file and shows only what its reader can
already read, so it is not logged. Nurses see colleagues' names and shifts only. The System Admin reads the log and may see no rostering attribute, so an attribute's change is logged as whose
changed and by whom, without its value or even which one, since a change to a two-way flag gives its value away. Unit
rules are logged with their values, as hospital rules are: they say nothing about a person. A nurse's skills, certificates
and licences are logged as whose changed and by whom (`nurse.skills_changed`), never the entry, the identifier or a date, and
their identifiers, issue dates and expiries reach no file (the staff list, a roster's CSV, Excel or print page) and no
notification (ticket 59). Attributes also stay off
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
hand, its filling and its expiry have no entry, since one beside the leave's would date it. Turning pushes on and off is logged
as `push.turned_on` and `push.turned_off`, the user as actor and target: nothing of the device, not its address, its keys or
even the IP it called from. A subscription ended by Log out is the user's own turn-off; one ended by a deactivation, by the
push service or by ten failures has no entry, and a push sent has none. `push.keys_rotated` has no actor, "from the server".

Two headers come from Caddy alone (`deploy/Caddyfile`, ticket 72). **One content security policy** on every answer it passes on,
pages, static files and the API alike, set deferred so it replaces any `web` sent: `default-src 'self'; script-src 'self';
style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'`. Only the
app's own scripts, styles and connections, no inline script or style and no eval (zod runs `jitless`, `frontend/src/lib/zod.ts`),
images from `data:` besides; the browser checks reach the
app through Caddy and fail on any violation a page reports (`e2e/support.ts`), so a change that needs more widens it there, by
name. **HSTS**, `Strict-Transport-Security: max-age=31536000`, without `includeSubDomains` or `preload`, only with `DOMAIN` (the
snippet that mode imports): a self-signed installation never sends it. Caddy's own error pages (the 502 while `web` restarts
or a restore runs) carry neither. No answer may be framed (ticket 62): `web` sends `X-Frame-Options: DENY` on every answer,
WhiteNoise's files included, and the policy's `frame-ancestors 'none'` says it again; nothing in the app frames itself. The routes
that answer with a file, the staff list, both import templates, a roster version's file and the System Admin's backup, are
plain GETs that the `SameSite=Lax` session cookie reaches from a link on another site, so they refuse with 403 a request whose
browser says another site started it (`Sec-Fetch-Site: cross-site`, `accounts.authz.for_a_file`), before the user and the role are
read: the answer is the same for everyone, nothing is logged, the idle limit does not move, and it says nothing of who is signed
in or which backups exist. The
app's own links are `same-origin`; a request with no such header, from an older browser or a script, is served.

### Nurse import and the staff list

A CSV of hospital ID, full name, gender, unit, start date and, optionally, on probation (ticket 54: Yes, No, TRUE or FALSE, empty
meaning no; a file whose header leaves the column out imports as before, and the template names it), in UTF-8 or UTF-16 with a byte order mark, at most 500
nurses and 1 MB. Any other encoding is refused rather than guessed. Previewing saves nothing and keeps nothing, so
confirming sends the file again: it is judged again from the start, and with any problem, or when it no longer means what
was previewed, nothing is saved and the answer is the preview as it now stands. One password hash takes about half a second
on purpose, and the passwords may be kept nowhere, so the worker cannot make them and hand them back later. Confirming is
one long request instead: the hashes first, four at a time and holding no lock, then one transaction. It runs in one of
gunicorn's threads, which no timeout ends (section 2), so 500 rows on one core take what their hashes take. The password sheet is the
answer to that request and lives only in the page's memory: if the answer is lost after the transaction, the nurses stay and
their passwords are reset one at a time. Uploads stay in memory and never reach a temporary file. In a
staff list every cell is quoted, and one a spreadsheet would run as a formula starts with an apostrophe. Its columns are the
import's, the probation's last day (both empty unless a probation is not over), the end date, role, status and the transfers
to come.

The skills CSV is the same kind of file (`nurses.importing.read_file`: the encodings, 500 lines and 1 MB, in memory),
of hospital ID, skill and expiry, on its own Import skills page beside the nurse import's: a template, a preview that
judges every row and says what saving would do with it, and a confirm that sends the file again. A row names a nurse by
hospital ID, an active one, and a skill by its current name in any case of letters, live; its expiry is a date for a kind
that expires and empty for one that does not, a date already past accepted as a fact. A skill she does not hold is
recorded; one she holds takes the row's expiry, ending the old row as a renewal by hand does; one that says what is
already recorded changes nothing. A nurse and skill twice in a file is a problem on both lines. Confirming is one short
transaction under the locks every skill write takes, the hospital settings' then the nurses', in which the file is
judged again: the preview's token stands for each row's nurse, skill (its name and whether it expires), expiry and the
record a renewal would end, so a renewal by hand since the preview is a different preview and nothing is saved. The audit
log has one `nurse.skills_imported` entry with the number of rows and nothing from the file, not even whose skills. The template is its header alone, so it names no skill;
every cell of every CSV this application writes goes through the staff list's guard against a formula. Neither the nurse
import's template nor the staff list holds skills.

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
shows solver reachability and version, disk and database size, the backups with the last one's time, queue state, and pushes:
how many were sent and how many failed in the last 24 hours, counted by attempt (each send to one subscription, each try
again included, never by job) and why the last of those failed, in one of three fixed words (`unreachable`, `refused`,
`gone`; `unreachable` is also a push service answering 429 or 5xx). That block and its two gauges on `/metrics` hold nothing
of a user or a device; a run of `unreachable` with nothing sent is how a firewall that blocks the push services shows. The
public `/api/health` says only whether the database and the solver answer, and each web process keeps that answer five
seconds (`ops.public_health`, ticket 68), so a client polling it cannot make the application call the solver on every request;
the health page and `/metrics` ask afresh each time. Nothing else is bundled.

## 9. Defaults

- Hospital and unit rules are seeded from the reviewed default set the solver was shaped on
  (12-hour day and night shifts, Friday weekend, the standard forbidden successions, overtime
  caps, the weights) and flagged "defaults, review before the first solve". A unit's defaults
  follow the catalogue as it stands when the unit is created: a default shift the CNO renamed
  appears under its new code, and one the CNO retired is left out, which the solver refuses until
  the unit manager has chosen the unit's shifts.
- Every unit, existing ones included, starts with the most full runs in a month at 3 (a migration wrote it in, ticket 48), and
  the weight of a full run above it is 4; the solver's sample predates both, so these are the spec's, not the sample's.
- Every unit, existing ones included, starts with no skill needs and the needs hard, and the skill shortfall weight is 0 (two
  migrations wrote them in, ticket 34).
- Time limit cap 300 s; unit default time limit 60 s; a new unit's request cap 3 and preference cap 10 per nurse per month;
  backup 02:00 kept 30 days; close 00:30 on the first. All editable by the role that owns them. The time
  zone, `Asia/Riyadh` by default, is the environment's `TIME_ZONE`, set at install rather than on a page.
- A unit manager may roster any future month, not only the next.
- Nothing is hard-deleted: units are archived when they have no nurses, nurses are
  deactivated, requests and swaps keep their final state, leave corrected or removed stays as
  an ended row, every roster version and solve is kept. The exceptions are a public holiday and a month's fixed Ramadan dates, which have no
  history of their own: what a solve used is stored with it and the audit log keeps the rest. Housekeeping removes only what is
  no one's record (section 7): a notification after a year, a push attempt after seven days, an expired session, a username's
  count of failed logins a day after its last failure unless it is locked then, an address's throttle window once it has ended,
  and the queue's rows of jobs that ended;
  backups go after the days the System Admin keeps them.

## 10. Repository, build and tests

```
cp-sat-nurse-roster-app/
  backend/      Django project and apps, pytest-django suite
  solver/       vendored nurse_roster package and its tests, the FastAPI service
  frontend/     Vite + React SPA, Vitest suite
  deploy/       compose.yaml, Caddyfile, .env.example, INSTALL.md,
                reset-admin-password.sh, restore.sh, tests/operations.sh (the compose-level test)
  docs/         this document, adr/, research/
  e2e/          Playwright suite against stacks of its own (stack.sh builds, seeds, resets and removes them; ci.sh is CI)
  .github/      workflows/browser-checks.yml, which runs e2e/ci.sh
  Dockerfile    one multi-stage build, one image
  GLOSSARY.md
```

Development runs the installation's own stack, `deploy/compose.yaml` alone (Caddy on 443, gunicorn, the image built from the
checkout), with no hot reload: after a change, `docker compose up -d --build` rebuilds it, since a restart serves the image's
old code. The hot-reload overlay `compose.dev.yaml` was removed on 2026-11-11, unused since 2026-11-07. Tests never use that
stack's database: the backend's suite runs on a throwaway PostgreSQL 18 container.

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
The Umm al-Qura calendar is `hijridate` 2 (`<3` in the solver's and the backend's dependencies): fixed tables for
1925 to 2076, read offline by the solver and by the web container, which takes a month's Ramadan days from the
solver's calendar module and calls `hijridate` itself only to name a Ramadan by its Hijri year and to find it.

## 12. Revisit later

The amount of solve information shown (now: everything), TanStack Charts and TanStack Form 2
once mature, Arabic and RTL, LDAP/SSO, email, PDF
generation, the Deputy CNO's further responsibilities, the unit manager's further permissions.
