# Nurse roster solver — design (validation phase)

Goal: validate Google OR-Tools **CP-SAT** for monthly rosters, multi-department, with hospital-wide
general rules plus per-department rules. Test department: ER, 25 nurses (since 2026-11-03 a test
fixture only; the solver carries no unit's rules, see "Request/result contract").

## Decision variables
`x[n][t][s]` — nurse `n` works shift `s` on horizon day `t`; `off[n][t]` — nurse is off.
Exactly one of them is true per nurse per day. The horizon is P history days (fixed to the
previous month's tail, P = 10) followed by the D month days, so every pattern rule (successions,
night rest, max-in-a-row, double cycle) runs over the whole horizon and sees across the month
boundary with no special cases. Hours, headcount, fairness and weekend counts use month days only;
night-rest penalties count only when the D day is inside the month. Presolve removes the fixed vars.

## Data contract

### Request and result (`request.py`, `result.py`; request schema 2, schema 1 still read; result schema 1)
The solver is a pure function of one **request**: one unit, one month, every rule explicit, dates
not indices. A caller (the future app, with its database of hospital rules, units, nurses and
results) assembles the request and stores the **result**; the solver has no database and no
defaults that could hide a unit's numbers. Decided 2026-11-03.

    {"version": 2, "month": "2026-03",
     "ramadan_days": {"from": "2026-02-18", "to": "2026-03-19"},     # optional
     "public_holidays": [],
     "general": {... every GeneralRules field, "weights": {... every Weights field}},
     "department": {... every DepartmentRules field},
     "nurses": [{"id": "N01", "gender": "M", "team_leader": true, "score": 0.99,
                 "ramadan_reduced": false, "breastfeeding": false, "ytd_overtime": 100,
                 "hours_balance": 0, "night_balance": 0.0, "friday_balance": 0.0,
                 "leave": ["2026-03-04"], "undesired_days": [], "desired_days": [],
                 "pinned": {"2026-03-01": "D"}, "allowed_shifts": null,
                 "previous": ["D", "D", "", "N", "N", "N", "", "", "D", "D"],
                 "last_shift_kind": null, "rest_owed": 0, "preferences_not_kept": 0,
                 "skills": {"BLS": "2026-03-14", "ICU": null}}],          # optional (version 2)
     "solver": {"time_limit_seconds": 20, "reproducible": false},
     "published": {"N01": {"2026-03-01": "D", "2026-03-02": "", ...}},   # optional
     "replan_from": "2026-03-12",                                      # optional
     "renamed_shifts": {"N": "Night"}}                                 # optional

* **Version 2 (2026-11-09, skills; ADR 0010 of the app).** `general` gains `required_skills`
  (the skill names required to work, each once) and `weights.skill_shortfall`; `department`
  gains `skill_needs` (a list of `{"shift", "skill", "weekday_min", "weekend_min"}`, the shift
  one of the unit's, one need a shift and skill) and `skill_needs_hard`; all four are required.
  A nurse's `skills` (optional, absent = no record) maps each skill name to its **expiry**, the
  last day it counts, or null for one that counts all month. The expiry is the one dated field
  accepted before the month: a skill expired before it is sent with that date, because absence
  has to mean "no record" (only a recorded required skill that expired keeps her off), and it
  is read as expired before day 0 whatever the date. A date after the month is refused (the app
  sends null), as is a skill named twice in a list or a need naming a shift the unit does not
  work. **Version 1 is still read**, as version 2 with no skills, no needs, the needs hard, no
  required skills and the weight 0 (`request._version_1`, on copies: a stored input is never
  touched), because every input the app stored before is version 1: a draft is still explained
  and a month still closed from it. A version-1 request carrying any of the five fields is
  refused, so nothing is read half one version and half the other. This departs on purpose from
  the internal problem's refusal of older schemas (below): the request is the app's history, the
  problem file is not. The result's `version` stays 1: its shape did not change (its `penalties`
  gain the key `skill_need`, as for every soft rule, and a violation may name `skill_need` or
  `skill_expired`).
* The server derives the day count, first weekday and Ramadan days from `month`
  (`calendar.parse_month`). `ramadan_days` has three states: absent/null = derived from the
  Umm al-Qura calendar, `[]` = none, a list of dates = exactly these; a `{"from", "to"}` range
  (may start or end outside the month) is intersected with the month, for the dates fixed after
  the moon sighting.
* `general` (hospital-wide) and `department` (the unit) carry **every** field of
  `GeneralRules` / `Weights` / `DepartmentRules`; a missing one is an error with its path
  (`request: general.weights: missing field(s) ['change']`). Per nurse the twelve scalars are
  required, among them the two memories the rules keep across any number of days (2026-11-04):
  `last_shift_kind`, the kind ("night", "day" for any other work, null when none is known) of
  the last shift she worked before `previous` begins (the switch rule's memory; a kind, so it
  survives a renamed or retired shift), and `rest_owed`, the off days still owed to her last
  night before `previous` begins (the night-rest rule's memory). A name in `previous` the
  unit no longer defines is accepted as work of no kind (neither night nor day; precheck
  says so); `renamed_shifts` maps the old name of a renamed shift to its current one in
  every history. One more carried scalar may be absent (2026-11-08, ADR 0013 of the app), so a
  request stored before it still loads: `preferences_not_kept` (absent = 0), how many of her
  undesired and desired days the month before did not keep; above 0, each of hers this month is
  priced twice (`problem.preference_factor`, read by the model, which lists her term twice, and by
  the validator, whose match has amount 2 and says "counts double"). The six lists (`leave`, `undesired_days`,
  `desired_days`, `pinned`, `allowed_shifts`, `previous`) may be absent (absent = none).
  Unknown fields are errors.
* Dates are `YYYY-MM-DD` inside the month, no duplicates; a wrong shift name, an unknown
  nurse, an out-of-month date is reported by the loader with the date, before the internal
  check could report an index. Only `ValueError` leaves the loader, prefixed `request: <path>:`.
* `solver.time_limit_seconds` is the budget; `reproducible: true` solves with one worker, a
  fixed seed and a *deterministic-time* budget of that many units (`max_deterministic_time`,
  CP-SAT's own clock, which runs 4–5× slower than the wall clock with one worker on a 10-nurse
  month), so the same request gives the same roster on any machine; the wall clock (10× the
  budget) then only stops a runaway search, and the result's `solver.stopped_by` /
  `solver.deterministic` say what ended it. Single-worker search is slow on the real ER instance (first roster after
  ~40 s), so the mode trades speed for determinism. The worker count is a server setting
  (`--workers`, `$NURSE_ROSTER_WORKERS`, default 8), never part of the request.
* `published` is the roster in force in the shape the result's `roster` has, so a result can
  be pasted straight into the next re-plan request; `replan_from` is the first date to re-plan
  (`Problem.replan_from`). The first day after the month is accepted too: every day has
  happened, the recorded facts are validated and reported, and the carry-over is computed
  from them (month-end reconciliation; a last-day shortage is then a fact, not an
  infeasibility). Under-hours has no hard floor at all (2026-11-04): what a nurse can still
  work is bounded by every other hard rule at once (runs, rest, headcount maxima), so a floor
  from any per-nurse bound could make the month infeasible. Instead the `avoidable_shortfall`
  weight, meant to dominate the others, charges every hour she ends short beyond a remainder
  below one shift and the hours her recorded and free days cannot give
  (`Problem.unreachable_hours`): a preference never idles a free shift of hers, an hour the
  run rule costs her is reported as a cost, and the whole debt is carried into next month's
  `hours_balance`. A weight is no guarantee: a search stopped by its time limit may still
  carry avoidable shortfall, and so may an optimal one when the other rules and preferences,
  at their weights, cost more than the shortfall (an `undesired_day` weight above
  `avoidable_shortfall` × 12 h keeps a shift idle); the penalty, the per-nurse `shortfall` and
  the CLI's "avoidable shortfall" line make it visible, and the CLI never claims that a hard
  rule made it unavoidable, since weighted optimality proves no such thing.

The result (`result.build_result`, written by `solve --out`):

    {"version": 1, "month": "2026-03", "ok": true, "status": "FEASIBLE", "message": "",
     "fingerprint": "<sha256 of the problem the roster was scored against>", "precheck": [...],
     "roster": {"N01": {"2026-03-01": "D", "2026-03-02": "", ...}},        # "" = off or leave
     "violations": [{"rule": "headcount", "nurse": null, "date": "2026-03-02", "text": "..."}],
     "elapsed_violations": [...],                            # facts before replan_from
     "cost": 23, "penalties": {"night_rest": 0, ...}, "department_cost": 9,
     "solver": {"objective": 23.0, "best_bound": 18.0, "solve_seconds": 20.1, "build_seconds": 0.07,
                "deterministic_time": 11.3, "improvements": 7, "workers": 8, "reproducible": false,
                "time_limit_seconds": 20, "deterministic": false, "model": {"variables": ..., ...}},
     "replan": {"from": "2026-03-12", "recorded_cells_differ": 2},        # null when absent
     "nurses": {"N01": {"leave": ["2026-03-04"], "contract": 200, "leave_credit": 8, "required": 192,
                        "hours_worked": 192, "overtime": 0, "shortfall": 0, "shifts": {"D": 9, "N": 7},
                        "cost": 3, "carry_over": {"hours_balance": 0, "night_balance": 0.33,
                                                  "friday_balance": -0.2, "ytd_overtime": 100,
                                                  "previous": ["N", "N", "", "", "D", "D", "D", ""],
                                                  "last_shift_kind": "day", "rest_owed": 0,
                                                  "preferences_not_kept": 1}}}}

* `carry_over` uses the request's own nurse field names: next month's request is this month's
  static nurse fields plus this block (`hours_balance` = `Problem.carry_over`, the balances =
  `fairness.balances_out`, `ytd_overtime` = input + this month's overtime, `previous` = this
  month's row (more only when `precheck.needed_history` exceeds a month; capped at
  `MAX_HISTORY`), `last_shift_kind` and `rest_owed` = the two memories walked up to where that
  row begins (`validate.last_worked`, `validate.rest_owed_after`), so a history of any length
  collapses into one month plus two scalars with nothing the rules read lost), and
  `preferences_not_kept` = this month's days asked off and worked plus asked to work and off,
  leave days out, whatever the weights (`validate.preferences_not_kept`). The app resets
  the year-to-date value and the balances at year start. Leave days are `""` in `roster` and listed under `nurses[id].leave`;
  `"L"` never appears in JSON (it is the CSV export's marker only).
* `ok` is true exactly when the CLI exits 0 (`result.verdict`: 1 no roster, 2 hard violations,
  3 model / validator mismatch). Without a roster `roster`, `nurses` and `cost` are null.
* `fingerprint` is opaque and comparable only within one code version. The result is
  serialized from the snapshot the roster was scored against (`Solution.problem`), never from
  the caller's request, which an app may edit while the solver runs; a problem that no longer
  matches the model's fingerprint is refused. `Request`, `MonthInfo` and `SolverSettings` are
  frozen, the solution records the limits it ran with (`Solution.time_limit` / `workers` /
  `seed` / `deterministic_budget`), the month itself is a field of the problem (`Problem.month`,
  set by the loader, checked against the day count and first weekday, part of the fingerprint),
  and `build_result` takes the month, the cutoff with its recorded differences
  (`Problem.recorded_differences`) and the settings from the snapshot and the solution,
  refusing a request that disagrees with them, another month of the same shape included
  (2026-11-04).
* `solver.stopped_by` names what ended the search (`proof`, `deterministic_budget`,
  `time_limit`, `cancelled`, `model_invalid`); `solver.deterministic` is true only for a proof
  or an exhausted deterministic budget under `reproducible`, never for a wall-clock stop or a
  cancellation, however short the run. The cause follows CP-SAT's own limits (`model.stop_cause`):
  it stops at or just past the limit it hit, so the budget is the cause only when the
  deterministic clock is at or past it *and* the wall clock is still under its limit; both
  tripped is ambiguous and counts as the wall clock's.

The CSV (`export.write_csv`) survives as an optional export of a result (`solve --csv`); there
is no CSV reader any more. The ER instance (real scores, the three single-shift nurses, the
random generator) lives in `tests/er_fixture.py`, and `tests/fixtures/er_request_2026-03.json`
is the committed ER request every end-to-end test and benchmark uses.

### Internal problem (`problem.py`; schema 5, everything explicit)
The solver's own contract, built by the request loader (0-based day indices, derived calendar).
`Problem.from_dict` / `to_json` round-trip it for tests and debugging; schema 3 (2026-11-03)
requires every field of the rule objects and every nurse scalar, and refuses versions 1 and 2
instead of migrating them (a migration could only work by filling defaults the code no longer has).
Schema 4 (2026-11-08) adds the optional nurse scalar `preferences_not_kept` (absent = 0) and
refuses a version-3 file like any other; the request's own version stays 1, the field optional.
Schema 5 (2026-11-09) adds skills: `GeneralRules.required_skills`, `Weights.skill_shortfall`,
`DepartmentRules.skill_needs` (`SkillNeed`: shift, skill, weekday_min, weekend_min) and
`skill_needs_hard`, all required in a file, and the optional `Nurse.skills` {name: last day index
or null}, where -1 is any day before the month. A version-4 file is refused like any other. The
two versions move apart here: the request goes from 1 to 2 and still reads 1 (above); the problem
goes from 4 to 5 and reads only 5, since the request loader builds every problem and no stored
input is a problem file. (The Python dataclasses give the new fields defaults, empty and hard,
so code that builds a problem by hand need not name them; `from_dict` still requires them.)
* `Nurse`: id, gender, team_leader, score (0–1), ramadan_reduced, breastfeeding, ytd_overtime,
  unavailable days, `allowed_shifts` (None = any; ER: staff 4 and 11 D only, staff 13 N only),
  `previous` = the last days of the previous month (a month, from a result), oldest first, shift
  name or "" for off, `last_shift_kind` / `rest_owed` = the switch and night-rest memories before it,
  `preferences_not_kept` = last month's unkept preferences (above 0 doubles this month's price),
  `undesired_days` / `desired_days` (soft requests, disjoint from each other and from leave),
  `pinned` = {day: shift or ""} cells fixed by the admin or already worked (hard): the record
  of executed work, which the published plan never overrides.
  Staff numbers are 1-based: ids N01..N25, team leaders N01..N06.
* `GeneralRules`: shift hours (D/N 12 h, A/B/C 8 h), hours/day (8, Ramadan 6), weekend weekdays
  (Friday), forbidden successions, overtime caps (40 h/month, 720 h/year, 400 h/dept soft), weights.
* `DepartmentRules`: shifts used, headcount rules per anchor shift (with overlapping shifts that also
  count), team-leader / gender requirements, minimum average score, night-rest rule, fairness shifts.
* `Problem`: days, first weekday, `month` (the "YYYY-MM" it was built for, optional for a problem
  built by hand), public holidays, Ramadan days, nurses, general, department,
  `published` = the roster in force (nurse × day shift names), the baseline a re-solve stays
  close to (weight `change` per unpinned cell that differs); `replan_from(day)` pins the past:
  recorded facts (pins, leave) are kept, the rest is filled from the plan, and `planning_from`
  = day marks the cutoff: days before it have happened (every cell pinned), so a hard rule they
  broke is reported (`Analysis.elapsed`), not enforced, while an obligation reaching into the
  free days still is, exactly as for the previous-month history.
  `Problem.check()` is the contract: strict types (flags are booleans, arrays are lists), every
  name a rule refers to resolves (`night_shift`/`day_shift` in `shifts` while a night rule is on,
  fair shifts have a headcount, succession pairs name known shifts), and sizes are bounded
  (`days` ≤ 62, history ≤ 62 days, ≤ 1000 nurses, weights ≤ 10^6, `|hours_balance|` ≤ 10^6: a
  sanity bound only since 2026-11-04, because a month whose recorded days could not reach the
  requirement carries its whole debt, which no shift length bounds). `from_dict` only ever
  raises `ValueError`.
  Required hours = (days − Fridays − holidays) × 8, with 6 on Ramadan days for eligible staff,
  minus 1 per working day for breastfeeding staff (8→7, Ramadan 6→5).
  Leave days (sick, educational, marriage, bereavement…) are off and credited as worked at the
  nurse's regular daily rate (8 / 6 / 7 / 5), so hours to work in shifts = contract − credit;
  leave on a Friday or holiday earns nothing. Decided 2026-10-30. The requirement never goes
  below 0: an advance credit a month cannot absorb (`unused_credit`) is carried on, not paid
  as overtime; `carry_over(nurse, worked)` gives next month's `hours_balance`: below the nurse's
  own shortest shift when the month was planned (2026-11-01), the whole debt when its recorded
  days could not reach the requirement (2026-11-04).
  `ramadan_days` is a per-day list, so a Ramadan that straddles two Gregorian months is just
  the subset of days that fall in it. `calendar.month_info(year, month)` derives days, first
  weekday and the Ramadan day list from the Umm al-Qura calendar (hijridate); the request's
  `ramadan_days` overrides it after the moon sighting. Verified: Ramadan 1447 = 18 Feb – 19 Mar
  2026, and a Ramadan-eligible nurse in March 2026 owes 17×6 + 10×8 = 182 h.

## Rules implemented

General, hard:
| Rule | Encoding |
|------|----------|
| One shift per day | `add_exactly_one(shifts + off)` |
| Forbidden successions (10 pairs) | clause `¬x[d,a] ∨ ¬x[d+1,b]` for pairs whose shifts the department uses |
| Hours: `worked − required = overtime − shortfall` | one IntVar each per nurse |
| Shortfall < one shift (carried to next month as `hours_balance`) | soft since 2026-11-04, weight `avoidable_shortfall` (meant to dominate) per hour of `shortfall − (min shift hours − 1) − unreachable`, where `unreachable` (`Problem.unreachable_hours`) is what her recorded and free days cannot give; no hard floor, since the other hard rules bound what she can still work; the whole debt carried |
| Overtime ≤ 40/month and ≤ 720 − YTD | `ot ≤ min(40, 720 − ytd)` |
| Unavailable days | `off = 1` |

General, soft: department overtime > 400 h (per hour), individual shortfall (1 per hour,
carried over), individual overtime (1 per hour, so
reduced-hours staff stay at contract unless coverage needs them; hours above the department cap
therefore cost 2); contract-relative D/N fairness: for every nurse free to work both, the
deviation of her D (and N) count from `share × shifts_worked`, where share comes from the headcount
demand (50/50 in ER), is penalised per 0.1 shift beyond a free half-shift tolerance — linear, so
no weak bound; Friday fairness: max − min of Fridays worked across all nurses.
In a two-shift unit the D and N deviations mirror each other, so the pair simply doubles the weight.

ER, hard: headcount D and N 7–9 on weekdays, 8–9 on Fridays;
max 3 shifts in a row ("cycle") — clause: an off day in every window of 4;
cycle + 1 day off + cycle ⇒ at least 2 days off — clause per window of 7 days and each of the
2 following days (W W W O W W W → O O);
≥ 1 team leader on every D and N; ≥ 1 male and ≥ 1 female on every D and N;
shift restriction: `x = 0` on every month day for shifts outside `allowed_shifts`.
Fair D / N distribution is measured only among nurses free to work both shifts, since a
single-shift nurse cannot have a fair mix.

ER, hard (since 2026-10-30, was soft): N → D with fewer than 2 rest days between — plain clause
`¬x[t,N] ∨ ¬x[t+2,D]`; `night_rest_hard=False` turns it back into the soft, penalised form.

General, soft — cross-month fairness (2026-10-30): each nurse carries `night_balance` and
`friday_balance` (shifts above (+) or below (−) her fair share, cumulative, reset by the app at
year start). This month's night target becomes share × shifts − balance (day target mirrors it)
and the Friday target becomes fair Friday share − balance, each adjustment clamped to
`carry_cap` (2 shifts) per month. Friday fairness is therefore now a per-nurse deviation from
the fair share (Friday slots ÷ nurses, tolerance 0.5 shift) instead of a max − min spread.
The reports give `night_bal_out` / `fri_bal_out` per nurse for next month. Shared arithmetic lives
in `fairness.py` so model, validator and reports agree.

ER, hard: no mixed D/N work blocks — D→N and N→D added to the forbidden successions
(`no_mixed_blocks`, 2026-10-30).

Skills (2026-11-09, request version 2, ADR 0010 of the app), two rules in the registry:
* **`skill_need`**, hard or soft by `skill_needs_hard` (as night rest is by its flag), weight
  `skill_shortfall` (the one soft rule whose weight field is not its id; `RULES[id].weight`
  names it), unit "nurse short of a skill need on a shift-day", on when the unit has a need.
  Per need and day: the nurses on exactly its shift holding the skill that day
  (`problem.holds_skill`: recorded, the day not after its expiry; `problem.skill_holders`)
  against the weekday or weekend minimum. Hard: `Σ x ≥ min` on every free day (an elapsed day
  is a fact, reported in `Analysis.elapsed`). Soft: `short ≥ min − Σ x`, `0 ≤ short ≤ min`, one
  term per shift-day priced by the weight; elapsed days still counted, as every soft rule's are.
  The match reads "skill need: day 4 N has 1 holding ICU, needs 2 (1 short)", amount the
  nurses short. It does not count a headcount's `also_counts` shifts.
* **`skill_expired`** (the bar), hard, unit "shift on a day a required skill has expired", on
  when some nurse holds a required skill that expires before the month's last day. From the day
  after the first such expiry she works no shift (`problem.barred_days`): fixed off on every free
  day; an elapsed shift on one is a fact. `max_hours` skips barred days like leave, so the hours
  her remaining days cannot hold are unreachable: exempt from `avoidable_shortfall` and carried
  over whole in `hours_balance`, the existing mechanism; unlike leave they earn no credit. A
  nurse with no record of a required skill is not barred. A shift pinned on a barred free day is
  refused by `Problem.check` (as one on a leave day is). The match reads "skill expired: N01
  works D on day 15, BLS is required to work and its last day was day 14" ("was before the
  month" for one expired earlier).
* Precheck: barred days count like leave in every capacity sum (per nurse and per day); a need
  whose skill no nurse holds on any free day; a need whose largest minimum exceeds the nurses who
  hold the skill and may work the shift; per free day, a minimum above the holders who may work
  the shift that day (not on leave, pinned elsewhere or barred); per nurse, each required skill
  expiring inside the month (before its last day), with its last day.

ER, soft:
* D/N switches above `max_switches` (2) per month: a memory Boolean per nurse-day (last worked
  type was N), a switch literal when a worked day differs from the memory, excess penalised
  (weight 8). History feeds the memory so the month boundary counts. Decided 2026-10-30.
  This combination (pure blocks + hard N→D rest + switch limit + Friday score target) makes the
  soft optimisation converge slowly: 20 s gives a rough roster, 120 s a reasonable one. A
  structural solve shows ≤2 switches is always achievable; a hard version did not converge faster.
* More than 3 weekend days (Fridays) worked: `excess ≥ Σ work[fri] − 3`, per weekend.
* Score target: each shift's average score should reach `score_target` (0.70 on weekdays,
  `score_target_weekend` 0.80 on Fridays). Shortfall is an IntVar `deficit ≥ Σ(thr − score)·x`,
  penalised per 0.01 × person. The band ceiling is likewise 0.78 weekdays / 0.88 Fridays.
