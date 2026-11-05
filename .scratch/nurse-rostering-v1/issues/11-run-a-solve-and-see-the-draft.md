# 11: Run a solve and see the draft

**What to build:** The unit manager picks a month, sees a summary of what the solver will receive (nurses, leave, pins) and the precheck warnings, chooses a time limit up to the cap, and starts a solve. He sees his position in the hospital-wide queue, then the best cost so far and the number of improving rosters as it runs, can stop early and keep the best roster found, and when it finishes sees the draft grid with the penalties per soft rule. Each solve replaces the draft's grid. The hours of a shift an open month uses cannot be changed.

**Blocked by:** 10 Leave

**Status:** ready-for-agent

- [x] Solve input assembler builds the complete solver JSON from hospital rules, unit rules, Ramadan days, holidays, nurses with opening values or zero carry-over, leave, and credits days outside start and end dates like leave; the input is stored verbatim with the solve
- [x] Precheck shown before solving via the solver's precheck call
- [x] Time limit defaults to the unit's and is capped by the technical setting
- [x] Solve rows go through the queue; the worker runs one at a time under a hospital-wide lock, writes queue position and progress, relays cancellation, retries a failed solve once and records the failure reason
- [x] The draft roster is created or its grid replaced on success; the result is stored verbatim
- [x] Draft grid shows the nurse × date cells with shift colours, leave, and the penalties per rule
- [x] Changing a shift's hours is refused while any open month's roster uses it
- [x] API tests run the whole flow with the scripted solver fake and once end to end with the real solver service on the four-nurse sample, including cancellation and the queue order across two units

## Comments

**From ticket 07a (2026-11-05): a start date or gender can now change after a solve.** The CNO corrects them at `nurses.api.correct_details`, which has no guard because no roster exists yet. This ticket has to decide and test what follows. What must hold:

- A stored solve input stays as it was: it is the record of what the solver was given. The next solve reads the corrected values.
- A draft or roster solved from the old values must not pass silently as current. A new gender can break a gender requirement, and a new start date changes which days are credited like leave and can leave worked cells before the start. Compare the nurse's start date and gender with the latest solve input, warn the unit manager, and validate again before submit.
- `correct_details` can move a nurse's first placement back to cover an earlier start date (`membership.reach_back_to_start_date`). A nurse whose first placement begins before their start date is normal, and a nurse whose end date is before their start date was never present. A nurse who worked cannot be corrected into that state (`membership.start_date_fits`).

**From ticket 09 (2026-11-05).** Four things for this ticket.

- **The hours guard:** rosters arrive here, so add section 4's "hours cannot change while an open month's roster uses the shift" to `update_shift` in `hospital/catalogue_api.py`, as `refuse((("hours",), ...))` under its lock. Ticket 09 could not: there was nothing to check.
- **A nurse in the input:** start from `nurses.rostering.nurse_block(nurse, placement)`, with the placement of that month, since allowed shifts are on the placement. Add leave and pins, and replace the opening values and empty history with the carry-over once there is one.
- **A block the solver now refuses:** a unit's save checks its night and day shifts against the CNO's `night_rest` and `shift_switch` weights as they stood. A one-shift unit saved with them at 0 is refused if one rises. Show that like a gap from seeding, as "review the unit rules", not as a failed solve.
- **The time limit:** `Unit.default_time_limit` may be above the cap, if the System Admin lowered the cap after the unit's save. Use the lower. A nurse's `allowed_shifts_to_check` may still be up: block the solve until the manager has checked it, as the user decided on 2026-11-05 (see the last comment).

**From ticket 10 (2026-11-05): leave in the solve input.** The seam is proven in `nurses/tests/test_leave.py`; extend it there.

