# 17: Re-plan from a date

**What to build:** Mid-month the unit manager chooses a date and re-plans: days before it are facts (the roster in force plus recorded leave and pins), the solver keeps the new roster close to the current one through the change weight, and the result is a new version in force with a comparison against the previous one and the recorded facts that broke rules shown as facts, not errors.

**Blocked by:** 16 Changes after approval

**Status:** ready-for-agent

- [x] Solve input assembler supports the published roster and the re-plan date; facts before the date are pinned from the roster in force, leave and pins
- [x] Re-plan solve runs through the same queue with progress and cancel; success creates a version with origin 're-plan'
- [x] Comparison view: cells changed, cost before and after, per-rule differences; elapsed violations listed as facts
- [x] API tests cover the assembler's fact pinning and the version created, with the fake and once with the real solver

## Comments

**From ticket 11 (2026-11-05).** `solves.input.assemble` has no re-plan yet. A month that has started can be solved from scratch today, which replaces the draft's whole grid: `_what_stops_it` refuses only a month that is over. Once a month has an approved roster a plain solve should be refused in favour of a re-plan.

**From ticket 12 (2026-11-05).** `rosters.drafts.why_not_restore` refuses a month that is over and allows the month under way, as `_what_stops_it` does for a solve. When this ticket refuses a plain solve once a month has an approved roster, restore needs the same refusal, which ticket 14's state check will already give. A result's `replan` block is not shown anywhere yet: `solves/history_api.py`'s `SolveResult` leaves it out, and section 8's "in a re-plan the comparison with the roster in force" is yours to add to `components/solve-result.tsx`.

**From ticket 14 (2026-11-05).** A submitted or approved month refuses a plain solve, its end on the grid and a restore, all through `rosters.drafts.why_frozen` (`solves.api._what_stops_it`, `solves.running._finish`, `drafts.why_not_restore`). A re-plan of an approved month has to pass that check on purpose and end in a new `RosterVersion` with origin `replan` (ticket 16), not through `drafts.replace_grid`, which refuses a frozen roster outright.

**From ticket 16 (2026-11-06).** Versions exist, and one function makes them.

- **Make the re-plan's version with `rosters.versions.make_version(roster, grid, VersionOrigin.REPLAN, by, reason, solve=solve)`**, holding the roster's row lock. It numbers it (latest + 1) and writes `Roster.grid` from it, so `Roster.grid` stays the latest version's grid under today's codes. Then `record("roster.changed", ...)` with the version and counts and no reason, and `notifications.sending.roster_changed(unit, month, by)`, as `rosters.api.save_version` does.
- **`rosters.drafts.why_frozen` still refuses an approved month's solve, `_finish` and a restore.** That is on purpose: your re-plan passes it deliberately. Its words for an approved roster now point the manager at editing cells by hand.
- **The comparison with the roster in force:** `rosters.versions.differences(before, after)` compares two grids cell by cell under today's codes, and `GET /units/{id}/roster/versions/compare` answers any two versions. The page's `components/roster-versions.tsx` already labels origin `replan` "Re-planned".
- **Facts before the date** include the manager's pins (origin `manager`, which every direct edit now makes) and leave. Leave recorded on a worked day of an approved roster already took the shift off as a version of its own (origin `edit`), with no pin: the leave is the fact.
- **Locks:** the nurses' locks are now `FOR NO KEY UPDATE` (`no_key=True`). A notification's foreign key to a colleague's user is checked at commit, and `FOR UPDATE` deadlocked a leave against an edit (`rosters/tests/test_two_at_once.py`). Keep any new nurse lock the same.


**Implemented on 2026-11-06,** on branch `claude/ticket-17-replan-b2d1df`. The backend ran under pytest on a throwaway PostgreSQL 18 container of my own, the frontend under Vitest with the real routes and generated client over a stubbed `fetch`.

- Results on the final code: backend 1854 passed, frontend 466 of 466, and `npm run build` clean.
- `makemigrations --check` is clean (one new migration, `solves.0002_replan`), and `frontend/openapi.json` is the same as a fresh export.
- **The frontend suite ran alone in this worktree, not in clean exports in parallel.** That is left to the session that brings this into `main`.
- The solver's suite was not run: nothing under `solver/` changed.

What was built:

