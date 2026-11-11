# Findings detail — cp-sat-nurse-roster-app

This file is specified for confirmed findings of medium severity or higher. **This run confirmed 0 such findings.** The 5 confirmed findings are all `low`; their full source paths, sandbox reproductions and fixes are included below for convenience.

## 1. A far-future month makes one request run a database query per nurse per month in between, for any signed-in nurse and, on a solve start, under the hospital-wide catalogue lock

`backend/closes/chain.py:Chain.carry_in:per-nurse-per-month-queries-up-to-caller-chosen-month` — severity **low**

### Ordered trace

1. **entrypoint** `backend/requesting/preferences_api.py:84` (`my_preferences`) — GET /api/preferences/mine?month=YYYY-MM as any Staff Nurse (the lowest signed-in role); line 91 calls doubled_by(nurse, month) for the month given.
2. **propagation** `backend/rosters/own_month.py:142` (`doubled_by`) — Chain().carry_in(nurse, month) for the nurse's own chain: one walk, two queries a month.
3. **propagation** `backend/solves/api.py:114` (`preview`) — GET /api/units/{unit_id}/solves/preview?month=YYYY-MM as the unit's manager; line 118 calls assemble(unit, month) before _what_stops_it. preview_replan (line 245) and GET /api/units/{unit_id}/close (backend/closes/api.py line 142, also CNO and Deputy CNO) reach the same walk for every nurse of the unit.
4. **propagation** `backend/solves/api.py:193` (`start_solve`) — POST /api/units/{unit_id}/solves: assemble(unit, month) runs inside the transaction that locked the hospital settings row (line 188) and the unit row (line 189); the refusals are checked only afterwards (line 194).
5. **propagation** `backend/solves/input.py:104` (`assemble`) — chain.carry_in(nurse, month) once for every nurse rostered in the unit that month.
6. **propagation** `backend/closes/chain.py:113` (`Chain.carry_in`) — while step is not None and step < month: one _through call per month from the month after her latest closed month, or from her first approved roster, to the requested month.
7. **sink** `backend/closes/chain.py:135` (`Chain._through`) — membership.placement_in(nurse, month) evaluates nurse.placements.all() (backend/nurses/membership.py line 75), a query on every call; line 136 adds an approved-roster lookup memoised per unit and month, so one more query per month.

### Evidence

- `backend/nurses/api.py:58` — MonthText is bounded only by iso_date's year range (backend/hospital/catalogue_api.py lines 41 and 62: 1925 to 2076); MyRosterFilter (backend/rosters/reading_api.py line 257) and the solve and close MonthFilter use it unchanged.
- `backend/solves/api.py:66` — _what_stops_it refuses only a month before the current one; no route sets an upper bound on how far ahead the month may be.
- `backend/solves/input.py:94` — The nurses queryset uses select_related('user') and prefetches current skills only, so nurse.placements.all() is not cached.
- `backend/nurses/membership.py:75` — placement_in builds list(nurse.placements.all()) on each call.
- `backend/closes/chain.py:121` — With no closed month the walk starts at the earliest approved roster holding her, and with neither it does not run: the sandbox control with nothing closed ran 43 statements for the same 2076-12 preview.
- `backend/solves/api.py:188` — start_solve takes HospitalSettings.load(for_update=True) before assembling. The same row lock is taken at 27 call sites in 16 modules (repository search for HospitalSettings.load(for_update=True) in backend code outside tests, docstring mentions left out), among them backend/solves/running.py, backend/closes/making.py, backend/rosters/api.py and backend/hospital/catalogue_api.py.
- `backend/closes/api.py:108` — _carry_over calls chain.carry_in for every nurse of the unit for the month in the query string; the route's readers are Unit Manager, CNO and Deputy CNO (line 30).
- `deploy/compose.yaml:55` — web runs gunicorn with 3 workers and a 300 s timeout; backend/config/gunicorn.py sets no worker class or threads, and backend/config/settings.py sets no statement or lock timeout on the database connection.

### Dummy attacker and affected resource

A signed-in Staff Nurse or Unit Manager of the hospital sending ordinary API requests with a month far in the future.

Availability only, and it ends when the requests stop: each request occupies one of three web workers for the length of the walk (about 1 s for a nurse and 2.5 s for a 4-nurse unit in the sandbox), and a refused solve start holds the hospital settings lock for that time. Lasting harm to other users needs a sustained stream of such requests, which was not generated or measured; no data is read or changed.

### Native input and bounded instructions

Input:

```
GET /api/preferences/mine?month=2076-12
```
```
GET /api/units/{unit_id}/solves/preview?month=2076-12
```
```
POST /api/units/{unit_id}/solves {"month": "2076-12", "time_limit_seconds": 60}
```
```
GET /api/units/{unit_id}/close?month=2076-12
```

Instructions:

1. In a throwaway database, create two dummy units of 2 and 4 staff nurses with their managers, and one closed month (a MonthClose for 2026-09 with a closed CarryOver for each nurse).
2. Signed in as each principal through /api/auth/login, send each request once for month 2026-12 and once for 2076-12, counting the SQL statements of the request with a connection execute wrapper.
3. For the POST, first create a queued Solve row for the same unit and month, and during the request try SELECT ... FOR UPDATE NOWAIT on the hospital settings row from a second connection.
4. Compare the statement counts; send nothing concurrently and do not repeat requests.

### Observed output and the invariant it proves