* Score balance, default mode "band": each shift's average should also stay ≤ `score_band_hi`
  (0.78); the excess above it is a linear IntVar, so together with the 0.70 target every shift is
  pushed into a 0.70–0.78 band. Mode "spread" (minimise `avg_hi − avg_lo`, averages linearised by
  enumerating headcount h) is kept as an option but gives CP-SAT a weak bound.
Scores are integers ×100 inside the model. Real ER scores (25 staff) live in
`tests/er_fixture.py` (`ER_SCORES`), assigned in descending order so the 6 team leaders hold the
top 6 scores (assumption).

Rule switches (2026-10-30, so a front end can turn rules on/off): `GeneralRules.forbidden_successions_enabled`,
`hours_rule_enabled` (off: any number of shifts, no overtime / shortfall terms),
`overtime_caps_enabled` (off: per-nurse cap = 24 h × days, yearly cap ignored) and
`DepartmentRules.headcount_enabled`; all given by the request (the ER fixture sets them on) and
honoured identically by the model, `validate.py` and `precheck.py`. Other rules switch off via
their existing fields (bools, 0 values, weight 0).

Decisions confirmed with the ward (2026-10-30): weekend = Friday only; no O shift in ER;
department overtime cap is soft; score rule = soft target 0.70 **plus** balance across shifts.

