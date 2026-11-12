# 50: The carry-over chain carries a nurse's overtime balance, from her opening values to January

**What to build:** A nurse's overtime balance, how far her overtime has stood above or below her overtime share so far this year, is one more carried value in the carry-over chain, from the result's carry-over block: projected from the roster in force, corrected at the close from the month's facts and re-worked at a re-close; carried unchanged through a month with no roster for her; following her across a transfer; reset to zero in the carry-over handed into January, with overtime this year and the night and weekend balances; and 0 out of a close stored before the balance existed, with nothing worked back through earlier months. Her opening values gain it: "Overtime above or below their fair share (hours)", default 0, on the rostering attributes form beside the night and weekend balances, read and written through the same API by the same people, locked with them once her first month closes and audited with them. Every solve input, a re-plan's and a close's included, carries each nurse's balance from the chain. Until ticket 51 switches the rule on for a unit the solver hands every balance on unchanged, so this ticket is proven with the solver's unit fields set in the tests. Spec: `.scratch/nurse-rostering-v2/specs/overtime-share.md`; the words: `GLOSSARY.md` (Overtime share, Carry-over, Opening values); the reason for the chain: ADR 0004.

**Blocked by:** 49 The solver prices overtime above a nurse's share, and carries her balance

**Status:** ready-for-agent

- [x] The chain carries the balance from the result's carry-over block: projected from the roster in force, corrected at the close with what really happened, re-worked on a re-close
- [x] A month with no roster for her hands her balance on unchanged; a transfer carries it into the new unit; the carry-over into January has it at zero; a close stored before the balance existed hands on 0
- [x] The opening value: default 0, edited and read by those who edit and read the other opening values, refused outside the solver's bound with the usual field error, locked once her first month closes, in the audit entry beside the others
- [x] The rostering attributes form shows it beside the night and weekend balances with its label and help, and read-only once locked
- [x] Every solve input, a re-plan's and a close's included, carries each nurse's balance from the chain; a nurse's first month takes her opening value
- [ ] The narrowing ticket 49 left for the carried value is removed
- [x] Tests at the agreed seams: the backend API suite (closes: projected, corrected, re-close, no roster, transfer, January, a close stored before, opening values; nurses: the opening value; solves: the input and a re-plan's) and the frontend app-level suite (six runs at once)
- [x] `docs/ARCHITECTURE.md`: the balance among the opening values, in the chain's paragraph and in the January reset; the OpenAPI document and the generated client regenerated; a migration for the new opening value, `makemigrations --check` clean

## Comments

**Note from ticket 49 (2026-11-12):** the balance already passes through the chain (`closes.chain.CARRIED`), 0 from opening
values (`chain.opening`, a literal to replace) and from a close stored before it (`CARRIED_SINCE`); the January reset is not
done (`NEW_YEAR`). Ticket 49 left no narrowing for the carried value, so the criterion removing one has nothing to act on.
Details in ticket 49's comment, "Things later tickets should know".

**Implemented on 2026-11-12,** on branch `claude/ticket-50-chain-overtime-balance-b0c515`, pull request
devjazzar/cp-sat-nurse-roster-app#26, from `main` at `d759f0d` (`cae3c18` the build, `32c72cd` the review's points and a note
on ticket 57, `79f1939` a test body in `test_flow.py` that GitHub's backend job caught; then a merge of `main` with ticket 52,
`2bf6bf2`, and this comment). The suites, locally, under the heavy-run lock, on `79f1939`:
- the backend under pytest on a throwaway PostgreSQL 18 container of my own: **3451 passed**; `makemigrations --check`: no
  changes;
- the frontend: `npm test` **813 passed**, `npm run build` clean, the typecheck clean; the OpenAPI document exported again and
  the client generated from it (`npm run generate:api`), and they match the export;
- the solver's suite not run: nothing in `solver/` changed here. GitHub ran it, with the rest, on every push.
- Before ticket 52's merge, GitHub's run on `79f1939` passed the backend, frontend (six at once), image and solver jobs. Both
  workflows on the merged head are named in the merge's line below.

**What the dev stack needs:** a **rebuild** (`docker compose up -d --build`): **a migration** (`nurses.0007_opening_overtime_balance`,
one column with a default of 0) and the SPA. No dependency, compose, Dockerfile or solver change. Every nurse starts at 0, so
nothing a solve gives changes until ticket 51 switches the rule on.

