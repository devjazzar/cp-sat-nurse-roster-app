# 52: The solver rosters a nurse on probation

**What to build:** The vendored solver's contract gains two optional per-nurse fields: that she is on probation, and her preceptor's id (absent means not on probation and no preceptor, so every stored solve input and close input still loads and gives what it gave). A nurse on probation counts toward nothing about a shift (headcount minimum and maximum, team leader, both genders, score target and balance, skill needs) and is left out of the day and night fairness, the weekend fairness, the overtime share and the unit's overtime totals, with her fairness balances zero in and zero out. She works no night shift. She works less than the hours she owes plus the length of her shortest allowed shift, the excess recorded as her own overtime; the shortfall rule is unchanged. One hard rule makes her follow her preceptor: on a followable day (a free day her preceptor works a day shift she is allowed, and she is not on leave, outside her dates or pinned) she works her preceptor's shift or is off, never another shift, and if any followable day is left off she works no free day that is not followable. With no preceptor there is nothing to follow, and precheck warns. Nothing in the app changes in this ticket. Spec: `.scratch/nurse-rostering-v2/specs/probation.md`; the words: `GLOSSARY.md` (Probation, Nurse on probation, Preceptor); the reasons: ADR 0014.

**Blocked by:** 49 The solver prices overtime above a nurse's share, and carries her balance (both change the solver's input, and she is left out of the overtime share)

**Status:** ready-for-agent

- [x] The request loader accepts the two nurse fields, treats them as absent = not on probation and no preceptor, and refuses, with the usual `request: <field path>` error, a preceptor that is not another nurse of the input, one who is herself on probation, one named by two nurses, and a preceptor on a nurse not on probation; the problem's schema version notes the change
- [x] She counts toward nothing about a shift: a headcount minimum is not met by her, a maximum not exceeded by her, a team leader, both-genders, score and skill rule not satisfied by her; the fairness figures, the overtime share and the unit's overtime totals are the same with and without her; her carried fairness balances are zero out
- [x] She works no night shift: her allowed shifts are narrowed by the unit's night shift, and a pin of the night shift on a free day of hers is refused
- [x] Her hours stay under what she owes plus her shortest allowed shift, shown with 12-hour shifts (208 owed, 18 shifts, 8 hours of overtime) and 8-hour shifts (26 shifts, none); the excess is her overtime for the month and the year; she may still end under one shift short and carry the debt
- [x] The following rule, in the registry as a hard rule: on every followable day she is on her preceptor's shift or off; hours win when her preceptor's day shifts are more than her hours hold, and she then works no free day that is not followable; a pin and leave hold over following; elapsed days are facts; her own rest, run and succession rules apply
- [x] With no preceptor she is rostered on freely placed day shifts, and precheck names her
- [x] The validator's and the explanation's words name the nurse, the day, her preceptor's shift and hers; the per-nurse explanation carries them
- [x] Tests in the constraint-verifier style for each of the above, expected values counted by hand; the service contract test's sample request and result carry the fields; the solver's suite, the service tests and the contract tests pass
- [x] `solver/DESIGN.md` gains the contract change; `docs/ARCHITECTURE.md` section 6 names the fields

**Worth your review, already known:** her rounding overtime is on her own record but outside the unit's overtime totals (the department cap and the overtime share), so it does not move her colleagues' shares; with shifts of several lengths the hours bound is her shortest allowed shift, the mirror of the existing shortfall bound.

## Comments

**Implemented on 2026-11-12,** on branch `claude/ticket-52-probation-solver-be79a3`, pull request
devjazzar/cp-sat-nurse-roster-app#25, from `main` at `d759f0d` (`856109a` the solver and its tests, `c0a5e63` the docs, `50156ad`
the review's points, then this comment). The suites, locally, under the heavy-run lock, on `50156ad`:
- the solver's whole suite with the service tests (`cd solver && uv run --no-sync pytest -q`): **736 passed**; 32 tests are new in
  `tests/test_probation.py` and four in `service_tests/test_contract.py`;
- the backend under pytest on a throwaway PostgreSQL 18 container of my own: **3430 passed**; `makemigrations --check`: no changes;
- no frontend, OpenAPI or Playwright change, so `npm test`, `npm run build` and the browser checks are GitHub's: both workflows
  (backend, solver, frontend, image, browser checks) green on `50156ad`.

**What the dev stack needs:** a **rebuild** (`docker compose up -d --build`): the vendored solver changed. No migration,
dependency, compose or Dockerfile change. The app writes neither field until ticket 55, so every solve on the stack is as before.

**What was built, criterion by criterion.**
- **The loader.** A nurse's `on_probation` (absent = false) and `preceptor` (absent or null = none), optional in both request
  versions; the problem's schema 7 → 8 (both optional in a problem file too; a version-7 file refused like any other). Refused
  with the path, checked after every nurse is read (`request._preceptors`): "request: nurses[2].preceptor: 'nobody' is not
  another nurse of the input" (her own id the same), "... 'Amal' is herself on probation", "request: nurses[3].preceptor: 'Amal'
  already precepts nurses[2] (one nurse on probation each)", "... 'Badr' is named for a nurse not on probation"; the types
  ("request: nurses[1].on_probation: must be true or false, got 'yes'"). `Problem.check` refuses the same by id. Absent fields
  load to the same problem as explicit `false`/`null` (same fingerprint), so every stored input gives what it gave.