## Results (2026-10-30, 8 workers, OR-Tools 9.15, 25 nurses, D/N, real scores, all rules so far)
| Instance | Build | 30 s result |
|---|---|---|
| 31 days, baseline, 10-day history | ~70 ms | 23 vs bound 18: 9 h unavoidable OT, D/N spread 2 and 1, score spread 0.05 |
| 31 days, seed 7 | ~66 ms | 19 vs bound 15 |
| 31 days, Ramadan | ~64 ms | 566 vs bound 559: 471 h OT needed, 71 h above dept cap |
| 31 days, 2 holidays, 5 Fridays | ~64 ms | 851 vs bound 836: 600 h OT needed, 200 h above cap, 5 excess Fridays |

Build time stays ~55 ms with ~5 000 constraints. Good solutions appear within 5–10 s; proving
optimality is slowed only by the score-balance encoding. Validator confirmed all hard rules and
reproduced the objective on every run.

    # since 2026-11-03 (the `bench` / `gen` commands of the time are gone):
    uv run python -m nurse_roster solve tests/fixtures/er_request_2026-03.json --out result.json --csv roster.csv

## Review (2026-10-30): bottlenecks, fixes, open points

Python is not a bottleneck: build is 60–70 ms for 25 nurses and ~200 ms for 100 nurses
(16 k vars / 22 k constraints); solution extraction and validation are milliseconds.

What slows the *solver* and what was done:
| Finding | Evidence | Action |
|---|---|---|
| Score-balance via ratio (max−min of averages) gives a weak bound | 25 nurses: 20 s, obj 24 vs bound 15, unproven; without it: optimal in 1.8 s | Linear "band" encoding is now default: optimal in ~2–10 s, shift averages 0.70–0.78 |
| Fairness via max−min of counts is the remaining weak piece at 100 nurses | 100 nurses: good solution at ~15–25 s, bound gap stays | Acceptable for monthly use; option: two-phase solve (no fairness → hint) gave 129 vs 144 at 60 s |
| Fixed history could make the month infeasible | random 100-nurse history broke the double-cycle rule → INFEASIBLE | Pattern rules now constrain only windows that reach into the month |
| Solver params: workers 4/8/16, symmetry_level 2, linearization 2 | no consistent gain over defaults with 8 workers | Keep defaults. `random_seed` is fixed, but a wall-clock time limit with 8 workers is not reproducible: the same input can give a different roster (audit 3). Reproducibility would need `max_deterministic_time` and one worker |
| Warm start | hint from a previous solution → optimum in 0.1 s instead of 4 s | `solve(..., hint=assignment)` for re-solves after an admin edit |
| INFEASIBLE comes with no explanation | — | `precheck.py`: capacity vs demand (department, team leaders, each gender), per-day availability against leave, eligibility per shift, per-nurse fewest shifts over every allowed shift length vs the exact "at most m shifts fit the month under the cycle rules" (small-state DP over the calendar, leave days forced off, history sets the start state), history depth vs rule look-back, shifts no headcount governs |

Open policy points (not solver issues):
1. Leave credited as regular hours — done.
2. Thursday-night N shift: only shifts dated Friday count as weekend — confirmed, keep.
3. Public holidays reduce owed hours but not headcount — confirmed.
4. Ramadan override after moon sighting — `--ramadan-days`, and the JSON list is editable.
5. Friday fairness and contract-relative D/N fairness — done (2026-10-30).
6. Remainders: decided 2026-10-30 — a shortfall smaller than one shift is allowed and carried to
   next month via `Nurse.hours_balance` (+ owed, − worked ahead); overtime and shortfall are
   penalised equally so the nearest shift count wins (200 h owed → 204 worked, 184 → 180 and 4 h
   carried). The CSV reports `balance_in`, `overtime`, `carry_over` per nurse for the next run.

## Adversarial audit (2026-10-31): core fixes

An adversarial audit reviewed revision 54a8685 (report since removed; findings summarised here). The core findings were fixed as below; the
interface-only findings (F02 F03 F04 F07 and the app side of F05 F09 F17) concerned the temporary
Streamlit playground, which was removed on 2026-10-31 (it lives on in git history on the `streamlit`
branch). A future front end should still honour those invariants: bounded day-range parsing,
transactional imports, results tied to the exact inputs they were solved for, and enough history
for the active pattern rules (`precheck.needed_history`). Every core fix has a regression test in
`tests/test_audit.py`.

| Finding | Fix |
|---|---|
| F01 omitted JSON `headcounts` silently emptied the staffing rules | `Problem.from_dict`: absent fields keep the dataclass defaults, an explicit `[]` stays empty, unknown fields are an error |
| F06 night rest counted calendar days | A D is forbidden (or penalised, once per D day) while fewer than `night_rest_days` off days have passed since the last N. In a pure D/N unit the short clauses are exact; with a third worked shift, gaps up to `R·(K+1)` days get an enforced linear `Σoff ≥ R`. Validator walks back from each D counting off days |
| F08 unchecked day indices | `Problem.check()` validates every field (indices, ids, genders, scores, shift names, headcounts, weights) and runs in `from_dict`, `build_model`, `validate`, `precheck` |
| F09 `allowed_shifts: []` | rejected by `check()` (use `null` for any shift, leave days for absence) |
| F10 single-shift nurses skipped the switch rule | the switch memory is built for every nurse, so a D-history nurse restricted to N this month counts the boundary switch |
| F11 Friday-fairness deviation bound could cut feasibility | deviation bounds derived from the target and the count range (D/N deviation bound widened by the carried adjustment too). Fairness targets keep coming from the headcount midpoints even when headcount enforcement is off; that is the intended definition |
| F12 spread mode enumerated the pure headcount over the combined bounds | enumerates 0..max (0 = no shift) so overlapping `also_counts` coverage stays legal |
| F13 solver and validator disagreed on switches with A/B/C | definition: a switch is a change between night work and any other work; A/B/C are day-type. Same in model (`¬off ∧ ¬N` after N memory) and validator |
| F14 CSV formula injection | text cells starting with `= + - @ TAB CR` are prefixed with `'` in every CSV row |
| F15 validator accepted malformed matrices | shape and domain (`-1..S−1`, integers) are checked first; a bad matrix returns only `matrix:` errors |
| F16 precheck span bound was wrong and ignored leave as rest | replaced by an exact DP (`max_shifts_fit`) verified against brute force in the tests |
| F05 (core) truncated history can hide a boundary violation | `needed_history(dep)` = max(K, 2K+R, rest look-back); precheck warns when a nurse's history is shorter |
| F17 (core) converter range | `month_info` raises a clear `ValueError` outside 1924-08-01..2077-11-16; the app's year selector stops at 2076 |