**What was built, criterion by criterion.**
- **The chain.** `closes.chain.opening` takes the nurse's `overtime_balance` in place of the literal 0.0, and `NEW_YEAR` gains
  `"overtime_balance": 0.0`, applied in `Carried.into` as January's input is built (ADR 0004), never inside a close.
  `CARRIED` and `CARRIED_SINCE` already held it (ticket 49); it is not in `NO_HISTORY`, so it carries through a month with no
  roster unchanged. Proven in `closes/tests/test_close.py`'s `TestTheOvertimeBalance` with the unit sharing its overtime
  (`shares_overtime` writes `share_overtime`, a tolerance and a limit of 12 straight into `unit.rules`, as ticket 49 left it to
  do until ticket 51). The month: SOUND's June with Amal coming in 24 hours ahead, counted by hand in `amal_works_ahead`'s
  docstring. She owes 184 and works 204, so 20 hours of overtime, the unit's whole overtime; the four owe 782. Her balance
  moves by 20 − 20 × 184 / 782 = **+15.29**, Badr's and Emad's by **−5.32**, Dana's by **−4.65**. With a day of leave on the
  1st recorded late, 16 hours among 774 owed: **+12.36, −4.30, −3.76, −4.30**.
  - *projected* from the roster in force: July's input carries the four, source `projected`;
  - *corrected at the close*: the late leave gives the second four, stored and in July's input, source `closed`;
  - *re-worked on a re-close*: 15.29, then 12.36 after the leave and Close again, the first close's row left as it was;
  - *a close's input* is the month before's close: July's close takes June's corrected four;
  - *a month with no roster* (July): August's input carries June's four unchanged;
  - *a transfer*: ICU's July input carries Amal's +15.29;
  - *January*: a December close storing +9.5 gives January 0.0 with the other two balances and overtime this year, and the
    December row still holds 9.5; opening values entered in December reset into January too (7.5 → 0.0);
  - *a close stored before it*: June's rows stripped of the field give 0.0 to all four in July, source `closed`;
  - *her opening value*: her first month takes it (Dana −6.5, source `opening`), and the month moves on from it (3.5 + 15.29 =
    18.79).
- **The opening value.** `NurseProfile.overtime_balance` (FloatField, default 0, help "Hours of overtime above (+) or below (−)
  their overtime share so far this year"), migration 0007. On the rostering attributes API it is in `AttributesBody`
  (required, as the other four are), the row, `OPENING_VALUES` (so locked on its own field once her first month closes, with
  the usual words) and the `opening_values_locked` description; the same `nurse.attributes_changed` entry, with no value, as
  for the others. Bound: the solver's own, ±1 000 000 hours (`nurse_roster.problem.MAX_HOURS`, what `request.py` checks for
  `overtime_balance`), not the shift balances' ±1000. Tests in `nurses/tests/test_attributes.py`: the solver's default, a save
  reaching the solver (`load_request`), ±1 000 000 and 0.25 accepted and loaded, 1 000 001, −1 000 000.5, `"3"`, `true`, null
  and Infinity refused on the field, the CNO and Deputy CNO reading it and refused writing, a change of it alone logged with
  no value, and the System Admin's log free of its name and value; `closes/tests/test_guards.py`: locked with the others after
  the first close, and kept.
- **The form.** "Overtime above or below their fair share (hours)", after the weekend balance, `step="any"`, help "Hours of
  overtime above their share of the unit's overtime so far this year, or below zero, under it.", read-only once locked, the
  bound from the generated client (`updateNurseAttributesBodyOvertimeBalanceMax`) with "Between -1000000 and 1000000.". The
  table gains an "Overtime balance" column after the weekend balance, which is how the CNO and the Deputy CNO read it (they
  have no form). `app.test.tsx`: the column and its value, the field's value, help and save, the bound refused before the
  API is asked, −1 000 000 accepted, and read-only and sent unchanged once locked.
- **Every solve input.** `nurses.rostering.nurse_block` carries the opening value (the chain then sets it, as the other
  carried values); `solves/tests/test_input.py`: an opening value reaching the input and the solver, and May's closed balance
  reaching June's input with 0 for the others; `rosters/tests/test_replan.py`: a re-plan's input carries Amal's −11.5 from May
  and Dana's opening 4.25, loaded by the solver; the close's input as above.
- **The narrowing ticket 49 left: none to remove.** Ticket 49's note says so: the carried value never had one (the three
  `OVERTIME_SHARE_FIELDS` narrowings are the unit rules' and the weight's, ticket 51's). Left unticked, as there was nothing
  to do.
- **Docs.** `docs/ARCHITECTURE.md`: the nurse profile's opening values, the January reset (with where it is applied), section
  6's paragraph on the overtime share, and the worker's chain paragraph. ADR 0004 is unedited: its "fairness balances" covers
  it, as the spec says.

**What was driven, and how.** My scratch stack (`e2e/stack.sh up nr-t50`, seeded), with a throwaway Playwright file in
headless Chromium (removed after; the browser pane was hidden), and the stack's own Django shell:
- as `mona`, ER's Rostering attributes: the new column; Amal's form with the field at 0 and its help; 2 000 000 refused
  beside the field ("Between -1000000 and 1000000."), nothing sent; 4.5 saved, the row showing 4.5;
- added a nurse, Noor Test, from November (shell), then fired `close_month`: October closed. Amal's field read-only with 4.5
  and the closed wording; Noor's editable, −3.25 saved;
