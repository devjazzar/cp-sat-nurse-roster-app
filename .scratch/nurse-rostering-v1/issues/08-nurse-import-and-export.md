# 08: Nurse import and export

**What to build:** The CNO downloads a CSV template, uploads a filled one, sees a preview that reports every row's problem (unknown unit, duplicate hospital ID, bad date) before anything is saved, confirms, and receives the generated passwords as a sheet shown once. The CNO exports the current staff list at any time.

**Blocked by:** 07 Nurses; 07a Correct a nurse's details

**Status:** ready-for-agent

- [x] Template download with the exact columns (hospital ID, full name, gender, unit, start date)
- [x] Preview reports per-row problems and saves nothing until confirmed; a file with any error cannot be confirmed
- [x] Confirmation creates nurses and accounts in one transaction and returns a password sheet once
- [x] Staff list export as CSV with the profile fields a CNO may see
- [x] API tests cover template, preview errors, confirm, and export

## Comments

Implemented on 2026-11-05. Backend under pytest on real PostgreSQL 18, frontend under Vitest with the real routes and generated client over a stubbed `fetch`.

Driven in the built-in browser as a CNO, **not on the dev overlay**: its `admin` password is not known to a session, so a scratch database on the same PostgreSQL held a CNO and three units, with `runserver` and Vite on their own ports and a scratch settings module trusting that origin. That database is dropped. Driven: the template's bytes and headers, read with `fetch` in the page; a file with duplicate, taken, unknown, archived and badly dated rows; a semicolon-separated UTF-8 file with a byte order mark and Arabic through to the password sheet; ICU archived in the database between preview and confirm, which saved nothing and showed the new preview; the leave and close dialogs; the staff list's bytes and headers; the audit log as the System Admin; no sideways page scroll at 375 px with the form, a preview, the sheet and the Nurses page, and at 320 px with the form and a preview. The file went into the input by script, because the built-in browser has no file picker, and most buttons were pressed by script; "Check file" was also reached by Tab and pressed with Return. A 500-row file ran through `gunicorn --workers 3 --timeout 300` with real hashing: 62.5 s on 8 cores, 500 accounts, a generated password logging in, and none in gunicorn's log. A hash here takes 0.49 s on one thread and 0.16 s each with four.

What was not checked:

- **A click on either download link saving a file.** The links' addresses and `download` were checked, and the answers read with `fetch`; nothing was saved to disk.
- **The staff list and the template in real Excel.** Neither the byte order mark, the quoting nor the apostrophe was seen in a spreadsheet. The tests hold the bytes.
- **Printing the sheet.** `window.print` is tested as called; the `print:` styles were never seen on paper or in a preview.
- **A successful copy to the clipboard.** The built-in browser refuses it, so only the fallback message was seen; success is a stubbed test.
- **The production compose file through Caddy,** and the 300-second timeout on it. Gunicorn ran on the host with those flags. **A real hospital server's hash speed was not measured.**
- **Two people at once.** The orders and locks are by design and no test races them. A taken ID, a unit archived and a CNO deactivated during hashing are tested by making the change at that moment.
- **Dark mode, and browsers other than the built-in one.**

Decisions this ticket took:

