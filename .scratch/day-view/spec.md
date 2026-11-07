# The Day view: one date across every unit

Status: ready-for-agent
Type: enhancement
Published: 2026-11-07 by /to-spec
Ticket: `.scratch/day-view/issues/01-day-view.md` (one slice).

Spec drawn from the grilling of 2026-11-07 (two rounds, every answer as recommended). Vocabulary: `GLOSSARY.md`, whose
**Day view** entry this branch adds. Decisions and their reasons: `docs/ARCHITECTURE.md` and `docs/adr/`. Where this spec
and those documents disagree, the documents win and this spec is wrong.

## Problem Statement

**The CNO and the Deputy CNO see the hospital one unit at a time.** The Rosters overview says where each unit's roster
stands, month by month, and the Unit roster page shows one unit's month. Nobody can see the hospital on a date: which
units are short on a shift today, which have no team leader or only one gender on a shift, who is away, and where
overtime is piling up. These are the blind spots the 2026 HealthStream survey found in department-only scheduling, where
57% of hospitals are. To answer "how is the hospital staffed on Thursday?", the Deputy CNO opens thirty rosters.

## Solution

**A Day view for the CNO and the Deputy CNO**: one date, every unit in a row. For each unit, from the roster in force and
checked on the month as it stands with the solver's own code: the headcount on each shift against the unit's range, its
team leader and gender requirements met or not where it has them, who is on leave, and the month's overtime against the
hospital's department cap. A unit whose month has no roster in force shows its state alone. A date in a closed month shows
the close's facts. A row expands to names; a totals line sums the hospital. Clicking a unit opens its Unit roster on that
month with the date's column marked. Today by default, any date on request. Read-only, and it floats nobody: a nurse
belongs to one unit and is never rostered on another.

## User Stories

1. As the Deputy CNO, I want one page that shows every unit on one date, so that I see the hospital's staffing without opening each unit's roster.
2. As the CNO, I want the same page, so that I read the hospital as the Deputy CNO does when I stand in.
3. As the Deputy CNO, I want the page to open on today, by the hospital's clock, so that the usual question needs no typing.
4. As the Deputy CNO, I want Earlier day and Later day links and a date field, so that I read tomorrow, next Friday or a date last month.
5. As the Deputy CNO, I want the date in the page's address, so that I can share or bookmark a day.
6. As the Deputy CNO, I want each unit's headcount on each shift it works, so that I see who is on duty where.
7. As the Deputy CNO, I want each headcount shown against the unit's range for that kind of day, weekday or weekend, so that a short or an overfull shift is plain.
8. As the Deputy CNO, I want a short or overfull shift marked in words, not by colour alone, so that I read it on any screen and in print.
9. As the Deputy CNO, I want the count counted as the solver counts it, pure shift staff plus the shifts that also count, so that the page never disagrees with the Roster page's check.
10. As the Deputy CNO, I want a unit with headcount switched off to show its counts with no range, so that I am not shown a rule the unit does not have.
11. As the Deputy CNO, I want to see whether each shift has a team leader, where the unit requires one, so that a shift without a lead stands out.
12. As the Deputy CNO, I want to see whether each shift has both genders, where the unit requires it, so that the hospital's rule is visible across units.
13. As the Deputy CNO, I want nothing shown for team leader or gender where the unit requires neither, so that a blank is not mistaken for a failing.
14. As the Deputy CNO, I want to see who is on leave in each unit that day, by name, so that I know who is away.
15. As the Deputy CNO, I want no leave type on the Day view, so that a glance at the hospital says who is away and not why; the type stays on the unit's Leave page, which I may read.
16. As the Deputy CNO, I want each unit's overtime for the month, as the roster in force plans it, so that I see where the month is costing hours.
17. As the Deputy CNO, I want that overtime against the hospital's department overtime cap, with how many nurses have any, so that I see the unit's exposure in one figure.
18. As the Deputy CNO, I want the overtime figure to be the one each nurse reads on My month, so that no two pages disagree about a nurse's hours.
19. As the Deputy CNO, I want a unit whose month has no roster in force to show its state alone, No roster, Draft or Submitted, so that I know why it has no numbers.
20. As the Deputy CNO, I want a Submitted state to link to the Unit roster as the overview does, so that I can go and decide it.
21. As the Deputy CNO, I want a date in a closed month to show the close's facts, so that the past reads as it happened, whatever has been corrected since.
22. As the Deputy CNO, I want counts in each row and names only when I expand a unit, so that a hospital of three hundred nurses is still one screen.
23. As the Deputy CNO, I want an expanded unit to list the nurses on each shift with its team leaders marked, so that I can see who leads.
24. As the Deputy CNO, I want a unit expanded or collapsed without the page reloading, so that the page stays quick.
25. As the Deputy CNO, I want a totals line for the hospital, on duty per shift, on leave, overtime hours and how many units are short somewhere, so that the hospital reads in one line.
26. As the Deputy CNO, I want to click a unit and land on its Unit roster for that month with the date's column marked, so that I go from the figure to the roster behind it.
27. As the Deputy CNO, I want the columns to be the shifts any unit works that day, blank where a unit does not work one, so that units with different shifts share one table.
28. As the Deputy CNO, I want the date's heading to say the weekday and whether it is a weekend day or a public holiday, so that I know which range applies and why hours differ.
29. As the Deputy CNO, I want an archived unit shown only when it has a roster for that month, so that old units do not clutter today and past months stay complete.
30. As the Deputy CNO, I want a Day view link in my header, so that it is one click from any page.
31. As the Deputy CNO, I want the page to print on A4 landscape from the browser, so that I can take the day to a meeting.
32. As the Deputy CNO, I want the page to show what it read when I loaded it and to refresh when I reload or change the date, so that it does not flicker or poll while I read.
33. As the Deputy CNO, I want the whole hospital to arrive in one request, so that the page does not fill unit by unit.
34. As the Deputy CNO, I want only headcount, team leader, gender and overtime flagged, so that the page is a day view and not every rule; the Roster page has the rest.
35. As the Deputy CNO on a phone, I want the table to scroll sideways within the page, so that nothing is cut off.
36. As a screen reader user, I want the table with row and column headers, the expand control named for its unit, and the short and overfull marks as text, so that I read the day as a sighted user does.
37. As a keyboard user, I want to expand a unit and move between days with the keyboard, so that the page needs no mouse.
38. As a Unit Manager, I want no Day view, so that I am not offered the hospital's figures; my Roster page is my unit's day.
39. As a Staff Nurse or the System Admin, I want no Day view, so that nothing I may not read is offered to me.
40. As the System Admin, I want no audit entry for a Day view read, so that the log stays about changes; the view is a read of what its readers can already read.
41. As the CNO, I want the Day view to float nobody, so that a short unit is a fact to act on elsewhere, never a reassignment made here.

