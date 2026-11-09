# 39: The Day view

**What to build:** The CNO and the Deputy CNO open a Day view from their header and see every unit on one date, today by default: each unit's headcount on each shift it works against its range for that kind of day, whether a team leader and both genders are present where the unit requires them, who is on leave by name, and the month's overtime against the hospital's department cap with how many nurses have any. Every figure comes from the roster in force checked on the month as it stands with the solver's own code, or from the close in force for a closed month. A unit whose month has no roster in force shows its state alone. A row expands to the names on each shift and on leave; a totals line sums the hospital. Earlier day, Later day and a date field move the date, which is in the address. Clicking a unit opens its Unit roster for that month with the date's column marked. The page prints on A4 landscape from the browser. Read-only, nothing audited, nobody floated. Spec: `.scratch/nurse-rostering-v2/specs/day-view.md`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] One new API read answers the hospital's day for a date, for the CNO and the Deputy CNO only: the date, weekday, weekend day or holiday, the shift columns in catalogue order, one row per unit (every unit not archived, and an archived one with a roster or a close that month) and the totals; today on the hospital's clock when no date is given; a malformed date is a 422
- [x] For an approved month not closed, a unit's figures come from one assembly, one check and one accounting with the solver's own code: counts as the solver counts (pure staff plus the shifts that also count), the weekday or weekend range, short and over, team leader and gender findings on that date, and each nurse's overtime equal to My month's; leave wins over a shift; a month over but not closed reads the same way
- [x] For a closed month, the figures come from the close in force (its facts, its findings and its nurses block) and are not worked out again
- [x] Who is on leave comes from the leave rows current for the date, by name, with no leave type anywhere in the answer; a nurse outside her dates is neither on duty nor on leave
- [x] Team leader and gender are null where the unit requires neither; the range is null with headcount off or no headcount entry; the hours rule off gives zero overtime
- [x] A unit whose month is none, draft or submitted has its state and no figures, and no draft cell is in the answer
- [x] The Day view page at `/day` with the date in its search params, guarded for the CNO and the Deputy CNO, with a Day view link in both headers and the phone Menu and no card on Home; Earlier day, Later day and a native date field change the address; the previous day stays shown while the next loads
- [x] The table has real row and column headers, the unit column staying in view while the rest scrolls sideways in a named scrollable region; shift cells read the count against the range with the words short or over, and the words no team leader or one gender, never colour alone; a state-only row says No roster, Draft or Submitted, Submitted linking to the Unit roster
- [x] A disclosure button named for the unit expands its row to the names on each shift with team leaders marked and the names on leave, collapsed by default, with no further request; a totals row at the foot gives on duty per shift, on leave, overtime hours and how many units are short somewhere
- [x] The unit's name links to the Unit roster with unit, month and date; the Unit roster page scrolls that date's column into view and marks its header visibly and to assistive technology, and is unchanged without a date
- [x] A print stylesheet lays the page out for A4 landscape with the header row repeated and the navigation hidden; no file is made and nothing is audited
- [x] No polling: the query reads on load and on a date change
- [x] The read is timed on the seeded stack and the time reported in the ticket comment
- [x] API tests in the style of ticket 14's review tests, on the sound four-nurse rosters of June and July 2026, cover each figure against hand-written expected values: columns, a weekday and a weekend range, short and over through a hand edit, team leader and gender met and null, headcount off, leave by name with no type and not counted, a nurse outside her dates, overtime equal to My month's with the cap and count, the hours rule off, the three state-only rows with no draft cell, a closed month unchanged by later leave and a month over but not closed, an archived unit, today by default, a 422, the totals
- [x] The authorization walk names the endpoint for the CNO and the Deputy CNO only, the System Admin still reaches no roster content, and the OpenAPI export and generated client match a fresh export
- [x] The frontend's app-level Vitest suite covers the link per role and the guard, the default date, day navigation, the heading's weekend and holiday words, the cells' words and blanks, state-only rows, expanding with no new request, the totals row, the link to the Unit roster and that page's marked column, and the loading, error and no-units lines
- [x] One Playwright desktop check in ticket 24's seeded project: the CNO opens Day view from the header, reads a unit's row, expands it and clicks through to the Unit roster with the date marked; `e2e/ci.sh` passes
- [x] `docs/ARCHITECTURE.md` section 8 names the Day view among the CNO's and the Deputy CNO's screens and section 3's "View every unit's rosters" row names it; no ADR (0014 if one is ever needed), no migration expected; the ticket comment says what the dev stack needs (a `web` restart, no rebuild) and what was not checked

