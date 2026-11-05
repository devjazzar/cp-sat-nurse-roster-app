# 14: Submit, approve, reject

**What to build:** The unit manager submits the draft; it freezes. The Deputy CNO and the CNO see submitted rosters waiting on their home page, open one with the grid and every result detail, and approve or reject it with a comment. Approval makes it the roster in force: the unit's nurses now see it with colleagues' names and shifts only. A rejection returns it to draft with the comment visible to the manager. Approvers see a per-unit, per-month overview (no roster, draft, submitted, approved) and can view any unit's roster read-only.

**Blocked by:** 11 Run a solve

**Status:** ready-for-agent

- [x] Roster states draft → submitted → approved, submitted → draft on rejection with the comment kept; a frozen draft refuses edits and solves
- [x] Approvers' home lists submitted rosters; approve and reject with comment; both audited
- [x] First approval creates roster version 1 with origin 'solve'
- [x] Nurse roster page shows the approved roster for the current and coming months with names and shifts only
- [x] Overview of every unit's state per month for the CNO and Deputy CNO; read-only roster view of any unit
- [x] API tests cover the state machine, authorization of each transition, and the nurse view's field restriction

## Comments

**From ticket 10 (2026-11-05): two things to hold.**

- **Colleagues see a day off.** Ticket 10 ticked this at the seam only, and this ticket's nurse roster page is where it becomes true or false. A colleague's leave day must be the same `""` as any day off, which `roster` in a result already is. So the read's plain schema must not take anything from the result's `nurses[id]` (it holds `leave` and `leave_credit`), from the stored input's `nurses[].leave`, or from `Leave`, for anyone but the nurse reading. Add a test that a colleague's leave day and day off are indistinguishable in the answer, and one that their own cell may differ. An approver's read-only view may show leave as leave. A stored input and a result hold no type, so any type it shows comes from `Leave`, which the CNO and the Deputy CNO may read since the change on ticket 10 (2026-11-05).
- **Leave under a frozen or approved roster.** Leave writes look at no roster today. A submitted roster is frozen, but leave recorded during it changes what the approver is deciding on: refuse it there, or re-validate and show it, in `_refuse_dates` and `_rows_to_change` in `nurses/leave_api.py`. Ticket 16 has the approved case.

**Decisions from the user (2026-11-05).** A draft older than a change to a start date, gender or leave: warn, and block submit only if validating again fails. So submit validates such a draft again through the solver's validate call: a pass goes through with the warning shown, a failure refuses the submit. Ticket 11 has the warning.

**Leave recorded while a roster is submitted is allowed** (settled 2026-11-05), which answers "refuse it there, or re-validate and show it" above. Warn the approver and validate again at approval, blocking approval only if that fails.

**From ticket 11 (2026-11-05).** What to hold when freezing: `solves.api.start_solve` looks at no roster state, and `solves.running._finish` calls `drafts.replace_grid` whatever the state. A solve queued before a submit must not replace a frozen grid when it ends, so check in both. `changes_since(solve.input, unit, month)` in `solves/input.py` is the stale-draft comparison, and `Draft.changes` is the warning: submit validates such a draft again through the solver's validate call and refuses only if that fails. It compares gender, credited days and who is in the month, and start and end dates count through their credited days. `Roster.solve` is the solve of the grid; once a hand edit exists, compare with that input still. Roster versions were not begun here: the first approval creates version 1, as this ticket says. Open reading of `getRosterMonth` to the approvers here: it is manager-only today.

**From ticket 12 (2026-11-05).** Three things.

- **Restore is a third path that must check the roster's state.** Beside `start_solve` and `_finish` (the comment above), `solves.history_api.restore_result` writes `Roster.grid` through `rosters.drafts.replace_grid`. It looks at no state today. Refuse it while the month's roster is submitted or approved, in `rosters.drafts.why_not_restore`, which the page also reads to say why instead of offering the button, so that one place holds. A test should hold it.
- **Opening the panels to the approvers is yours.** `getSolveResult` (`/units/{id}/solve-history/{solve_id}`), which holds the accounting, the explanations, the statistics, the facts and the grid, and `listUnitSolveHistory` are the manager's only, as `getRosterMonth` is. To open them, widen `auth=manager` in `solves/history_api.py`, and keep `restoreSolveResult` the manager's. `components/solve-result.tsx` is the panels and takes a `SolveResult`; `restore_refusal` should be left out or ignored for an approver, because they cannot restore. A stored result holds leave dates, which an approver may read, and no type.
- `accounts/tests/test_authorization.py` walks the endpoints; a test in `solves/tests/test_history.py` currently holds that the CNO and the Deputy CNO are refused these reads. Change it when you open them.