- as `hala` (Deputy CNO): the column with Noor's −3.25, no Set attributes buttons;
- the chain, from `solves.input.assemble` on the stack: October's close row stores Amal's 4.5 (the unit does not share
  overtime, so the solver hands it on); November's and December's inputs carry Amal 4.5 (`closed`) and Noor −3.25
  (`opening`); January 2027's carries 0.0 for both.
The stack is down; the throwaway file, the nurse and the stack went with it.

**What was NOT checked:**
- A balance moving on the stack: the unit rules cannot switch the share on until ticket 51, so every stack balance is handed on
  as it came in. The moving cases are the backend tests' (the scripted solver and the real carry-over code).
- The Roster page's carry-over table (`closes.api.CarryValues`, `month-close.tsx`) does not show the balance: not asked, see
  below.
- The browser checks locally (no Playwright file of the repo changed); GitHub's run.

**Decisions taken here:**
- **Worth your review: the label and help.** The label is the spec's, "Overtime above or below their fair share (hours)";
  the help is mine, "Hours of overtime above their share of the unit's overtime so far this year, or below zero, under it.",
  in the voice of the night and weekend helps. The code review noted that the glossary's word is "overtime share" while the
  screen says "fair share"; the label is the spec's decision, so it stays, and the help says "their share of the unit's
  overtime" in plain words. The table column is "Overtime balance", beside "Night balance" and "Weekend balance".
- **Worth your review: the bound and step on the form.** ±1 000 000 hours, the solver's (and the yearly overtime field's)
  bound, any fraction (`step="any"`): the solver carries it to hundredths. A manager entering an honest value never meets the
  bound; a tighter one (say ±744, a month's hours) would be a rule the solver does not have.
- **Worth your review: how the January reset shows in the stored carry-over.** It does not: as ADR 0004 says, the boundary is
  applied when January's input is built, so December's stored row keeps what December handed on (+9.5 in the test) and
  January's input has 0. The Roster page's `into` column for January already reads the values after the reset.
- **Worth your review: the column on the attributes table.** Not asked for by the spec's words (the form), but the CNO and
  the Deputy CNO read opening values only through that table, and the criterion asks that they read it.
- **Worth your review: not on the Roster page's carry-over table.** `CarryValues` shows hours, overtime this year and the two
  shift balances; I left the overtime balance off, as the spec changes no page but the form. It would be one column.
- The field is required in the API body, as the four others are; the SPA sends it. A client built before this would be
  refused with "Field required", which GitHub's backend job showed on `test_flow.py`'s hand-built body (fixed).

**Review:** `code-review` against `d759f0d`, both axes, on `cae3c18`. *Standards:* (1) "fair share" on screen against the
glossary's "overtime share": the label is the spec's, kept; the help reworded (above). (2) `HoursBalance` read like the hours
balance's type: renamed `OvertimeBalance`. (3) the form's new zod rule copied `balance`'s shape: one `within(max, message)`
for both. (4) the opening values are listed in about seven places (`OPENING_VALUES`, `_row`, `opening()`, `NEW_YEAR`,
`nurse_block`, two test tuples): true before this ticket, extended not created; kept, noted for whoever adds the next. (5)
`carried_from_may`'s optional balance: kept, the missing-key case is tested elsewhere. *Spec:* nothing missing or wrong; it
recounted every hand count from the fixture and the solver's formulas and got the same numbers; it named the table column
and the ARCHITECTURE sentence on where the reset is applied as beyond the words (kept, above). The fixes were small; no second
run. No Codex review, by the brief.

**Things later tickets should know.**
- **51:** once the unit rules write `share_overtime`, delete `shares_overtime` in `closes/tests/test_close.py` (or make it save
  the unit rule through the API) and leave the rest of `TestTheOvertimeBalance` as it is: its hand counts hold with a tolerance
  and limit of 12. The balance's opening value and chain are done; the weight's description can say the balance resets each
  January.
- **57:** a note on its ticket: the chain reads the profile's `overtime_balance` for a first month and resets it in January;
  `TestTheOvertimeBalance` is the case list beside the preferences count's.
- Whoever adds the next opening value: it is listed in `nurses.attributes_api` (body, row, `_row`, `OPENING_VALUES`, the lock's
  description), `closes.chain` (`opening`, `NEW_YEAR` if it resets), `nurses.rostering.nurse_block`, the form's schema,
  defaults and fields, and the table.

**Merged on 2026-11-12:** `main` fast-forwarded to `73bf19b`, the branch's head after merging `main` with tickets 52 (`2bf6bf2`)
and 72; both workflows green on it (solver, backend, frontend, image, browser checks), as on `2bf6bf2` before it. The local
suites ran on `79f1939`, before those merges; ticket 52 touched the solver's fairness for nurses on probation (none in these
tests) and ticket 72 how zod is imported (an alias, nothing in this ticket's files).
