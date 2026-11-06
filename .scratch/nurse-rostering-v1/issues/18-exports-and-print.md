# 18: Exports and print

**What to build:** Any roster version downloads as CSV and as an Excel workbook (one row per nurse, one column per date, then hours and shift counts) and opens as a print-friendly page the browser saves as PDF. Managers export their unit; the CNO and Deputy CNO any unit.

**Blocked by:** 16 Changes after approval

**Status:** ready-for-agent

- [x] CSV and Excel export of a chosen version with the agreed columns
- [x] Print page for a version, styled for paper
- [x] Authorization: unit-scoped for managers, hospital-wide for approvers, none for nurses beyond their own unit's print page
- [x] API tests cover both exports' content and authorization

## Comments

**Decisions from the user (2026-11-05).** Roster exports are audited the same way as the staff list (`export_staff_list`): one entry per download, saying who and which roster, with nothing from the file. Name the new action in `ACTION_NAMES`, and add roster exports to the line in `docs/ARCHITECTURE.md` that says each taking of the staff list goes to the audit log. The print page is not audited, because it makes no file and shows only what that role can already read.

**From ticket 14 (2026-11-05).** Roster versions exist (`rosters.models.RosterVersion`, from the first approval). The CNO and the Deputy CNO read a unit's month only while it is submitted or approved: a draft is its manager's (the glossary's Draft), and the read, the solve history and the results all hold to that (`rosters.review.SEEN_BY_APPROVERS`). An export for them should hold to it too, or say why not. A version's grid keeps its old codes; read it through `rosters.drafts.in_current_codes`.

**Implemented on 2026-11-06,** on branch `claude/ticket-18-exports-aed919`. The backend ran under pytest on a throwaway PostgreSQL 18 container of my own, the frontend under Vitest with the real routes and generated client over a stubbed `fetch`.

- Results on the final code: backend 1898 passed, frontend 479 of 479, and `npm run build` clean.
- `makemigrations --check` is clean (no migration), and `frontend/openapi.json` is the same as a fresh export.
- **The frontend suite ran alone in this worktree, not in clean exports in parallel.** That is left to the session that brings this into `main`.
- The solver's suite was not run: nothing under `solver/` changed.

What was built:

- **`rosters/sheets.py`, one table for all three outputs.** `sheet_of(version)` gives a row a nurse by name, a column a date of the month, then "Shift hours" and one count column a shift the version uses, headed "Day (D)". Cells are the version's grid under today's codes (`in_current_codes`), so an old version reads a renamed shift by its new code.
- **Files:** `GET /api/units/{id}/roster/export?month&version&format=csv|xlsx` (`exportRosterVersion`), for the unit's manager, the CNO and the Deputy CNO.
  - The CSV is `csv_response`, unchanged in its choices: a byte order mark, every cell quoted, an apostrophe before a cell that opens like a formula. Dates are `YYYY-MM-DD`; a day off is an empty cell. Name `roster-er-2026-12-v3.csv`, from the unit's name slugified (Arabic kept, sent as `filename*`). The staff list's header is built the same way now (`content_disposition_header`), which leaves its ASCII name exactly as it was.
  - The workbook is `xlsx_response` in `nurses/spreadsheets.py`, beside `csv_response`: text written as text (never a formula, link or number, so an ID keeps leading zeros), numbers as numbers, date headings as real dates shown `yyyy-mm-dd`, text that opens like a formula marked as text with Excel's own `quote_prefix` (no apostrophe shows), the header row and the two name columns frozen, and the title in the workbook's properties.
  - Both answer `Cache-Control: no-store` and are built in memory.
- **Print sheets (JSON, not audited):** `GET /api/units/{id}/roster/sheet?month&version` (`getRosterVersionSheet`) for the same three roles, and `GET /api/rosters/mine/sheet?month` (`getMyRosterSheet`) for a nurse (and a manager with a nurse profile, as `/mine` allows): the roster in force of the unit their month falls under, this month and later, with `mine` saying their own days.
- **Audit:** each file taken writes one `roster.exported`, target `ER, 2026-12` (`Roster.audit_target`, the form a solve's has), `after` `{"version", "format"}`, nothing from the file. A refused download writes nothing. Named "Exported a roster version" in `ACTION_NAMES`; ARCHITECTURE section 8's audit line names it.
- **Pages:**
  - The Versions table (manager's Roster page and the approvers' Unit roster) has "Print or download": Print, CSV and Excel on every version, each link named for its version.
  - `/roster/print?unit&month&version`: the version as a table for paper, saying whether it is in force ("Version 3 has replaced it, so this is not the roster in force."), a Print button, a back link to the reader's own roster page, and a legend.
  - `/my-roster/print?month`, from "Print this roster" on My roster: the same layout from the nurse's own sheet, their row marked "(you)", their leave "L" and days outside their dates "·", with the legend saying what those are.
  - `components/roster-sheet.tsx` is the table and the page around it, drawn whole (never windowed, unlike the roster grid). `index.css` has a named `@page roster` (A4 landscape, 10 mm margins), so other pages, such as the password sheet, print as they did.
- **XlsxWriter 3.3.1** (`xlsxwriter>=3.3.1,<3.4` in `backend/pyproject.toml`, exact in `uv.lock`). Checked on 2026-11-06: released 28 October 2026 (3.3.0 on 22 October, 3.2.9 in September 2025), its last commits that day bug fixes; no advisory in OSV for the PyPI package and none in the repository's GitHub security advisories; BSD-2-Clause; no dependencies. Chosen over openpyxl, whose last release is June 2024 and which writes through temporary files unless told otherwise; XlsxWriter only writes, which is all this needs, and has an `in_memory` mode. No reader was added: the tests read the workbook's XML with the standard library.

Seams:
- `rosters/tests/test_exports.py`, 31 tests, the API with the scripted solver on the real optimal roster of the four-nurse sample: the table's content against literals read off the fixture by hand, any version, an old version under a rename, leave in a file, formula-like and Arabic names in both formats, the workbook's own XML (cell types, number formats, `quotePrefix`, no `<f>` anywhere), leading zeros, no temporary file (every `tempfile` maker made to fail), headers, who may take what, a draft, a version that does not exist, the approvers' hold, the audit entries, the print sheet equal to the CSV row for row, and a nurse's own sheet.
- `accounts/tests/test_authorization.py` names the three new endpoints' roles; the walk holds the System Admin to none.
- `app.test.tsx`: 8 new tests and the two print routes in the route guards, through `start`. No raised timeout, no fake timers, no wait that proves something did not happen.
- **Honestly: most of the export code came with or just ahead of its first test, not after a red one.** So I broke the guards by hand and saw tests fail: the approvers' hold, the unit's scope, `in_memory` (the temporary-file test fails), and the `quote_prefix` branch (the formula test fails). Making xlsxwriter's `write` guess types with `strings_to_formulas` on fails no test, since every text cell that opens like a formula goes through the marked branch first; the two guards are layered.

**Driven in the built-in browser,** on scratch project `nr-t18`:
- The setup: the production compose file with its own image (`nr-t18-app`), secrets and volumes; `web` published on `127.0.0.1:18018` under `DJANGO_DEBUG` and joined to the `public` network; no Caddy; the real solver and worker. ER was the solver's four-nurse sample with three names changed: Arabic (`بدر الحربي`), formula-like (`=HYPERLINK("http://example.invalid","Dana")`) and plain. ICU was 60 nurses (every seventh with a long name) with an approved December written to the database by the seed script, not solved, to see the print page at that size.
- **As the manager, over the API from the page:** a real solve of December 2026 (31 days, 20 s), submit; **as the CNO** approval, version 1; **as the manager** a hand edit (Emad on the 2nd, version 2) and Sick leave for Badr on the 2nd, a day he worked (version 3), and Annual on the 1st, a day off (no version).
- **The Versions table** showed Print, CSV and Excel on all three rows.
- **Both downloads read with `fetch` in the page:**
  - CSV of version 3: 200, `text/csv; charset=utf-8`, `attachment; filename="roster-er-2026-12-v3.csv"`, `no-store`, bytes `EF BB BF` first, the header through `"2026-12-31","Hours worked","Day (D)","Night (N)"` (renamed "Shift hours" after the review; checked again by API test, not in the browser), Dana's name as `'=HYPERLINK(...)`, Badr's 1st and 2nd empty, and no "leave", "sick" or "annual" anywhere.
  - Workbook of version 1: 200, the xlsx type, `roster-er-2026-12-v1.xlsx`, `no-store`, a zip (`PK`).
- **In Microsoft Excel** (installed here; driven by AppleScript after you granted the permission): the workbook's date headings are dates shown `2026-12-01`, the hours a number (180), Dana's name stays text and its value is the text itself, not "Dana", and the Arabic name is intact. The CSV in Excel: the formula-like name shows with its apostrophe as text, Arabic intact, the date headings read as dates (shown in Excel's locale, `01/12/2026`), the hours as numbers. **Not checked in Excel:** Windows Excel, a locale with `;` as list separator, column widths and frozen panes by eye, and the file opened by a double-click on a download (it was opened from a file fetched with `curl` under the manager's session).
- **Each role's refusals, over `fetch` in the page:** Badr (staff nurse) 403 on CSV, workbook and sheet, and 200 on his own sheet; Omar (ICU's manager) 403 "This is not your unit." on all three; the Deputy CNO and the CNO 200 on all three; a version that does not exist 404. The System Admin's 403 on all four was checked over Django's test client inside the scratch `web`, as their first login needs a password change.
- **The audit log** held one `roster.exported` for each successful download (8), each with actor, `ER, 2026-12` and `{"format", "version"}`, and none for the refused ones.
- **As Badr in the page:** "Print this roster" on My roster led to the print page; his own row read "L" on the 1st and 2nd, nobody else's said leave. Opening `/roster/print` sent him home.
- **At 375 px,** the nurse's print page: no sideways page scroll, the table scrolls in its own region.
- **Print, at A4 landscape**, by headless Chromium (the cached Playwright build, `page.pdf` with the page's own `@page`, print media) as Omar, the CNO and Badr, then each PDF page rendered and looked at:
  - **ICU, 60 nurses, 31 days: 3 pages** (27, 29 and 4 rows). All 31 days, the hours and both counts fit across every page; nothing is cut off at the right.
  - **The header row repeats** at the top of pages 2 and 3; the title, version line and legend print once (first page, and the legend after the last row).
  - **Names do not need repeating:** the table never splits sideways, so each row carries its own name. A long name wraps inside its cell, and **no row is split** across pages.
  - Weekend shading prints; the app's header, the Print button, the back link and the hint are hidden; nothing the page needs is hidden.
  - The CNO's print of version 1 says "Version 3 has replaced it, so this is not the roster in force."
  - That run found the single-letter weekdays ambiguous ("S" for Saturday and Sunday), now two letters, printed again.
- Everything of `nr-t18` has been removed since: containers, volumes, network and image.

What was NOT checked:
- **The browser's own print dialog and its preview**, and a real printer. The built-in browser cannot show print preview; the pages were seen as PDFs from headless Chromium, which honours `@page` as Chrome does. Firefox and Safari print, and their handling of the named page, were not checked.
- **A click on a download link saving a file.** The links' addresses and `download` were checked, and the answers read with `fetch`.
- **The approvers' print page in the browser pane** (the CNO's was seen only as a PDF), and Unit roster's links (a Vitest test).
- **Dark mode, 320 px, 200% zoom, a screen reader, and through Caddy.**
- **A large unit's files' speed.** The sheet reads one version's grid and the names; nothing was timed.

**Decisions taken here:**

- **Worth your review: a day of leave is a day off in every file and on every print page, for every role.** Only a nurse's own row on their own print page says "L". The manager, the CNO and the Deputy CNO read leave with its type in the app, but a file or a printout leaves the system and may be pinned on a ward wall, where colleagues read it. A leave's type is never in any of them, which tests hold. The alternative, "L" without a type in the manager's and approvers' files, is one line in `sheets.py`.
- **Worth your review: "Shift hours" is the hours of the shifts on the row**, at the hours the version's solve was given (a hand-edit version takes those of the version it was made on; a code that solve was not given takes the catalogue's, and since a shift's hours cannot change while a month not over uses it, these are the month's). It is not what the month owes, the overtime, or the hours My month shows, which count leave as worked: any of those would say how much leave a colleague had. The column was first called "Hours worked"; the review pointed out the glossary's Leave "counts as worked for her hours", so it was renamed. A nurse's own print page says that My month counts their leave and these hours do not.
- **Worth your review: a draft has no file and no print page.** It is not a version, the ticket says "any roster version", and a printed draft would be taken for the roster. A manager reads the draft on the Roster page. Opening it would be `version_for` reading the draft's grid.
- **Any version, not only the one in force,** for the manager and the approvers; a nurse prints only the version in force, this month or later, as My roster.
- **The approvers' hold** (`SEEN_BY_APPROVERS`) is checked in `version_for`, though only an approved roster has versions and it never goes back to draft; a test forces the case.
- **The audit entry says the format too.** It is not from the file, and tells the System Admin which kind of file left.
- **The print page is in the signed-in layout** (its header hidden on paper), not a bare page, so the guards, the bell and a way back work as everywhere.
- **Names are today's,** as everywhere a roster is read; a version keeps codes, not names.

`docs/ARCHITECTURE.md` section 8 (the audit line and a new "Roster files and the print page") and the glossary's Leave moved.

**Review.** The `code-review` skill's two axes against `a1b4f2d`.
- Standards found the new audit sentence splitting the staff list's "Its import template…" from its subject (fixed), a regex repeating `monthInAddress`, the weekend shading written twice, an unused default and a no-op format flag, the sheet's name fixed inside the shared module (now a parameter), the export format typed by hand, a doubled import, `next()` with no default in the hours (now falls back to the roster's solve), and a redundant `select_related`. All fixed. Left as judgement calls: the dataclasses beside the schemas in `sheets.py` (the table is also the files', which are not schemas), `MyRosterSheet` repeating `MyRosterMonth`'s heading (built by the same `heading()`), and "sheet" in the code's names though the glossary has Password sheet (it names no domain term, and no glossary entry was added for it).
- Spec found "Hours worked" clashing with the glossary (renamed, above), a nurse's own hours differing from My month without a word (the print page says why now), and the A4 fit untested (it was driven, above; jsdom cannot test layout). It also raised the staff list's header now built by `content_disposition_header` (kept: ASCII names are unchanged, ticket 08's tests pass), `in_force`, frozen panes and the "(you)" marker as not asked for (kept as small help), and a test of leave given to the solve that only searches for the word "leave" (kept beside the test that compares whole answers before and after leave).

`better-interface` and its domain skills, held by hand against the code and the run: the print table has a caption, column and row headers, each date heading an `abbr` with its full date, and scrolls in a labelled, focusable region on a phone; each download link's name includes its visible word ("Version 1 as CSV"); refusals say why; the copy uses the glossary's words (version, roster in force, leave); no new colour beyond the existing muted shade. `interface-review` is yours to invoke.

**Things later tickets should know:**
- **Swaps and requests (19, 20):** a version they make is printed and exported like any other with nothing more to do; `VersionOrigin` needs no change here.
- **PWA (23):** a comment there names the endpoints that must not be cached.
- **Month close (21):** a closed month's versions still export; the hours are the version's solve's, not the close's.
- `nurses/spreadsheets.py` now has `xlsx_response` beside `csv_response`, and `looks_like_a_formula`.

**The dev stack was not touched:** no restart, no migration, no login. There is no migration. When this reaches `main`, rebuild the image (or `uv sync`) for XlsxWriter, a new dependency, and restart `web` and `worker`; without it the backend fails to import `xlsxwriter` at start.