ER benchmark after the fixes: build 75 ms, 5.2 k vars / 10.2 k constraints, validator matches the
solver objective; the solve profile is unchanged (the extra rest constraints only appear with a
third worked shift).

## Adversarial review (2026-10-31, second pass): core fixes

A second read-only review of 82ff0cc found six core issues, fixed on branch `review-fixes`
with regression tests in `tests/test_review.py`.

| Finding | Fix |
|---|---|
| 1 `also_counts` could name the anchor or repeat a shift, counting one nurse twice | rejected by `Problem.check()`; with distinct shifts a nurse holds one shift a day, so model, validator and CSV count people once |
| 2 rest owed from history relied on the history obeying the max-in-a-row rule | rule restated as "the first D after an N needs R off days in between; an earlier D ends the rule". In-month gaps keep the bounded encoding (the cap holds inside the month); for the last historical N with no D after it, the off days still owed are known and enforced on the first D of the month directly. Validator stops its walk-back at a D |
| 3 score targets / band limits accepted 1.1 or NaN, turning a soft rule into INFEASIBLE or a crash | `check()` requires finite numbers in 0..1 for the four thresholds, non-negative `fair_tolerance` and `carry_cap`, finite nurse scores and balances |
| 4 unknown root JSON fields were dropped silently | the root object goes through the same unknown-field check as nested objects |
| 5 precheck ignored `also_counts` coverage | eligibility counts nurses able to work the anchor or any shift counted with it (team-leader and gender checks stay on the pure anchor); minimum demand is divided by the largest number of headcounts one shift can satisfy |
| 6 `generate` sampled up to 5 leave days whatever the horizon | sample bounded by `days` |

ER benchmark after the fixes: build ~72 ms, same model size, validator matches the solver objective.

## Adversarial audit (2026-10-31, third pass): three reports, core fixes

Three independent reviews of 70f3506 (`AUDIT-2026-10-31-CC/OC/CO.md`) agreed that the hard-rule
encodings are sound (exhaustive model-vs-validator sweeps found 0 disagreements) and that the
gaps were in the input contract, cross-month fairness arithmetic, precheck coverage and the
reported numbers. Fixed on branch `audit3-fixes`, regression tests in `tests/test_audit3.py`.