- **A large file stays one long request, at most 500 rows and 1 MB.** Passwords may be kept nowhere, so the worker cannot make them and hand them back later. Hashing runs first, four at a time and holding no lock; then one transaction takes seconds. 500 rows at 0.5 s is 250 s on one core, inside the new `--timeout 300` on gunicorn, whose default of 30 would kill it. Dying before the transaction saves nothing. **Worth your review:** a server slower than about 0.6 s a hash on one core could hit the timeout at the limit; nothing is lost then, and a smaller file works.
- **An answer lost after the transaction loses the passwords.** The nurses are saved and each needs a reset, one at a time, and the page says so when it cannot tell. Nothing can be done about this without keeping passwords. **Worth your review.**
- **Previewing is stateless.** Confirming sends the same bytes again, held in the page's memory, with a token: a SHA-256 of what the rows mean, with each unit's id and name. The file is judged again from the start, so there is one path through every rule. A problem or a different token is a 409 with the preview as it stands, whose token can then be confirmed. Saved differently, such as in another encoding, is the same preview; a renamed unit is not. A taken ID is left to the constraint and a changed unit is seen under its lock, because hashing can take minutes, and a CNO deactivated meanwhile gets 403.
- **Users before units,** as everywhere, by hospital ID so that two imports wait rather than deadlock. Ticket 07 named `_unit_to_join`, but that refuses with a 422 on one unit; the import locks them together and answers 409.
- **UTF-8, with or without a mark, and UTF-16 with one; any other encoding is refused, not guessed.** The same bytes are valid Windows-1252 and Windows-1256, and a wrong guess saves names nobody can read. Comma, semicolon or tab, decided by which makes the header match. The header must be exactly the five columns in order, in any case.
- **Dates are YYYY-MM-DD only.** Excel may rewrite them as `1/10/2026` on saving, and that cannot be told from 1 October. The refusal and the page say what to do. **Worth your review:** this will catch people out, and a file then fails on every row until the column is formatted. Excel also drops an ID's leading zeros without a sign, which the page warns of and the preview shows.
- **The template has a byte order mark and no example row,** so that Excel opens and saves it as UTF-8, and no example can be imported.
- **Uploads stay in memory:** `FILE_UPLOAD_HANDLERS` has only the memory handler, so a file over 2.5 MB arrives as no file (422) and never reaches a temporary file. It holds names and genders. The page refuses over 1 MB before sending.
- **The sheet offers Print and Copy all, and no download.** "Nothing on disk" is taken to include a file the app makes. **Worth your review:** printing to PDF and clipboard history can still keep them, and a CNO with hundreds to hand out may want a file.
- **Leaving is asked about, not blocked,** because the sheet is on the page rather than in a dialog: "Leave without the passwords?", also while adding, and "Close these passwords?" on Done. It stays on the page rather than in a modal so that it can print.
- **Audit:** one `nurses.imported` with the count and each unit's count, then the same `user.created` and `nurse.added` for each nurse as adding one, with no gender. A preview, a refused confirm and the template write nothing. Each staff list taken writes one `nurses.exported` with who took it and the count, and nothing from the file. This ticket first logged no export, as section 8 logged only changes; the user chose on 2026-11-05 to log it, because a staff list holds everyone's gender and the System Admin saw no sign it was taken. Section 8 now says so.
- **The staff list has the import's five columns, then End date, Role, Status and Transfers to come,** every nurse included, deactivated ones too, as on the CNO's list. Every cell is quoted, because Excel splits on its locale's separator and `a;=1+1` would otherwise start a cell, and a cell that opens like a formula gets an apostrophe. Such a hospital ID then reads `'-A1`. Names themselves are not refused, as adding one does not refuse them. **Worth your review:** "the profile fields a CNO may see" could be narrower.
- **Added though no criterion asked:** the page's own route, `/nurses/import`, as a preview can be 500 rows; a preview with problems lists only those lines.

Things a later ticket should know:

- **Rostering attributes (09):** if the staff list is to carry them, add them to `_staff_list_row`; the CNO reads nurses, and the System Admin never sees this file. The import stays at five columns.
- **PWA (23):** nothing may cache `/api/nurses/import/*` or `/api/nurses/export`: they answer `no-store`, and a service worker must honour it. The confirm is a POST that can take minutes.
- **`create_user`** takes `password=`, a `NewPassword` hashed beforehand, and always builds the user itself. `new_passwords(count)` is for many.
- **`new_profile` and `with_units`** lost their underscores, as `nurses.files_api` uses them.
- **Downloads:** the `csv_response` in `nurses/spreadsheets.py` is there for ticket 18, with `safe_cell`. A link styled as a button needs `cn(buttonVariants(...))`, or the transparent border wins.
- **A test tab on `localhost`:** cookies ignore the port, so two stacks on `localhost` log each other out. The scratch stack used `127.0.0.1`.
- **Audit actions added:** `nurses.imported` and `nurses.exported`, named in `ACTION_NAMES`. Plural on purpose: each is about the batch and has no target.

**Review (2026-11-05).** The `code-review` skill's two axes found a 500 from a control character Python strips and pydantic does not, formula cells reachable through a semicolon locale and through a tab in a pasted name, a form without Zod against ADR 0008, mutation state mirrored into the page, a CNO deactivated during hashing still adding nurses, two imports able to deadlock, "Check file" live while adding, "female" accepted though the page says F or M, the lost answer not recorded, and names. All fixed. Left as judgement calls: `Row` and its schema mirror each other because `nurse` must stay hidden; `Row`'s fields follow `COLUMNS` by position, with a comment; TanStack Table as in ticket 07; `MAX_ROWS` and the paste guard repeated in the page, each saying so. `better-interface` and its six domain skills were held against the page by hand, since `interface-review` is user-invoked. They found errors naming no way forward, "Finish" where the app says "Done", wrong grammar in the heading, and the links' lost border, all fixed. Measured: problem text on its card 4.77:1.

**Reviewed by the user (2026-11-05), and kept as built:** import dates (YYYY-MM-DD only); encodings; the password sheet with no download; lost passwords when an answer is lost; the staff list's contents; the 500-row limit, which ticket 22 measures on the real server at first install; an interrupted export still logged. TanStack Table is no longer a breach here: ADR 0008 changed on 2026-11-05, so short lists stay plain tables and TanStack Table is for the roster grid and any table that needs sorting or filtering.