## Implementation Decisions

- **One new API read: the hospital's day for a date**, for the CNO and the Deputy CNO only, as the overview is. The date is a
  query parameter; left out, it is today on the hospital's clock. Any date is accepted. It is the only new endpoint; the OpenAPI
  export and the generated client are regenerated.
- **The answer** holds: the date, its weekday, whether it is a weekend day by the hospital rules, the public holiday's name if
  it is one; the shifts that are the columns, in the shift catalogue's order; one row per unit; and the totals.
  - **The columns** are the codes any shown unit works that day: the unit rules' shifts for a unit whose month is approved, and
    the codes its roster or close holds for a closed month, so a shift retired since still shows under its code. Codes are
    read under today's codes, as every version is.
  - **A unit row** is the unit's id, name, whether archived, the month's state (`none`, `draft`, `submitted`, `approved`,
    `closed`) and, for `approved` and `closed` only, its figures: per shift the count present, the range for that kind of day
    (null when the unit's headcount rule is off or the shift has no headcount entry), whether it is short or over, whether a
    team leader is present (null where the unit does not require one), whether both genders are present (null where not
    required), and the nurses on the shift (hospital ID, full name, team leader flag); the nurses on leave that day
    (hospital ID, full name, no type); the month's overtime in hours, the hospital's department overtime cap, and how many
    nurses have any overtime. With the hospital's hours rule off nothing is owed, so overtime is zero and the page says so.
  - **The totals** are, per shift, how many are on duty across the hospital; how many are on leave; the overtime hours summed;
    and how many units are short on at least one shift.
  - **Units shown**: every unit not archived, and an archived one with a roster or a close for that month, as the overview
    chooses.
- **Where the figures come from, for an approved month not yet closed.** For each unit, once: the month's solve input is
  assembled as it stands (the same assembly the Roster page's check and My month use), the version in force is read under
  today's codes, and the solver's own code gives both the hard-rule findings (the Roster page's check) and each nurse's hours
  accounting (the per-nurse block ADR 0009 lifted into the vendored package beside the validation). From those, for the date:
  - the count on each anchor shift is the solver's, pure shift staff plus the shifts that also count towards it, and the range
    is the headcount entry's weekday or weekend pair by the hospital's weekend days (a public holiday does not change the
    range);
  - short or over is a headcount finding on that date for that shift, team leader and gender likewise, so the page can never
    disagree with the Roster page's check;
  - a nurse's overtime is the accounting's `overtime`, exactly My month's figure; the unit's is their sum; the cap is the hospital
    rules' department overtime cap.
  - Leave wins over a shift, as everywhere: a nurse on leave that day is not counted on a shift the version may still hold.
  - A month over but not yet closed (the half hour before the close, or a worker down) reads this way too, as My month does.
- **For a closed month**, the close in force is the record: its facts (the month as it happened) give the counts and the nurses
  on each shift, its findings give short, over, team leader and gender on that date, and its nurses block gives the overtime.
  Nothing is worked out again, so a correction made since leaves the day as the close read it.
- **Who is on leave** comes from the leave rows current for that date, for the nurses the month places in the unit: not from
  the roster's credited days, which mix leave with days outside a nurse's dates. A nurse outside her dates is neither on duty
  nor on leave. Leave's type is not read.
- **A unit whose month is `none`, `draft` or `submitted`** has its state and no figures. Drafts stay the unit management's
  alone: the approvers already see one only as existing (ticket 14, kept). A `submitted` state links to the Unit roster as the
  overview does; `none` and `draft` do not.
- **Cost**: one assembly, one check and one accounting per unit per read, tens of milliseconds each on the 25-nurse sample, so
  one request serves the whole hospital. The ticket times the read on the seeded stack and reports it; no caching unless the
  measurement demands it, and then per request only.
- **The page** lives at `/day` with the date in its search params (`date`, ISO; missing or malformed, today). Guarded for the CNO
  and the Deputy CNO as the Rosters page is. Title "Day view".
  - The header's link lists for the CNO and the Deputy CNO gain **Day view**, beside Rosters. No card on Home.
  - A heading with the date in full, the weekday, and "weekend day" or the holiday's name when it is one. **Earlier day** and
    **Later day** links and a native date field; changing it changes the address. The previous day's table stays while the
    next loads, as the overview keeps the previous month.
  - One table, the unit the row header, a column per shift, then On leave, then Overtime. Row and column headers are real
    headers. The first column stays in view while the table scrolls sideways; the table is a scrollable region named for the
    date, as the overview's is. The page keeps within the width on a phone; it is not made for a phone first.
  - A shift cell reads the count against the range, "3 of 4–6", and the words "short" or "over" when it is; the team leader
    and gender marks are words ("no team leader", "one gender"), never colour alone. A unit requiring neither shows nothing
    there.
  - The On leave cell is a count; the Overtime cell is "36 h of 80, 4 nurses".
  - A state-only row says No roster, Draft or Submitted in the state's cell, spanning the shift columns.
  - **Expanding** a row, by a disclosure button named for the unit, shows the names on each shift with team leaders marked, and
    the names on leave. Collapsed by default; the answer already holds the names, so expanding fetches nothing.
  - A totals row at the foot.
  - The unit's name is the link to the Unit roster with `unit`, `month` and the new `date`.
  - Loading and error lines as the overview's; "There are no units yet." when there are none.
- **The Unit roster page accepts a `date`** in its search params: the roster grid scrolls that date's column into view and marks
  its header, visibly and to assistive technology. Without `date` nothing changes. The manager's Roster page is not changed.
- **Printing** is the browser's print of the page: a print stylesheet lays the table out for A4 landscape with the header row
  repeated, hides the navigation and the controls, and prints expanded rows as they stand. No file is made, so no audit entry,
  as for the roster print page (decision 43).
- **No polling.** The query reads on load and on a date change; a reload is the refresh.
- **Nothing is written** by the view and nothing is audited: reads are not logged today, exports aside, and the view shows only
  what its readers can already read on the Unit roster, the unit's Leave page and the attributes page.
- **`docs/ARCHITECTURE.md`**: section 8's screens per role gain the Day view for the CNO and the Deputy CNO; section 3's row
  "View every unit's rosters, with the per-month state overview" names the day view too. No ADR: nothing here is hard to
  reverse. (If one is written after all, it is 0014; 0010–0013 are the other grillings'.) The glossary's **Day view** is on this
  branch.
- **Covers** are not in this spec. Whichever of this feature and "Cover for a sick call" lands second adds an open-covers column
  to the Day view; this spec carries no dependency on the cover feature.
- **Hard limit**: the view floats nobody. No control on it changes a roster, a placement or a cell.

## Testing Decisions

- **What a good test is here:** it reads the API's answer or the rendered page as a reader would, and checks figures, words,
  links and accessible names. It does not check how the figures were worked out, which query ran or how the router is wired.
  Figures are checked against a roster whose truth is known, never against the code that produced them.
- **Seam 1, the API** (the main seam), in the style of ticket 14's review tests: through the API with the real worker code, on
  the real four-nurse sample roster approved for June and July 2026 (`sound_rosters.json`), with the scripted solver where a
  solve is needed. Each test knows the fixture's cells, so the expected counts are written by hand:
  - the columns for a day, in catalogue order, blank where a unit does not work a shift;
  - a weekday's and a weekend day's count against the right range, and "short" and "over" when a hand edit of the approved
    roster (which saves even breaking a hard rule) makes them so;
  - team leader and gender met or not, and null where the unit requires neither; headcount off giving counts with no range;
  - leave recorded on a worked day: the nurse on leave by name, no type anywhere in the answer, not counted on the shift;
  - a nurse outside her dates neither on duty nor on leave;
  - overtime equal to what My month answers for each nurse, summed, with the cap and the count;
  - the hours rule off: zero overtime;
  - `none`, `draft` and `submitted` rows with no figures; a draft's cells nowhere in the answer;
  - a closed month read from the close in force, unchanged by leave recorded after the close; a month over but not closed read
    as approved;
  - an archived unit shown only with a roster or a close that month;
  - today by default on the hospital's clock, and a malformed date refused as a 422;
  - the totals;
  - the authorization walk names the endpoint for the CNO and the Deputy CNO only, and the System Admin reaching no roster
    content still holds;
  - the OpenAPI export matches the committed copy.
- **Seam 2, the frontend's app-level Vitest suite**, the whole app rendered at `/day` over a mocked API, as the Rosters and Unit
  roster tests are:
  - the Day view link for the CNO and the Deputy CNO, and for no other role, on a wide screen and in the phone Menu;
  - the route guard sending other roles home;
  - today by default; Earlier day, Later day and the date field changing the address and the table;
  - the heading's weekend and holiday words;
  - the shift cells' words for short, over, no team leader and one gender, and the blanks;
  - a state-only row, with Submitted linking to the Unit roster and Draft not;
  - expanding a unit showing its names with team leaders marked and its leave names, collapsed by default, no new request;
  - the totals row;
  - the unit's link carrying `unit`, `month` and `date`, and the Unit roster page marking that column;
  - loading, error and no-units lines.
- **Seam 3, one Playwright desktop check** in ticket 24's seeded project: the CNO opens Day view from the header, reads a unit's
  row for the seeded approved month, expands it, and clicks through to the Unit roster with the date marked. No new spec file
  beyond the desktop folder; it runs with `e2e/ci.sh`.
- **Prior art:** the review tests on the sound rosters and the authorization walk in the backend; the Rosters, Unit roster and
  header tests in the frontend's app-level suite; ticket 24's desktop checks in `e2e/`.

## Out of Scope

- Floating a nurse to another unit, or any control that changes a roster from this page. A nurse belongs to one unit (GLOSSARY,
  Unit); floating would be a separate feature with its own ADR.
- An open-covers column: whichever feature lands second adds it.
- A Day view for the Unit Manager, the Staff Nurse or the System Admin.
- Overtime "so far" on a date within the month: the solver's arithmetic is monthly, and the page shows the month's.
- Flagging any rule other than headcount, team leader, gender and overtime; the Roster page shows the rest.
- A draft's figures: approvers see a draft only as existing.
- Leave types on the view.
- Polling, live updates or notifications about a short shift.
- A file export of the day (CSV, Excel, PDF); the browser's print is the only output.
- A phone-first layout; the page keeps within the width as the other approvers' pages do.
- Caching across requests, unless the measured read demands it.
- A `date` on the manager's Roster page.

## Further Notes

- The solver counts headcount on anchor shifts with `also_counts`; team leader and both genders are checked on the pure staff of
  each anchor shift; the weekend range follows the hospital rules' weekend days only; a public holiday zeroes the hours owed
  and leaves the range alone. The ticket should read the shift rows off the solver's findings rather than re-deriving them.
- Per-nurse overtime caps are hard rules, so a nurse above her cap in the roster in force is only ever a hand edit, which the
  Roster page already flags; that is why the view shows a sum against the department cap rather than "nurses above cap".
- The date's "today" is the hospital's (`membership.today`, movable on an e2e stack), and the month of a date is the month the
  figures belong to.
- The dev stack needs a restart of `web` after the API change and no rebuild unless a dependency is added. No migration is
  expected: the view reads existing rows.