## Comments

**From the grilling (2026-11-07).** Covers are not in this ticket: whichever of this feature and "Cover for a sick call" lands second adds an open-covers column. The solver's team leader and gender checks are on the pure staff of each anchor shift; the weekend range follows the hospital rules' weekend days only, and a public holiday changes hours owed, not the range. Per-nurse overtime caps are hard rules, so "nurses above cap" would only ever be a hand edit the Roster page already flags; that is why the view shows a sum against the department cap.

**Implemented on 2026-11-09,** on branch `claude/ticket-39-day-view-914b9b`, pull request
MoustafaJazzar/cp-sat-nurse-roster-app#8 (draft), from `main` at `4d3e8fc` (`edd527a`, `429055e`, `79f363b`, `b3012bc`,
`6f00044`, then this comment with one last change to the page's query). The suites:
- the backend under pytest on a throwaway PostgreSQL 18 container of my own: 2705 passed and one failed on `6f00044`'s
  code less its review fixes, `ops/tests/test_logs.py::test_gunicorn_logs_its_own_lines_and_each_request_as_json`, which fails
  the same way on `4d3e8fc` on this Mac and passes on GitHub; after the review's fixes `rosters/tests/test_day.py` (25) and
  `accounts/tests/test_authorization.py` again. `makemigrations --check` clean;
- the frontend: `npm test` 656 passed, `npm run build` (with `tsc -b`) clean;
- the OpenAPI document and the generated client regenerated, matching the export;
- GitHub: both workflows green on `6f00044` (backend, frontend with its six runs, image, solver, and the browser checks,
  `e2e/ci.sh`, which runs the new desktop check).

**What the dev stack needs:** a restart of `web` would do for the API, but the page is in the image, so `docker compose up -d
--build`. No migration. No change to `deploy/compose.yaml`, the `Dockerfile`, the solver or any dependency.

