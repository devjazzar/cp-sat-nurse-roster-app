# 66: A restore empties the login attempts and lists what it undid

**What to build:** `deploy/restore.sh` brings back no lockout or throttle, and tells whoever restores which account changes it undid. Once the backup is restored into the new database and before the swap, it empties the login attempts and the throttle's addresses there; a table a backup from before ticket 63 does not have is skipped, and `web` creates it empty when it migrates. After the swap and before the replaced database is dropped, it prints every `user.deactivated`, `user.password_reset`, `auth.password_changed` and `push.keys_rotated` entry of the replaced database whose time is after the restored database's newest audit entry: its action, its account and its time on the hospital's clock, nothing else, then one line saying to do them again, or one line saying none were recorded. It re-applies nothing. A failure to print does not stop the restore. Spec: `.scratch/nurse-rostering-v2/specs/hardening.md` (Restore); the words: `GLOSSARY.md` (Restore, Backup).

**Blocked by:** 63 The throttle on failed logins from one address

**Status:** ready-for-agent

- [x] The emptying runs in the new database before the swap, so a failure there is the script's ordinary "the restore did not finish, the database is as it was"
- [x] A backup without the throttle's table restores and starts as before
- [x] The list compares by time, not id, so restoring the "before" backup to undo a restore still lists what was done in between (a test of that case)
- [x] The list names the action, the account and the time, and nothing else; an empty list says so
- [x] The restore completes and the application starts if the list cannot be printed
- [x] `deploy/INSTALL.md`'s restore section and `docs/ARCHITECTURE.md` section 2's restore line say what a restore empties and prints
- [x] `docs/security/2026-11-11-security-audit.md`: the restore note of section 4 marked fixed, with this ticket's commits
- [x] Tests at the agreed seams: the restore check of `deploy/tests/operations.sh` also finds the login attempts emptied and the list printed for a deactivation, a reset, a change and a key rotation written after the backup; both workflows

## Comments

**From ticket 63 (2026-11-11).** The throttle keeps a second table of login attempts, `accounts_addressfailures` (one row per
client address and its window). A restore brings back the backup's moment of it too; whether "the login attempts" emptied
here include it is this ticket's to say (an emptied one only gives every address a fresh budget).