Sandbox run of harness-carry-walk.py (PostgreSQL 18, one CPU, date 2026-11-10), output in check-carry-walk.txt. Staff Nurse GET /api/preferences/mine: 19 statements for 2026-12, 1,219 for 2076-12 (605 placement reads, 603 roster reads, 1.0 s). Manager GET solves/preview, 2-nurse unit: 36, 72 and 1,836 statements for 2026-12, 2027-12 and 2076-12; 4-nurse unit: 48, 108 and 3,048 (2,414 placement reads, 2.4 s). Control with nothing closed: 43 statements for 2076-12. Manager POST solves for 2076-12 with a queued solve of that month: 409 'A solve of this month is already queued or running.', 3,048 statements, 2.6 s, Solve rows 1 before and 1 after; the hospital settings FOR UPDATE was statement 3, before any placement read, and the second connection's FOR UPDATE NOWAIT on that row failed with 'could not obtain lock on row in relation "hospital_hospitalsettings"' during the request and succeeded after it. Manager GET close?month=2076-12: 3,027 statements. The seconds are the sandbox's and say nothing about the deployed stack.

**Invariant:** A request for a caller-chosen month should cost database work that does not grow with how far ahead the month is, and a solve start that is going to be refused should not hold the hospital-wide lock for longer than a refusal takes.

### Conditions and containment

- _authentication_level_: A signed-in account. A Staff Nurse reaches the walk for her own chain (about two queries a month ahead); a Unit Manager reaches it for every nurse of their own unit, and only a Unit Manager reaches the path that holds the hospital settings lock.
- _data_state_: The nurse has a closed month or an approved roster that holds her. The schedule closes each month on its own, so an installation in use meets this after its first month; before that the walk does not run.
- _system_configuration_: The shipped deployment: three synchronous gunicorn workers, no request rate limit in the Caddyfile, no database statement or lock timeout.

### Source-level remediation and regression case

Make the walk's cost independent of the requested month, then bound the month. (1) In Chain.carry_in, stop stepping once no approved roster lies between the current step and the requested month: from there each month only hands on what came into it with no shift history, so the result is carried.into(month before the target) | NO_HISTORY in one step; look the last approved roster month up once per chain. (2) Read a nurse's placements once per chain (or prefetch them in assemble) instead of once per month. (3) Refuse a month more than a small number of months past the hospital's current one in the routes that take a month (solve and re-plan preview and start, close view, My month, My preferences). (4) In start_solve, check the refusals that need no assembly (month over, frozen roster, a solve already queued or running) before assemble, so a refused start releases the hospital settings lock at once. The code below is a sketch of (1) that was not run against the test suite.

`backend/closes/chain.py`:

```python
    def carry_in(self, nurse: NurseProfile, month: dt.date) -> Carried:
        closed = latest_closed(nurse, month)
        if closed is not None:
            carried = Carried(BEFORE_PREFERENCES | closed.values, CarrySource.CLOSED, closed.month, closed.month.year)
            step = next_month(closed.month)
        else:
            carried, step = Carried(opening(nurse), CarrySource.OPENING, None, _added(nurse).year), self._first_roster(nurse, month)
        last = self._last_roster(month)
        while step is not None and step < month:
            if last is None or step > last:
                # No approved roster from here to `month`: each month hands on what came into it, with no shift history.
                before = month_before(month)
                return Carried(carried.into(before) | NO_HISTORY, carried.source, before, before.year)
            carried = self._through(nurse, step, carried)
            step = next_month(step)
        return carried

    def _last_roster(self, month: dt.date) -> dt.date | None:
        """The latest month before `month` with an approved roster of any unit, read once for each month asked."""
        if not self.project:
            return None
        if month not in self._last:  # self._last = {} in __init__
            self._last[month] = (Roster.objects.filter(state=RosterState.APPROVED, month__lt=month).order_by("-month")
                                 .values_list("month", flat=True).first())
        return self._last[month]

```

## 2. Offering a cover names nurses of other units to a unit manager

`backend/covers/steps.py:offer:unscoped-nurse-name-in-refusal` — severity **low**

### Ordered trace

1. **entrypoint** `backend/covers/api.py:179` (`offer_cover`) — POST /api/units/{unit_id}/covers/{cover_id}/offer, for the Unit Manager role only. The body's `nurses` is a list of up to 500 free-text hospital IDs (OfferCoverBody, line 174). The route checks the unit with unit_in_scope (line 183) and passes the list to steps.offer (line 187).
2. **propagation** `backend/covers/steps.py:95` (`offer`) — After the cover is found waiting in the manager's unit (line 82) and judged (lines 91-94), the submitted IDs not yet offered are looked up as NurseProfile rows by username across the whole hospital, with no unit, roster or role filter.
3. **propagation** `backend/covers/steps.py:99` (`offer`) — For each submitted ID not in the judged list, the refusal is worded with name_of(nurses[hospital_id].user), the full name, when a profile was found, and with the ID itself when none was.
4. **sink** `backend/hospital/api.py:25` (`refuse`) — refuse raises ninja's ValidationError with each sentence as `msg`, which the API returns to the manager in the 422 response's `detail`.

### Evidence