**From ticket 13 (2026-11-05).** Saving pins is a fourth path that writes `Roster.grid`, beside a solve's start and end and a restore (the comments above), and two more read the roster without looking at its state.

- **Saving pins must check the roster's state.** `rosters.api.save_pins` writes the grid and `rosters.models.PinnedCell` rows. It refuses only a month that is over today, through `rosters.api._why_not_edit`, which the page also reads as `Draft.editor.refusal` to offer no editing and say why. Put "submitted" and "approved" there, so one place holds for the page and the save. A test should hold it.
- **Leave on a pinned day ends the pin whatever the roster's state** (`rosters.pins.end_for_leave`, called from `nurses.leave_api._begin`). Leave during a submitted roster is allowed, as settled: it also ends a pin the approver is looking at, and the grid keeps the pinned shift on a day of leave. Your re-validation at approval sees that as a broken hard rule (`unavailable`), so nothing more is needed unless you want the approver told which pin went: `Draft.pins_lost_to_leave` has it.
- **The check** (`POST /units/{id}/roster/check`) reads and writes nothing of the roster's state, so it can stay open while frozen, or be refused with the save.
- **Validating at submit:** `rosters.editing.check_saved(roster)` already scores the saved grid on the month as it stands with the solver's own code in `web`, and `Draft.check` carries it for an edited draft. Pins are now in `changes_since` too, as `what: "pins"`.
- **`Roster.updated_at` no longer moves on a hand edit** (`save(update_fields=["grid"])`), so a failed solve before an edit is still `last_solve`. If submitting needs "last changed", read the pins' `pinned_at` and `removed_at` as well.

Implemented on 2026-11-05, on branch `claude/ticket-14-submit-approve-5dc618`. Backend under pytest on a throwaway PostgreSQL 18 container of my own. Frontend under Vitest with the real routes and generated client over a stubbed `fetch`. Results: backend 1661 passed, frontend 424 of 424, `npm run build` clean, `makemigrations --check` clean, `frontend/openapi.json` the same as a fresh export. The solver's suite was not run: nothing under `solver/` changed.

Seams:
- `rosters/tests/test_review.py`, 69 tests: the API with the scripted solver and the real worker's code.
  - A submit and an approval check the grid with the solver's own code, so the scripted all-Day roster would be refused. These tests use a real optimal roster of the four-nurse sample for June and July 2026. I solved it once with the real solver and kept it as `rosters/tests/fixtures/sound_rosters.json`.
- `rosters/tests/test_two_at_once.py`, 5 races on the real PostgreSQL, in the style of `nurses/tests/test_two_at_once.py`. The second transaction is seen waiting for a lock before the first commits, so the order is forced, not hoped for.
- `accounts/tests/test_authorization.py`: each roster transition's and read's roles are named, and the System Admin is held to reach none.
- `app.test.tsx`: 400 tests became 424, 19 new ones and the three new pages in the route guards, through `start` and `hold`. No raised timeout, no fake timers, no wait that proves something did not happen.
- **Since the code came before most of its tests, I broke each guard by hand and saw its test fail**: `_finish`, a restore, a solve's start, a pin save, the nurses' lock (unit test and race), the re-check at approval, and a colleague's leave reaching the nurse's answer.