- **`solves/replans.py`**, the re-plan's rules in one place: which months and dates may start one (`why_not`, `why_not_from`, `earliest`), and its end (`finish`).
- **The input:** `solves.input.assemble_replan(unit, month, replan_from, in_force)` is `assemble` plus `published` (the roster in force under today's codes, with exactly the month's nurses) and `replan_from`. The solver itself makes the earlier days facts (`Problem.replan_from`): a pin that counts, of any origin, wins; then leave and days outside a nurse's dates; then the roster in force. `recorded_cells_differ` is the solver's own count of past cells whose facts differ from the roster in force.
- **API:** `GET /units/{id}/replans/preview?month&replan_from` (`previewReplan`) and `POST /units/{id}/replans` (`startReplan`, body `month`, `replan_from`, `time_limit_seconds`, optional `reason`), the manager's only. Progress, stop and retry are the solve's own endpoints and job.
- **`Solve`** gains `replan_from`, `replan_of` (the version in force at the start), `replan_reason` and `replan_outcome` (`version`, `unchanged`, `outdated`, `month_over`). `SolveProgress` and the unit's history row show `replan_from` and `replan_outcome`; the System Admin's row does not (a test holds its closed list of fields).
- **The end** (`solves.running._finish` → `replans.finish`), under the catalogue's lock, the month's nurses' (`FOR NO KEY UPDATE`, `review.lock_the_months_nurses`), the unit's and the roster's, as an approval takes them:
  - no roster, or one with `ok` false: the roster in force stays; the manager is told "no roster to keep".
  - the month over meanwhile: nothing applied (`month_over`).
  - the version in force is no longer `replan_of`, or `changes_since` finds a change in the month's nurses, leave or pins: nothing applied (`outdated`).
  - no cell changed: no version, no audit entry, no nurse told (`unchanged`).
  - otherwise `make_version(roster, grid, VersionOrigin.REPLAN, requested_by, reason, solve=solve)`, the roster's `solve` set to the re-plan (so the page's details and "clear gives the cell back to its solve" are the re-plan's), `roster.changed` `{"version", "pins": 0, "cells"}` with no reason, and `sending.roster_changed`.
