# 13: Edit the draft by hand

**What to build:** The unit manager clicks a cell of the draft and pins a shift, pins a day off, or clears it; within a moment he sees whether the grid now breaks a hard rule and how its cost changed, through the solver's validate call. A re-solve keeps his pins.

**Blocked by:** 11 Run a solve

**Status:** ready-for-agent

- [x] Cell editor for pin shift, pin off, clear; pending edits held client-side and saved explicitly
- [x] Live validation debounced through one hook, calling validate with the grid as it would be; violations and cost delta shown
- [x] Saved pins stored as pinned cells with origin 'manager' and included in the next solve input
- [x] API tests cover saving pins, validation pass-through and that a re-solve keeps pins

## Comments

**From ticket 10 (2026-11-05).** The solver refuses a shift pinned on a leave date. The cell editor must refuse pinning a shift on one, and leave can now arrive on a date already pinned: `_refuse_dates` in `nurses/leave_api.py` is the path of every write that adds a date, where a refusal or a warning belongs. Removing leave goes only through `_rows_to_change`, and leaves the cell as it stands.

**Decisions from the user (2026-11-05).** Leave wins over a pinned shift.

- **Recording leave on a pinned day removes the pin and tells the manager.** The write is not refused. `_refuse_dates` in `nurses/leave_api.py` is the path of every write that adds a date, as the comment above says, so the removal belongs on that path and the answer has to carry what the page tells the manager.
- **Pinning a shift on a leave day is refused,** in the cell editor and when saving pins.

**From ticket 11 (2026-11-05).** Pins go in `solves/input.py`, `assemble`, which counts them for the summary too: `Summary.pins` in `solves/api.py` is a literal 0 until then. Its docstring holds the decision: if a row ever holds a shift pinned on a credited day, leave wins and the pin is dropped there, so it is not a failed solve. A pin in the input also has to be part of `changes_since`, or a pin saved after a solve will not warn. `Roster.grid` is what the cell editor edits, and it follows renames through `rosters.drafts.carry_rename_through_grids`.

**From ticket 12 (2026-11-05).** Three things once a draft can be edited.

- **Restoring and pins.** `rosters.drafts.replace_grid` swaps the whole grid. A restored result knows nothing of a pin saved since it was solved, so a saved pin can then disagree with the grid. Decide whether a restore keeps pins, removes them or refuses, and whether a pin saved since counts in `changes_since`.
- **Restoring the draft's own solve** is refused today as "This result is the draft already" (`why_not_restore`, and `in_draft` in the history), because nothing could differ. After a hand edit it can differ, and a manager may want the solve's grid back, so that refusal has to look at whether the grid was edited. `in_draft` then means "came from this solve", not "is this result".
- **`roster_month`'s `last_solve`** counts a failed solve as old news once `Roster.updated_at` is newer than it. That was written for a restore. A hand edit also moves `updated_at`, so a solve that failed before an edit stops being mentioned. Check that is what you want.

Implemented on 2026-11-05. Backend under pytest on a throwaway PostgreSQL 18 container of my own, frontend under Vitest with the real routes and generated client over a stubbed `fetch`. Seams: the API with the scripted solver and the real worker code (`rosters/tests/test_pins.py`, 69 tests), and the Roster and Leave pages (`app.test.tsx`, through `start` and `hold`; no raised timeout, no fake timers, no wait that proves something did not happen). Results: backend 1557 passed, frontend 400 of 400, `npm run build` clean, `makemigrations --check` clean, `frontend/openapi.json` the same as a fresh export. The solver's suite was not run: nothing under `solver/` changed.

**Driven in the built-in browser,** on scratch project `nr-t13` with its own image, volumes and secrets. `web` was published on `127.0.0.1:18013` under `DJANGO_DEBUG`, with the real solver and worker. The unit was the solver's four-nurse sample as ER in December 2026. That run covered:
- A real solve from the page.
- The grid by keyboard: one Tab stop, arrows, Enter opening the cell's menu, Escape and a choice both returning focus to the cell.
- Pinning Day straight after a Night, which the real check showed as breaking the succession and headcount rules, cost +16.
- Pinning a day off and a Night. Emad's menu offered only Day, his only allowed shift.
- Leaving the month with unsaved changes: the question came up with focus on Stay, and staying kept the changes.
- Saving: the status line said so, focus went back to the cell, and the draft read "Edited by hand since. Cost 129, against 127 as solved", warning that pins had changed.
- Solving again: both pins kept, no warning.
- Clearing a pin.
- Recording leave on a pinned day from the Leave page: it said "It replaced a pin on the draft: N on 7 Dec 2026", and the Roster page listed the pin as replaced by Mona Ali's leave.
- Taking the shift off that day through "Take the shift off this day", saved.
- A solve held in the queue by stopping the scratch worker: a pin saved meanwhile was answered "The solve under way was given the month without them". Once the worker was back, the pin was on top of that solve's roster and the draft asked to solve again.
- At 375 px: no sideways page scroll, and the menu and unsaved panel usable.

