# 21: Month close and the carry-over chain

**What to build:** On the first day after a month, at the close time, the application closes every unit with an approved roster: the roster in force plus recorded leave and pins becomes fact, the solver validates and reports what the facts broke, and each nurse's carry-over is stored. The next month's solve input starts from the latest closed carry-over projected through the approved rosters in between; a close always takes the previous closed month's carry-over as input. The unit manager may record late facts and re-close while the next month is open, sees each nurse's projected carry-over, and opening values lock after the first close. The carry-over into January resets overtime-to-date and the fairness balances; transfers and shift-code renames are honoured in histories.

**Blocked by:** 17 Re-plan from a date

**Status:** ready-for-agent

- [x] Close job on the schedule and on demand; a unit with no approved roster is skipped; the close result and per-nurse carry-over stored with source 'closed'
- [x] Projection computed with the same solver computation and stored with source 'projected'; the assembler takes the latest closed carry-over projected forward, including the shift history
- [x] Re-close allowed until the next month is closed; refused afterwards
- [x] Opening values locked after the nurse's first close
- [x] January input resets overtime-to-date and both fairness balances
- [x] Shift-code renames mapped into histories; a transferred nurse's carry-over follows her into the new unit from the effective month
- [x] 'Closed' shown in the overview; projected carry-over per nurse shown to the manager
- [x] API and direct tests cover the chain across three months with the fake solver and one real closing of the four-nurse sample

## Comments

**From ticket 07a (2026-11-05): closed months have to stop a correction.** `nurses.api.correct_details` lets the CNO change a nurse's start date and gender and has no guard, because no month closes yet. Add the guard there, with its test:

- A closed month is a fact. Its stored close result and carry-over are never rewritten by a correction.
- **Start date:** refuse on `start_date` (`hospital.api.refuse`) a change that would alter which days counted in a closed month, on either the old or the new date's side. The refusal should say which month. While the month can still be re-closed, the alternative is to allow the change and tell the manager to re-close: decide which and record why.
- **First placement:** `membership.reach_back_to_start_date` must not move a placement back into a closed month.
- **Gender:** it changes no hours or carry-over, so it need not be refused. It applies from the next solve on, and closed months keep what their stored input says.

**From ticket 09 (2026-11-05).** Opening values are "editable until her first month closes", and no close exists yet, so nothing refuses them. Add that to `update_nurse_attributes` in `nurses/attributes_api.py`, refusing on the field and leaving the other attributes open. They travel in one body with the attributes, so compare them rather than refusing the save.

**From ticket 10 (2026-11-05): closed months have to stop leave too.** `record_leave`, `change_leave` and `remove_leave` in `nurses/leave_api.py` accept any date, because no month closes yet. In `_refuse_dates` and `_rows_to_change`, refuse a date in a closed month beside First day, leaving it open while the month can be re-closed, with a prompt to re-close: late facts are what that is for. A close reads `nurses.rostering.leave_dates`, adding days outside the start and end dates as a set. The month's manager is the one who answers, including a nurse since transferred, whom `membership.placed_in` finds.

**From ticket 11 (2026-11-05).** `solves/input.py` starts each nurse from `nurse_block`, so the opening values and an empty history, and that is where the projected carry-over replaces them, with `renamed_shifts` once a history can name an old code. "Open month" in `rosters.drafts.using_shift`, the hours guard, today means every month: narrow it to months not closed.

**From ticket 12 (2026-11-05).** A result's per-nurse `carry_over` is stored and shown nowhere: the panels show the hours accounting and cost the ticket named. If the close page wants to show it, `SolveResult.nurses` is where it would join. `elapsed_violations` is shown under "Recorded facts that broke rules" (`components/solve-result.tsx`), and the close's own report could reuse it. `rosters.drafts.using_shift` stays the hours guard: a shift no open draft uses can change hours while an older stored result still holds it, which is why `why_not_restore` compares a result's hours with the catalogue's. Once closed months count as not open, that holds the same.

