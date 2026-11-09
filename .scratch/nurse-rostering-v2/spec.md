# Nurse rostering web application, v2: seven features

Status: ready-for-agent
Type: enhancement
Published: 2026-11-07, from seven grillings run in parallel (prompts: `grilling-prompts.md`)

v1 (tickets 01–25, `.scratch/nurse-rostering-v1/`) is on `main`. v2 is seven features chosen on 2026-11-07 after a look at
what the app has, what the vendored solver supports but the app never fed it, and what Timefold, UKG, Allocate and QGenda
sell. Each feature was grilled against `docs/ARCHITECTURE.md`, `GLOSSARY.md` and `docs/adr/` in a session of its own, and
has its own spec under `specs/` and its tickets under `issues/`, numbered on from v1. Where a spec and those documents
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

## The order to build in

The order the features were proposed in, by value: cover first (the most-used thing in nurse scheduling apps is picking up
an open shift), then preferences (the solver already prices them), then skills (the largest; touches the solver, ADR 0010),
then the Day view, Web Push, the comparison, and the calendar. Full runs, the overtime share and probation, added after the seven, join the end of the queue in that order. Tickets with no blocker from different features can run at the
same time in their own sessions; two tickets of one feature go in order.

## How a ticket is built

`docs/guides/local-development.md`: one session per ticket in its own worktree, the checks on a clean copy, a fast-forward
of `main`, the user's review recorded on the ticket.