- **The comparison** (`SolveResult.replan`, `solves/history_api.py`): from, the version it started from, the version it made, its outcome, each cell changed (`rosters.versions.differences` against the input's `published`), the cost of the roster in force and of the re-plan **both on the re-plan's own input** (`solver_service.grid.validate_grid`), and each soft rule before and after. Elapsed violations stay `elapsed_violations`, now titled on the page as facts, not errors.
- **Notifications:** `SolveOutcome` gains `replanned`, `stopped_replanned`, `replan_unchanged`, `replan_outdated`, `replan_month_over` (payload only, no migration), and a re-plan's `solve_ended` carries `replan: true`, so its failure and "no roster" read as a re-plan's.
- **`FROZEN[APPROVED]`** now says "Re-plan it from a date, or change its cells by hand".
- **Pages:**
  - Roster page, approved month: a **"Re-plan from a date"** card with the date (min today or the month's first day, max its last), the time limit and an optional "Why". Each date asks the preview again; a date that cannot be one is said on the field and the button is disabled. It says what is kept as fact, how many cells before the date already differ from the version in force, and warns when the change weight is 0.
  - The progress card says "Re-planning November 2026 from 10 November", and its stop button "Stop and put the best roster in force".
  - Each end is said in the status line, and a re-plan that left the roster as it was says why where the last solve is shown.
  - While a re-plan runs, the editor says a change saved now makes the re-plan end without changing the roster in force.
  - `components/solve-result.tsx` has an **"Against the roster in force"** panel: what it kept, what it did, cost before and after, each rule before and after with the difference, and the cells it changed. It shows on the result page and under the roster in force, for the manager and the approvers.
  - The manager's history says "Re-plan from 12 June: made a new version", "…: not applied, the roster changed meanwhile", and so on.

Seams:
- `rosters/tests/test_replan.py` (52 tests, some parametrised): the API with the scripted solver and the real worker's code, on the real optimal roster of the four-nurse sample. The facts are read back through the solver's own loader (`load_request(...).problem`), not this code.
- `rosters/tests/test_two_at_once.py`: three new races on real connections, the order forced: the end waiting for leave on a day off (then `outdated`), leave waiting for the end (then the next version takes its shift off), and an edit waiting for the end (then builds on its version).
- `solves/tests/test_end_to_end.py`: a real solve, submit, approval, late leave on a worked day, then a re-plan from the 12th with the real solver: the days before it unchanged cell for cell, the version made with its reason, and the comparison read back.
- `accounts/tests/test_authorization.py` names the two new endpoints' roles.
- `app.test.tsx`: 10 new tests through `start`. No raised timeout, no fake timers, no wait that proves something did not happen.
- The backend tests for the start and for the comparison were written first and failed; the tests for the end were written right after its first code, so I broke each guard by hand (the version check, `changes_since`, "no cell changed") and saw a test fail for each. The version check needed a test of its own (`test_any_new_version_leaves_its_roster_out_even_with_no_pin_or_leave`), as every change today also changes a pin or leave. **Removing the nurses' lock at the end fails no test:** a leave write always takes the roster's row lock (`take_off_for_leave` selects it for update even on a day off), which already orders the two. The nurses' lock is kept as the approval's order, a second guard.

**Driven in the built-in browser,** on scratch project `nr-t17`:
- The setup: the production compose file with its own image (`nr-t17-app`), secrets and volumes; `web` published on `127.0.0.1:18017` under `DJANGO_DEBUG` and joined to the `public` network; no Caddy; the real solver and worker. The unit was the solver's four-nurse sample as ER, seeded by a shell script. Today was really 6 November, so **November was the month under way**.
- **As the manager:** a real solve (cost 116) and a submit. **As the CNO:** a real approval, to version 1.
- **As the manager, late leave:** Sick for Badr on 12 November, a night he worked: version 2, as ticket 16 built.
- **A real re-plan from 10 November**, 20 s, with the reason "Badr is off sick on the 12th; re-plan the rest of the month around it." The card offered 6 to 30 November and the button read "Re-plan from 10 November". It ended optimal at once: "The re-plan finished with a cost of 118, and its roster is now in force as a new version. The unit's nurses are told the roster has changed." Version 3 "Re-planned", 2 cells (Amal on Night on the 12th, off on the 22nd). The comparison read cost before 112, after 118, "Changes in a re-plan 0 → 6 (+6)", the other rules unchanged, and the two cells. Days 1 to 9 were untouched.
- **As Amal:** the bell read "Mona Ali changed the ER roster for November 2026." twice and the approval; the newest led to My roster, with her on Night on the 12th and off on the 22nd, and Badr's 12th "Off", not leave.
- **Stopping, and a change while one runs:** the sample is proven optimal in seconds, so I loosened its rules on my scratch database as `test_end_to_end.long_search` does, then set the change weight to 0 (the card then warned "The change weight is 0, so nothing keeps the re-plan close to version 5…"). Two more re-plans proved optimal before I could stop them (versions 4 and 5). Then:
  - A re-plan from 6 November, **stopped** with "Stop and put the best roster in force": "The re-plan stopped with a cost of 527, and its roster is now in force as a new version." Version 6.
  - Another, during which I **saved a hand edit** (Amal off on the 20th, "Amal asked for the 20th off.") as version 7, then stopped it: "The roster in force or the month changed while the re-plan ran, so its roster was not put in force: it would have undone that change. Re-plan again to take it in." Version 7 stayed in force. While it ran, the editor said "A re-plan of this month is under way…".
- **The history** read "Re-plan from 6 November: not applied, the roster changed meanwhile", "…: stopped, …", and so on, and the not-applied result's page explained itself against version 6.
- **The database then held:** `Roster.grid` equal to version 7 under today's codes; versions 3 to 6 with origin `replan`, the typed reason on 3 and "Re-planned from 14 November 2026." / "Re-planned from 6 November 2026." on the others; `roster.changed` `{"pins": 0, "cells": n, "version": n}` for each re-plan; every `roster_changed` payload only `unit_id`, `month` and `by`, to the four nurses; the manager's `solve_ended` outcomes `replanned`, `stopped_replanned` and `replan_outdated`.
- At 375 px, the roster page with the card and a re-plan's result page: no sideways page scroll.

That run found three things, all fixed with tests: the history said "in force" of re-plans a later version had replaced (now "made a new version"); the comparison's two tables had no visible heading; and an approved roster from a stopped re-plan said "You stopped this solve early". The code review found the result page saying "This result is the draft" of a re-plan (now "See the roster in force"); the scratch image was rebuilt with those fixes and that page checked again.

What was NOT checked:
- **A re-plan of a month not yet started, and the refusals of a draft, a submitted roster, a month over and a date over, in the browser.** API and Vitest tests only.
- **An approver reading a re-plan's comparison in the browser.** API test only (both approvers read it).
- **Leave or a pin recorded while a re-plan runs, in the browser.** API tests and races on real connections only; the browser drove a hand edit.
- **A unit that stopped working a shift the roster in force still holds before the date.** The solver's loader refuses such a `published` cell; the preview and the start would say so in the solver's words ("The solver refuses the month as it stands…"). Not driven and not tested.
- **The worker's retry of a re-plan** against a real solver. Scripted only.
- **Dark mode, 320 px, 200% zoom, a screen reader, browsers other than the built-in one, and through Caddy.**
- **A large unit.** The comparison costs the roster in force with the solver's code each time the result is read.

**Decisions taken here:**

- **Allowed dates:** today or later, within the month. Today is allowed: a nurse who calls in sick in the morning is re-planned around that day, and a pin keeps any shift of it already worked. The month's first day only while it is still to come (an approved December can be re-planned from 1 December). The first day after the month is month close (ticket 21's) and is refused like any date outside the month. A month already over is refused. "Today" is the hospital's (`membership.today`).
- **A draft** is refused with "solve it again instead"; **a submitted roster** with its frozen words; **a plain solve of an approved month** stays refused, and its words now point to a re-plan.
- **Worth your review: a re-plan whose roster in force, or whose month's facts, moved after it started is not applied.** That is: the version in force is no longer the one it started from, or the month's nurses, genders, leave or pins changed (`changes_since`). Its roster would undo what came since, such as a shift leave took off or a manager's edit, so it stays in the history and the manager re-plans. The alternatives were to apply it anyway, or apply it with a warning. A rename is no change: the roster goes in force under the new code. An hours change of a shift the roster in force works is refused by the catalogue meanwhile. **Not detected:** a change to the unit rules or a nurse's other attributes (allowed shifts, score, team leader) while it runs: the roster goes in force, and the roster's check on the page shows anything it now breaks, as for a direct edit.
- **Worth your review: a stopped re-plan's best roster goes in force like a finished one's,** as a stopped solve's becomes the draft, under the same "moved meanwhile" rule. The button says "Stop and put the best roster in force". The alternative was to keep it in the history only, which would need a way to apply it later.
- **A re-plan that finds no roster, or one breaking a hard rule (`ok` false),** leaves the roster in force as it was, tells the manager, and nobody else.
- **A re-plan that changes no cell** makes no version, no audit entry and tells no nurse, as the user decided for direct edits on 2026-11-06.
- **The roster's `solve` becomes the re-plan** when its roster goes in force: the page's details, the "solved before these changes" warning and "clearing a pin gives the cell back to its solve" are then the re-plan's. Version 1 keeps the approval's solve.
- **A nurse no longer in the month is left out of the re-plan and of the version it makes;** a nurse who joined since worked nothing before the date. Their old rows stay in earlier versions.
- **The reason** is optional; left empty it is "Re-planned from 12 June 2026.". It is stored on the solve and read only as the version's reason.
- **The audit log:** `solve.started` for a re-plan says only the time limit, as a solve's, since ARCHITECTURE section 8 keeps whether a solve was a re-plan from the System Admin; `roster.changed` says the version and the counts.
- **The comparison** costs both rosters on the re-plan's own input, so the roster in force pays nothing for changes and the re-plan's "Changes in a re-plan" is the price of the cells it moved. The page says so.
- **While a re-plan runs**, edits and leave are allowed, and make it end without changing the roster in force; the editor says so.

**Review.** The `code-review` skill's two axes against `a2ca974`.
- Standards found no hard violation. Fixed: the `solve.started` entry saying "replan" (against section 8), a local named `published` (the glossary's avoided word), the outcome's `Literal` written three times, `""` standing for "no outcome", two names that could be misread (`NO_ROSTER`, `latest`), a stale re-export and an out-of-place test import. Left as judgement calls: the re-plan card repeating the solve card's time-limit field and summary, the preview's precheck `try` beside the solve's, the outcome's words in four places (each says it for its own place: the bell, the history, the last solve, the result), and the comparison's costing in `history_api`.
- Spec found: the result page's "draft" words (fixed, test), a stopped re-plan with only a roster it could not keep said "no roster yet" (fixed, test), and test gaps for an hours change, a stop after a change, and the retry (three tests added). The real-solver test accepts `unchanged` as well as `version`, since whether a roster changes is the search's to decide; it has always made a version.

**Things later tickets should know:** comments are on 20 and 21. `solves/replans.py` holds a re-plan's rules and its end; `solves.input.assemble_replan` its input.

**The dev stack was not touched:** no restart, no migration, no login. When this branch reaches `main`, restart `web` and `worker` there for `solves.0002_replan`, which adds four columns to `Solve`.