**From ticket 13 (2026-11-05).** Pins exist: `rosters.models.PinnedCell`, current while `removed_at` is null. Three things for the close.

- **A month that is over holds up nothing:** a shift's hours and retiring it, a unit dropping a shift and narrowing a nurse's allowed shifts all look only at pins from the current month on (`rosters.pins.counted_uses`, `_counted_from_now_on`). So a closed or unclosed past month can hold a pin on a shift since retired, renamed or had its hours changed. The close has to read such a pin under the shift's code now and with the hours it had, as it reads the roster in force.
- **A pin set aside counts for nothing.** `rosters.pins.month_pins` sets aside a pin on leave, outside the nurse's dates, on a shift the unit no longer works or the nurse may not work, or of a nurse no longer in the month, and leaves it out of a solve input. The close's "every recorded pin becomes fact" should take the same set, from the same function.
- **Saving a pin on a month that is over is refused** (`rosters.api._why_not_edit`), as a solve and a restore are. Re-closing with late facts may want to reopen that for the month before; it is one place.

**From ticket 14 (2026-11-05).** "The roster in force" is the approved roster's latest `RosterVersion` (`roster.versions.first()`), whose grid is also `Roster.grid` under today's codes. A month still submitted at the close time has no roster in force and, as section 5 says, is skipped.

**From ticket 15 (2026-11-06).** A nurse's own month (`GET /api/rosters/mine/month`, page My month) shows hours for this month and later only. A month already over shows its leave and no hours, as My roster shows no month before this one.

- **What to change:** once a month is closed, its closed figures are the right answer for it: hours worked, overtime, and what was carried. `rosters.reading_api._in_force` cuts at `membership.this_month()`. Open earlier months there from the close.
- **"Carried into next month"** is the projected carry-over today, worked out from the version in force on the month as it stands. The page already says it is worked out again at the month close.
- **A close is not notified.** Add an `Event` in `notifications.models` and a function in `notifications/sending.py` if the manager should be told what the facts broke.

**From ticket 16 (2026-11-06).** What holds for a month that is over, until this ticket.

- **No edit:** the roster in force of a month already over cannot be changed by hand (`rosters.api._why_not_edit`, `IN_FORCE_OVER`). Re-closing with late facts may want to reopen that for the month before: it is one place.
- **Leave recorded late on a month that is over makes no version** (`rosters.versions.take_off_for_leave` skips months before `membership.this_month()`), so that month's grid can still hold a shift on a day of leave. The close reads leave itself and leave wins, as it already does in `rosters.own_month`.
- **The month under way** is edited and versioned as any other approved month. Its days already passed can change too: a sick day recorded the day after takes that shift off.
- "The roster in force" is still `roster.versions.first()`, and `Roster.grid` equals its grid under today's codes.

**From ticket 17 (2026-11-06).** Re-plans exist, and the close is the same mechanism with the date set to the first day after the month.

- **The input:** `solves.input.assemble_replan(unit, month, replan_from, in_force)` builds the month as a solve would, with the roster in force under today's codes as `published` (exactly the month's nurses: one who left is dropped, one who joined gets an empty row) and `replan_from`. Pass the first day after the month and the solver makes every day a fact: pins that count, then leave and the days outside a nurse's dates, then the roster in force. A pin set aside is no fact there either: check that is what the close wants.
- **Not through the re-plan's endpoint:** `solves.replans.why_not_from` refuses the first day after the month ("Choose a date in …") and `why_not` refuses a month that is over. Those refusals are the re-plan's; the close calls the solver's validate path or its own job.
- **A re-plan that ends after its month did** is `ReplanOutcome.MONTH_OVER` and changes nothing, so the roster a close reads is never moved by a late re-plan.
- `Solve.replan_from` marks a re-plan in the manager's history. The System Admin's history does not show it (a closed list); keep a close out of it the same way or decide.

