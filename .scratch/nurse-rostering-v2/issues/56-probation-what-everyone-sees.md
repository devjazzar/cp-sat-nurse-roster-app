# 56: Probation: what everyone sees

**What to build:** Wherever the unit's roster is read, a nurse on probation's row sits below the counted nurses under an "On probation" heading, with her preceptor's name: the manager's grid, My roster for every nurse of the unit, the print page, the Excel file and the CSV. The totals those pages and files show (nurses on a shift each day, headcounts) leave her out. My month names her preceptor and her probation's last day for her, and names the nurse on probation for her preceptor. Each month reads by its own state: she is under the heading in a month she is on probation in, and among the counted nurses from the month after it ends. Spec: `.scratch/nurse-rostering-v2/specs/probation.md`; the words: `GLOSSARY.md` (Nurse on probation, Preceptor).

**Blocked by:** 55 Probation: the preceptor, and the solve

**Status:** ready-for-agent

- [x] The roster reads (the manager's grid, My roster, the print page) carry, per row, whether she is on probation in that month and her preceptor's name, and order her rows last under the heading
- [x] The Excel file and the CSV show the same heading and order; their totals and the pages' totals leave her out
- [x] A version in force planned before a probation changed (an end or extension not yet re-planned) is shown as it was planned, with the roster page's line from ticket 55
- [x] My month for a nurse on probation: her preceptor (or that none is assigned yet) and her probation's last day; for a preceptor: the nurse on probation she is paired with; nothing of either for anyone else
- [x] A colleague reads no more of her than the heading, her preceptor's name and her cells, as My roster shows any row; her leave is still the same empty cell as a day off
- [x] The heading and the preceptor's name read well on a phone and to a screen reader (a row group with its own name), held against `better-interface`, `better-writing` and `better-accessibility` by hand
- [x] Tests at the web API seam (the reads and both files, month by month across a probation's end, each role) and the frontend app-level suite (the heading on the grid, My roster and the print page; My month for both nurses); six runs at once
- [x] `docs/ARCHITECTURE.md`'s exports and roles sections say so; the OpenAPI document and the generated client regenerated

## Comments

**From ticket 54 (2026-11-11).** A probation's last day is `nurses.probation.last_day(nurse)`, derived and never stored. `probation.running(nurse)` says whether it is over on the hospital's clock. Whether she is on probation in a given month is `on_probation_in(nurse, month)`, which a roster read of a past month needs, since `running` is about today.
- `NurseRow.probation` (Nurses page) and `NurseAttributesRow.probation` (Rostering attributes) are empty once a probation is over.
- The staff list has the import's "On probation" column ("Yes", or empty) and "Probation's last day".
- My month's last day for her should read the same function.

**From ticket 55 (2026-11-12).** Who precepts whom, month by month, is `nurses.preceptors`:
- `preceptors.assignment_in(nurse, month)` is the assignment in force that month (None outside her probation, before the first,
  or after a leaving ended it); `preceptors.spans(nurse, since)` groups it into runs of months, as the Rostering attributes row
  shows ("Preceptor: Amal Hassan, December 2026 to March 2027"). For a roster, read the month's solve input instead
  (`row.get("on_probation")`, `row.get("preceptor")`): it is what the solve and the checks read, and it leaves out a preceptor
  who is not in the month or is herself on probation.
- The headcounts the app works out itself already leave her out in the cover list's "already full" and the Day view's counts and
  overtime (`covers.judging.CoverMonth.full`, `rosters.day._figures`). The sheets' totals (grid, print page, Excel, CSV) are yours:
  read `on_probation` off the month's input, as those two do.
- The Day view lists her on her shift and counts her toward nothing, so its `present` and its list of names can differ by her.
  The "On probation" heading is yours to add there if it is wanted.
- The swap and cover refusals say "Faten Ali is on probation in June 2026, so a swap cannot change their cells" and "…works beside
  her preceptor, Amal Hassan, on their day shifts", on the strength of your heading. They show on My roster only once your
  "On probation" heading with her preceptor's name is there.
- My month for both nurses: `assignment_in(nurse, month).preceptor` for her, and for the preceptor, the nurse whose assignment in
  force names him (`PreceptorAssignment.objects.filter(preceptor=…)`, then `assignment_in` on each row's nurse, as
  `preceptors.precepted_in` does).

**Implemented on 2026-11-12,** on branch `claude/ticket-56-probation-what-everyone-sees-e4b838` (`7796c77` the reads, `28ac163`
the frontend, `e24932c` and `83636a4` the docs, `16e096b` and `9969fd7` the two code reviews' points, `6112cc1` the row header's
name, then `origin/main` merged with tickets 61 and 57), from `main` at `8c83302`. After ticket 57's merge (its batched
carry-over read builds the input these reads read), the roster, export, My month and probation tests ran again: 98 backend and
196 frontend passed. Draft pull request
[devjazzar/cp-sat-nurse-roster-app#32](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/32).
- The backend suite ran on a throwaway PostgreSQL 18 container of my own, under the heavy-run lock: **3632 passed**, on
  `9969fd7`'s code (`6112cc1` touched the frontend only).
- The frontend: `npm test` **853 passed** on `9969fd7`. After `6112cc1` and the merge, the roster, print, My month, My roster and
  Rostering attributes tests ran again: 230 passed. `npm run build` was clean. GitHub's six runs at once passed on `9969fd7`.
- `makemigrations --check`: "No changes detected". There is no migration.
- `frontend/openapi.json` and the client were regenerated from the export, and still match it after the merge.
- The solver suite did not run: `solver/` did not change. No Playwright file changed, and there is no new journey.

**What the dev stack needs:** `docker compose up -d --build`, for the new code. There is no migration, and no `compose.yaml`,
`Dockerfile`, solver or dependency change.

**What was built, criterion by criterion.**
- **The roster reads.**
  - One reading of the month's input: `rosters.grids.OnProbation` reads `on_probation` and `preceptor` off the input the grid
    was planned with, as the solve and the checks read them.
  - For a version, that input is `rosters.versions.planned_with`: its own solve, or for a hand edit the solve of the version it
    was made on. The draft grid reads its own solve's input.
  - Each row carries `on_probation` and `preceptor_name` (a full name, or null when none was in force), on `GridRow` (the
    manager's grid and the approvers' reading of it), `ColleagueRow` (My roster) and `SheetRowOut` (both print sheets).
  - Rows come counted nurses first by name, then those on probation by name.
- **The files.**
  - In a month with someone on probation, the CSV and the workbook gain a last "Preceptor" column, empty for the counted nurses.
  - A row reading "On probation" in its first cell, full width and empty otherwise, heads her rows; in the workbook the column
    is as wide as a name.
  - A month with nobody on probation is the file it always was (tested).
  - **Totals:** no sheet, page or file shows a per-day total. Before this ticket, a row's "Shift hours" and its count of each
    shift were its own (ticket 18). So there is no total for her to be left out of. Her own row keeps its hours and counts, and
    `docs/ARCHITECTURE.md` now says so. The criterion is ticked on those grounds, as the main session decided (below).
- **Each month by its own state.**
  - Tested across a probation's end: June under the heading, July among the counted nurses (Abla, whose name sorts first, is
    first in July).
  - A June planned with her counted, then extended into, still reads her as counted on the grid, the sheet, the CSV and My
    roster. Ticket 55's line is in the page's `changes` (`on_probation`).
- **My month** (`MyMonth.probation`, `MyMonth.precepts`) reads the probation as it stands now, not as the roster was planned.
  - It answers with or without an approved roster.
  - For her: a "Probation" card with her last day and her preceptor, or "No preceptor is assigned to you yet. Your unit manager
    chooses one. Until then, your day shifts are planned without a preceptor to follow."
  - For her preceptor: a "Precepting" card, "In January 2027 you precept Faten Ali, a nurse on probation, who works beside you
    on your day shifts." (ticket 55's notification's words).
  - For anyone else: neither card.
- **A colleague** reads her name, the heading, her preceptor's name and her cells; `ColleagueRow`'s keys are pinned by a test.
  Her leave is the same empty cell as a day off; only her own My roster and print sheet say leave.
- **Phone and screen reader.**
  - On the grid, My roster and the print page, her rows are a second `<tbody>`, named by its heading row:
    `<th scope="rowgroup" colSpan>` "On probation".
  - On the grid the heading's words stay in view while it scrolls sideways (a sticky span).
  - Her row header reads "Faten Ali, Preceptor: Amal Saleh" (an `aria-label`), with "Preceptor: Amal Saleh" on a second line
    under her name.
  - In the editable grid the arrows pass over the heading; `aria-rowcount` and `aria-rowindex` count it.
  - A long, windowed grid scrolled past the heading names the group with an `aria-label`, and puts the heading's height in its
    spacer.
  - The legends add "On probation: works beside their preceptor and is not counted toward any shift".
- **Docs.**
  - `docs/ARCHITECTURE.md` §3 has two rows: reading the pairing on a roster, and one's own on My month.
  - "Roster files and the print page" says how the heading, the column and `planned_with` work.
  - §6's line on the sheets' totals says there are none.

**What was driven, and how.**
- **Setup.** Scratch stack `nr-t56` was seeded by `e2e/stack.sh up`: ER is the four-nurse sample, December 2026 is approved,
  and today is 12 November.
  - In its Django shell I added Faten Ali on probation from 1 December for 2 months (December and January).
  - I recorded Preceptorship (marked) for Amal Saleh and assigned her from January.
- **The solves.** The browser pane was hidden, so a headless Chromium (the e2e tree's Playwright) did the driving, signed in
  through the login page.
  - January and February were each solved for real (30 s) as Mona, submitted, and approved as Carla.
- **January.**
  - Faten: `DDD..D.D..D..DDD.D.DDD..D..DD.D`.
  - Amal: `DD.NN.NNN.N.NN.N....NN.N.NN...N`.
  - Faten was beside Amal on both of her day shifts (the 1st and 2nd) and worked no night.
  - The counted nurses held one D a day without her.
- **February.** Faten was counted with nights (`.NN.N.N.NN..NNNN..NN.NNN..D.`), and the grid had no "On probation" group.
- **The manager's grid.** January's accessibility tree has `rowgroup "On probation"` > `rowheader "On probation"`, then
  `rowheader "Faten Ali, Preceptor: Amal Saleh"`.
- **The print page** lays out the same, with "On probation" shaded above her row and the legend line.
- **The CSV.**
  - January's header ends "Shift hours","Day (D)","Night (N)","Preceptor".
  - Its rows: Amal, Badr, Dana, Emad, then "On probation", then Faten with "Amal Saleh".
  - February's header ends at "Night (N)".
- **My roster, as Badr at 360 px.** Rows: "Badr Harbi (you)", Amal, Dana, Emad, "On probation", "Faten Ali, Preceptor: Amal
  Saleh". There is no sideways scroll on the page, and the heading stays in view with the grid scrolled 400 px.
- **My month at 360 px.**
  - Faten, January: the Probation card ("…Its last day is Sunday, 31 January 2027. Your preceptor is Amal Saleh…").
  - Amal: the Precepting card.
  - Badr: neither.
  - Faten, February: neither.
- **Found and fixed:** real Chrome read the first row header as "Faten Ali , Preceptor…" (a stray space before a visually
  hidden comma). It is an `aria-label` now, checked again on the rebuilt stack.
- The stack is down and its volumes removed.

**What was NOT checked.**
- A real screen reader (VoiceOver, NVDA): only Chromium's accessibility tree.
- A long, windowed grid with a nurse on probation in a browser: the spacer arithmetic is tested in jsdom only through the
  short-grid tests and the existing windowed ones.
- Printing on paper: the print page was rendered, not printed.
- The frontend's whole suite after `6112cc1` and the merge: the affected describes ran (above), and GitHub's six runs are on the
  merged head.

**Decisions taken here.**
- **Each row says it, and the server orders it.** A page draws the heading before the first row marked `on_probation`.
  - My roster keeps its own rule within each group: the reader's own row first among the counted nurses, or first under the
    heading when she is on probation.
- **The files show it only in a month that has it**, so every other month's file is byte for byte what it was.
- **My month reads now, the roster reads as planned.** A version planned before an end or extension keeps its pairing until
  re-planned, as ticket 55's roster line says. A nurse reading My month needs to know where she stands today.
- **The Day view has no heading.** It lists names per shift, not rows. Ticket 55 already counts her toward nothing there.
- **A preceptor with no full name** shows by hospital ID, which the glossary calls the name she carries on every roster.

**Worth your review.**
- **No sheet shows a per-day total, so none was added.** A "Nurses on D" row per shift, counting only the counted nurses, would
  be one change across both print pages, Excel and CSV, if wanted. (The main session's decision; the spec's "the sheets'
  totals" assumed one.)
- **The heading's words and where the preceptor's name sits:** "On probation" as the group's heading, and "Preceptor: Amal
  Saleh" in small type under her name ("No preceptor" when none). The legend line explains the heading.
- **The Day view gains no heading** (above).
- **How the files show it:** a full-width "On probation" row and a last "Preceptor" column, only in a month with someone on
  probation. A program reading the CSV sees a column more, and one row whose first cell is no hospital ID, in such a month.
- **The roster and My month can name different preceptors** for a month planned before a change: the roster shows the pairing
  it was planned with, and My month the one in force now. Nothing on My month says why they differ.

**Review.** `code-review` against `8c83302`, both axes in fresh sub-agents, then a second run on the fixes, which were more than
small.

*First run, Standards:*
- `Apart` renamed `OnProbation`, with `names()` and `marks()`, so the three reads no longer repeat the pairing: fixed.
- `planned_with` moved to `rosters.versions`: fixed.
- `MyProbation.preceptor` is now `preceptor_name`: fixed.
- `_probation_of` returns a pair: fixed.
- The legend sentence is written once: fixed.
- Kept:
  - covers' and swaps' own one-line readings of `on_probation`: ticket 55's, and outside this ticket;
  - the pair of fields on four schemas: each is a response's own row;
  - the reader's own-row-first in My roster, within each group.

*First run, Spec:*
- The Preceptor column's width: fixed.
- A System Admin test: added (the reads and the file refused).
- Kept:
  - the legend lines and My month's wording: they say what the heading means, the reason colleagues see it;
  - the files' month-to-month shape, and the roster and My month differing: both under Worth your review;
  - the precepting words: ticket 55's notification's.

*Second run:*
- A windowed group scrolled past its heading had no name: fixed.
- Her preceptor's own My roster: tested.
- The width no longer builds the table twice: fixed.
- The test's two sign-ins now use `nurses_of_er`.
- The probation words moved to `lib/probation-words.ts`.
- Kept:
  - the name cell's two-line markup in the grid and the sheet (two lines each);
  - the heading not being a virtualizer row: its height goes into the spacers.

**Things later tickets should know.**
- A roster read's probation is `rosters.grids.OnProbation.of(planned_with(version).input)`. Use `.marks()` and `.ordered()` for a
  new read.
- If a per-day total row is wanted, `Sheet.table()` is the one place: skip rows with `on_probation`.
- The swap and cover refusals of ticket 55 now have the heading they lean on, on My roster.

**Reviewed by the user (2026-11-12):** all five points kept as built.
- No per-day totals added: no page or file had one to leave her out of.
- The heading "On probation", with "Preceptor: …" or "No preceptor" under her name.
- The Day view gets no heading.
- The files' "On probation" row and "Preceptor" column appear only in months with someone on probation.
- A month planned before a change may name a different preceptor than My month, with no words saying why.