- **The nurses of a month:** `membership.rostered_in(unit, month)`, and each one's block from `nurse_block(nurse, membership.placement_in(nurse, month))`, not their latest placement. It leaves out a nurse who was never present. It does not filter on the account: a manager's profile whose account the System Admin deactivated, with no end date, is still on it, so decide what that means.
- **Leave:** `block["leave"] = nurses.rostering.leave_dates(nurse, month)`: ISO dates in order, each once. An empty list is accepted.
- **Days outside the start and end dates:** add them as a set, not a list. A date recorded before a correction can also be outside them (the manager sees it flagged), and the solver refuses `lists a day twice`.
- **No type in a solve input,** and a test holds it. It is stored for good, where a type would outlive its correction and reach whoever reads the input later. The summary before a solve can count leave per nurse; the manager's grid may look a type up from `Leave` for their own month. The CNO and the Deputy CNO read a type on the Leave page since the change on ticket 10 (2026-11-05), not from here.
- **A pin on a leave day:** `load_request` refuses a shift pinned on a leave date (`on leave but pinned`), though `""` is fine and a desired or undesired day on leave is simply superseded. Leave does not look at pins, so the assembler must not pass such a pair on as a failed solve. Decide with ticket 13 which wins.
- **Leave changed since the last solve:** like a corrected start date (see the comment from 07a), a draft solved before leave was recorded, corrected or removed must not pass as current. Compare with the stored input, warn, and validate before submit.

**Decisions from the user (2026-11-05).** These settle what the comments above left open.

- **Allowed shifts a transfer emptied:** refuse to start a solve while `allowed_shifts_to_check` is up on the placement of that month for any nurse in it, naming them, until the manager has checked. This replaces the earlier "consider a warning".
- **Solve progress polling is not activity.** It does not count towards the twelve-hour idle limit. `SESSION_SAVE_EVERY_REQUEST` makes every signed-in request count today, so the polling call must not extend the session. A test holds it.
- **A draft older than a change to a start date, gender or leave:** warn the manager, and block submit only if validating again fails. Ticket 14 holds the submit side.
- **A review flag up on the hospital or unit rules:** warn beside the precheck, with no block.
- **A block the solver itself refuses** (a unit seeded with a gap, or a one-shift unit after the CNO raised a weight) shows as "review the unit rules", not as a failed solve.
- **Scores nobody has reviewed at the 0.8 default:** show a count beside the precheck, with no block. The count is the nurses whose attributes a manager has never saved. Ticket 09 left nothing that marks this, so this ticket adds a small marker, set on the first save.
- **A manager whose account is deactivated but whose nurse profile has no end date:** leave them out of the solve and warn. `membership.rostered_in` does not filter on the account, so the assembler has to.
- **Leave wins over a pinned shift.** Recording leave on a pinned day removes the pin and tells the manager, and pinning a shift on a leave day is refused (tickets 13 and 19). So the assembler should never meet the pair `load_request` refuses as `on leave but pinned`; if a row ever holds one, leave wins and it is not a failed solve.
- **Run the production compose file through Caddy once and report back.** Tickets 04 to 10 ran only the dev overlay or a scratch stack.
- **The session may read `INITIAL_ADMIN_PASSWORD` from `deploy/.env`** to use the dev stack. Earlier sessions worked around not knowing it.

**From ticket 10b (2026-11-05): how this ticket's frontend tests should be written.** Keep adding to `frontend/src/app.test.tsx`, through `start` and `hold`. A new route's chunk is imported before the tests by `test-setup.ts` without any change here. Do not raise a timeout in a test to wait for the solve's progress: let a handler change its answer and let `findBy` see the page change, keeping any poll interval short in the test. `vi.useFakeTimers()` does not work with `start` as it stands, because `findBy` and `user` would both stall, and nothing in the file has needed it. Before acting on a page you have just gone to, wait for something on it rather than for the address, which changes first. A wait that proves something did not happen, like the 50 ms one in the users page's test, can only pass more easily on a busy machine, so prove it another way if there is one.