- **She counts toward nothing about a shift.** One reading, `problem.counted`, read by the model, the validator, the precheck and
  the result: headcount minimum and maximum (`also_counts` included), team leader, both genders, score deficit and band/spread,
  skill needs (`skill_holders`). Hand counts: a D of 1..1 with her beside b is met and not exceeded, with her alone unmet; with b on
  leave one day the month is INFEASIBLE though she is free, and precheck says "day 1: headcounts need 1 nurses but only 0 are not
  on leave"; a team leader, a male and an ICU holder on probation satisfy nothing; b at 0.50 under 0.80 is 30 short with or
  without her at 1.00 (counted, 10). Fairness: `flexible` is false for her, the Friday slots are divided among the counted nurses
  and she has no Friday share; the overtime share's R and O and the department cap leave her out (`fairness.unit_overtime`). On a
  hand-built week the day, night and weekend fairness, the overtime share and the department overtime read the same, word for
  word, with and without her; her 6 h are on `nurse_overtime` only. Her three balances go out at 0 (April, through
  `nurse_accounting`; and the contract test).
- **No night shift.** `Problem.allowed`: her allowed shifts (or the unit's) less `night_shift`, her setting kept. A night pin on a
  free day is refused ("a: pinned shift 'N' on day 1 is the night shift, which a nurse on probation does not work"); an elapsed
  night is a fact. A night shift of hers in a grid is the `allowed_shifts` violation.
- **Hours.** `Problem.overtime_cap`: for her, the lower of the usual cap and her shortest allowed shift less 1. April 2026 (208 h
  owed), asking to work every day: 12 h shifts, 18 shifts, 216 h, 8 h over, a 19th refused ("overtime: a 20 > cap 11 (on
  probation: under one shift)"), a counted nurse would work 20; 8 h shifts, 26 shifts, none over, a counted nurse 30. Her
  `overtime` is 8 and her `ytd_overtime` 100 → 108; the department cap at 0 charges nothing for it. 17 shifts (204 h) end 4 short,
  nothing avoidable, `hours_balance` 4 carried.
- **The following rule**, `following`, hard, in the registry, active while some nurse on probation has a preceptor in the input.
  The judged days (`problem.followable_candidates`): from the cutoff, not pinned, not on leave (the days outside her dates are
  leave), not barred. Followable: her preceptor works on it a shift in her allowed set. Model: `fol[d]` = her preceptor on one of
  her shifts; her shift s on day d implies his s when `fol`; one literal `missed`, forced by a followable day off, forbids every
  judged day that is not followable. Hand counts: q on D, A, N, off, D, A, D: she is on D, A, -, -, D, A, D and works days 2 and
  3 on her own; seven days owing 48 h at 12 h with q on D six days: she follows four, and is off on the day q is off though she
  asked to work it; with q on D two days she follows both and fills 48 h; her accepted day off, her leave and her pin to A on q's
  D day hold, none judged; elapsed days where she worked A beside q's D are not reported; her run limit after D, D, D before the
  month leaves day 0 off, and then she works only q's days (".DD.D.."); her A → D succession after an A before the month, the
  same (".D.."). With two counted nurses free the month solves at 0, she on q's D every day q works it: the rule binds nothing of
  the preceptor. Mutation-checked: with the `missed` clause removed, three tests fail.
- **No preceptor.** She is rostered on day shifts placed freely (all four days asked, "DDDD"), the rule inactive, and precheck
  says "a: on probation with no preceptor, so she follows no one: she is rostered on freely placed day shifts, counted toward
  nothing".
- **The words.** "following: a works A on day 0, her preceptor q works D" and "following: a works D on day 2, when her preceptor q
  is off, while she is off on day 3, when q works D": the nurse, the day, her preceptor's shift and hers; each match carries her id
  and the day, so `/validate`'s rules and violations, and the result's `violations`, carry them per nurse.
- **Tests and contract.** The service test's copy of the sample (`with_faten`: a fifth nurse, Faten, on probation, Amal her
  preceptor) solves with no violation: Faten works no N, is on D or off on every day Amal works D, D's 1..1 is
  met by exactly one counted nurse every day while Faten works D beside one, her hours within 197..219, her three balances 0;
  `/validate` names her violation with its date; `/precheck` names her without a preceptor; an unknown preceptor is a 422
  "request: nurses[4].preceptor: 'Zaid' is not another nurse of the input". Every solve in `test_probation.py` checks that the
  solver's objective equals the validated cost with her in the month.
- **Docs.** `solver/DESIGN.md` (the request note, schema 8, the three readings and the rule), `solver/how-to.md` (the two fields),
  `docs/ARCHITECTURE.md` section 6.