**What was built, criterion by criterion.**
1. **The read.** `GET /api/rosters/day?date=YYYY-MM-DD` (`getHospitalDay`, `rosters/reading_api.py`), for the CNO and the
   Deputy CNO (`approver`, as the overview). The answer: `date`, `weekday`, `weekend` (the hospital rules' weekend days),
   `holiday` (its name), `shifts` (code and display name, the catalogue's order, any shown unit's), `units` (id, name,
   `archived`, `state`, `figures`, `unchecked`) and `totals`. No date is today on the hospital's clock (`membership.today`); a
   malformed one or one outside the catalogue's years is a 422 (`IsoDate`). Units as the overview chooses: every one not
   archived, and an archived one with a roster or a close that month.
2. **An approved month** (`rosters/day.py`, `_approved`): one `assemble`, the version in force (`Roster.grid`, today's codes)
   with every credited day (leave and the days outside a nurse's dates, the input's `leave`) blanked so leave wins, then one
   `scored` and one `accounted` (`rosters.editing`, the solver's `validate_grid` and `nurses_of`). Short, over, team leader
   and gender are the solver's findings on that date (`rosters.approved.shift_day`, `headcount_of`); the count is the
   solver's way (pure staff plus `also_counts`); the range the headcount entry's weekday or weekend pair. A month over but not
   closed reads the same.
3. **A closed month** (`_closed`): the close in force's `facts`, `facts_broke` and `nurses` block, and its own input's rules;
   nothing worked out again.
4. **Leave by name, no type:** the leave rows current for the date, of the nurses in the month's input, less a nurse outside
   her dates. For a closed month, the rows the close read (recorded by `closed_at`, not removed by then) on the days its input
   credits. No `leave_type` is read or answered.
5. **Nulls:** `team_leader` and `both_genders` null where the unit does not require them; `minimum`/`maximum` null with
   headcount off or no headcount entry; the hours rule off gives `hours_counted: false` and overtime 0.
6. **State-only rows:** `none`, `draft`, `submitted` carry `figures: null`; a draft's cells are nowhere in the answer.
7. **The page** `/day` (`routes/_signed-in/day.tsx`), `date` in the search params (missing or not a real date: today),
   guarded with `onlyFor(cno, deputy_cno)`, "Day view" beside Rosters in both roles' header lists and so in the phone Menu; no
   Home card. Earlier day, Later day and a native date field (`Date`) change the address; the previous day stays shown while
   the next loads (`keepPreviousData`), the controls following the day asked for.
8. **The table:** real column headers and a row header per unit; the unit column sticky; the table a scrollable region named
   "Day view, Thursday, 4 June 2026". A cell reads "3 of 1–2" (or "1 of 1", or "2" with no range) and the words **short** or
   **over**, then "no team leader", "one gender". On leave is a count; Overtime "36 h of 80, 4 nurses", or "Hours not counted".
   A state-only row says No roster, Draft or Submitted, Submitted a link to the Unit roster.
9. **Expanding:** a button "Names in ER" (`aria-expanded`, `aria-controls`) opens a row listing each shift's names, team
   leaders "(team leader)", and On leave; collapsed by default, no request. The foot row "All units" gives on duty per shift
   (the units' counts summed), on leave, overtime hours and "1 unit short somewhere" or "None short".
10. **The link:** the unit's name goes to `/unit-roster?unit&month&date`. The Unit roster accepts `date`
    (`dateInAddress`): `RosterGrid`'s `markedDate` scrolls that column into view once and marks its header with
    `aria-current="date"`, the primary colour and the hidden words ", the Day view's date". Without it nothing changes; the
    manager's Roster page passes none.
11. **Print:** `@page day-view { size: A4 landscape }` on the page's wrapper, the table header a `table-header-group` in
    print, the site header, the description, the day controls and the expand buttons hidden; expanded rows print as they
    stand. No file, no audit entry.
12. **No polling:** the query reads on load and on a date change; no refetch on a window's focus or on reconnecting.
13. **Timed on the seeded stack** (`t39-seeded`, ER 4 nurses and ICU 64, both approved for December 2026): 0.40 to 0.51 s over
    HTTP for 2026-12-01, in-process 0.74 s warm; a closed day (October) 23 ms; a day with no roster 7 ms. Under the load of
    three sessions at once the same read took 1.2 to 2.2 s. Nearly all of it is `assemble`, and in it the carry-over chain's
    per-nurse queries (`closes.chain.carry_in`, `leave_dates`): about 7 ms a nurse. The solver's check and accounting are 15 to
    20 ms for ICU. See Worth your review.
14. **API tests:** `rosters/tests/test_day.py`, 25, on the sound June and July with hand-worked counts: columns, a weekday and
    a weekend range and a holiday, short and over through a hand edit, `also_counts`, team leader and gender met, not met and
    null, headcount off, leave by name with no type and not counted, a nurse outside her dates, overtime equal to My month's
    (and 20 hours for Badr after two more Nights, by hand), the hours rule off, the three state-only rows with no draft cell, a
    closed month unchanged by leave recorded after it, leave a correction left outside her dates in a closed month, a month
    over but not closed, archived units with a roster and with only a close, today by default, two 422s, the totals, July.
15. **The walk:** `GET /api/rosters/day` added to `ROSTER_ROLES` as `APPROVERS`; the System Admin's no-roster-content check
    covers it. The OpenAPI export and client match.
16. **Frontend tests:** `app.test.tsx`, "the Day view" (12) and the two header lists: the link per role and in the Menu, no
    Home card, the guard, today by default, Earlier, Later and the date field with the previous day held, the weekend and
    holiday words, the cells' words and blanks, the state-only rows, expanding with no request, the totals, the link and the
    marked column, no column marked without a date, the loading, error and no-units lines.
17. **Playwright:** `e2e/tests/desktop/day.spec.ts`: the CNO opens Day view from the header, sets the date to the first day of
    the seeded approved month, reads ER's row, expands it and clicks through to the Unit roster with the date's column marked
    and in view. Passed on my stack and in GitHub's `e2e/ci.sh`.
18. **Docs:** `docs/ARCHITECTURE.md` section 3's row and section 8's screens for both roles. No ADR, no migration.

**What was driven, and how.** Scratch stack `t39-seeded` (`E2E_PORT=18390`), seeded, on `6f00044`'s code, under the shared
heavy-work lock, then taken down. Carla (CNO) through the API, timed above, and in the browser pane: the header link; Friday 4
December 2026 read "weekend day", ER "1 of 1", "2 of 1–2", "0 h of 400, 0 nurses", ICU "16 of 16", "18 of 16–32", "12 h of
400, 1 nurse", totals 17 and 20; both rows expanded to their names with team leaders marked; ER's link opened its December
roster with the 4th marked in the header. Printed once to PDF from Chromium (print media, CSS page size): one A4 landscape
page, the table with ICU expanded, no header or controls.

**What was NOT checked.** The header row repeating across printed pages (the seeded day fits one page); a real phone; a
screen reader (the names and states were read through the accessibility tree only); a unit whose month the solver's loader
refuses (the `unchecked` line); the page under thirty units.

**Decisions I took.**
- Leave wins before the check, not after: credited days are blanked in the grid that is checked and accounted, so the count,
  the findings and the overtime agree with each other and with My month. The Roster page's own check of the same version
  still counts such a shift and flags it as `unavailable`; the Day view does not repeat that.
- A shift with no headcount entry shows its own staff and nothing else: the solver checks team leader and gender only on
  headcount shifts, so those are null there even where the unit requires them.
- The totals sum the columns as shown, so with `also_counts` a nurse counts under both shifts, as each unit's cell does.
- The heading's weekend is the hospital rules' now; a closed month's ranges are its close's rules. They can differ only if
  the weekend days changed since.
- A closed month's leave is the rows the close read, less a nurse outside her dates as they are now: the close keeps no
  nurse's dates.
- `unchecked`: an approved month the solver's code cannot read says so in its row ("Could not be checked. The solver's code
  says: …") rather than failing the whole read.
- "Overtime this month" as the column's name, "All units" as the foot's row header, "(archived)" after an archived unit's name
  as on the Rosters page.

**Worth your review.**
- **The open-covers column was left out.** Section 3 gives the CNO and the Deputy CNO no covers, and the covers code says
  they see none, so showing them would change the documented access rules: the user's decision. The option, if wanted: per
  unit, a count of covers still waiting (open or offered) on that date, by shift code only, with no reason, note, offers or
  names; section 3's covers row would gain "a count of waiting covers on the Day view" in the CNO's and the Deputy CNO's
  columns.
- **The read's cost** is 7 ms a nurse, nearly all in the carry-over chain that `assemble` reads per nurse; a 300-nurse hospital
  would wait about 2 s. No caching was added. A batched `Chain.carry_in` would speed this, My month and every check; that is
  `closes/` and `solves/input.py`, outside this ticket.
- `refetchOnWindowFocus: false` is on this query only; the Rosters overview still refetches on focus.

**For later tickets.** The covers column above. Ticket 38 (skills on the roster in force) and any other rule the view should
flag would add to `rosters/day.py`'s `_figures`, which reads only headcount, team leader and gender findings.
