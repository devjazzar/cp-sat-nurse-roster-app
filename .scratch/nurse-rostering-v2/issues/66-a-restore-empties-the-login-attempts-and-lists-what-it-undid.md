# 66: A restore empties the login attempts and lists what it undid

**What to build:** `deploy/restore.sh` brings back no lockout or throttle, and tells whoever restores which account changes it undid. Once the backup is restored into the new database and before the swap, it empties the login attempts and the throttle's addresses there; a table a backup from before ticket 63 does not have is skipped, and `web` creates it empty when it migrates. After the swap and before the replaced database is dropped, it prints every `user.deactivated`, `user.password_reset`, `auth.password_changed` and `push.keys_rotated` entry of the replaced database whose time is after the restored database's newest audit entry: its action, its account and its time on the hospital's clock, nothing else, then one line saying to do them again, or one line saying none were recorded. It re-applies nothing. A failure to print does not stop the restore. Spec: `.scratch/nurse-rostering-v2/specs/hardening.md` (Restore); the words: `GLOSSARY.md` (Restore, Backup).

**Blocked by:** 63 The throttle on failed logins from one address

**Status:** ready-for-agent

- [ ] The emptying runs in the new database before the swap, so a failure there is the script's ordinary "the restore did not finish, the database is as it was"
- [ ] A backup without the throttle's table restores and starts as before
- [ ] The list compares by time, not id, so restoring the "before" backup to undo a restore still lists what was done in between (a test of that case)
- [ ] The list names the action, the account and the time, and nothing else; an empty list says so
- [ ] The restore completes and the application starts if the list cannot be printed
- [ ] `deploy/INSTALL.md`'s restore section and `docs/ARCHITECTURE.md` section 2's restore line say what a restore empties and prints
- [ ] `docs/security/2026-11-11-security-audit.md`: the restore note of section 4 marked fixed, with this ticket's commits
- [ ] Tests at the agreed seams: the restore check of `deploy/tests/operations.sh` also finds the login attempts emptied and the list printed for a deactivation, a reset, a change and a key rotation written after the backup; both workflows

## Comments

**From ticket 63 (2026-11-11).** The throttle keeps a second table of login attempts, `accounts_addressfailures` (one row per
client address and its window). A restore brings back the backup's moment of it too; whether "the login attempts" emptied
here include it is this ticket's to say (an emptied one only gives every address a fresh budget).