**From ticket 19 (2026-11-06).** An accepted request is a pin of origin `request`, so the close reads it like any pin, through `rosters.pins.month_pins`. A request of a month that is over can no longer be accepted, edited or cancelled (`requesting.deciding.MONTH_OVER`), and a pending one stays pending until its manager rejects it: decide whether the close should end those. Re-closing with late facts that reopens pins for the month before would reopen requests' too, in `requesting.deciding.why_the_pin_cannot_move`.

**From ticket 20 (2026-11-06).** Swaps exist (`swaps`). An approved swap's cells are pins of origin `swap`, read by the close like any other through `rosters.pins.month_pins`. A swap still waiting when its month ends has already expired by date (`swaps.expiring`), and approving one of a month that is over is refused. A re-close or late fact that makes a version through `rosters.versions.make_version` expires waiting swaps whose cells it changes, as every version does; one that writes `Roster.grid` another way would skip that.

**From the scheduled-jobs design (2026-11-06, ADR 0009): what to build so a solve never delays the close.** Agreed with the user; this supersedes ticket 11's "the worker's concurrency stays 1".

- **Concurrency 4:** `command: python manage.py procrastinate worker --concurrency 4` in `deploy/compose.yaml` (the dev overlay inherits it). Not an `.env` setting.
- **Every periodic job takes a run lock under its own name:** in `ops.queue._periodic`, `app.task(queueing_lock=job.__name__, lock=job.__name__)`. The queueing lock only stops two waiting copies; the lock stops a run beside its own previous run. Solves keep the hospital-wide lock.
- **The close never calls `POST /solve`,** and nothing but `run_solve` does: the solver runs one job, and `running._start` cancels one it finds that no solve is watching. So not "a re-plan from the first day after the month" submitted to the solver, as ticket 17's comment suggested.
- **Carry-over with no search:** lift the per-nurse block of `nurse_roster/result.py::build_result` (hours, overtime, `carry_over` with `previous`, `last_shift_kind`, `rest_owed`) into a function of the package that takes the problem and a complete grid, and have `build_result` use it. Expose it beside `validate_grid` in `solver_service/grid.py`. The close and `project_carry_over` call that and `validate_grid` in the worker's process, on `solves.input.assemble_replan(...)` with the first day after the month. A test should hold that a real solve's `nurses` block equals the function's on the solve's own roster.
- **The schedule:** `close_month` is `@hourly(at_minute=30)` and a catch-up: close every unit's month whose close time has passed on the hospital's clock and is not closed. Procrastinate's cron is UTC and fixed at import. The close time is therefore a whole hour plus 30 minutes; the default 00:30 is met exactly where the hospital's offset from UTC is a whole hour (Riyadh's is), and within the hour otherwise.
- **A solve of a later month in flight is left alone.** Its input was built from a projected carry-over. Add "older than the close" to the stale-draft comparison (beside gender, credited days and who is in the month), warning and validating again before submit.
- **Tests:** (1) in `solves/tests/test_queue.py`, the real queue at concurrency 4 with a scripted solve held open by `on_read`: defer a scheduled job and assert it finished while the solve's row says `running`; no clock waits. (2) Two solves still run one after the other at concurrency 4. (3) A close against a solver stub whose `start_solve` raises. `run_the_queue` may need a concurrency argument.
- **By hand, on a scratch compose project, never `nurse-roster`:** a real solve running and `recover_lost_jobs` completing in the worker's log meanwhile.
- `recover_lost_jobs` needs no change: it requeues only the jobs of a worker silent for 30 s and fails a solve only when its job is neither waiting nor running.

**Decided by the user (2026-11-06), for this ticket.**

- **Requests still pending at the close end.** Each pending request of the month being closed takes a final state with a fixed reason (for example "The month closed before a decision."), the same words for everyone and naming no one, and its nurse is told, as for any other decision. This replaces the open question in ticket 19's note above ("decide whether the close should end those").
- **A close stays out of the System Admin's solve history**, as a re-plan does: that history is a closed list of fields, and a close is about a roster.
- **Scheduled jobs and the worker's single slot** (a solve of up to five minutes delays the hourly jobs, and the close cannot wait) are settled by ADR 0009 (`docs/adr/0009-scheduled-jobs-run-beside-a-solve.md`) and the scheduled-jobs comment above.
- **A unit cannot stop working a shift its submitted or approved roster of a month not yet over holds** (review fixes, 2026-11-06: `rosters.drafts.frozen_cells_on_shifts_going`, refused in `units.rules_api`), because the solver refuses such a cell in the roster it is given. A month already over is not guarded, so a re-close of one whose unit has since dropped a shift its roster holds will meet the same refusal: decide what the close does then.

**Decision from the user (2026-11-06), settling the line above.** When a month already over is closed or re-closed and its roster in force holds a shift the unit has since stopped working, the close does not refuse: it skips the solver's unit-shift check for those cells and keeps the past roster as it stands, so they count as worked. Nobody can change a month that is over, so there is nothing to ask the manager to fix. Test it with a unit that drops a shift after its month ended.

**Implemented on 2026-11-06,** on branch `claude/ticket-21-month-close-df8578`. The backend ran under pytest on a throwaway PostgreSQL 18 container of my own (2233 passed), the solver's suite in full (442 passed after the lift, plus 5 new), the frontend under Vitest with the real routes and generated client over a stubbed `fetch` (528 passed) and `npm run build`. `makemigrations --check` is clean; `frontend/openapi.json` matches the export.

What was built:
- **The solver package (`nurse_roster/result.py::nurse_accounting`)**: the per-nurse block of `build_result` (hours, overtime, `carry_over` with `previous`, `last_shift_kind`, `rest_owed`) is one function of the problem and a complete grid, and `build_result` calls it. `solver_service/grid.py` exposes `nurses_of(solve_input, roster)` and `month_facts(solve_input)` beside `validate_grid`.
- **A new app, `closes`** (the name section 8 gives it; the glossary avoids "closing"):
  - `MonthClose` (unit, month, closed at, closed by: null for the schedule, the version closed, the input and the result: `facts`, `facts_broke`, `cost`, `nurses`). Nothing rewrites one: closing again is a new row, the latest is in force.
  - `CarryOver` (nurse, unit, month carried out of, source `closed` with its close, or `projected`, the latest a nurse and month; opening values have no row). Migrations `closes.0001`, `requesting.0002` (`expired`, a step's `by` nullable) and `notifications.0005` (`month_closed`).
  - `closes.chain`: the chain. A nurse's month starts from her latest closed carry-over (from that month's close in force), projected forward through each approved roster in between by the close's own computation, memoised per unit and month; a month with no approved roster hands on what came in with no shift history; without a close, her opening values from her first approved roster. The unit is the one each month falls under for her, so a transfer carries it. Overtime-to-date and both balances reset when the year turns. `solves.input.assemble` puts it into every nurse's block, with `renamed_shifts` for old codes in a history.
  - `closes.making`: the close. Under the catalogue's lock, the month's nurses' and users' `FOR NO KEY UPDATE` (`review.lock_the_months_nurses`), the unit's and the roster's; `assemble_replan` with the first day after the month and a chain that takes closed months only; `month_facts`, `nurses_of` and `validate_grid` in this process. It ends the month's pending requests, writes `month.closed` (`{"version", "again"}` only), tells the nurses of expired requests and, for the schedule's close, the manager. `due()`/`catch_up()` close every approved month whose close time has passed on the hospital's clock, oldest month first across units, each in its own transaction.
  - `closes.tasks`: `close_month` (`hourly(at_minute=30)`), and `project_carry_over` under its own lock, on demand after every version (`make_version`) and every close, storing the projected rows.
  - API: `GET /api/units/{id}/close?month` (manager, CNO, Deputy CNO): the close in force, what the facts broke with names, whether the facts changed since, why it cannot close (again) now, and each nurse's carry-over into and out of the month with its source. `POST /api/units/{id}/close` (manager only) closes a month that is over, or closes it again.
- **ADR 0009:** `deploy/compose.yaml` runs the worker with `--concurrency 4`. `ops.queue._periodic` gives every periodic job `queueing_lock` and `lock` under its own name; `under_its_own_lock` and `enqueue_once` (a savepoint, so a waiting copy fails only itself) for on-demand jobs. Nothing in `closes` imports `ops.solver_client`.
- **Pages:** a "Carry-over and month close" card on the manager's Roster page for every month; "Closed" on the overview, linking to the roster; My month and My roster open a closed month as its close read it; the Leave page says a closed month's leave is taken in by closing it again, or is fixed; the attributes form shows the opening values read-only once locked; an expired request reads "Expired" with the fixed reason.

Seams:
- `solver/tests/test_carry_over.py` (5): a real solve's `nurses` block equals `nurse_accounting` on its own roster, with and without the analysis given, and through `nurses_of`; the facts (leave wins, a pin wins), what the facts broke is elapsed, the history carried.
- `closes/tests/test_close.py` (26) and `test_guards.py` (12), through the API and the close's functions on the sample's sound June, July and August (August added to `rosters/tests/fixtures/sound_rosters.json`, solved reproducibly by the real package on June's and July's projection).
- `solves/tests/test_queue.py`: the real queue at concurrency 4 with a scripted solve held open by `on_read` until the close's row exists (no clock wait: the solve ends on a read count if the close never runs, and the test then fails); two solves still one after the other at concurrency 4; every periodic job's lock and queueing lock are its own name. `run_the_queue` takes a concurrency and runs the worker again while a job waits, since a worker that does not wait stops once a lock blocks what is left.
- `solves/tests/test_end_to_end.py`: **one real closing of the four-nurse sample**: solved by the real service, approved, closed by the schedule; its facts are the solve's roster and every nurse's hours and carry-over equal the solve's own block.
- `app.test.tsx`: 7 new tests (the close card thrice, My month closed, the locked opening values, the closed month's leave, an expired request) and the overview's Closed. No raised timeout, no fake timers, no wait that proves something did not happen.
- **Honestly: the code came just ahead of most of its tests**, written right after each piece. The spec review found three bugs the tests had not (below); each now has a test.

The checklist from the comments above:
- **07a, start date and first placement:** `nurses.api._closed_for_good`. A start date that changes which days counted in a month fixed for good (closed, and the month after closed too) is refused beside `start_date`, naming the month; so is a first placement reaching back into one. While the month can still close again the change is taken, and the close card says its facts changed since. The same for an end date (**Worth your review**, not asked). Gender is not refused, and a closed month keeps what its input says.
- **09, opening values:** refused on each changed field alone once the nurse has any closed carry-over; the rest of the body saves.
- **10, leave:** `_refuse_dates` and `_rows_to_change` refuse a date in a month fixed for good, beside First day; a closed month that can close again is open, with the prompt on the Leave page. The close reads `leave_dates` plus the days outside her dates, as `assemble` does.
- **11, the input:** the projected carry-over replaces the opening values and the empty history in `assemble`, with `renamed_shifts`. `using_shift` now means a month not over, or an approved month over and not closed; a draft or submitted roster of a month over holds nothing, since it can never close.
- **12, the result's `carry_over`** is stored per close and shown on the close card; what the facts broke is the solver's `elapsed_violations` (`facts_broke`).
- **13, pins:** `month_pins(..., facts=True)`: a pin set aside for its day counts for nothing; one on a shift since dropped or no longer allowed counts as worked (**Worth your review**: ticket 13 says "the same set, from the same function", and the user's decision on dropped shifts speaks of roster cells; this reads it for pins too). A shift renamed since is read under its code now; one dropped or retired is listed among the unit's shifts for the close's input only, with its catalogue hours. Pins and edits on the month before stay closed: **late facts are leave and corrections to dates** (the user's decision that nobody can change a month that is over).
- **14, the roster in force** is `roster.grid` (the latest version under today's codes); a submitted month is skipped.
- **15, a nurse's own month:** `_in_force` opens a month before this one once it has closed, from the earliest of hers; My month reads the close's stored figures. A close is notified to the manager: `Event.MONTH_CLOSED` with `unit_id`, `month`, `close_id` only; how many hard rules broke is read when shown.
- **16:** the close reads leave itself and leave wins; no version is made for a month that is over.
- **17:** the close is not a re-plan and is not a solve: no `Solve` row, so it is in neither history, and `why_not_from` is untouched.
- **19, requests:** pending ones of the month become `expired` with "The month closed before a decision.", by no one, and the nurse is told.
- **20, swaps:** read like any pin; nothing writes `Roster.grid`.
- **ADR 0009:** all as written, the three queue tests included.

**Driven in the built-in browser,** on scratch project `nr-t21`: the production compose file with its own image (`nr-t21-app:t21`), secrets and volumes, `web` on `127.0.0.1:18021` under `DJANGO_DEBUG`, no Caddy, the real solver and worker at concurrency 4. ER was the four-nurse sample, Mona (manager) and Carla (CNO); September, October and November 2026 were solved for real in-process by a seed script and approved, on the real clock (6 November).
- **The catch-up closed September and October** when the worker started (`closes.tasks.close_month` succeeded, `lock = close_month`), both "by the schedule". September's card then read "October 2026 has closed, so September 2026 can no longer be closed again." with no button.
- **A late leave and closing again:** Sick leave for Amal on 14 and 15 October from the Leave page, which said the month had closed and how leave is taken in. October's card then said "Leave or a nurse's dates have changed since it closed." "Close October 2026 again" made a close by Mona Ali: 14 October's night was now uncovered ("Its recorded facts broke a hard rule"), and Amal handed on 16 hours owed instead of 8.
- **The projected carry-over:** December's card showed each nurse starting from "Projected from November 2026", and "No approved roster" for what it hands on.
- **A real solve beside the close:** with ER given the end-to-end suite's long-search rules and a third unit (CCU) with an approved October not closed, a 90 s December solve was started from the page. While its job was `doing` and the row `running` (23 improvements), `close_month` and `recover_lost_jobs` were deferred from the worker's CLI: CCU's October closed at 18:42:08 UTC and `recover_lost_jobs` succeeded at 18:42:14; the solve ended `succeeded` at 18:43:22. Read from Procrastinate's job and event tables, since the worker logs nothing per job at its level.
- **The overview** (as Carla) showed Closed for ER's September and October and for ICU's and CCU's October, Approved for November and Draft for December.
- **Amal's My month for October** said the month had closed and showed 180 hours worked, 16 of leave credit, 196 asked, 16 hours owed carried.
- Timing on the stack: the December Roster read 0.56 s, the close view 0.06 s.
- Everything of `nr-t21` has been removed: containers, volumes, networks, image, and my PostgreSQL container for the tests.

What was NOT checked:
- **The `:30` firing on its own in the real worker.** The catch-up ran when the worker started and when deferred from the CLI; the schedule's registration is read in the lock test. The "before 00:30 on the 1st" boundary is an API test only.
- **A first close on demand in the browser.** The catch-up had closed the months before I could; the API test closes and closes again on demand.
- **January in the browser, a transfer, a rename into a history, a dropped or retired shift, an end or start date refused, opening values refused, and an expired request:** API tests only (and Vitest for the pages).
- **A late-leave re-close changing the month after's draft warning in the browser:** API test only.
- **A race between a close and a leave or edit on real connections.** The lock order and `FOR NO KEY UPDATE` are asserted on the close's SQL, not raced.
- **A large unit or a long chain.** Every `assemble` now works out the chain back to the latest close: one month in steady state. On an installation upgraded with many approved months never closed, the first catch-up closes them all, oldest first, and until then a read projects from the first approved roster.
- Dark mode, 320 px, 200% zoom, a screen reader, and browsers other than the built-in one.

**Decisions taken here:**
- **Worth your review: late facts are leave and corrections to a nurse's dates, not pins or hand edits.** `rosters.api._why_not_edit` and the requests' `MONTH_OVER` stay as they are, following your decision that nobody can change a month that is over.
- **Worth your review: a month is "fixed for good" once the month after has closed** (in its unit, or for one of its nurses transferred since). Leave and date corrections are refused only then; while it can close again they are taken, and the card asks for another close. Ticket 07a's "must not move a placement back into a closed month" is read the same way.
- **Worth your review: the end-date guard,** the same as the start date's, not asked for.
- **Worth your review: a pin on a shift since dropped or disallowed counts in a month that is over** (above).
- **Worth your review: an expired request is a state of its own, `expired`,** with a step of no one's hand, rather than a rejection, which would say the manager decided. Its nurse reads "Your request for … has ended: the month closed before a decision."
- **Worth your review: the manager is told of the schedule's close** (`month_closed`), with how many hard rules the facts broke read when shown, never which. A close by the manager tells nobody: they see it.
- **Worth your review: closing again reads the hours the first close read** for every shift the month holds, since `using_shift` no longer holds a closed month; a first close reads the catalogue's, which cannot have changed while the month was open.
- **Worth your review: "older than the close" is a timestamp:** a draft or submitted roster whose input was stored before a close of any month its nurses' carry-over comes through warns, per nurse, "the month before has closed since", and is checked again on the month as it stands, as at submit. A re-plan is never made outdated by a close.
- **Worth your review: opening values stand at the month a nurse was added** (her first placement's), so ones entered in December reset when her first month in the application is January.
- **On demand runs in the request,** not as a queued job: it is milliseconds, the manager sees what the facts broke at once, and it takes the same locks as the schedule's. It refuses a month whose earlier approved month has not closed.
- **The projected rows are a record.** Every read works the chain out again, so a stored projection never feeds a solve; the card reads live.
- The close's audit entry names the version and whether it closed again; a close by the schedule has no actor.

`docs/ARCHITECTURE.md` sections 4, 5 and 7 and the glossary's Request and Month close moved.

**Review.** The `code-review` skill's two axes against `500d231`.
- Spec found: opening values entered the year before not reset in January; a missed close not due before the close time on the 2nd and later days; the date guards counting a boundary day that does not move; the stale warning only for the month directly before, and none on a submitted roster. All fixed, with tests. It also listed what goes beyond the ticket (the end-date guard, pins counting as facts, the Leave page's state, the "changed since" check, the notification), kept and recorded above. Its note that a pin of an unclosed past month could be read at changed hours does not hold: an approved roster's pins are in its grid, which `using_shift` reads.
- Standards found the app named `closing` against section 8 and the glossary: renamed `closes`, with the module `closes.making`. Also fixed: two dead functions, a wasted query when not projecting, the projection fan-out after a close, and one name (`facts_broke`). Left as judgement calls: function-local imports between `closes` and `solves`/`rosters` (the chain assembles months, and assembling reads the chain), `next_month` beside two private copies, and `(unit, month)` pairs.

`better-interface` and its domain skills, held by hand: the card's table has a named scroll region, row headers and column groups; its confirmation is a polite live region (not a second `status`); a refusal at the press is an alert; the read-only opening values say why; the copy uses the glossary's words (close, carry-over, projected, roster in force). No new colour, type or motion. `interface-review` is yours to invoke.

**Things later tickets should know:**
- **Backup (22):** take a lock of its own with `ops.queue.under_its_own_lock` or `_periodic`'s pattern; `run_the_queue(concurrency=4)` exists for its test.
- **Browser journeys (24):** the manager's journey ends with the month closing and the card on the Roster page; the nurse's with My month of a closed month.
- **The dev stack was not touched.** When this branch reaches `main`, **recreate** (not restart) `worker` there, since `deploy/compose.yaml`'s command changed to `--concurrency 4`, and restart `web`, for `closes.0001`, `requesting.0002` and `notifications.0005`. Without it every new version fails, since `make_version` imports `closes`. On its first run the catch-up closes every approved month whose close time has passed, oldest first. **No new dependency.**