**Driven in the built-in browser,** on scratch project `nr-t14`. It ran the production compose file with its own image, secrets and volumes, `web` published on `127.0.0.1:18014` under `DJANGO_DEBUG`, no Caddy, and the real solver and worker. The units were the solver's four-nurse sample as ER and as ICU, rostering December 2026. Everything has been removed since. The run covered:
- A real solve from the page (cost 127).
- Leave on a nurse's day off, then **a stale-draft submit** from the page. The warning showed, Submit sat beside the draft and went through. Focus moved to the status line, and the cell editor and the solve form were gone.
- **Refusals on the submitted roster, over the real API:** a solve, a pin save, the check and a restore were all 409, each with the one sentence. Leave was still recorded.
- **Leave on a worked day while submitted.** The Deputy CNO's home listed the roster with "Something has changed since it was submitted". The roster read "leave or dates changed, since it was submitted", with the broken `unavailable` rule. Approve was refused, saying why.
- **A rejection with a comment**, typed and sent. Focus went to the status line, and the grid left the approver's view.
- **The overview**: ER in December reading Draft, not a link.
- **The manager saw the comment** above the draft, solved again (cost 119, leave taken in), and **resubmitted**, with the comment kept as "Rejected before this submit".
- **The CNO approved through the dialog.** Escape returned focus to Approve. After confirming, focus went to "Approved … Version 1 is in force".
- **A colleague's view:** Amal read Badr's two days of sick leave as "Off", the same as his day off, with the word "leave" nowhere in her answer. Badr read his own as "L".
- No sideways page scroll at 375 px on My roster.

That run found two bugs no test had, both fixed with tests:
- **What was new since a submit compared only whose and what kind of change.** A second leave of a nurse the manager had already been warned of did not show to the approver. The submit now keeps the month's nurse rows in a solve input's words: gender, credited days, the pins that count, and no leave type. What changed since is compared with those rows.
- **Submit sat below the long result panels.** It now sits beside the draft's check.

It also led to one change: a nurse's home spoke only of this month though the next was approved, so it now links to My roster for the months ahead.

What was NOT checked:

- **The frontend suite under load, or from a clean export.** `npm test` ran alone in the working tree.
- **An approved roster refusing a solve, a pin save and a restore, in a real browser.** API tests only; the submitted case was driven.
- **The approvers' pages at 375 px, dark mode, 320 px, 200% zoom, RTL, a screen reader, and browsers other than the built-in one.**
- **The races in a browser.** They are tests on real connections only.
- **Through Caddy.**
- **The audit log page with the new entries.** The labels are in `ACTION_NAMES`; the entries' contents are API tests.
- **A large unit.** Each read of a month assembles it again for what changed since the submit, as it already did for the draft's own changes.

**Decisions taken here:**

- **Worth your review: the CNO and the Deputy CNO see a draft only as one that exists.** The glossary's Draft says nobody outside the unit's management sees one; the ticket says "view any unit's roster". I read both as: the approvers read a submitted or an approved roster, grid and every result detail, and a month in draft shows them only its state (`rosters.review.SEEN_BY_APPROVERS`). That holds for `getRosterMonth`, the unit's solve history and a result, which is a 404 for a draft month. So a rejected roster goes out of their sight, with its comment, until it is submitted again. Opening drafts to them is a change in one place.
- **Worth your review: there is no way to withdraw a submit.** It is not in the ticket or the lifecycle. A manager who wants a submitted roster back asks for a rejection. The races are therefore with a second approver, with each other's decision, with leave and with a solve's start.
- **A solve queued or running refuses the submit** ("Stop it or wait for it first"), as a restore does. So no solve ends on a frozen grid through the API. `_finish` still checks: one meeting a roster frozen behind the API's back keeps its result in the history and leaves the grid alone. `replace_grid` also refuses on its own.
- **One check freezes a roster**, `rosters.drafts.why_frozen`, behind a solve's start and preview, `_finish`, `why_not_restore`, and `_why_not_edit` (a save of pins and the check). A rename still follows a frozen grid, since it is the same shift; a test holds it. Leave is recorded as before and ends a pin there, as you decided.
- **Submit always checks again** with `check_saved`. It refuses a draft that breaks a hard rule or cannot be checked, and a pin breaking one (ticket 13 left that here). A stale draft that passes goes with its warning, as you decided. **Approval checks again the same way** and refuses only if that fails.
- **Locks:** approve and submit take the catalogue's lock, then every nurse of the month's (user and profile, the lock a leave write takes), then the unit's and the roster's. Reject takes the catalogue's, then the unit's. Of two approvers, the second waits and is told "approved already by Carla CNO". The races are tests.
- **An approval of a month already over is allowed**, though its submit is not. A late decision on a submitted roster still makes the record month close needs (ticket 21). Say if you want it refused.
- **Version 1** is `Roster.grid` as approved, so it holds hand edits, with origin `solve` and the roster's solve. The pins say where a cell came from. A version keeps its codes and is read under today's. Ticket 16 has a comment.
- **Rejection comments:** one `Submission` row per submit, so every comment stays; the latest shows to the manager until approval, including through the next submit. The audit entries `roster.submitted`, `roster.approved` (with `{"version": n}`) and `roster.rejected` name the unit and month only. A comment can name a nurse and their leave, so it is not in the log; a test searches the log for it.
- **The nurse's view** (`GET /api/rosters/mine`, page My roster):
  - Built from the latest version, `User` names, and the weekend and holidays from the hospital's settings. Each colleague is a hospital ID, a name, and a shift or `""` a day. Only the reader's own row (`mine`) says leave or outside their dates, from `Leave` and their own profile.
  - Tests compare whole answers before and after a colleague's leave, a start date and a deactivation.
  - **The hospital ID stays in a colleague's row**, as it is the name a nurse carries on every roster (the glossary's Hospital ID).
  - The unit is the one the month falls under for the reader, so a transfer shows each month its own unit's roster. A nurse due to start sees their unit's roster with no row. A manager with a nurse profile reads theirs; one without sees none.
  - This month and later only.