| Finding (CC / OC / CO) | Fix |
|---|---|
| CC1, OC A3: night balance drifted when N was not a fair shift (+21 after one month) | `balances_out` moves the night balance only when the night shift is a fair shift for the nurse |
| CC2: Friday balance not prorated for leave (−2.72 after a month of leave) | `friday_expected_m(p, nurse)` is prorated by the weekend days the nurse is not on leave; model, validator and carried balance all use it |
| OC A6: integer-percent shares never summed to 100, biasing every target | shares are in thousandths and sum to exactly 1000 (residual to the largest share) |
| CC3, OC A5, CO3: precheck silent on attribute capacity and leave clustering | per month: anchor-shift slots vs Σ most-shifts of team leaders / each gender; per day: nurses not on leave vs demand, eligible nurses per headcount, team leader and gender availability per anchor shift |
| CC8: precheck false alarm with mixed shift lengths | `fewest_shifts`: DP over every allowed shift length for the window `[required − shortfall, required + cap]` |
| CC4, OC A3: flags and lists were not type-checked (`"team_leader": "no"` was true, `"general": []` silently defaulted, `first_weekday: true`) | `check()` requires booleans for every flag, lists for every array, objects for `general` / `department` / nurses / headcounts |
| CC5, OC A3, CO2: `night_shift: "n"` or a shift list without N silently switched the night rules off; succession typos were inert | `night_shift` / `day_shift` must be department shifts while any night rule is on (rest, mixed blocks, switches, carry), and must differ; succession entries are pairs of known shift names; a fair shift must have a headcount; duplicate fair shifts rejected |
| CC6: a department shift without a headcount is unbounded | precheck warns on a shift no headcount names |
| CC7, OC A2: solver objective overstated the cost on FEASIBLE solutions, CLI exited 0 on mismatch | `Solution.objective` / `penalty_breakdown` are the validator's cost of the returned roster; `solver_objective` is a diagnostic; `run()` exits 3 if an OPTIMAL objective disagrees |
| CC9, OC A3: negative required hours (`hours_balance: -100`, breastfeeding reduction ≥ daily hours) | `|hours_balance|` < one shift (only a remainder is carried), `breastfeeding_reduction ≤ ramadan_hours_per_day ≤ hours_per_day`, `ytd_overtime ≥ 0` |
| CC10, OC A1, CO1: no size bounds (`days: 10^9` parsed; a 2000-day history built 204 k variables) | `days` ≤ 62, history ≤ 62 days, ≤ 1000 nurses, ≤ 12 shifts; `solve()` requires a positive finite time limit and 1..128 workers |
| CC11, OC A4: TypeError leaked out of `from_dict` | container guards and a TypeError → ValueError wrapper with the field path |
| CC12, CO5: unbounded weights gave MODEL_INVALID with no explanation | weights ≤ 10^6, hours ≤ 24, caps ≤ 10^6; `Solution.message` explains MODEL_INVALID / INFEASIBLE / UNKNOWN |
| CC, OC A7, CO4 (CLI): raw tracebacks, `--time -1`, `--ramadan-days 20-2` silently empty, `gen` wrote invalid JSON | argparse types for `--time` / `--workers`, checked `--month` and `--ramadan-days` parsing, `gen` runs `check()` before writing, every ValueError / OSError prints `error: …` and exits 2 (exit 4 since the 2026-11-02 cloud review, so a hard-violation roster's 2 is unambiguous). `--holidays` is now 1-based like `--ramadan-days` |
| CC, OC A8: `solve(hint)` silently truncated, `write_csv` crashed on a bad matrix, `to_json` took only a path | hints go through `matrix_errors`; `write_csv` raises ValueError on a bad matrix; `to_json` accepts a stream |
| CC: `score_target > score_band_hi` made every shift pay | rejected by `check()` |
| CC: empty history next to colleagues with history got no warning | precheck warns when any nurse has history and this one has less than the rules look back |
| CC, OC: `hijri-converter` deprecated; determinism promise false | dependency is now `hijridate` (same Umm al-Qura data and range); the determinism claim above is corrected |

Not changed, by decision: fairness targets still come from headcount midpoints even when
headcount enforcement is off; a department without a night shift must switch the night rules off
explicitly (rest days 0, mixed blocks off, switch weight 0, carry off) rather than name a
non-existent shift. Soft penalty variables stay one-directional (tying them with equalities
would slow the search); the validator's cost is the number to show.

## Adversarial audit (2026-11-01): nine findings on 04f3c67, core fixes

`ADVERSARIAL_AUDIT_2026-11-01.md`: 4,000 randomised model-vs-validator comparisons agreed; the
findings were in cross-month state, accounting and input handling. Fixed on `audit4-fixes`,
tests in `tests/test_audit4.py`.

| Finding | Fix |
|---|---|
| 1 a history of the recommended depth can still hide an obligation (eight off days hide the N before them when switches are capped; `C C` hides an N owing rest when runs are unbounded) | precheck also reads the tail's content: with a switch rule, a history with no worked day leaves the shift kind before the month unknown; with night rest, a history showing neither N nor D and fewer than `night_rest_days` off days leaves owed rest unknown. Both are warnings, as the fixed-depth one |
| 2 an exported `carry_over` of 8 h could not be imported by a D-only nurse | the incoming bound is the nurse's own shortest allowed shift, the same bound `max_shortfall` uses |
| 3 a negative balance with a month of leave became 11 h of overtime, or INFEASIBLE with the cap at 0 | `required_hours` is clamped at 0; the credit the month cannot absorb is `unused_credit` and comes back as a negative `carry_over` in the CSV |
| 4 `solve(rm, p)` with a `p` edited after `build_model` claimed OPTIMAL for the new rules | `RosterModel.fingerprint` (sha256 of the problem); `solve` raises ValueError on a mismatch |
| 5 overlapping coverage doubled the Friday share (a C counted for D and N) | `friday_expected_m` divides the summed midpoints by the coverage multiplicity, like precheck's demand |
| 6 `shifts: [["D"], "N"]`, `fair_shifts: [{}]`, `score: 10**400` crashed with TypeError / OverflowError | element types are checked before any set is built, large ints are rejected before float conversion, `check()` converts any TypeError / OverflowError / AttributeError into a ValueError, and the CLI catches those too |
| 7 `gen --nurses 10**9` allocated before the bound was checked | `generate` checks its bounds first; `--nurses` / `--days` are bounded argparse types |
| 8 `night_rest_days = max_consecutive_shifts = 1000` iterated a million gaps per nurse (2.3 s for 25 nurses, 1 day) | gap ranges are clamped to the horizon and only built when the rule is on: 2 ms |
| 9 precheck claimed "headcount allows at most 0" for an N-only nurse when N had no headcount | the summed maximum is a cap only when every shift some nurse may work has a headcount |

## Timefold concepts (2026-11-01)

A review of Timefold Solver (archived Python port; Java employee-scheduling quickstart) found
six product concepts worth borrowing. None touches the solving approach; CP-SAT stays. Branch
`timefold-concepts`, tests in `tests/test_rules.py`, `test_replan.py`, `test_progress.py`.

| Concept | What was done |
|---|---|
| One constraint definition per rule (Timefold: `ConstraintProvider`, zero weight disables) | `rules.py` registry: id, level (hard / soft / switched by a department flag), `Weights` field, unit, `enabled(p)`. `active(p, id)` is the single truth table; `build_model` derives its penalty dict and every rule condition from it, `validate.py` is one match function per rule (`CHECKS`), and a test asserts registry = Weights fields = checks = model terms. The drift audits 2–4 kept finding cannot recur silently |
| Score analysis: justifications and indictments | `explain.py`: `Analysis` with per-rule matches (nurse, day, amount, text), per-nurse weighted cost (department-level rules under `""`), `diff` between two analyses; `Solution.analysis`; CLI `--explain` / `--explain-json` |
| `ConstraintVerifier` unit tests (`penalizes_by`) | `tests/rules_helper.py`: `penalises`, `violates`, `only`; every hard rule has an exact violation text on a 2-nurse fixture, every soft rule an exact amount, and each soft rule is solved alone so solver objective = validator amount rule by rule |
| Desired / undesired dates | `Nurse.undesired_days` (2 per day worked), `desired_days` (1 per day off); generator gives 10 % of staff requests |
| `PlanningPin` and nondisruptive replanning | `Nurse.pinned` (hard; checked against allowed shifts and leave; precheck flags contradicting pins and drops pinned-off nurses from the per-day count), `Problem.published` + `Weights.change` (3 per changed unpinned cell), `replan_from(day)` (keeps recorded facts, fills the rest of the past from the plan); CLI `solve --published roster.csv --from-day 12 --explain` prints the diff against the published roster |
| `SolverManager.solve_and_listen` / `terminate_early` | `solve(on_solution=..., stop=Event)`: every improving incumbent arrives validated; the event ends the search within 50 ms, incumbent or not (design review below). CLI `--progress`. The async job / HTTP layer is app work, not solver work |

Not copied: Timefold itself (archived, slower than its Java parent; CP-SAT proves optimality on
the small instances), multi-level scores (a weight does the same here), `load_balance` (our
per-nurse deviation from a target share is the same idea), skills (team leader / gender cover
the ER; generalise when a department needs a certification).

Benchmark after the change (25 nurses, 31 days, 30 s, 8 workers): build 77 ms, 5,169 vars,
10,218 constraints, 300 objective terms; FEASIBLE at cost 840 (bound 355). The default
instance is not solved to optimality in 30 s with the audit-4 fairness terms, before or after
this branch (main: 998 at 30 s); a wall-clock run is not reproducible, so costs vary.

## Adversarial audit (2026-11-01, Codex): twelve findings on f3a6e94, core fixes

`ADVERSARIAL_AUDIT_2026-11-01_CODEX.md` reviewed the Timefold branch. The import boundary
(CSV, JSON) and the new solve lifecycle (callback, cancel) carried most of it. Fixed on
`audit5-fixes`, tests in `tests/test_audit5.py`.

| Finding | Fix |
|---|---|
| F01 the CSV reader located day columns from the current history length, so a file exported with another history shifted every cell by a day | day columns are found by their header (`1Mo`, `2Tu`, …) and must match the problem's day count and weekdays; a mismatch is an error |
| F02 the callback (or another thread) could edit the problem during the search and the result was scored against the edited problem | `solve` deep-copies the problem on entry (21 ms for 1000 nurses); callbacks, extraction and analysis use the snapshot. Pushed back on severity: editing an input mid-solve is misuse, but the guard is cheap |
| F03 cancellation returned the solver's last incumbent, whose validated cost can exceed an earlier one's (slack) | with a callback or stop event every incumbent is validated, only improvements in validated cost are reported, and the best one is returned. Without either, the last incumbent is returned as before |
| F04 a failed `replan_from` had already written some pins | pins are proposed for every nurse first, written together, and restored if the final check fails |
| F05 a shift named `L`, an id starting with `'`, a nurse named `D headcount`, a shift `=1+2` could not round-trip through the CSV | reserved at the input boundary: `L` is not a shift name; ids and shift names may not start with `= + - @ '` or a control character (the writer's formula escape stays); summary rows are recognised by their empty sex column, not by name |
| F06 JSON pin keys `"0"` and `"00"` collapsed to one pin | a key that normalises to an already-seen day is an error |
| F07 a day listed twice counted twice (requests) or multiplied constraints (50,000 copies of one leave day → 50,001 constraints) | every day list must be duplicate-free (leave, requests, holidays, Ramadan) |
| F08 an `also_counts` shift nobody may work lowered the people needed and the Friday share | `fairness.coverage` counts only shifts some nurse may work; precheck uses the same map. Pushed back on the fuller redesign: the midpoint share is a target, not an exact load |
| F09 a nurse row appearing twice in the CSV silently replaced the first | duplicate rows are an error |
| F10 spread mode enumerated headcounts up to the configured maximum (1000) although the staff is smaller | enumeration clamped to `min(max, nurses)`: 51 variables either way |
| F11 `seed=2**31` failed inside OR-Tools with a TypeError | seeds must be signed 32-bit integers |
| F12 eligibility used the larger of both day-type minima even when the month has no such day | the need is the maximum over the days the month actually has |

Not changed (policy, as the audit itself noted): leave proration gives coverers a positive
Friday balance without a matching debt for the absent nurse; D/N fair shares count all worked
shifts, including other shift types; cancellation takes effect at the next incumbent (revisited
in the design review below: it now takes effect within 50 ms).

## Adversarial review (2026-11-01, on e9efda0): four nits

`AUDIT-2026-11-01-e9efda0.md`: no blocking finding. Fixed on `audit6-fixes`, tests in
`tests/test_audit6.py`.

| Finding | Fix |
|---|---|
| 1 the progress callback received the same `Solution` object the solver retains, so a callback edit changed the returned roster unvalidated | the callback gets a deep copy |
| 2 the fingerprint was checked on the caller's problem before the snapshot was taken, leaving a window for an edit to enter the snapshot unchecked | the snapshot is taken first and fingerprinted itself |
| 3 the audit-5 name guard also refused nurse ids starting with `= + - @`, although the writer's escape and the reader's unescape round-trip ids (shift cells are not unescaped, so the shift-name guard stays) | nurse ids are refused only for a leading apostrophe or a newline, the two cases that break the round trip |
| 4 the "no headcount names it" warning read the usable-coverage map, so a governed shift nobody may work was reported unbounded | the warning checks the configured anchor and `also_counts` names |

## Full-repository adversarial audit (2026-11-01, on e49b4e8): seven nits

`AUDIT-2026-11-01-e49b4e8.md`: no blocking finding; 800 model-vs-validator probes agreed.
Fixed on `audit7-fixes`, tests in `tests/test_audit7.py`.

| Finding | Fix |
|---|---|
| 1 with the hours rule off the CSV still exported a `carry_over` the input contract then rejected | `overtime` and `carry_over` are 0 while the hours rule is off |
| 2 a 132 kB nurse id exported fine but the CSV reader's field limit raised an uncaught `csv.Error` | the CLI treats `csv.Error` as an input error; ids and shift names are capped at 100 characters |
| 3 `score_target > score_band_hi` was refused even with the band penalty off | the guard applies only while `score_balance` is on in band mode |
| 4 a request on a leave day was an error, so adding sick leave to a nurse with a request blocked the re-plan | leave supersedes the request: accepted, and the model and validator ignore requests on leave days |
| 5 `--from-day` demanded `--published` even when the JSON carried a published roster | the flag needs a published roster from either source |
| 6 `--from-day 5` on a two-day month was clamped and froze the whole roster | days beyond the month are refused |
| 7 the history automaton reset on a rule-breaking day, losing the trailing block and overstating capacity (130 of 1,280 combinations) | a forbidden worked day saturates the block at K instead of resetting, and drops the double-cycle memory (the model anchors the rest window at the K-th worked day, which the automaton cannot express past K). Over 1,143 history/rule combinations against the validator: 109 overestimates before, 4 after, and no underestimate either way, the direction that would raise a false warning |

## Full-repository adversarial audit (2026-11-01, on dee3132): six nits

`AUDIT-2026-11-01-dee3132.md`: no blocking finding; 1,600 randomised probes and 40 exhaustive
tiny problems agreed with the validator. Fixed on `audit8-fixes`, tests in `tests/test_audit8.py`.

| Finding | Fix |
|---|---|
| N01 zero-weight rules still imposed cross-field guards (target vs band, `night_shift` for a weight-0 rest rule) and `needed_history` assumed a boundary rule | the band-order guard needs both the deficit and the band weight on; the night-shift requirement counts the rest rule only when hard or weighted; `needed_history(dep, general)` is 0 when no active rule crosses the month boundary |
| N02 `carry_over()` computed a balance with the hours rule off (the CSV caller had been patched, the helper not) | the helper returns 0 while the hours rule is off; the CSV uses it directly |
| N03 "cells changed" counted `change` matches, so a weight of 0 or pinned cells reported 0 | the count compares the published matrix with the roster cell by cell |
| N04 precheck ignored pins: two nurses pinned to the one D slot, or every day pinned off with hours owed, gave no explanation | a nurse pinned to a shift is eligible for that shift only; more nurses pinned to a headcount than its maximum is reported; pinned-off days count like leave in the capacity and per-nurse fit |
| N05 exact duplicate JSON keys were collapsed by the decoder before the pin-collision check | `from_json` decodes with a pairs hook that rejects any repeated key |
| N06 a deeply nested JSON file raised an uncaught RecursionError | decoded inside `from_json` as "JSON nested too deeply"; the CLI catches RecursionError too. No pre-decode size cap: the input is the user's own local file |

## Adversarial design review (2026-11-01, Codex, on 1926b52): two findings

A challenge review of the Timefold branch as a whole ("was this the right design"): no
implementation defect, two places where the design rejected or ignored real-world events.
Fixed on `audit9-fixes`, tests in `tests/test_audit9.py`.

| Finding | Fix |
|---|---|
| 1 `replan_from` required every past pin to match the published roster, so a completed D/N swap or a sick cover (both recorded as pins, which the data contract defines as "already worked") raised "the past cannot be changed", and a past leave day the plan had as worked failed the leave-vs-pin check. The only way through was to rewrite the published baseline, which then hid the real change | the published roster is the plan, `Nurse.pinned` and `unavailable` are the facts. `replan_from(day)` keeps every past pin as recorded, fills a past leave day as off, and fills only the remaining past cells from the plan; it returns the number of past cells whose fact differs from the plan and the CLI prints it ("2 recorded cell(s) differ from it"). The plan stays the `change` baseline from `day` on; recorded facts are pinned, so they are never charged as changes. No separate "executed work" field: pins already were that record |
| 2 the stop event was read only inside the solution callback, so a search with no incumbent, or one that stopped improving, ignored cancellation until its time limit (reproduced: 20 s with one worker on the default instance, zero incumbents) | `solve` returns at once, without solving, when the event is already set (status UNKNOWN, "cancelled" message), and otherwise runs a watcher thread that polls the event every `STOP_POLL` = 50 ms and calls `CpSolver.stop_search()` (thread-safe, a no-op before the solver starts and when repeated, so the request is re-issued until the solve returns); the watcher is joined when the solve ends, so no thread outlives the call. The callback still stops the search at an incumbent as before. An UNKNOWN after a cancel says so instead of "within the time limit" |

## Adversarial design review (2026-11-01, Codex, on 6fe46c5): the planning cutoff

A second whole-repository challenge review, after the audit-9 fixes: one high finding. Fixed on
`audit10-fixes`, tests in `tests/test_audit10.py`.

| Finding | Fix |
|---|---|
| `replan_from` froze the past as pins but kept enforcing every hard rule on it, so a real staffing incident (a nurse absent on day 0, nobody covered: headcount 0 of 1) made the whole month INFEASIBLE although the remaining days solve on their own. The only ways out were to falsify the record or to switch rules off globally | `Problem.planning_from` (0-based, set by `replan_from`, JSON field, `check()` requires every earlier cell pinned) is the cutoff. Elapsed month days get the status the previous-month history already had: the model enforces a hard rule only where its consequence lands on a free day (succession: the later day; run limit: the window's end; double cycle: the rest day; night rest: the D day; headcount, team leader, gender, shift restriction: the day), and a month total the past alone already exceeds (overtime cap, hard switch maximum) is capped at the recorded level, so the free days may add nothing but the month stays feasible. Soft rules keep counting elapsed days in model and validator alike, so the costs still agree at OPTIMAL. The validator marks a hard match wholly before the cutoff `Match.elapsed`; `validate()` and `Solution.hard_errors` leave it out, `Analysis.elapsed` lists it, the CLI prints it as "recorded before day N (facts, not errors)". Precheck checks the free days only and skips a pinned succession wholly in the past. An elapsed pin may name a shift the nurse may no longer work; a future pin may not |

Rest obligations crossing the cutoff are tested explicitly: a night on the last elapsed day still
blocks a D on the first free days, a run of K ending at the cutoff still forces the next day off
(also when the past already exceeded K), the double-cycle rest after an elapsed W^K O W^K is
still owed, and a nurse already over the overtime cap or the switch maximum simply gets no
further shift / switch.

A Codex challenge review of that commit (e667e66) found three gaps in it, fixed by Codex
(`gpt-6.1-sol`) on the same branch, tests in `tests/test_audit10_followup.py`:

| Finding | Fix |
|---|---|
| 1 the long-gap night-rest bound (`rest_long`, and the reach of the historical "owed rest" block) assumed the run limit K held on every gap day, but elapsed days may now have broken it: with K=1, two rest days and an elapsed N/C/C/C the model accepted a D after a single off day | both bounds add `cut`: only the free part of a gap is guaranteed R off days after R·(K+1) days |
| 2 the department-overtime excess variable was bounded by the original per-nurse caps while the per-nurse `ot` variables may now carry recorded excess: 60 h recorded against 40 owed with cap 10 and a department cap of 0 was INFEASIBLE because of a soft penalty | the bound is the sum of the expanded caps |
| 3 `replan_from` ran `check()` before setting the cutoff, so an already-recorded elapsed pin outside the nurse's current `allowed_shifts` blocked the re-plan although `planning_from` set by hand accepted it | the checks run on a deep-copied snapshot that carries the requested cutoff (missing past cells filled as off for the structural pass, then the real facts); the caller's problem is written only after both pass |

## Adversarial design review (2026-11-01, Codex, on 157a263): two findings

A whole-repository challenge review after the planning cutoff landed on `main`: two medium
findings, both on the re-planning path. Fixed by Codex (`gpt-6-astra`) on `audit11-fixes`,
tests in `tests/test_audit11.py` (22 cases through the real CLI).

| Finding | Fix |
|---|---|
| 1 with a soft night-rest rule and `no_mixed_blocks`, an elapsed N,N,D made the model charge the D a rest penalty through the long-gap and historical encodings while the validator exempts a D directly after an N (that is a forbidden succession, not rest owed to an earlier N): OPTIMAL at solver cost 7 against a validated cost of 0, and the CLI refused to export the valid roster | every soft-rest encoding (short gaps, long gaps, the historical "owed rest" block) carries the same exemption literal: no rest penalty when the day before the D is an N and N->D is a forbidden succession |
| 2 the CLI validated the JSON in full before `--from-day` reached `replan_from`, so an already-recorded elapsed pin outside the nurse's current `allowed_shifts` exited 2, although `replan_from` itself accepts it | `Problem.from_json` / `from_dict` / `check` take `check_planning`; with `--from-day` the CLI defers only the two cutoff-dependent pin checks (eligibility, elapsed-prefix completeness) to `replan_from`'s prospective validation. Every structural check still runs at load, `--published` without `--from-day` still checks in full, and an invalid future pin is still rejected |

## Adversarial design review (2026-11-01, Codex `gpt-6-astra`, on 0208224): two findings

A deep whole-repository challenge review (3,500 randomised history / cutoff cases agreed between
model and validator): two medium findings. Fixed on `audit12-fixes`, tests in `tests/test_audit12.py`.

| Finding | Fix |
|---|---|
| 1 `build_model` read the caller's mutable problem while constructing constraints and fingerprinted it only at the end, so an edit by another thread during the build (a widened `allowed_shifts`) was certified by the fingerprint: `solve` accepted the stale model and returned OPTIMAL at cost 3 for an input whose optimum is 0, with no hard error | `build_model` deep-copies the problem on entry (as `solve` already did) and builds constraints and fingerprint from that snapshot alone; an input edited during the build now fails `solve`'s fingerprint check |
| 2 an incoming `hours_balance` was bounded by the nurse's *current* shortest shift although it is a remainder of *last* month's shifts: a legitimate 9 h debt from a 12 h D-only month was rejected once the nurse became C-only (8 h), so the next month could not be planned without falsifying the debt or keeping obsolete eligibility | the input bound is eligibility-independent: below the longest shift the hospital defines (`max(shift_hours)`); a newly generated shortfall stays below the nurse's own shortest shift (`max_shortfall`, unchanged) |

## Adversarial review (2026-11-01, Codex, on e04f558): one finding

A challenge review of the audit-12 fixes (3,500 solver / validator probes agreed): one medium
finding. Fixed on `audit13-fixes`, tests in `tests/test_audit13.py`.

| Finding | Fix |
|---|---|
| 1 the incoming `hours_balance` was still bounded by *this* month's shift definitions (`max(shift_hours)`) although it is a remainder of *last* month's: a legitimate 9 h debt exported by an OPTIMAL 12 h month was rejected once the shift was shortened to 8 h, and accepted again only while an unused 12 h shift stayed in the configuration, so shortening or retiring a shift blocked the month-to-month accounting unless the debt was falsified or obsolete configuration kept | the bound is configuration-independent: below the longest shift any configuration can define (`MAX_SHIFT_HOURS` = 24, the ceiling `shift_hours` is checked against), so every exported `carry_over` imports whatever next month's shifts are; a newly generated shortfall stays below the nurse's own shortest shift (`max_shortfall`, unchanged) |

## Adversarial review (2026-11-02, CodeRabbit CLI, on 12d58f0): two findings

A review of the whole diff since ff4bab0 (the prototype): two minor findings. Fixed on
`audit14-fixes`, tests in `tests/test_audit14.py`.

| Finding | Fix |
|---|---|
| 1 with a progress callback or a stop event, `solve` replaced the final roster by an earlier incumbent whenever that incumbent's validated cost was lower, relabelled FEASIBLE. At a proven optimum such an incumbent can only exist when the model and the validator disagree, so the swap turned exactly the mismatch `run()` exits 3 on into a "slack (not proven optimal)" message and exit 0: the drift detector was off whenever `--progress` was on | the swap applies to time-limit (FEASIBLE) results only; an OPTIMAL roster is returned as is and `run()` reports the mismatch with or without `--progress` |
| 2 two cancellation tests (`tests/test_audit9.py`) assumed one worker finds no roster for the default instance within 0.5 s / 1 s; `ortools` has no upper bound, so a faster release could produce an incumbent and fail them although cancellation still works (measured with OR-Tools 9.15: the first single-worker incumbent arrives after 38 s, eight workers find one in 0.7 s) | the stop-latency and thread-count assertions stay unconditional; status and message are asserted per outcome (UNKNOWN with the "cancelled" or time-limit message without an incumbent, FEASIBLE and not cancelled with one), so neither branch is vacuous |

## Deep review (2026-11-02, CodeRabbit CLI `--deep`, on a040802): one finding

The full pull-request review policy over the whole diff since ff4bab0: one minor finding, a
follow-up to the audit-14 fix. Fixed on `audit15-fixes`, test in `tests/test_audit15.py`.

| Finding | Fix |
|---|---|
| 1 `run()` reported a model / validator mismatch only at OPTIMAL (any gap of 0.5 or more). The solver's penalty variables are bounded from below, so its objective can only overstate the roster's validated cost (the one-directional slack `tests/test_rules.py` asserts per rule): a validated cost above the solver objective is a disagreement at any status, yet a time-limited FEASIBLE roster the validator charged more than the solver did printed "solver objective carries N of slack" and exited 0 | the gap is signed: a solver objective at least 0.5 below the validated cost exits 3 at any status, any gap at OPTIMAL still does, and only an overstating solver objective is reported as slack |

## Cloud review (2026-11-02, Claude ultrareview, on 1f2a693): ten findings

A multi-agent cloud review of the whole diff since ff4bab0: three normal findings and seven
nits, all confirmed against the code. Finding 1 is kept by decision; the rest are fixed on
`audit16-fixes`, tests in `tests/test_audit16.py`.

| Finding | Fix |
|---|---|
| 1 (normal) the shift name `L` is reserved for every load path, not only for users of the published CSV, so a ward with a Late or Long-day shift coded `L` cannot be rostered | **kept** (decided 2026-11-02): one unambiguous leave marker in the CSV is worth more than the name; the error now says to rename the shift (e.g. `LT`) |
| 2 (normal) problem.json had no schema version, so a file written by the prototype was silently read with every rule added since switched on (hard night rest, no mixed blocks, the switch penalty, separate weekend score targets) and its `fair_weekend: 3` in a unit that no longer exists | `Problem.version` (`SCHEMA_VERSION`, 2) is written by `to_json` and carried by `asdict`; a file without the key is version 1 and is migrated to the meaning it had: the new rules off, the weekend targets following the weekday ones, the untouched `fair_weekend` becoming the new default; a tuned `fair_weekend` has no equivalent and is a clear error; an unknown version is rejected. *Migration removed 2026-11-03: schema 3 requires every field, and versions 1 and 2 are refused* |
| 3 (normal) `.gitignore` lost the `.streamlit/secrets.toml` entry although the playground lives on in the `streamlit` branch | the entry is back |
| 4 (nit) on a re-plan, precheck counted headcount demand over the free days but staff capacity over the whole month (the fit DP from day 0, the hours window unspent), so the capacity and team-leader / gender warnings went quiet exactly when the remaining days could not be covered | capacity is counted over the free days: the fit DP runs from the cutoff with the elapsed pins appended to the history, and the hours already worked come off the hours window |
| 5 (nit) malformed input exited 2, the code `run()` uses for a roster that breaks hard rules, and the catch-all also turned TypeError / RecursionError into "input errors" | input errors exit 4 (`EXIT_INPUT`); the clause catches only what malformed input raises (ValueError, OSError, csv.Error), so a programming error keeps its traceback |
| 6 (nit) `write_csv` and `Analysis.to_json` treated anything but a `str` as an open stream, so a `pathlib.Path` reached `csv.writer` / `json.dump` and raised, while `Problem.to_json` accepted one | `os.PathLike` goes to the file branch in both |
| 7 (nit) the night-rest clauses list every day of the gap, so the model grows with the square of `night_rest_days`, which was bounded only by `MAX_PARAM` (1000) and the horizon: a file with a huge value and a full history could build hundreds of millions of literals | `night_rest_days ≤ MAX_REST_DAYS` (7): a week of rest after a night is beyond any real rule, and the encoding stays within a few thousand literals per nurse |
| 8 (nit) `friday_expected_m` recomputed `coverage` (O(nurses)) on every call and was called once per nurse by the validator and the model (O(nurses²), on every incumbent under `--progress`); `balances_out` recomputed it and `share_m` and ran twice per CSV row | `friday_slots_m(p)` is the per-problem part, computed once per roster and passed in (`per`); `balances_out` takes `share` / `per` and runs once per row; results are bit-for-bit the same |
| 9 (nit) every incumbent was scored through `explain` → `analyse` → `p.check()`, re-validating the whole contract inside CP-SAT's solution callback although the snapshot was checked when the model was built | `explain` / `analyse` take `checked=True` on the solver's path and skip the contract check |
| 10 (nit) `_workers` duplicated `_bounded_int(1, MAX_WORKERS)` with a differently worded message | `--workers` uses `_bounded_int` |

## Request/result contract (2026-11-03): the ER data leaves the core

Decided with the ward's planner: the solver runs on a server as a pure function of a request a
front end assembles (later, from a database of hospital rules, units, nurses and results); the ER
instance and its 25 nurses were only ever test data. What changed:

| Before | After |
|---|---|
| The ER rules were the dataclass defaults of `GeneralRules`, `DepartmentRules`, `Weights`, `Headcount`; `from_dict` filled omitted fields from them | No rule, switch or weight has a default; a request (and a problem dict) missing one is rejected with the field path. The ER configuration is `tests/er_fixture.py` (`er_general()`, `er_department()`, the real scores, the random generator) |
| `bench` / `gen` built a random instance; `solve problem.json` took 0-based day indices; the time limit was `--time` | `solve request.json [--out result.json] [--csv roster.csv]`: one unit, one month, dates everywhere, the time limit and `reproducible` in the request's `solver` block; workers stay a server setting |
| The output was the CSV, read back by `--published` for re-solves; leave was the pseudo-shift `L` | A JSON result (`result.py`) with the roster as nurse × date, violations with rule / nurse / date, the penalty breakdown and a per-nurse `carry_over` block in the request's own field names; the CSV is an optional export; the request's `published` / `replan_from` replace `--published` / `--from-day` |
| problem.json versions 1 and 2 were migrated by filling defaults | schema 3; older files are refused |
| `reproducible` did not exist (`random_seed` fixed, but a wall-clock limit with 8 workers is not reproducible) | `reproducible: true` = one worker + `max_deterministic_time` (`model.solve(deterministic_time=...)`, `Solution.deterministic_time`) |

`Nurse` keeps its constructor defaults (they carry no policy and ~200 test call sites rely on
them); strictness is enforced at the JSON boundary. `RESERVED_SHIFT` (`L`) stays reserved for the
CSV export. The CLI tests that used 7- and 10-day problems now run over real months (June 2026,
December 2025: Monday starts, no Ramadan) through the request path, so date mapping is exercised
by every one of them. `tests/test_request.py` covers the calendar, the loader's rejection table,
the result (every `carry_over` value against its core function, and the round trip into next
month's request), reproducibility and the CLI end to end.

## Adversarial review (2026-11-04, Codex `gpt-6-astra`, on e57c4da): four findings on the contract

| Finding | Fix |
|---|---|
| 1 (high) `carry_over.previous` kept only the last `needed_history` days, so a nurse whose month ended D, off handed July a history of one off day; with a hard zero-switch cap July then accepted an N (`previous` = D, off makes it INFEASIBLE) | `previous` is this month's row, extended back into the incoming history when the nurse worked no day this month, so the last worked shift is always carried (capped at `MAX_HISTORY`); the switch memory walks the whole history, so any number of trailing off days is fine |
| 2 (high) `build_result` read shift names and hours off the caller's `req.problem`, which an app can edit while the solver runs (reproduced by reversing the shift list in a progress callback: a pinned D exported as N with `ok: true`) | `Solution.problem` is the snapshot the roster was scored against; the result is serialized from it, and a problem that does not match the model's fingerprint is refused |
| 3 (medium) `replan_from` could not express "the whole month has happened" (`planning_from == days`), so a last-day shortage could only be solved as INFEASIBLE, never recorded as a fact | the first day after the month is an accepted cutoff (`MonthInfo.cutoff_index` / `cutoff_iso`); the result's `replan.from` and the CLI print it |
| 4 (medium) `deterministic` was inferred from the elapsed wall time being under the guard, so a wall-clock stop just under it, or a cancellation, was reported as reproducible | `solve` records `stopped_by` (proof / deterministic_budget / time_limit / cancelled / model_invalid; the budget counts as reached at 98 % of it, CP-SAT lands within 0.2 % past it); `deterministic` is true only for a proof or an exhausted budget |

Regression tests: `tests/test_request.py`, section 6.

## Adversarial review (2026-11-04, Codex `gpt-6-astra`, on e4298b0): five findings on the fixes

The second pass challenged the four fixes above and reproduced five defects. The fixes of
findings 1 and 4 above are superseded by the ones below.

| Finding | Fix |
|---|---|
| 1 (high) `carry_over.previous` reached back to the last worked shift but was capped at `MAX_HISTORY`: `previous` = D then 61 off days, plus a month of leave, exported 62 off days, and July accepted an N under a hard zero-switch cap | the switch memory is an explicit nurse scalar, `last_shift` (the last shift worked before `previous` begins, null when none is known), consumed by the model (`validate.switch_memory` seeds `last_n`, also when no nurse has a history), the validator (`count_switches(..., last=)`) and precheck; the result carries it walked up to where next month's `previous` begins, so `previous` is the month and nothing more |
| 2 (high) the night-rest memory is unbounded too when there is no run limit and a third shift: an N followed by a month of C had paid no rest back, but the export kept the 30 C only, so July accepted a D on its first day (the 31-day history refuses it) | the night-rest memory is an explicit nurse scalar, `rest_owed` (off days still owed to the last night before `previous` begins), walked through the history by `validate.rest_owed_after` (a night owes `night_rest_days`, the day shift ends the rule, an off day pays one back, other work nothing) in the model's static obligation, the validator's walk-back and the result's carry-over; the precheck warning "rest still owed is unknown" is gone, the memory is never unknown |
| 3 (high) the problem was snapshotted but the month, the cutoff and the solver settings were read from the mutable request: setting `req.month` to September after solving June relabelled every date under the June fingerprint, and `reproducible` / `replan_from` fabricated `workers: 1`, `deterministic: true` and a cutoff the snapshot never had | `Request`, `MonthInfo` and `SolverSettings` are frozen; `solve` records the limits it ran with on the `Solution` (`time_limit`, `workers`, `seed`, `deterministic_budget`); `build_result` reports workers, reproducible and the time limit from the solution, the cutoff and its recorded differences from the snapshot (`Problem.recorded_differences`), and refuses a request whose month shape, settings or cutoff disagree |
| 4 (medium) a whole month reconciled with 16 of 208 h missing was still INFEASIBLE: the shortfall cap stayed hard with no free day left, and the validator never marked under-hours as a fact | `Problem.max_hours` (pinned shifts plus the longest allowed shift on every free day) bounds what any roster can give: a requirement further above it than `max_shortfall` drops the cap in the model (the shortfall penalty still pulls) and is an elapsed under-hours violation in the validator; the whole debt is carried (`hours_balance` is bounded by `MAX_HOURS` only, no longer by a shift length), precheck says so, the CLI prints such facts even without a cutoff, and a month with a free day keeps the cap and uses the day |
| 5 (medium) `deterministic_budget` was inferred at 98 % of the budget, so a wall-clock stop at 99.5 % of it was reported reproducible | `model.stop_cause` follows CP-SAT's own limits: it stops at or just past the limit it hit, so the budget is the cause only when the deterministic clock is at or past it and the wall clock is still under its limit (`solver.wall_time`); both tripped is ambiguous and counts as the wall clock's |

Regression tests: `tests/test_request.py`, section 7; the memories in precheck and the validator
(`tests/test_audit4.py`), a nurse whose days cannot reach her hours (`tests/test_audit3.py`,
`tests/test_audit8.py`), the balance bound (`tests/test_audit12.py`, `tests/test_audit13.py`).

## Adversarial review (2026-11-04, Codex `gpt-6-astra`, on 4b8a144): five findings on the second pass

The third pass found no new blocker in the stop cause and five adjacent cases in the rest;
the fixes of findings 1, 3 and 4 of the second pass are completed by the ones below.

| Finding | Fix |
|---|---|
| 1 (high) a hand-built `Request` for November 2027 (30 days from a Monday, like June 2026) reported a June solution under November's dates with June's fingerprint: neither the snapshot nor the fingerprint knew the month, only its shape | `Problem.month` ("YYYY-MM", set by the loader, checked against the day count and first weekday, part of `asdict`, hence of the fingerprint): the result's `month` comes from the snapshot and `build_result` refuses a request for any other month; a problem built by hand (tests) has none and cannot be reported at all |
| 2 (high) dropping the whole shortfall cap for an unreachable requirement let the solver leave reachable shifts unworked: 168 h recorded, 208 h owed, two free 12 h days, a change weight of 100 against a shortfall weight of 1 gave an idle roster with 40 h carried as a "fact", 24 of them avoidable | `Problem.unreachable_hours` (requirement − `max_hours`) is exempt from the cap and nothing more: `shortfall ≤ max_shortfall + unreachable`, so the floor is `max_hours − max_shortfall` and both days must be worked; the validator marks an under-hours elapsed only within the exemption and names the unreachable part; precheck's window and note use the same figure |
| 3 (medium) with no nurse carrying a history (P = 0) a known `last_shift` seeded only the day-0 switch clause, so an off day 0 lost the memory and a D on day 1 after an N passed the model but not the validator | with P = 0 the memory is tied to `last_n[0]` while day 0 is off, so it propagates to the first worked day as it does through a history |
| 4 (medium) the adjacent-night exemption of the soft night-rest obligation read the cell before day 0, which for a nurse with no history while another has one is free padding: the solver invented an N there to waive a carried `rest_owed` penalty (solver 0, validator 7, exit 3) | the exemption reads a real day only (the nurse's own history or the month), never the padding before a short history |
| 5 (medium) `last_shift` had to be one of the unit's current shifts, so a C carried through months of leave blocked every request once the unit retired C | `last_shift` is any shift name (`_is_name`, ≤ MAX_NAME); its kind is "night" only when it equals the unit's night shift, so a retired or renamed shift counts as day work, and precheck says so while a switch rule is on |

Regression tests: `tests/test_request.py`, section 8; `tests/test_audit15.py` solves the request's
own problem (the month is part of the fingerprint).

## Adversarial review (2026-11-04, Codex `gpt-6-astra`, fourth pass): four findings on the third

The stop cause, the switch memory through off days and the rest exemption held; four adjacent
cases remained. Two change the contract: under-hours is no longer a hard rule, and the switch
memory is a kind.

| Finding | Fix |
|---|---|
| 1 (high) the hours floor `max_hours − max_shortfall` assumed every free day could be worked at the longest shift: with a run limit of 3 and the recorded prefix ending in three worked days only one of two free days could be, so the floor of 181 h made the re-plan INFEASIBLE (double-cycle rest, successions with `allowed_shifts` and shared headcount maxima reproduce it) | no hard floor: what a nurse can still work is bounded by every other hard rule at once, so no per-nurse bound is safe. `Weights.avoidable_shortfall` (explicit, meant to dominate; ER 1000 per hour) charges every hour short beyond a remainder below one shift and `Problem.unreachable_hours`; the soft rule `avoidable_shortfall` is in the registry, the validator and the result's penalties; `hours_bounds` keeps only the overtime cap. The idle case costs 13 000, the run-limited one 1 000 and a roster; two short nurses split two headcount slots |
| 2 (high) `last_shift` was a name, so renaming N to Night turned a carried N into day work: a pinned D was accepted and a pinned Night refused, the reverse of the record | `last_shift_kind` ("night" / "day" / null) replaces it: a kind, derived by the result from the last worked shift and the unit's night shift, consumed as such by the model (`validate.switch_seed`) and the validator, so a rename cannot change it |
| 3 (medium) `previous` still had to name current shifts, so retiring or renaming a shift rejected the next request outright | any shift name is accepted in a history; one the unit no longer defines is "work of no kind" (worked, neither night nor day: index `S` in the validator, no shift column in the model, precheck says so), and `renamed_shifts` (`{old: current}`, optional) maps a renamed shift in every history |
| 4 (medium) a request loaded with `published` and no cutoff, whose problem the caller then re-planned, was reported with `replan: null`: presence came from the request | `replan` is reported whenever the solved snapshot has a cutoff (or the request asked for one), from the snapshot |

Regression tests: `tests/test_request.py`, section 9; `tests/test_rules.py` (under-hours as the soft
rule), `tests/test_audit3.py` / `tests/test_audit8.py` (no elapsed under-hours, no penalty within the
exemption).

## Adversarial review (2026-11-04, Codex `gpt-6-astra`, fifth pass): three findings on the fourth

The hours change and the kind-based memory held; three narrow cases remained.

| Finding | Fix |
|---|---|
| 1 (high) the CLI wrote the CSV (and the `--explain` diff) from the caller's `req.problem`: an app editing it at solver return got a JSON roster from the snapshot and a CSV of the edited problem (nurse a on D in one, nurse b on N in the other), exit 0 | after `solve` the CLI rebinds its problem to `Solution.problem`, so every later line, the CSV included, reads the snapshot |
| 2 (medium) `renamed_shifts` accepted `{"": "D"}` and turned recorded off days into D, which cleared a hard night-rest obligation | a rename key must be a shift name; an off day is never renamed |
| 3 (medium) the month-label check replaced the shape check, so a hand-built `MonthInfo` claiming 31 days for June reported `replan.from` as 2026-06-31 | both checks run, and the reporting calendar (`MonthInfo`) is rebuilt from the snapshot's month, day count and first weekday |

The review also asked that the soft-hours limitation stay explicit: a weight does not eliminate
avoidable shortfall in every result, so the CLI prints an "avoidable shortfall" line naming the
nurses, with whether the search was proven optimal (for the weighted objective as a whole).
Regression tests: `tests/test_request.py`, section 10.

Found by the suite under load on the same day: with eight workers CP-SAT can deliver a second
incumbent after the callback asked it to stop, so `improvements` ran ahead of what the caller had
seen and the returned roster could be the later one. The callback now ignores deliveries after
the stop, and a search the callback stopped returns the incumbent it stopped at
(`tests/test_progress.py`).

## Adversarial review (2026-11-04, Codex `gpt-6-astra`, sixth pass): two findings on the fifth

| Finding | Fix |
|---|---|
| 1 (medium) the incumbents handed to `on_solution` carried no solver settings (`workers` 0), so a front end building a result from its progress callback got a ValueError on the first incumbent | every incumbent is stamped with the search's limits before the callback sees it, in both modes |
| 2 (medium) the CLI's "avoidable shortfall" line at OPTIMAL claimed the other hard rules left no way to give the nurse more, although weighted optimality proves nothing of the kind: an `undesired_day` weight of 10 000 against `avoidable_shortfall` 1 000 keeps two free days idle at cost 5 000 | the line says the search is optimal for the weighted objective as a whole, that the other rules and preferences cost more at their weights or a hard rule allows no more, and that the solver does not say which; DESIGN says the same |

Regression tests: `tests/test_request.py`, section 11.

## Adversarial review (2026-11-04, Codex `gpt-6-astra`, seventh pass): one finding on the sixth

| Finding | Fix |
|---|---|
| 1 (medium) a search the callback stopped still returned the solver's own roster when the solver had proved OPTIMAL meanwhile (ten nurses, no soft weight: every roster costs 0 and the proof is instant), 183 cells away from the incumbent the caller had seen and stored | the stopped-at incumbent is returned whenever the search did not end OPTIMAL, and at OPTIMAL too when its validated cost is the proven optimum (reported as OPTIMAL, with the proven objective); only a genuine model / validator discrepancy keeps the solver's roster, for `run()` to report. *Completed by the eighth pass below.* |

Thirty-six monthly lifecycle round-trips in the review found no value a stored request and
solution cannot reproduce. Regression test: `tests/test_progress.py`.

## Adversarial review (2026-11-04, Codex `gpt-6-astra`, eighth pass): one finding on the seventh

| Finding | Fix |
|---|---|
| 1 (medium) the equal-cost case was handled, but a *cheaper* optimum another worker proved meanwhile (incumbent 138, proof 0) still replaced the incumbent the callback stopped at, as OPTIMAL with `ok: true` | a callback-stopped search always returns the stopped-at incumbent: OPTIMAL with the proven objective when it attains the proven optimum, else FEASIBLE under the proven bound; its cause is `cancelled` either way (a stop is the caller's timing, never a function of the input, so `deterministic` is false); only an incumbent validated cheaper than the proof, a model / validator discrepancy, keeps the solver's roster |

Regression test: `tests/test_progress.py`.

## Adversarial review (2026-11-04, Codex `gpt-6-astra`, ninth pass): one finding on the eighth

| Finding | Fix |
|---|---|
| 1 (medium) the discrepancy test compared the incumbent with the final roster's *validated* cost, not with the proven optimum, so an injected incumbent validated at 1 against a proof of 3 came back as a clean FEASIBLE roster (`ok: true`) instead of the exit 3 the same disagreement earns without a cancellation | the selection is one function, `model._select`: at OPTIMAL the incumbent is compared with the solver's proven objective (where the slack is squeezed out), and one validated below it is model / validator disagreement carried as `Solution.mismatch`, which `verdict` reports as exit 3 whatever the final roster's own numbers say |

Regression tests: `tests/test_progress.py` (every branch of `_select` with hand-built solutions,
and the result each produces).

## Adversarial review (2026-11-04, Codex `gpt-6-astra`, tenth pass): three findings on the ninth

| Finding | Fix |
|---|---|
| 1 (medium) `_select` checked only the incumbent-below-proof case, so a final roster that itself disagreed (validated 5 against a proven 3) was discarded in favour of a clean stopped-at incumbent, and rewriting the incumbent's solver objective could erase its own under-reporting | disagreement on either candidate is gathered before any selection or rewriting (a solver objective below a validated cost, a gap at OPTIMAL, an incumbent below the proof); any of it returns the final roster with the whole evidence in `mismatch` |
| 2 (medium) `verdict` returned exit 2 before looking at `mismatch`, so a disagreement next to a hard violation was reported as hard violations only | the mismatch takes precedence (exit 3) and names the hard violations too; the CLI prints both the violations and the error |
| 3 (medium) rules whose look-back exceeds `MAX_HISTORY` (`max_consecutive_shifts` 30 with `double_cycle_rest` 7 look back 67 days) were accepted, so the carried history lost a double-cycle obligation and July accepted a D that three days of mandatory rest forbade | `needed_history` lives with the contract (`problem.py`, re-exported by precheck) and `Problem.check` refuses rules that look back further than a history may hold |

Regression tests: `tests/test_progress.py`, `tests/test_request.py` section 12.

## Adversarial review (2026-11-04, Codex `gpt-6-astra`, eleventh pass): one finding on the tenth

| Finding | Fix |
|---|---|
| 1 (medium) the evidence was gathered only when a progress callback had produced an incumbent, and `verdict` still ranked hard errors above a numerical gap, so the default CLI path reported an OPTIMAL roster validated at 5 against a solver objective of 0 next to a pin violation as hard violations only (exit 2) | `_select` gathers the final roster's evidence on every path, and `verdict` ranks a disagreement, from the search or from the numbers, above hard errors (exit 3, naming both) |

Regression tests: `tests/test_progress.py`, `tests/test_request.py` section 12.