That run found four bugs no test had, all fixed with tests:
- A draft out of date after leave showed the solve's cost while the check's delta counted from the cost on today's month.
- Taking a shift off a day of leave changed the grid without an audit entry.
- Discard left focus on the page body.
- The unsaved panel could fill a phone's screen.

**Validation was measured, not assumed,** on the same stack with the hospital's 25-nurse ER sample (`solver/tests/fixtures/er_request_2026-03.json`), five runs each:

| | Solver idle | During a real search on all 8 cores |
|---|---|---|
| In `web` (`solver_service.grid.validate_grid`) | about 8 ms | about 20 ms |
| The solver's `POST /validate` | about 29 ms | about 91 ms |

The solver call also fails outright when the solver is down.

What was NOT checked:

- **The frontend suite under load, or from a clean export.** `npm test` ran alone in the working tree.
- **The Spec review's fixes in a real browser.** These are a pin of the old unit after a transfer, edits dropped on leaving a month, focus on a refused save, an unknown cost change, a cached check outliving a change to the month, a joined nurse's pin, and a restored draft's leave notice. They were fixed after the browser run and are held by tests only.
- **A grid long enough to be windowed, edited in a real browser.** Vitest holds the windowed grid as a `grid` with 201 rows. Arrow keys scrolling it for real were not tried.
- **A real transfer, date correction, rename, retire, hours change, unit-rules save or allowed-shifts save against a pin.** API tests only.
- **A screen reader.** Labels and roles are read from the DOM, not heard.
- **Dark mode, 320 px, 200% zoom, RTL, browsers other than the built-in one.** The arrows mirror in a right-to-left grid in code; nothing has run in one.
- **`beforeunload`** (reloading or closing the tab with unsaved changes): TanStack Router's own, as on the password pages. jsdom cannot show it.
- **Through Caddy.**

**Decisions taken here:**

- **Worth your review: a pin always wins over the grid.** Every solve and every restore puts the pins that count on top of its roster (`rosters.drafts.as_a_draft_would_hold`), so the draft never shows a cell that disagrees with a pin. That is the one rule behind the answers to ticket 12's questions:
  - **A restore keeps pins**, on top of the restored result, and the draft warns ("pinned cells changed") because the restored solve's input lacked them. A request's or swap's pin is a promise, so a restore must not drop it quietly. To get a solve's grid back, clear the pins.
  - **Restoring the draft's own solve** is refused only while restoring would change nothing: "This result is the draft already, with your pins on top. Clear a pin to give its cell back." It goes through when something else differs, such as a shift taken off a day of leave. `in_draft` now means "came from this solve", and its description says so.
  - **`last_solve`:** a hand edit does not move `Roster.updated_at` (`save(update_fields=["grid"])`). So a solve that failed before an edit is still news until the next solve or restore. That is chosen, not inherited, and a test holds it.