- **Approvers' pages:**
  - Their home lists what waits, oldest first, with a flag when something changed since. It is the CNO's home too, since the CNO approves.
  - Rosters (`/rosters`) is every unit's state over four months.
  - Unit roster (`/unit-roster?unit=&month=`) shows the roster read-only, what changed, with "since it was submitted" marked, the check, the pins leave ended, the result's panels, and Approve behind a question with a Reject form needing a comment.
  - The solve history pages stay the manager's in the interface. The API opens them to the approvers for submitted and approved months, and `restore_refusal` tells an approver only the manager restores.
- **`RosterMonth.draft` still carries the grid when the roster is submitted or approved,** under that name, rather than renaming the field and every page and test that reads it. `state` says which it is.
- **A manager with a nurse profile can open My roster** (the route and the API admit them), but their header has no link to it, as it has none to My leave: the header cannot tell whether they have a profile. Say if they should have one.
- **Small additions:** a `Textarea` in the shadcn style, `ConfirmDialog`'s `tone`, and `components/roster-notes.tsx` holding what the two roster pages share.

`docs/ARCHITECTURE.md` sections 4 and 5 and the glossary's Submitted and Rejected moved. **Migration:** `rosters.0004_submissions_and_versions`.

**Review.** The `code-review` skill's two axes against `3ddb1a3`.

Spec found:
- No notes yet for later tickets.
- No test of a start date or of a deactivated colleague on a nurse's roster.
- Submit taking no nurses' lock, so leave between its check and the month it keeps could go unflagged to the approver.

All fixed. It also raised the version origins only later tickets use (kept: section 4 names them), the own row's kinds (kept, as above), the check refused while frozen (a choice ticket 13 allowed), the hospital ID and the month over (both above).

Standards found no hard violation. Fixed:
- "snapshot", an Avoid word, as a name.
- The nurse's read taking the overview's filter.
- A query repeated in `why_not_decide`.
- Missing type hints.
- The result details and the state headings duplicated between the two roster pages.

Left as judgement calls:
- The `approver` and `reader` guards defined per module, as `leave_api.py` does.
- The shift schemas per page.
- `RosterMonth` built on two branches for the two kinds of reader.
- `decision=""` for undecided.
- The state literal beside `RosterState`, as ticket 11 did for the solve's.
- The sorted call list in the role-homes test, since the homes now read two things at once.
- Submission is not in the glossary: it is a record, and the glossary's Submitted is the word for its state.

`better-interface` and its domain skills, by hand from the code and the run: focus follows every button that goes, Escape returns to Approve, refusals say why before the press, the comment's field has its label and description, and the new copy uses the glossary's words. `interface-review` is yours to invoke.

**Things later tickets should know:** comments are on 15, 16, 17, 18 and 21. **The dev stack was not touched:** no restart, no migration, no login. When this reaches `main`, its `web` reloads the code from the main checkout at once, and the Roster page and saving pins fail for want of `rosters.0004` until `web` and `worker` are restarted.

**Reviewed by the user (2026-11-06), and kept as built:** the CNO and the Deputy CNO see a draft only as one that exists, so a rejected roster leaves their view until it is submitted again; a submitted roster cannot be withdrawn, and a manager who wants it back asks for a rejection; a month already over can still be approved; and a manager with a nurse profile can open My roster with no link to it in their header, which you chose to keep over adding one.