**What was driven, and how.** The CLI on the ER sample with N20 on probation and N05 her preceptor (`uv run --no-sync python -m
nurse_roster solve <er_request_2026-03.json with the fields> --explain --workers 4`, 20 s): FEASIBLE, every hard rule kept, cost
matching the validator. N05 `.DD.NNN..D.DD.DDD..NN.NN.NN.NNN`, N20 `DDD...DD.D.DD.DDD.D.....DD....D`: on each of N05's eight D
days, no night, her other seven shifts on N05's nights and days off; 180 h of 182 owed (2 short, carried); her balances 0; every
shift-day's headcount met by the other 24 alone; precheck empty. Nothing in a browser: nothing in the app changed.

**What was NOT checked:**
- The app's side (tickets 54–56): nothing writes the fields yet; the scratch-stack check of the spec is ticket 55's.
- Performance beyond the ER sample: a boolean a judged day plus one a nurse on probation, and 2 + shifts clauses a day.
- That the preceptor's roster is exactly what it would be without her (below).
- The frontend suites locally: nothing in `frontend/` changed; GitHub's six runs and the browser checks are the evidence.

**Decisions taken here:**
- **Names:** `on_probation` and `preceptor` (the glossary's words), the rule `following`.
- **Her balances in are ignored, out are 0**, whatever came in ("zero in and zero out"); a value sent in is not refused.
- **`excess_weekend`, `excess_full_run`, the switch rule, preferences and `nurse_overtime` still apply to her**, as her own rules.
- **The solver refuses a nurse on probation whose allowed shifts are the night shift alone** (the spec puts that refusal in the
  app): without it she would have no shift and `min_shift_hours` would raise a bare error; it is the gap ticket 54 left for 55,
  now refused loudly at the solver too.
- **Worth your review, the ticket's own: her rounding overtime is on her own record** (`overtime`, `ytd_overtime`, priced by
  `nurse_overtime`) **but outside the unit's overtime totals** (the department cap and the overtime share's O), so it moves no
  colleague's share; **with shifts of several lengths the bound is her shortest allowed shift**, the mirror of `max_shortfall`
  (with D 12 h and A 8 h she stays under owed + 8).
- **Worth your review: with the hospital's hours rule off she has no hours bound**, as nobody does; the spec's "she works less than
  the hours she owes plus her shortest shift" is built inside the hours rule, like every hours bound.
- **Worth your review: the preceptor is not held "exactly as before".** Nothing in the rule binds him (she can always be off), but
  the solve is one model: her hours (the dominant `avoidable_shortfall`) and her preferences can pull the preceptor's free days
  toward day shifts she can follow, at no cost to his own rules. A two-stage solve (the counted nurses first, then her) would
  guarantee it; the spec does not ask for one.
- **Worth your review: the service sample file does not carry the fields,** as ticket 49's did not: the backend's tests and the
  browser checks' seed read its nurses. The contract tests add Faten on a copy; the result shows her fields' effects, not the
  fields (a result echoes no nurse attribute).
- **Worth your review: "which of her preceptor's day shifts she did not follow and why" (story 51) has no channel yet.** The
  per-nurse explanation the app shows holds priced soft rules only, and a hard rule has no match on a valid roster. I built
  criterion 7 as written (the violation's words) and added no result field; the note on ticket 55 says how to work the list out.

**Review:** `code-review` against `d759f0d`, both axes. *Standards:* the validator and the precheck built their own list of who
counts and the model summed the unit's overtime itself: all three now read `problem.counted` and `fairness.unit_overtime`; the
balances test called the fairness functions with inputs computed as the code does: now through `nurse_accounting` on April,
counted by hand. Kept: the followable test written in the model's and the validator's forms over the one set `Problem.allowed`
(a CP-SAT expression and a plain check cannot share code; `followable_candidates` and the allowed set are shared); the
`on_probation` guards in each fairness function (each says its own reason); the preceptor checks in both the request (paths) and
the problem (ids), the `overtime_balance` pattern. *Spec:* no correctness finding; it flagged the sample copy, the night-alone
refusal and the hours rule off (all above), and that elapsed days left the judged set only by being pinned: the set now starts at
the cutoff as well. The fixes were small; no second run. No adversarial review, by the brief.

**Things later tickets should know.**
- **55:** a note on ticket 55 says what to write into the solve input, the refusals, and the explanation gap.
- **56:** headcounts the app works out itself must leave her out with the solver's reading (`problem.counted`).

**Merged on 2026-11-12:** `main` fast-forwarded from `d759f0d` to `4faa2f0`; both workflows (backend, solver, frontend, image,
browser checks) green on `50156ad`, the last code commit; what follows it is this ticket's markdown only (`[skip ci]`).

**Reviewed by the user (2026-11-12):** all seven points kept as built.
- Her rounding overtime on her own record, outside the unit's totals.
- With shifts of several lengths, the hours bound is her shortest allowed shift.
- With the hours rule off, no hours bound for her, as for every nurse.
- One solve: her preceptor's roster is not guaranteed the one he would have without her; ticket 55 watches for it on the real thing.
- The shared sample file without the fields; the contract tests add a nurse on probation to a copy.
- Story 51's list of shifts not followed is ticket 55's, from this ticket's note.
- The solver also refuses a nurse on probation whose allowed shifts are the night shift alone.
