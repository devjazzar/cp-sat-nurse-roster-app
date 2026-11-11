# 67: Ten devices a user, and a push job that hands on after 30 seconds

**What to build:** A user holds at most ten push subscriptions: turning pushes on for an eleventh device ends the user's earliest turned on, with no audit entry of its own, while a browser's renewal adds and ends none and an address moving from another user counts. A push job starts no new send once it has run 30 seconds and hands the sends it has not made to a new push job at the normal priority, with the same try number, behind any push already waiting; nothing is dropped, and tries again work as today. A push `auth` key longer than the model's column is refused with 422 at turn-on, and `pushing.send` never raises: an exception the library raises that is not already sorted is a refusal. Spec: `.scratch/nurse-rostering-v2/specs/hardening.md` (Push subscriptions and the push job); ADR 0012, ADR 0009; the words: `GLOSSARY.md` (Push subscription, Push).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `subscriptions.turn_on`, under the user's row lock, ends the earliest subscriptions by `turned_on_at` until the user holds ten, after a new address or one moving from another user; a renewal (`replaces`) ends none; no audit entry for the ended one
- [ ] `pushes.deliver` takes the job's start and a 30-second budget on a clock the tests can move, and returns the sends it did not make beside those to try again
- [ ] The push job defers the sends handed on as a new push job at normal priority and the same try number; a try again stays at priority −1
- [ ] A test: a job past its budget makes no more sends; the next job makes them as first tries, after a push already waiting; every send is made once
- [ ] The API's `auth` key limit matches the column; a longer key is 422, not a database error
- [ ] A library exception of an unforeseen kind in `pushing.send` is `refused`, and the job goes on to the next send
- [ ] `docs/ARCHITECTURE.md` section 7's `push` paragraph gains the cap and the budget; ADR 0012 gains a consequence line for the eleventh device
- [ ] `docs/security/2026-11-11-security-audit.md`: lead 4 and the push hardening notes marked fixed, with this ticket's commits
- [ ] Tests at the agreed seams: the backend API suite (`notifications/tests/test_pushes.py` with its scripted push service); the usual full suites and both workflows

## Comments