- `backend/covers/steps.py:95` — The name lookup, lines 95-96: NurseProfile.objects.select_related("user").filter(user__username__in=added), hospital-wide.
- `backend/covers/steps.py:99` — The refusal sentence uses name_of(nurses[hospital_id].user) if hospital_id in nurses else hospital_id, so the answer tells an existing nurse profile (by name) from an unknown ID.
- `backend/covers/steps.py:94` — `could` holds only nurses judged on the cover's own roster, so an ID from another unit is always in `refused` (line 97) and always named.
- `backend/rosters/review.py:77` — name_of returns user.full_name, or the username when the name is empty.
- `backend/covers/api.py:174` — The `nurses` field accepts up to 500 strings with no format or membership check.
- `backend/covers/tests/test_offers.py:92` — The existing test pins that the refusal reaches the caller as a 422 whose message begins with the nurse's name, for a nurse of the same unit. No test offers a cover to an ID from another unit.
- `backend/nurses/api.py:193` — The intended control: list_nurses gives a manager only membership.on_the_list_of(unit), 'naming no other unit' (lines 193-201). In the local run the other unit's nurse was not in this list.
- `docs/ARCHITECTURE.md:127` — 'A unit manager sees nothing of other units.' Line 101 gives 'Read nurses' to a manager for their own unit only.
- `backend/swaps/judging.py:102` — A sibling control: a swap echoes an ID that is not on the roster and resolves no name.
- `backend/rosters/editing.py:54` — A sibling control with the intent written down: a pin edit's refusal is 'the same for a nurse of another unit as for no such nurse' and says only the ID.
- `backend/nurses/leave_api.py:211` — A sibling control: recording leave gives 'the same 403 whether another unit's nurse exists or not'.
- `backend/accounts/api.py:40` — A hospital ID is a username: 1 to 150 letters, digits, dots, dashes and underscores. Where IDs follow a staff-number pattern they can be guessed.

### Dummy attacker and affected resource

A signed-in Unit Manager of one unit, using the application's own API with their own session, who wants the names of nurses in units they do not manage.

It discloses the full name behind a hospital ID, and whether a nurse profile exists, for staff of other units in the same hospital. No roster, leave, attribute or credential is exposed and nothing is changed.

### Native input and bounded instructions

Input:

```
POST /api/units/{own_unit_id}/covers/{waiting_cover_id}/offer with JSON body {"nurses": ["<hospital ID of a nurse placed only in another unit>", "<an ID no nurse holds>"], "note": ""}
```

Instructions:

1. Run harness-offer.py in the database sandbox (one run, throwaway PostgreSQL 18, no network, config.test_settings, repository at commit f2492e0 mounted read-only and unchanged). It uses dummy data only.
2. The harness seeds two units, each with its own manager. Unit A holds the solver's four-nurse sample and an approved roster of the current month written as rows; one more staff nurse, 'Zeta Otherunit' with hospital ID sa-b-0001, is placed only in unit B.
3. It signs in as unit A's manager through POST /api/auth/login and opens a cover by hand through POST /api/units/{A}/covers for Day on the month's last day. The hospital's clock is not changed.
4. As a control it reads GET /api/nurses (the manager's own list) and GET /api/units/{B}/covers (another unit's page).
5. It sends the one offer: POST /api/units/{A}/covers/{cover}/offer with {"nurses": ["sa-b-0001", "sa-nobody-9999"], "note": ""}, writes the status and body to check-offer.txt and stops.
6. The harness holds a second scene (June 2026 with the clock moved, as the test suite does) only as a fallback. It did not run.

### Observed output and the invariant it proves

Executed locally once, on 2026-11-10 (check-offer.txt). The cover opened with 201 and its check listed only unit A's four nurses. The manager's own nurse list held unit A's four nurses and not 'Zeta Otherunit'; GET /api/units/{B}/covers answered 403. The offer answered HTTP 422 with two messages: 'Zeta Otherunit cannot take this cover now, so it cannot be offered to them.' and 'sa-nobody-9999 cannot take this cover now, so it cannot be offered to them.'. The full name of unit B's nurse was returned to unit A's manager in place of the ID sent, and the unknown ID was echoed, so the two cases can be told apart. No offer row was written, the cover stayed open and no cover.offered audit entry was made.

**Invariant:** A unit manager reads only the nurses of their own unit: docs/ARCHITECTURE.md line 101 gives a manager 'Read nurses' for their own unit only, and line 127 says a unit manager sees nothing of other units. The rest of the code keeps to this and treats another unit's nurse the same as no such nurse: the manager's nurse list is membership.on_the_list_of(unit) (backend/nurses/api.py:193-201), a pin edit says only the ID back (backend/rosters/editing.py:54-56), recording leave answers the same 403 whether another unit's nurse exists or not (backend/nurses/leave_api.py:210-215), and a swap echoes an ID that is not on the roster (backend/swaps/judging.py:100-102). No route was found that gives a manager the names of nurses who were never on their unit's list or rosters. A hospital ID that is not on the cover's roster should therefore be refused without being resolved to a name.

### Conditions and containment

- _authorization_role_: The caller is signed in as a Unit Manager who holds a unit.
- _data_state_: The manager's unit has a cover that is open or offered. A manager can open one by hand for any shift-day today or later of a month whose roster is approved (POST /api/units/{unit_id}/covers); the local run did so.
- _data_state_: The cover's roster can be checked and its shift-day is below its maximum headcount. Otherwise the offer answers 409 before the lookup (backend/covers/steps.py lines 91-93).
- _data_state_: The manager supplies hospital IDs that exist, in their exact case. They must be known or guessed, for example from a staff-number pattern, up to 500 in one request.

### Source-level remediation and regression case

Name a refused ID only when it is on the cover's own roster, whose people the manager already reads; say any other ID back as it was sent, as the swap check and the pin edit do. After the refusal every remaining ID is in the judged list, so the lookup for the offer rows then holds only this roster's nurses. Add a regression test that offers a cover to the hospital ID of a nurse placed in another unit and asserts that the 422 holds the ID and not that nurse's name. The code below replaces lines 94-100 of offer(); it was written from source and has not been run.

