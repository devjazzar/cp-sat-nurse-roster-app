# Nurse rostering web application, v2: twelve features

Status: ready-for-agent
Type: enhancement
Published: 2026-11-07, from seven grillings run in parallel (prompts: `grilling-prompts.md`)

v1 (tickets 01–25, `.scratch/nurse-rostering-v1/`) is on `main`. v2 began as seven features chosen on 2026-11-07 after a look at
what the app has, what the vendored solver supports but the app never fed it, and what Timefold, UKG, Allocate and QGenda
sell. Each feature was grilled against `docs/ARCHITECTURE.md`, `GLOSSARY.md` and `docs/adr/` in a session of its own, and
has its own spec under `specs/` and its tickets under `issues/`, numbered on from v1. Four more were grilled and added
on 2026-11-08 and 2026-11-09 (rows 8 to 11), one on 2026-11-11 from the security audit (row 12), and ticket 57 came out of the review of ticket 39. Where a spec and those documents
disagree, the documents win.

| # | Feature | Spec | Tickets | Decisions recorded |
|---|---|---|---|---|
| 1 | Cover for a sick call | `specs/cover.md` | 26, 27 | GLOSSARY: Cover; ADR 0011 |
| 2 | Preferences, a soft kind of request | `specs/preferences.md` | 28, 29, 30 | GLOSSARY: Preference, Kept; ADR 0013, ADR 0005 addendum |
| 3 | Skills and credentials per shift-day | `specs/skills-per-shift-day.md` | 31–38 | GLOSSARY: Skill, Expiry, Required to work, Skill need; ADR 0010 |
| 4 | The Day view across every unit | `specs/day-view.md` | 39 | GLOSSARY: Day view |
| 5 | Web Push for things with a deadline | `specs/web-push-for-deadlines.md` | 40, 41, 42 | GLOSSARY: Push subscription, Push; ADR 0012 |
| 6 | Compare two results of the same month | `specs/compare-two-results.md` | 43 | none |
| 7 | Ramadan and the Eids from the Umm al-Qura calendar | `specs/ramadan-and-eid-from-the-calendar.md` | 44, 45, 46 | none |
| 8 | Full runs: a priced cap per nurse a month (added 2026-11-08) | `specs/full-runs.md` | 47, 48 | GLOSSARY: Run, Full run |
| 9 | Overtime share: a unit's overtime spread fairly (added 2026-11-09) | `specs/overtime-share.md` | 49, 50, 51 | GLOSSARY: Overtime share |
| 10 | Probation: a newly hired nurse beside a preceptor, counted toward nothing (added 2026-11-09) | `specs/probation.md` | 52–56 | GLOSSARY: Probation, Nurse on probation, Preceptor; ADR 0014 |
| 11 | Certificates and licences: kinds of skill, with an identifier and an issue date (added 2026-11-09) | `specs/certificates-and-licences.md` | 58–61 | GLOSSARY: Skill (widened), Certificate, Licence, Identifier; the Deputy CNO records |
| 12 | Hardening against one client's load: a throttle on failed logins, Caddy holding the body, threaded workers, ten devices a user, HSTS and a content security policy, what a restore clears and lists (the security audit's leads 1 to 4, added 2026-11-11) | `specs/hardening.md` | 63–72 | GLOSSARY: Lockout, Throttle, Push subscription and Restore widened; ADR 0015 |
| — | A batched carry-over read, for speed (from the review of ticket 39, 2026-11-09) | none; the ticket is the spec | 57 | none |
| — | Audit follow-ups: no late approval, one solve a unit, no framing, no cross-site downloads (the user's decisions on the security audit, 2026-11-11) | none; the ticket is the spec, with `docs/security/2026-11-11-security-audit.md` | 62 | none |

## The ticket graph

Blocking edges are inside each feature only; the features are independent of one another, except that the Day view (39)
shows open covers if covers exist by then, and Web Push (40–42) pushes a cover offered if covers exist by then. Each ticket's
`**Blocked by:**` line is the rule.

- **Cover:** 26 → 27.
- **Preferences:** 28 and 29 side by side → 30.
- **Skills:** 31 and 32 side by side; 32 → 33 → 36, 37; 31 + 32 → 34; 31 + 33 + 34 → 35 → 38.
- **Day view:** 39.
- **Web Push:** 40 → 41 → 42.
- **Compare:** 43.
- **Ramadan:** 44 → 45; 46 beside them.
- **Full runs:** 47 → 48.
- **Overtime share:** 47 → 49 → 50 → 51 (49 after 47: both change the solver's input).
- **Probation:** 49 → 52; 33 → 53; 54 beside them; 52 + 53 + 54 → 55 → 56 (52 after 49: both change the solver's input).
- **A batched carry-over read:** 57, blocked by nothing.
- **Audit follow-ups:** 62, blocked by nothing.
- **Certificates and licences:** 53 → 58 → 59 → 60; 59 + 54 → 61 (58 after 53: both change the catalogue's API and page; 61 after 54: both put controls on the Rostering attributes row).
- **Hardening:** 63 → 64 → 65 (each changes the login's failure path); 63 → 66; 67 and 68 beside them; 62 + 63 → 69 → 70 → 71 → 72 (the Caddy chain: each edits the Caddyfile, `operations.sh` or the install guide; 69 and 72 after 62, which edits the Caddyfile; 69 after 63: it changes the address the throttle's tests send).

## The order to build in

The order the features were proposed in, by value: cover first (the most-used thing in nurse scheduling apps is picking up
an open shift), then preferences (the solver already prices them), then skills (the largest; touches the solver, ADR 0010),
then the Day view, Web Push, the comparison, and the calendar. Full runs, the overtime share, probation and certificates and licences, added after the seven, join the end of the queue in that order. Tickets with no blocker from different features can run at the
same time in their own sessions; two tickets of one feature go in order.

Tickets 57 and 62 have no blocker and no feature: each may run beside any of them.

Hardening (row 12), added on 2026-11-11 from the security audit, joins the queue; where it goes in the order is the user's
call. Within it, 63, 67 and 68 can start at once and side by side; the Caddy chain (69 to 72) waits for 62 and 63.

**On `main` (2026-11-12):** 26–50, 52–54, 58, 59 and 62–72, each with its session's comment and the user's review. **Still to build:**
51, 55–57, 60 and 61. Every ticket's `Status:` line says `ready-for-agent` whether built or not; the comments say which.

## How a ticket is built

`docs/guides/local-development.md`: one session per ticket in its own worktree, started with a brief and the user's pasted
`/implement-spec`; both GitHub workflows green on its pull request; the session fast-forwards `main` and reports; the main
session checks, refreshes the dev stack and records the user's review on the ticket.