Implemented on 2026-11-05. Backend under pytest on real PostgreSQL 18, frontend under Vitest with the real routes and generated client over a stubbed `fetch`. Seams: the assembler (`solves/tests/test_input.py`, with the solver's own four-nurse sample as the expected answer), the API with the scripted solver and the real job called directly (`test_flow.py`), the real queue on real connections with the scripted solver (`test_queue.py`), and everything real, with the service in its own process (`test_end_to_end.py`: the whole flow, a stop, and the queue order across two units). None of them waits on a clock: a stop is asked for once the row shows a roster.

**The production compose file through Caddy, as you asked: it works.** Run twice under its own project (`-p nr-t11`), its own image tag and its own volumes, and removed afterwards, image, volumes and networks; the dev stack's data was not involved. The second run was on the final code. From an HTTP client over HTTPS through Caddy: all five services healthy, `/api/health` reports the solver reachable, plain HTTP answers 308 to HTTPS, a deep link serves the page, login and CSRF work behind TLS, Caddy's container cannot resolve `solver`. Two units' solves: the second reported 1 ahead and ran after the first ended; 409 for a second solve of the same month, 422 over the cap; a stop mid-search ended `cancelled` with cost 420 as the draft, stopped early. No traceback in the worker's or web's logs. **Not through Caddy in a browser:** the built-in browser refuses Caddy's self-signed certificate, and only you can accept that in the pane. Run once earlier in the work, before the review's changes: a real solve kept going through `docker compose restart worker`, its progress frozen for 219 s until `recover_lost_jobs` put the job back, at `attempts` 1, and then a stop kept its best roster.

**Driven in the built-in browser,** on that same scratch project with `web` also published on `127.0.0.1:18000` under `DJANGO_DEBUG` and Vite on `localhost:5173`, because of the certificate. Twelve nurses in each of two units, real solver, real worker, real clicks on Start and Stop. The summary, the warnings and the time limit; Start with focus moving to the card; progress with the best cost going down; a solve queued behind others showing 2 ahead, then 1; a real Stop ending at cost 377 with "you stopped this solve early", the status announced and focus on the draft; the grid with shift colours, L, the dots before a late start date and shaded Fridays; the penalties under the hospital rules' names; a corrected gender warning beside the draft; a nurse's emptied list blocking the month and naming them; the grid at 375 px with names in view and no sideways page scroll. That browser run found two bugs no test had: each cell's screen-reader text was escaping the scroller, so the whole page scrolled sideways, and times were shown in UTC rather than the hospital's. Both fixed.

**The dev stack:** I restarted `web` and `worker` for the code and migrations, and stopped `worker` for a while. Its database now has `nurses.0004_attributes_saved`, `solves.0001_solve` and `rosters.0001_roster`. Those were first applied under other names, rolled back and applied again as the models changed, which only touched what this ticket added. The `frontend` service I started and stopped, so it is stopped as it was. I logged in as nobody there and ran no solve there: it holds a manager whose password I have no business knowing, so everything was driven on the scratch project. **The new page has therefore not been opened on your dev data.**

What was not checked:

- **The frontend suite under load, or from a clean export.** `npm test` ran alone in the working tree, 348 of 348. The new tests should hold under load, with a 10 ms poll, `findBy` and no wait that proves something did not happen, but that is reasoning and not a measurement.
- **A grid long enough to be windowed, in a real browser.** Above 60 nurses only the rows in view are drawn. A test with a stubbed size shows that and `aria-rowcount`; scrolling it for real was not done.
- **Rules the solver refuses, on a real page with a real unit.** The refusal is in API tests against the real loader, and the page in Vitest. The block for an emptied list was seen with the flag set by hand; a real transfer reaching it is in an API test.
- **A solver crash for real, and so a real retry.** Scripted only.
- **The hours guard on the Shifts page.** Its refusal came back correctly from the real API, naming the rosters; the field's display is the page's existing one.
- **Dark mode, 320 px, 200% zoom, RTL and browsers other than the built-in one.** Viewed at 375 px only.
- **`recover_lost_jobs` on the final code.** That run was before the review's changes, none of which touched it apart from moving its decorator's helper.

**Decisions taken here:**

- **Worth your review: the queue position is worked out when asked, not written by the worker.** The criterion says the worker writes it. A written one goes stale when a solve ahead is stopped, and needs every other row rewriting. It counts active solves with a lower queue job id, which is the order they run in. Section 4 and 7 now say so.
- **Worth your review: `succeeded` with no roster.** A search that ends with no roster, or with one the validator says breaks a hard rule (`ok` false), is `succeeded` with the draft left as it was and the page saying why, not `failed`, because the solver did give an answer and a retry would not change it. It is not retried. A stopped solve with a roster replaces the draft, **even if that roster costs more than the draft it replaces**, as "each solve replaces the draft's grid" says: seen at cost 377 over 216. The history (ticket 12) keeps the other.
- **Worth your review: a month already over is refused, and the current month is allowed,** replacing its whole grid. "Any future month" did not say whether the current one counts, and a hospital starting out needs it. Ticket 17 has a comment.
- **Worth your review: the hours guard also refuses while a queued or running solve's input names the shift,** not only a roster, because that solve's result would otherwise have been worked out on the old hours. Asked only for rosters.
- **Grids follow a rename:** `Roster.grid` carries it, the stored input and result do not. Otherwise renaming a shift and then changing its hours would pass the guard, and the page could not colour it. A solve that ends after a rename gets the new code as it is written, under the catalogue's lock.
- **Retrying inside the job,** not with Procrastinate's retry, so one counter decides, on the row, and the solve keeps its place in line. A retry that works keeps the first failure's reason in `error`. A worker's death is not an attempt while the solver still has the job; one the solver has lost is.
- **`recover_lost_jobs`, which nobody asked for.** Without it a dead worker's job holds the hospital-wide lock for good and no solve ever runs again. Every five minutes, so a solve can wait that long after a crash.
- **A job the solver is running that no solve is watching** is stopped before the next starts: only a worker that died between starting it and writing its id can leave one.
- **Stale drafts compare gender, credited days and who is in the month** with the stored input. A start date counts only if it moves a day of that month. Other attributes do not warn, as you asked only for these.
- **A deactivated account:** left out and warned when it has no end date, or one still to come. One whose end date has come stays for the days worked, as a staff nurse's does.
- **Worth your review: `attributes_saved`** is set by a save of the attributes form even if nothing changes, and not by the allowed-shifts-only save, which is all a joining unit's manager has. Existing nurses count as never saved, so your dev data's 24 nurses will show in the warning on first opening the page.
- **What is outside a nurse's dates is stored with the solve** (`Solve.outside_days`), because the input lists those days with leave and a cell should say what it was when solved. A later correction shows as a warning instead of changing the cell.
- **The worker's concurrency stays 1.** The lock would hold at any number, but a five-minute solve delays the crons by that much. A later ticket with a job that cannot wait should raise it.
- **Rules refused are checked in `web` with the solver's own loader,** so a refusal needs no call to the solver, and in the worker too in case the rules change while it waits.
- **No roster version yet:** ticket 14 creates version 1 at the first approval.
- **`jsonb` keeps no key order,** so "verbatim" holds as values, not as text.
- **Polling:** 1.5 s while the page is open and a solve is active, stops on a refusal. A poll, refused or not, does not move the idle limit, unless authentication itself refuses it, and then the page stops asking.

The glossary needed no change: `Solve`, `Result`, `Draft` and the rest mean what they did. The architecture's sections 4, 5, 7 and 8 moved and say so.

**Review.** The `code-review` skill's two axes. Spec found a refused poll polling forever and keeping the session alive, a retry's reason being lost, focus lost after taking a solve out of the queue and taken from elsewhere when a solve ended, and a cell's label going wrong after a correction: all fixed, with tests. Standards found roster reads in the `solves` app, no `result` reader, Avoid words, an unsorted audit map, a badly named migration, the table's accessors unused and several duplications: all fixed. Left as judgement calls: `solver_health` keeps its own `httpx.get`, because the health tests patch that; `plural` is one more ad hoc plural beside the others, in an English-only v1; `changes_since` returns dicts; `POLL_MS` has a test branch in production code, which this ticket's last comment suggests. `better-interface` and its six skills, by hand, from the code and the screenshots: nurse names truncated with only a title now wrap, a public holiday carried only by shading now says Hol, the muted weekday on a shaded day now uses the plain foreground, because the page's own tokens looked short of 4.5:1 (computed by eye, not measured). `interface-review` is yours to invoke.

**Things later tickets should know:** comments are on 10b, 12, 13, 14, 17, 19, 21 and 22. Tests that use a real worker need the `empty_queue` fixture and `run_the_queue` from `solves/tests/conftest.py`: flushing leaves the queue's tables alone. `TanStack Table` and `Virtual` are installed at 9.3.1 and 3.14.26; `components/roster-grid.tsx` is where ticket 13's cell editor starts.

**Reviewed by the user (2026-11-05), and kept as built:** the queue position worked out when asked, not written by the worker; a search with no valid roster leaving the draft alone, and a stopped solve replacing it even at a higher cost; the current month can be solved, until ticket 17 refuses it once a month has an approved roster; hours also refused while a queued or running solve uses the shift; existing nurses counting as never reviewed; and the two additions nobody asked for, `recover_lost_jobs` and stopping a solver job a dead worker left.