`backend/covers/steps.py`:

```python
    could = {nurse.hospital_id for nurse in judged.nurses}
    refused = [hospital_id for hospital_id in added if hospital_id not in could]
    if refused:
        # Only someone on this cover's roster is named, as a swap's check does (`swaps.judging`): any other ID is said back
        # as it was sent, the same for a nurse of another unit as for no such nurse (docs/ARCHITECTURE.md section 3).
        on_roster = {nurse.user.username: nurse.user for nurse in NurseProfile.objects.select_related("user")
                     .filter(user__username__in=[hospital_id for hospital_id in refused if hospital_id in cover.roster.grid])}
        refuse(*[(("nurses",), f"{name_of(on_roster[hospital_id]) if hospital_id in on_roster else hospital_id} cannot take "
                               "this cover now, so it cannot be offered to them.") for hospital_id in refused])
    nurses = {nurse.user.username: nurse
              for nurse in NurseProfile.objects.select_related("user").filter(user__username__in=added)}

```

## 3. The downloadable backup carries every live session, so its holder can act as any signed-in user

`backend/ops/backups.py:dump_database:live-session-rows-in-downloadable-backup` — severity **low**

### Ordered trace

1. **entrypoint** `backend/ops/api.py:150` (`update_technical_settings`) — The System Admin sets `backup_time` to a moment just past while the people of interest are signed in. Optional: without it the nightly backup holds whoever was signed in at that hour.
2. **propagation** `backend/ops/backups.py:94` (`is_due`) — A backup is due once the backup time has come round since the newest one, so the five-minute job (backend/ops/tasks.py:6-12) takes one within five minutes of the change.
3. **propagation** `backend/ops/backups.py:104` (`dump_database`) — pg_dump --format=custom of the whole database, no table or table data excluded: django_session goes in with every unexpired session key.
4. **sink** `backend/ops/api.py:121` (`download_backup`) — The finished dump is streamed to the System Admin as an attachment. Read with pg_restore on any machine, its session_key values are accepted as the `sessionid` cookie by backend/accounts/authz.py:22-30.

### Evidence

- `backend/ops/backups.py:104` — The pg_dump argv: format, connection and database name only; nothing narrows what is dumped. Re-executed in the sandbox against Postgres 18: dump_database wrote a 376 KB custom-format dump whose django_session row (session_key szf31322huqq5ehh06aixaouobpeb4qf) was recovered with `pg_restore --data-only -t django_session`.
- `backend/accounts/provisioning.py:190` — Sessions are rows of django.contrib.sessions' Session model: deactivating a user ends their sessions by reading and deleting those rows.
- `backend/config/settings.py:44` — django.contrib.sessions is installed and the file sets no SESSION_ENGINE, cache or signed-cookie backend, leaving Django's database-backed sessions; lines 97-98 keep a session alive for twelve idle hours, renewed on every request.
- `backend/accounts/authz.py:23` — A request is whoever its session says: `authenticate` takes `request.user` and checks only the forced password change and the role, with no binding to an address, a device or anything else a holder of the key would lack. The CSRF token is a cookie the client sets itself. Confirmed in the sandbox as far as `request.user`: a fresh CSRF-enforcing client carrying only the recovered session_key as `sessionid` was reported as the dummy nurse by GET /api/auth/session (200), a route open to anyone (auth=None, backend/accounts/api.py:96) that answers with `request.user`. A role-guarded route and an unsafe method were not run; that they accept the same key is read from this line.
- `backend/ops/api.py:114` — Backups are downloadable by the System Admin role; the audit entry (line 123) holds the actor, the file's name and, as every entry does, the client address (backend/audit/log.py:25-26).
- `backend/accounts/api.py:30` — The System Admin's managed accounts are the CNO, the Deputy CNO and unit managers, never a nurse; the audited route to one of them is reset_user_password at line 243.
- `docs/ARCHITECTURE.md:127` — 'The System Admin sees no roster and no rostering attribute.' Lines 72-74 make backups downloadable on their health page.
- `deploy/INSTALL.md:92` — What the operator is told a backup holds: password hashes and leave. Sessions are not mentioned, and line 98 shows the daily off-server copy.

### Dummy attacker and affected resource

A System Admin signed in to the application, or a person holding a recent off-server copy of a backup.

Full use of another user's signed-in session, the CNO's included, with every audited action entered under that user's name and nothing shown to them; only the client address on the entry, which the System Admin alone reads, is the replayer's. The same actor can already reach the data in the dump and can already take a managed account by an audited reset, so the gain is acting under another's name with next to no trace, and as nurses, not new data.

### Native input and bounded instructions

Input:

```
pg_dump --format=custom --no-password --host <HOST> --port <PORT> --username <USER> --dbname <NAME>   (the argv at backend/ops/backups.py:104-105; no --exclude-table-data)
```
```
pg_restore --data-only -t django_session -f - <backup>.dump   (recovers each live session_key from the dump)
```

Instructions:

1. In the DB sandbox (config.test_settings, throwaway Postgres 18), harness-session-in-backup.py signed a dummy staff nurse in with django.test.Client, keeping session_key szf31322huqq5ehh06aixaouobpeb4qf.
2. It then called the project's own ops.backups.dump_database into /scratch: a 376657-byte custom-format dump, the same call the nightly worker job runs.
3. pg_restore --data-only -t django_session on that dump returned exit 0 and the dummy nurse's session_key appeared verbatim in the restored rows: the live key is recoverable from the backup.
4. A fresh django.test.Client with enforce_csrf_checks=True, carrying only that recovered key as the `sessionid` cookie, received 200 from GET /api/auth/session identifying the user as 'dummynurse'. That route is open to anyone (auth=None, backend/accounts/api.py:96) and answers with `request.user`; a role-guarded route and an unsafe method were not run. authz.py reads the same `request.user` and binds the request to nothing but the session key, so by source the same holds for any role (CNO included).