- **Worth your review: saving while a solve of the month is queued or running is allowed.** The page says before and after that the solve was given the month without it. When the solve ends, the pin goes on top of its roster and the draft warns through `changes_since`. Refusing, as a restore does, was the alternative.
- **Worth your review: validation runs in `web` with the solver's own code**, not through `POST /validate`. The ticket says "through the solver's validate call". Ticket 12 set the precedent, which you kept, and the measurement above settles it: it is the same code, faster, and works with the solver busy or down. The page is honest when the check cannot answer: when the solver's code cannot read the month ("The solver's code could not check these changes. It says: …"), and when the server does not answer ("…the server did not answer. They are still here, and saving still works."). Section 6 says so.
- **Worth your review: a pin that falls out of step is set aside, not removed.** That covers a nurse no longer in the unit's month (transfer, end date, a deactivated manager), a day outside their dates, a day of leave written behind the API's back, a retired shift or one the unit no longer works, and a shift outside the allowed list. Such a pin reaches no solve, the draft lists it with the reason, and it counts again if things change back, as leave does after a date correction. Only leave removes a pin, as you decided. A pin of the old unit after a transfer is ended as `replaced` when the new unit's manager pins that day.
- **Worth your review: three new refusals.** The CNO cannot change a shift's hours while a counted pin uses it in a month not yet over. That is needed because a pin of a nurse who joined after the solve is in no grid. A unit's rules cannot drop a shift a pin uses, and a nurse's allowed shifts cannot be narrowed past their pin. Both name the nurse and date. Otherwise the next solve is infeasible with no readable reason. Retiring needed no new guard: a counted pin is on a shift its unit works, so `units_using` refuses it already, and a test holds that. Past months block none of these. Ticket 21 has a comment.
- **Pins are rows that end, never deleted** (`removed_at`, `removed_by`, `removed_why`: cleared, replaced, leave), because section 9 lists what may be hard-deleted and a pin is not on it. The shift is a key, so a rename needs nothing, and an edit sent under the old code is carried. Off is a null shift. One current pin per nurse and date. `origin` already holds `request` and `swap`, and the editor refuses to change a pin of either: "change it there".
- **Leave on a pinned day** ends the pin in `nurses.leave_api._begin`, which every path that adds a date goes through (record and change; there is no leave import). The answer names the pin in `pins_removed`, and only this unit's pins. The draft keeps saying so (`pins_lost_to_leave`) until a solve newer than the leave, whoever recorded it, so the manager is told even when someone else recorded it. Removing the leave does not bring the pin back. The grid's cell keeps its shift, as for any leave recorded after a solve. "Take the shift off this day" clears it by hand, and the check shows it as broken until then. Pinning a shift or a day off on a day of leave is refused.
- **Clearing gives the cell back to its solve,** or off on a day of leave or outside the nurse's dates.
- **A draft edited, or out of date with its month, is costed and checked on the month as it stands.** It shows "Cost 117 on the month as it stands, against 127 as solved" and what it breaks. Otherwise the solve's cost and nothing else, as before.
- **The audit entry** is `roster.draft_edited`, with the target "ER, 2026-06" and `{"pins": n, "cells": n}`. It holds no nurse, date or shift, and a test searches every entry for them. Leave ending a pin adds nothing to leave's own entry, since that would date the leave for the System Admin.
- **The page:**
  - Unsaved changes live in a Zustand store per page, as ADR 0008 says. The debounce is TanStack Pacer behind `lib/use-debounced.ts`, at 400 ms.
  - The check is a query keyed by the settled changes and everything else the answer depends on, so a late answer to older changes is never shown. A test answers the requests out of order to prove it.
  - Leaving the page or the month with unsaved changes asks first. Choosing to leave drops them.
  - A refused save keeps every change, marks the refused cells and lists why, with focus on the list.
  - Solve again is held back while changes are unsaved, because a solve is given only saved pins.
  - A pin breaking a hard rule saves: blocking that is submit's job (ticket 14).

The glossary's Pinned cell and sections 4, 5 and 6 of the architecture moved. **New dependencies:** `@tanstack/react-pacer` 0.24.1 and `zustand` 5.0.16, both named in ADR 0008 and neither installed before.

**Review.** The `code-review` skill's two axes against `5089f0e`.

Spec found seven bugs, all fixed with tests:
- A 500 when the new unit pinned a day the old unit's set-aside pin held.
- Unsaved changes carried into another month after "Leave without saving".
- No focus after a first refused save.
- "(no change)" shown when the cost change was unknown.
- The check's cache key missing the month's leave and dates.
- A false pin violation for a nurse who joined after the solve.
- Leave notices coming back after restoring an older result.

It also found `in_draft`'s description, now changed. It counted as scope creep the guards and the request and swap refusals (kept, for the reasons above), Home, End and PageUp/PageDown (kept, as the grid pattern expects them), the leave notice on the draft (kept, as the user asked that the manager be told and a page answer reaches only the recorder), and the nullable cost (kept).

Standards found:
- "re-solve" in a test name, now gone.
- Imports out of order and lines over 130 characters, fixed.
- A weak either/or assertion, fixed.
- Duplications, fixed: the date wording, the "month is over" sentence, a second credited-days helper, a query in the API module, and a refusal worked out twice.
- `Month` renamed `DraftEdits`. An unused debounce parameter dropped.

Left as judgement calls:
- The three actions branched on in a few places.
- `(hospital_id, date)` travelling loose.
- `""` for a day off, which is the solver's own.
- `pin.nurse.user.username` chains, as the rest of the codebase has.
- The guards spread over four APIs, all calling into `rosters/pins.py`.
- A pin ended by leave warning as both "leave" and "pins".

`better-interface` and its domain skills, by hand, from the code and the screenshots:
- Keyboard: the grid is one Tab stop, with roving focus; arrows mirror right to left. The menu opens with Enter or Space and focus comes back on close.
- Screen reader: each cell's label says its value, pin and unsaved change, and the swatches are hidden from it.
- Messages: results are announced in a status line, a refusal takes focus, and Discard returns focus to the grid (fixed above).
- Phone: the panel is capped at half the screen.

`interface-review` is yours to invoke.

**Things later tickets should know:** comments are on 14 (pin saving must check the roster's state, in `rosters.api._why_not_edit`), 16, 19 (one table, `origin` `request`, leave ending its pin) and 21. `rosters/pins.py` decides which pins count; `rosters/editing.py` is the editor's rules; `components/cell-editor.tsx` and `RosterGrid`'s `editing` prop are the page's. **The dev stack:** it was up (Docker started it). I restarted its `web` and `worker` straight after the commit, which applied `rosters.0003_pinned_cell`, and did nothing else there: no login, no solve, no data. Its `web` reloads from the working tree, so from my first model change until that restart its Roster page would have failed for want of the table. **The new page has not been opened on your dev data.**