**Implemented on 2026-11-11,** on branch `claude/ticket-66-restore-clears-0cd300` (`d867d32`, `a851c33`, `74dc476`, then
this comment and the audit document, and `origin/main` with ticket 64 merged in), from `main` at `e2ae502`. Draft pull request
[devjazzar/cp-sat-nurse-roster-app#12](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/12).

- `deploy/tests/operations.sh nr-t66`, run locally under the heavy-run lock:
  - red against the old `restore.sh` (it listed nothing);
  - then on `a851c33` it failed on a flaw in the test itself, described below;
  - green on `74dc476`, "All checks passed", with the stack removed.
- `shellcheck` (the `koalaman/shellcheck` image, with SC2015, the house's `A && B || C`, left out) is clean on both scripts.
- No Python, migration, API, frontend or Playwright file changed, so the backend `pytest` and `makemigrations --check` were
  not run.
- GitHub's two workflows ran on the pull request; `operations.sh` runs in the browser checks.

**What the dev stack needs:** nothing. `restore.sh` is read from `deploy/` when it is run. `deploy/Caddyfile`,
`deploy/compose.yaml` and the `Dockerfile` did not change.

**What was built, criterion by criterion.**
- **The emptying runs in the new database before the swap.**
  - Once `pg_restore` has filled `nurse_roster_restoring`, one `DO` block truncates `accounts_loginattempts` and
    `accounts_addressfailures` there.
  - It runs while the `EXIT` trap is armed and before the rename. A failure there is the script's ordinary "The restore did
    not finish. The database is as it was".
  - **"The login attempts" include the throttle's table.** The ticket's words are "the login attempts and the throttle's
    addresses", so both are emptied. An emptied `accounts_addressfailures` only gives every address a fresh budget.
- **A backup without the throttle's table restores and starts as before.**
  - Each table is truncated only if `to_regclass` finds it. `web` creates the missing one, empty, when it migrates.
  - The check fakes a backup from before ticket 63: it drops `accounts_addressfailures` and the `0003_address_failures` row
    of `django_migrations`, then takes a backup and restores it. A failed login afterwards answers 401 and the System Admin
    logs in. So the table exists and counts.
- **The list compares by time, not id.**
  - The newest audit entry of the restored database is `coalesce(max(at), '-infinity')`.
  - `nurse_roster_replaced` is then asked for the four actions with `at` later than that, ordered by `at, id`.
  - The check restores the backup the first restore took. It first asserts that the key rotation written in between has an
    id below the undone database's newest, so a list by id could not pass. That restore lists exactly that rotation.
- **The list names the action, the user and the time, and nothing else; an empty list says so.**
  - One line an entry: action, user (`-` when the entry names none) and time on the hospital's clock, to the minute.
  - Then "Recorded after the backup and undone by this restore: do these again by hand." With none, a single line: "No
    deactivation, password reset, password change or push key rotation was recorded after the backup."
  - It re-applies nothing.
- **The restore completes and the application starts if the list cannot be printed.**
  - `list_undone` reads everything before it prints anything. Each step returns on failure, and the call is
    `list_undone || echo "Could not list what the restore undid: the backup <before> holds the audit log as it stood." >&2`.
  - The check renames `audit_auditentry` in the live database just before a restore. The restore prints that line, exits
    0, the application answers, and the System Admin logs in.
- **`deploy/INSTALL.md` and `docs/ARCHITECTURE.md` section 2** say what a restore empties and prints. The install guide
  quotes the closing line and says the hourly job deactivates ended staff nurses again anyway.
- **The audit document:** section 4's restore note is marked fixed, with this ticket's commits.
- **Tests at the agreed seam.** `operations.sh`'s restore part now checks, after its own backup, each of the following:
  - The System Admin is locked out, and this address is one failure short of its throttle (49 of 50). The restore lists
    `user.password_reset admin`, `auth.password_changed admin`, `user.deactivated manager.after` and `push.keys_rotated -`,
    written after the backup, in that order. Each time falls within the hospital-clock minutes the test read around the
    writes (`TZ=$TIME_ZONE date`), not times recomputed with the script's own SQL.
  - Afterwards a failed login answers 401, then the System Admin's login 200. Had either table come back, that would be
    429 (the fiftieth failure throttles) or 423.
  - Restoring the before-backup lists by time; an empty list says so; the pre-63 backup restores; a list that cannot be
    read stops nothing.

**What was driven, and how:** only `operations.sh` on its own stack, `nr-t66`, at port 18443. It made five real restores
through `restore.sh --yes`, by backup name, and every printed list is shown in its log. The dev stack was not touched.

**What was found, and fixed.** The test's first green attempt picked the wrong backup. It restored "the job's backup", which
turned out to be one the worker took at its first start, before the test wrote anything. `ops.tasks.backup` takes one only
when one is due, so the deferred job made none. The list then rightly included the test's own first password change. The
ticket's checks now take their own backup with `manage.py backup`, after the earlier restore checks, which are unchanged.
A comment there says why. **Finding for you, not fixed:** the existing check
"The backup job that was running as that backup was taken comes back as running" may not hold, for the same reason. The
job may not have been running in the first-start backup. `recover_lost_jobs` succeeds either way, so the check passes
without proving that case.

**What was NOT checked.**
- A mutation run with each `TRUNCATE` removed was not made. That the check would then fail (429 or 423) is reasoning from
  ticket 63's rules: fifty failures throttle, and a locked refusal counts. The lockout itself was seen (423) before the
  backup. The 49 was counted, not read.
- A real backup file from before ticket 63; one was faked as above.
- A `TIME_ZONE` other than the default `Asia/Riyadh`, and a restore from a file path rather than a backup's name. Both go
  through the same code.
- Stopping the script while it lists.

**Decisions taken here.**
- The hospital's clock is the database container's `TZ`, which `deploy/compose.yaml` sets from `TIME_ZONE`, as it sets
  Django's `TIME_ZONE`. It is read with `printenv` and used as `AT TIME ZONE`. The server's `timezone` setting is not
  used, since `initdb` fixes it at the first start.
- The traps now stay armed until the replaced database is dropped. A Ctrl-C while the list prints still starts `web` and
  `worker` again; it leaves `nurse_roster_replaced`, which the next run refuses to pass, as before.
- A progress line, "Listing what the restore undid…", comes before the list, in the style of the script's other steps.
  This is so the entries do not appear to be part of "Putting it in the old one's place…".

**Worth your review.**
- **The words the script prints.** The closing line, the line for none, and the line for a list that could not be
  printed. The spec says only "one line saying to do them again".
- **`push.keys_rotated` lists `-` as its user.** The rotation names no user (it is the installation's key pair), so the
  user column has nothing to show.
- **Time to the minute, without the zone's name.** The spec says "on the hospital's clock" and nothing more.
- **Only the four actions are listed.** For example, a reactivation, a role or unit change, a name correction or a push
  subscription ended after the backup are not listed. That is the spec as written.

**Review.**
- `code-review` against `e2ae502`.
- The **standards** axis found:
  - the expected list recomputed with the script's own SQL (local-development.md 5.2, "Seams first"). Fixed: the
    expected times are now a clock of the test's own;
  - "account" and "lock" where the glossary says user and lockout. Fixed;
  - the CSRF read repeated, and names like `undo`, `older`, `first`. Fixed;
  - `fail` messages that logged in again to build themselves. Fixed: they now print the codes already taken;
  - the traps cleared before the list. Fixed;
  - `psql_db` reading oddly beside `psql_in`. Kept, since it is the old name for psql in the `postgres` database.
- The **spec** axis found nothing missing and no scope creep. It confirmed the emptying sits on the ordinary failure path,
  that the list goes by time, and that a failure to print stops nothing. It raised the same trap window and the circular
  expected value, both fixed. It also noted that an `echo` that itself fails would end the script. That was not changed:
  it is an `echo` to stderr.

**Things later tickets should know.**
- **Ticket 69** (the client address): the restore check counts on this address having exactly 49 failed logins in its
  window when the backup is taken. A check added before it that fails a login from the same address shifts the count;
  recount. Nothing here reads `audit.log.client_ip` or `REMOTE_ADDR`.
- **A later `accounts` migration** (ticket 64 merged in here without one): the check fakes a pre-63 backup by deleting the
  migration row `0003_address_failures`. A migration after it must have its row deleted too (and what it did undone), or
  `migrate` meets an inconsistent history.
- `restore.sh`'s `list_undone` holds the four actions in its SQL. A new action that a restore undoes and someone must
  redo belongs there and in `deploy/INSTALL.md`.

**Reviewed by the user (2026-11-11):** all four points kept as built.
- The closing, "none recorded" and "could not list" lines stay as written.
- `push.keys_rotated` shows `-` as its user.
- Times are to the minute, without the time zone's name.
- Only the four actions the spec names are listed; reactivations and role changes are not.

Noted, left for later: the restore check "the backup job that was running comes back as running" probably never exercises that case, because the worker takes a backup at first start and the job takes one only when one is due.