### Observed output and the invariant it proves

Demonstrated end to end in the sandbox, not inferred: ops.backups.dump_database (pg_dump, no --exclude-table-data) wrote the django_session rows into the dump; `pg_restore --data-only -t django_session` recovered a signed-in user's live session_key from that dump; and that key, presented as the `sessionid` cookie to a fresh CSRF-enforcing test client, authenticated the request as that user (GET /api/auth/session -> 200, username 'dummynurse'). No deployment was contacted and no real session was used; the dummy principal, dump and replay were all created in the throwaway database.

**Invariant:** A backup should hold what a restore needs and no credential that works as it stands. The System Admin manages accounts and operations and 'sees no roster' (docs/ARCHITECTURE.md:127, GLOSSARY.md:63); taking over a managed account is meant to go through the audited password reset, and nurses' accounts are not theirs to manage (backend/accounts/api.py:29-30).

### Conditions and containment

- _authorization_role_: The actor is the System Admin (or has their session), or holds a copy of a backup taken off the server.
- _timing_dependency_: The victim was signed in when the backup was taken and their session has not since ended: twelve hours without a request, a logout, a password change or a deactivation ends it; the key must still be a live row on the running server when it is replayed.

### Source-level remediation and regression case

Leave the session rows out of the dump: add `--exclude-table-data=django_session` to the pg_dump argv, so the table is restored empty and a restore signs everyone out, which is what a restore should do anyway. Add a test that the argv carries it, and say in deploy/INSTALL.md what a backup still holds (password hashes, the push key, every nurse's data).

`backend/ops/backups.py`:

```python
    # Sessions are working logins and no part of the record: a restore signs everyone out.
    command = ["pg_dump", "--format=custom", "--no-password", "--exclude-table-data=django_session",
               "--host", database["HOST"], "--port", str(database["PORT"]),
               "--username", database["USER"], "--dbname", database["NAME"]]

```

## 4. A staff nurse who proposes and withdraws the same swap 25 times pushes a named colleague's earlier notices out of the only list that shows them (the unit manager's branch was observed for one round)

`backend/swaps/steps.py:propose:no-bound-on-propose-withdraw-rounds-notifying-chosen-recipients` — severity **low**

### Ordered trace

1. **entrypoint** `backend/swaps/mine_api.py:211` (`propose_swap`) — POST /api/swaps/mine, any staff nurse (`nurse_only`). Each of the body's 1 to 62 cells names a hospital ID, so the body chooses which colleagues are in the swap; with only her own cells the unit's manager is told instead.
2. **propagation** `backend/swaps/steps.py:64` (`propose`) — Checks placement, month not over, approved roster, one own cell, then `judge` (lines 72-85). Nothing counts this proposer's earlier swaps. Writes the swap, its cells and participants and the audit entry, then calls `sending.swap_step` with `proposed`, or `awaiting` when no colleague is named (lines 99-104).
3. **propagation** `backend/swaps/judging.py:88` (`SwapMonth.__init__`) — The only rule about other swaps: cells of swaps in a WAITING state are collected here and refused at line 140. A withdrawn swap's cells are not read, so they are free again in the next request. Observed: 422 while the first swap waited, 201 after its withdrawal, 25 times.
4. **propagation** `backend/notifications/sending.py:132` (`swap_step`) — Recipients by step: the named colleagues at `proposed`; the manager at `awaiting`; at `withdrawn` the colleagues, and the manager when the swap awaited her. Never whoever took the step.
5. **propagation** `backend/notifications/sending.py:25` (`notify`) — One new Notification row for each active recipient (`bulk_create`, line 36), never merged with an earlier one.
6. **propagation** `backend/swaps/mine_api.py:222` (`withdraw_swap`) — POST /api/swaps/mine/{swap_id}/withdraw by the proposer: `steps.withdraw` (backend/swaps/steps.py:145-155) sets `withdrawn`, writes the second audit entry and tells the same recipients a second time. The round can start again with the same body.
7. **sink** `backend/notifications/api.py:70` (`list_notifications`) — The recipient's only read of her notifications: the newest 50 (`SHOWN`), no paging. Observed: after 25 rounds the list held 50 swap notices from one sender and the recipient's earlier unread notice was no longer in it, while `unread` said 51.

### Evidence

- `backend/swaps/steps.py:81` — The proposal's own refusals end here and at `judge` (lines 83-85); none is about how many swaps the proposer has made or ended.
- `backend/swaps/steps.py:151` — A withdrawal moves the swap to `withdrawn`; `Swap.waiting` (backend/swaps/models.py:58-60) is then false and its cells no longer block a new proposal.
- `backend/swaps/judging.py:140` — The per-cell rule, applied to waiting swaps only: the strongest control on repetition in the path. Observed as the 422 "Your cell on 9 June 2026 is already in another swap." while the first swap waited.
- `backend/notifications/sending.py:141` — `proposed` goes to the colleagues the body named; lines 143-144 send `accepted` to the proposer alone; lines 145-146 send `awaiting` to the manager; line 148 sends a rejection, a withdrawal, an expiry and an approval to the proposer, the colleagues and, when it awaited her, the manager; line 149 leaves out whoever took the step.
- `backend/notifications/sending.py:36` — `Notification.objects.bulk_create(rows)`: one row a recipient a step.
- `backend/notifications/api.py:21` — SHOWN = 50, used at line 70 as the slice of the only list a reader has. The router's other routes are the unread count (line 62), mark one read by id (line 81) and mark all read (line 91); none takes a page or an older-than marker, and none removes a row.
- `backend/notifications/api.py:59` — The unread count is taken over every row of the reader, so it keeps counting notices the list no longer shows (observed: 51 unread, 50 listed).
- `backend/notifications/models.py:50` — The list's order is newest first by creation time alone; an unread row is not kept ahead of newer read or unread ones.
- `backend/notifications/tasks.py:15` — The only removal of notifications: those older than 365 days. A displaced notice stays in the table until then but is never listed again, since only newer rows are added above it.
- `frontend/src/routes/_signed-in/notifications.tsx:87` — The Notifications page asks for the list with no argument and renders `items` as returned; it has no "older" control.
- `backend/swaps/mine_api.py:116` — My swaps returns every swap the nurse proposed or is named in, every state, unpaged (observed: 25 withdrawn rows for the colleague after 25 rounds).
- `backend/swaps/tests/test_swaps.py:454` — The project's own test of one round's end: the colleague's last step is `withdrawn` and the manager holds `awaiting` then `withdrawn`. Lines 671-674 propose the same cells again right after a withdrawal and expect it accepted, so one re-proposal after a withdrawal is tested, intended behaviour; no test repeats propose-and-withdraw rounds or fills a recipient's list past 50.
- `backend/config/settings.py:62` — The middleware list holds no throttle, and a search of the tracked files for throttle, rate limit and cool-down finds none in the application or in deploy/Caddyfile, which apart from TLS and a 404 for /metrics is a bare `reverse_proxy web:8000`.
- `backend/nurses/api.py:273` — The one way a staff nurse's account is ended: the CNO sets her end date (`auth=cno`), which deactivates her at line 302 and ends her sessions (backend/accounts/provisioning.py:109-122). The System Admin's deactivation route takes only the CNO, Deputy CNO and Unit Manager roles (backend/accounts/api.py:200). A staff-nurse recipient has no stop of her own.
- `backend/nurses/api.py:383` — A lever a unit manager holds over the sender, from source only and not exercised in this run: a Unit Manager, for a staff nurse of her unit this month (line 398), or the CNO can reset a staff nurse's password. `reset_password` (backend/accounts/provisioning.py:162-184) sets a new generated password that only the caller is shown and forces a change; by its own description the new hash ends her sessions, which the project's test asserts for the same function (backend/accounts/tests/test_users.py:285). It interrupts the sender's account while the password is withheld; it is not a limit on swaps and it restores no displaced notice.

### Dummy attacker and affected resource

A signed-in Staff Nurse using only her own session and the two swap routes the Swaps page uses.

One recipient at a time loses sight of her earlier notices on the Notifications page, with no way to bring them back. A staff-nurse recipient cannot stop the sender herself. From source, not exercised: a Unit Manager, for a staff nurse who belongs this month to the unit she holds, or the CNO can interrupt the sender by resetting her password (backend/nurses/api.py:383-404), which ends her sessions and keeps her out until the new password is handed to her; and the CNO alone can end her account by setting her end date to today or earlier (backend/nurses/api.py:273-302), which ends her sessions and stops her rounds for as long as that date stands. Neither is a limit on the swaps of a nurse who is signed in, and neither restores a displaced notice. No data is disclosed, changed or deleted: the rows stay in the table, the pages the notices pointed to still show the facts, and the bell still counts them. The reach to many colleagues in one body, repeated phone alerts and any load effect were not demonstrated.

### Native input and bounded instructions

Input:

```
POST /api/swaps/mine {"month": "2026-06", "cells": [{"hospital_id": "Badr", "date": "2026-06-09", "shift": null}, {"hospital_id": "Emad", "date": "2026-06-09", "shift": "D"}], "note": ""}
```
```
POST /api/swaps/mine/{swap_id}/withdraw {}
```
```
POST /api/swaps/mine {"month": "2026-06", "cells": [{"hospital_id": "Badr", "date": "2026-06-19", "shift": null}], "note": ""}
```

Instructions:

1. In the database sandbox only (throwaway PostgreSQL 18, no egress, `config.test_settings`): run `tools/sandbox-db-run.sh v16-p3 harness-swap-rounds-v.py`. It builds the solver's four-nurse sample as unit ER with a dummy manager, June 2026 approved as the project's sound roster, and moves the hospital's clock in the process to 2026-05-15 as the project's tests do, because the fixture month is June 2026. The push service is a stub that raises and no worker runs.
2. The application's own sender writes one earlier notice for the colleague and the manager (`notifications.sending.roster_approved`).
3. Signed in as the dummy nurse Badr with CSRF enforced, send the first payload, then the second with the returned id; repeat 25 times, stopping at the first answer that is not 201 then 200. In round 1 also send the first payload once more while the swap waits.
4. Signed in as the dummy colleague Emad, GET /api/notifications after round 24 and after round 25, GET /api/notifications/unread, then POST /api/notifications/{earlier notice id}/read.
5. For the manager's branch, once: place 48 fixture rows in the manager's list, send the third payload as Badr and withdraw it, and GET /api/notifications as the manager before and after.

### Observed output and the invariant it proves

Run once; output in check-swap-rounds-v.txt. All 25 rounds on the same cells answered 201 then 200; the same cells while the first swap waited answered 422. Emad was told `proposed`, `withdrawn` alternately, 50 times; Badr and the manager were told nothing by these rounds. After round 24 Emad's list: items=49, unread=49, the earlier roster-approved notice listed and unread. After round 25: items=50, all `swap_step` with two distinct texts naming Badr, the earlier notice not listed, unread=51 (the unread route agreed), and the earlier row still in the table unread. Marking it read by id answered 204; the list still did not show it and unread fell to 50. Emad's GET /api/swaps/mine returned 25 rows, all withdrawn. Rows: 25 swaps, 50 cells, 25 participants, 50 `swap.*` audit entries, all with Badr as actor. Manager's branch: the own-cell proposal answered 201 with state `awaiting_manager`, its withdrawal 200, the manager was told `awaiting` then `withdrawn`, and her list went from 49 items with her earlier notice listed to 50 items without it, unread=51. The whole run took 6.5 seconds. No bound appeared before the claimed count. Pushes, a second device alert and any load effect were not exercised.

**Invariant:** One user should not be able to decide what another user's notification list shows. Either repeated propose-and-withdraw rounds by one nurse are limited or collapsed so they cannot fill a recipient's list, or a reader can still reach every notice she has not read, however many newer ones arrive.

### Conditions and containment

- _authentication_level_: A signed-in session of the application; CSRF token sent as the SPA sends it.
- _authorization_role_: Staff Nurse, placed on a unit for the month of the swap.
- _data_state_: The unit's roster for this month or a later one is approved and has a date of today or later, and one change exists that the roster's rules accept: a cell of hers together with a cell of a staff-nurse colleague on the same roster (to reach that colleague), or a cell of her own alone (to reach the unit's manager).
- _data_state_: The effect on a recipient is the loss from view of notices older than the 50 newest; a recipient with fewer than 50 notices loses one earlier notice for each notice beyond the 50th.

### Source-level remediation and regression case

Fix both sides, since either alone leaves a gap. Sender's side: stop one proposer's rounds from writing an unbounded run of notices. The smallest change is to keep one notice per recipient per swap (at a withdrawal, update or remove the recipient's still-unread `proposed` or `awaiting` notice for that swap instead of adding a second row), together with a small cap on how many swaps one nurse may withdraw on one roster within a day, refused with a plain 409. The cap's number is a product decision. Reader's side: make every unread notice reachable whatever arrives after it, for example by letting GET /api/notifications take an older-than marker so the page can load more, or by listing unread rows first; and collapse consecutive notices about the same swap into one line. Add a test that runs two rounds on the same cells and one that fills a list past 50 and still finds the oldest unread notice.

## 5. A unit manager whose nurse profile has ended keeps reading that unit's rosters after losing the unit

`rosters.reading_api.in_force:ended-nurse-profile-keeps-unit-roster-read` — severity **low**

### Ordered trace

1. **entrypoint** `backend/rosters/reading_api.py:318` (`my_roster`) — GET /api/rosters/mine?month=YYYY-MM is open to the staff_nurse and unit_manager roles (nurse_reader, line 37) and takes the month from the caller. GET /api/rosters/mine/sheet (line 351) is the same.
2. **propagation** `backend/rosters/reading_api.py:300` (`in_force`) — The reader's unit for the month is the placement's unit. The only later conditions are that the month is not before the reader's first month and that the unit has an approved roster of it. Neither the profile's end date nor who manages the unit is read.
3. **propagation** `backend/nurses/membership.py:75` (`placement_in`) — Returns the latest placement whose from_month is on or before the month. An ended profile keeps its placement in force: cancel_transfers_after (line 270) deletes only placements still to come.
4. **sink** `backend/rosters/reading_api.py:334` (`my_roster`) — Every row of the version in force is returned: each nurse's hospital ID, full name and shift code for each day of the month. The reader not being on the grid only makes `mine` null.

### Evidence

- `backend/nurses/api.py:300` — set_end_date deactivates the account only when the user's role is staff_nurse; its docstring (lines 275-277) says a manager's account is the System Admin's, so their profile ends alone.
- `backend/nurses/tasks.py:11` — The hourly close_ended_nurses job deactivates only users with role staff_nurse whose end date has passed.
- `backend/accounts/authz.py:22` — SignedIn.authenticate checks the session, the forced password change and the role list, and nothing about a nurse profile's dates.
- `backend/units/api.py:130` — Reassigning a unit or taking its manager off sets Unit.manager and nothing else, so the former manager's nurse profile and its placement stay as they were.
- `backend/nurses/leave_api.py:399` — The docstring shows a manager holding no unit is meant to read their own nurse pages, so the gap is only the ignored end date, not the role.
- `backend/nurses/tests/test_managers.py:191` — The project's own test fixes that an end date on a manager's profile leaves the account active, so the starting state is a designed one and not a mistake of the harness.
- `backend/rosters/tests/test_review.py:712` — The only test of a manager reading My roster covers a manager with a running profile and one with no profile. None covers an ended profile, so no test states the observed read as intended.
- `docs/ARCHITECTURE.md:123` — States that a manager account with no unit assigned can log in but do nothing, and (line 127) that a unit manager sees nothing of other units.
- `GLOSSARY.md:27` — Defines the end date as the last day a nurse is part of her unit.

### Dummy attacker and affected resource

A signed-in Unit Manager account that holds no unit and whose own nurse profile ended before the month asked for, in the unit it used to manage.

Read-only disclosure of one unit's hospital IDs, names and shifts for later months, to a former manager and member of that unit who still has an active hospital account. No leave type, attribute or write is reachable; a colleague's leave reads as a day off.

### Native input and bounded instructions

Input:

```
GET /api/rosters/mine?month=2026-06
```
```
GET /api/rosters/mine/sheet?month=2026-06
```

Instructions:

1. Run harness-ended-manager.py in the database sandbox (throwaway PostgreSQL 18, no network, config.test_settings). It builds the scene the way the project's tests do (solves/tests/conftest.py, rosters/tests/test_review.py): the four-nurse sample unit, the scripted solver in place of the solver service, and the hospital's today moved to 2026-05-15.
2. As the CNO: POST /api/units creates ER with manager mona (201); POST /api/nurses/managers gives mona a nurse profile in ER (201); PUT /api/nurses/<mona>/end-date sets 2026-05-10, a day already past (200, is_active stays true); PUT /api/units/<ER> gives the unit to manager omar (200).
3. As mona, controls: GET /api/units answers an empty list and GET /api/units/<ER>/roster?month=2026-06 answers 403 "This is not your unit."; GET /api/rosters/mine?month=2026-06 already names the unit ER, with no roster yet.
4. As omar: POST /api/units/<ER>/solves for 2026-06 (201), the solve run with the scripted result, POST roster/submit (200). As the CNO: POST roster/approve (200).
5. As mona: GET /api/rosters/mine?month=2026-06 and GET /api/rosters/mine/sheet?month=2026-06, and read the status and body.
6. Contrast: the CNO sets the same end date on staff nurse Emad of the same unit, and Emad repeats her GET /api/rosters/mine with the session that answered 200 a moment before.

### Observed output and the invariant it proves

Observed locally in one sandbox run (check-ended-manager.txt). With mona an active unit_manager holding no unit, her profile ended 2026-05-10 and still placed in ER, GET /api/rosters/mine?month=2026-06 answered 200 with unit "ER", version 1, `mine` null and four rows giving the hospital ID, full name and daily shift codes of Amal, Badr, Dana and Emad. GET /api/rosters/mine/sheet?month=2026-06 answered 200 with a sheet. Her manager pages refused her in the same state (empty GET /api/units, 403 on the unit's roster). The same end date on staff nurse Emad set is_active false and her GET /api/rosters/mine went from 200 to 401. Only that one month was requested; no later month, and neither the no-successor nor the deactivate-then-reactivate route, was run.

**Invariant:** The end date is the last day a nurse is part of her unit (GLOSSARY.md:27), a unit manager sees nothing of other units and a manager account with no unit assigned can log in but do nothing (docs/ARCHITECTURE.md:123-127). A profile whose end date is before a month begins should give its holder no roster of that month, as a staff nurse's deactivation already does. No document or test says an ended manager profile should keep the read.

### Conditions and containment

- _authorization_role_: The reader is an active Unit Manager account that has a nurse profile.
- _data_state_: The CNO has set an end date on that profile that has passed, and the manager no longer holds the unit (in the run, the CNO gave it to another manager). The profile has not been transferred to another unit, and the System Admin has not deactivated the account.
- _data_state_: The unit has an approved roster for the month asked for, which is this month or a later one.

### Source-level remediation and regression case

Make the nurse reader's unit depend on the profile's dates as well as its placement: in rosters.reading_api.in_force, give no unit for a month that begins after the profile's end date, keeping the month the end date falls in and earlier months readable as they are now. My roster, its sheet and My month all go through in_force, so one change covers them. in_force has two more callers, both open to staff nurses only: the swap composer (backend/swaps/mine_api.py:148) and what the roster kept of a nurse's preferences (backend/requesting/preferences_api.py:73). Both already answer for a month with no unit or no version in force (the composer says the reader is on no unit's roster, the other returns none), so they need no change, but the new condition applies there too, and to a staff nurse whose end date is still to come: while the account is active, a month that begins after that end date will no longer be read or offered for a swap. Update the `unit` field descriptions of MyRosterMonth, MyRosterSheet and MyMonth to say it is also null after an end date. Add a regression test in backend/rosters/tests that a manager with an ended profile and no unit gets `unit: null, roster: null` for a later approved month, and that a manager with a running profile and no unit still reads theirs. The change below was not run.

`backend/rosters/reading_api.py`:

```python
def in_force(user: User, chosen: str | None) -> MonthInForce:
    """The unit is the one the month falls under for them, so across a transfer each month shows its own unit's roster, and a
    nurse due to start sees their unit's with no row of their own. A month before this one only once it has closed. A month that
    begins after their end date falls under no unit: the end date is the last day they are part of it, whatever their role."""
    month = dt.date.fromisoformat(f"{chosen}-01") if chosen else membership.this_month()
    nurse = NurseProfile.objects.filter(user=user).select_related("user").first()
    placement = membership.placement_in(nurse, month) if nurse else None
    if nurse is not None and nurse.end_date is not None and nurse.end_date < month:
        placement = None
    found = MonthInForce(month=month, first=_first_month(nurse), nurse=nurse, unit=placement.unit if placement else None)
    if found.unit is None or month < found.first:
        return found
    found.roster = Roster.objects.filter(unit=found.unit, month=month, state=RosterState.APPROVED).first()
    if found.roster is None:
        return found
    if month < membership.this_month():
        found.close = MonthClose.objects.filter(unit=found.unit, month=month).first()
        if found.close is None:
            found.roster = None
            return found
        found.version = found.roster.versions.get(number=found.close.version)
        return found
    found.version = found.roster.versions.first()  # The latest, by `RosterVersion.Meta.ordering`: the one in force.
    return found

```
