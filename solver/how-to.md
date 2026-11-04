# How to use the nurse roster solver

The solver is a command-line program that turns one **request** (one unit, one month, every
rule spelled out) into one **result** (the roster as nurse × date, the rules it breaks, its cost,
and a per-nurse carry-over block for next month). There is no database and no screen yet: you
write the request as a JSON file, run one command, and read the result JSON (or the optional
CSV). A future app will assemble requests from its database and store results; this guide is
what that app, or you by hand, has to do.

Contents

1. Install and run the sample
2. Build a request
3. Run the solver
4. Read the result
5. Month to month: the carry-over
6. Re-plan a month that has started
7. Close a month: the month-end reconciliation
8. Reproducible runs
9. Renaming or retiring a shift
10. The hours rule, explained
11. Troubleshooting

---

## 1. Install and run the sample

You need Python 3.12 and `uv`.

```bash
uv sync
```

Solve the committed sample (the ER unit, 25 nurses, March 2026) and write the result and a CSV:

```bash
uv run python -m nurse_roster solve tests/fixtures/er_request_2026-03.json --out result.json --csv roster.csv
```

The sample file is also the best template for your own request: copy it and change the
values. Run the test suite with:

```bash
uv run python -m pytest -q
```

---

## 2. Build a request

A request is one JSON file. Everything is explicit: every rule, switch and weight must be
present, and an unknown field is an error, so the solver can never fill in a number you did
not choose. Dates are written `YYYY-MM-DD` and must fall inside the month.

### 2.1 Top level

```json
{
  "version": 1,
  "month": "2026-03",
  "ramadan_days": {"from": "2026-02-18", "to": "2026-03-19"},
  "public_holidays": [],
  "general":    { ...hospital-wide rules, see 2.2... },
  "department": { ...the unit's rules, see 2.3... },
  "nurses":     [ ...one object per nurse, see 2.4... ],
  "solver":     {"time_limit_seconds": 20, "reproducible": false},
  "published":  { ...optional, see section 6... },
  "replan_from": "2026-03-12",
  "renamed_shifts": {"N": "Night"}
}
```

| Field | Required | Meaning |
|---|---|---|
| `version` | yes | Always `1`. |
| `month` | yes | `YYYY-MM`. The solver derives the day count, the first weekday and the Ramadan days from it. |
| `ramadan_days` | no | Absent or `null`: derived from the Umm al-Qura calendar. `[]`: no Ramadan days. A list of dates: exactly those. `{"from", "to"}`: an inclusive range (it may start or end outside the month) intersected with the month, for the dates fixed after the moon sighting. |
| `public_holidays` | yes | Dates (may be empty). No regular hours are owed on them. |
| `general` | yes | Hospital-wide rules, section 2.2. |
| `department` | yes | The unit's rules, section 2.3. |
| `nurses` | yes | The staff, section 2.4. |
| `solver` | yes | `time_limit_seconds` (a positive number) and `reproducible` (true/false, section 8). |
| `published` | no | The roster currently in force, in the shape of a result's `roster`. Needed for a re-plan, section 6. |
| `replan_from` | no | The first date to plan again; earlier days are recorded facts. The first day *after* the month closes the month, section 7. |
| `renamed_shifts` | no | `{"old name": "current name"}`, applied to every nurse's history after a shift was renamed, section 9. |

The worker count (solver threads) is not part of the request: it is a server setting
(`--workers`, section 3).

### 2.2 `general`: hospital-wide rules

```json
"general": {
  "shift_hours": {"D": 12, "N": 12, "A": 8, "B": 8, "C": 8},
  "hours_per_day": 8,
  "ramadan_hours_per_day": 6,
  "breastfeeding_reduction": 1,
  "weekend_weekdays": [4],
  "forbidden_successions": [["D", "C"], ["N", "D"], ["N", "A"], ["N", "B"], ["A", "B"],
                            ["A", "C"], ["B", "D"], ["C", "D"], ["C", "A"], ["C", "B"]],
  "forbidden_successions_enabled": true,
  "hours_rule_enabled": true,
  "overtime_caps_enabled": true,
  "overtime_month_cap": 40,
  "overtime_year_cap": 720,
  "dept_overtime_cap": 400,
  "weights": { ...see below... }
}
```

| Field | Meaning |
|---|---|
| `shift_hours` | Every shift any unit may use, with its length in hours. A unit's `shifts` must all appear here. |
| `hours_per_day` | Regular hours a nurse owes per working day (a day that is not a weekend day or a public holiday). |
| `ramadan_hours_per_day` | The same for a nurse with `ramadan_reduced: true`, on Ramadan days. |
| `breastfeeding_reduction` | Hours taken off each working day for a nurse with `breastfeeding: true`. |
| `weekend_weekdays` | Weekdays that count as the weekend, 0 = Monday … 6 = Sunday. `[4]` is Friday only. |
| `forbidden_successions` | `[today, tomorrow]` pairs that may not follow each other. |
| `forbidden_successions_enabled` | Switch for the list above. |
| `hours_rule_enabled` | Off: any number of shifts, no overtime or shortfall accounting at all. |
| `overtime_caps_enabled` | Off: no per-nurse monthly or yearly overtime cap. |
| `overtime_month_cap` | Hard cap on a nurse's overtime hours this month. |
| `overtime_year_cap` | Hard cap on a nurse's overtime hours in the year (uses her `ytd_overtime`). |
| `dept_overtime_cap` | Soft cap on the unit's total overtime hours this month. |

`weights` are the prices of the soft rules, per unit of violation. A weight of `0` switches that
rule off. Only their ratios matter: the solver minimises the weighted sum.

| Weight | Per … |
|---|---|
| `night_rest` | night shift followed by a day shift with too little rest (only when `night_rest_hard` is false). |
| `dept_overtime` | hour of unit overtime above `dept_overtime_cap`. |
| `nurse_overtime` | hour of a nurse's overtime. |
| `nurse_shortfall` | hour a nurse ends under her requirement (that remainder is carried over). |
| `avoidable_shortfall` | hour a nurse ends short *beyond* a remainder below one shift and the hours her days could not give anyway. Set this far above every other weight (the sample uses 1000) so that no preference ever idles a nurse while a shift of hers is still free. Section 10 explains. |
| `fair_day`, `fair_night` | 0.1 shift a nurse's day (night) count deviates from her proportional share, beyond `fair_tolerance`. |
| `fair_weekend` | 0.1 shift her weekend days deviate from her fair share. |
| `score_deficit` | 0.01 score point × person a shift's average score falls below the target. |
| `score_spread` | 0.01 score point × person above the band ceiling (band mode), or 0.01 between the strongest and weakest shift (spread mode). |
| `excess_weekend` | weekend day worked above `max_weekends`. |
| `shift_switch` | day/night switch above `max_switches` (only when `switches_hard` is false). |
| `undesired_day` | day a nurse asked off but works. |
| `desired_day` | day a nurse asked to work but is off. |
| `change` | cell that differs from the `published` roster in a re-plan. |

### 2.3 `department`: the unit's rules

```json
"department": {
  "name": "ER",
  "shifts": ["D", "N"],
  "headcounts": [
    {"shift": "D", "weekday_min": 7, "weekday_max": 9, "weekend_min": 8, "weekend_max": 9, "also_counts": []},
    {"shift": "N", "weekday_min": 7, "weekday_max": 9, "weekend_min": 8, "weekend_max": 9, "also_counts": []}
  ],
  "headcount_enabled": true,
  "require_team_leader": true,
  "require_both_genders": true,
  "score_target": 0.70,
  "score_target_weekend": 0.80,
  "score_balance": true,
  "score_balance_mode": "band",
  "score_band_hi": 0.78,
  "score_band_hi_weekend": 0.88,
  "night_shift": "N",
  "day_shift": "D",
  "night_rest_days": 2,
  "night_rest_hard": true,
  "fair_shifts": ["D", "N"],
  "fair_tolerance": 0.5,
  "fair_weekends": true,
  "carry_fairness": true,
  "carry_cap": 2.0,
  "max_consecutive_shifts": 3,
  "double_cycle_rest": 2,
  "max_weekends": 3,
  "no_mixed_blocks": true,
  "max_switches": 2,
  "switches_hard": false
}
```

| Field | Meaning |
|---|---|
| `name` | The unit's name. |
| `shifts` | The shifts this unit works, each present in `general.shift_hours`. |
| `headcounts` | One entry per staffed shift: how many nurses it needs on a weekday and on a weekend day (min and max). `also_counts` lists other shifts that count towards it (overlapping shifts). |
| `headcount_enabled` | Off: no headcount rule at all. |
| `require_team_leader` | Hard: every staffed shift needs at least one `team_leader`. |
| `require_both_genders` | Hard: every staffed shift needs at least one `M` and one `F`. |
| `score_target`, `score_target_weekend` | Soft: the average `score` of each staffed shift should reach this (weekday / weekend). |
| `score_balance`, `score_balance_mode`, `score_band_hi`, `score_band_hi_weekend` | Soft: keep shift averages close together. Mode `band` penalises an average above the ceiling (fast); mode `spread` minimises the gap between the strongest and weakest shift (slower). |
| `night_shift`, `day_shift` | Which shifts the night-rest and switch rules talk about. |
| `night_rest_days` | After a night shift, this many off days are owed before the next day shift (0 = rule off). `night_rest_hard` makes it a hard rule; otherwise the `night_rest` weight prices it. |
| `fair_shifts` | Shifts whose counts are spread fairly among the nurses who may work them; `fair_tolerance` is the free deviation in shifts. |
| `fair_weekends` | Spread weekend days worked evenly. |
| `carry_fairness`, `carry_cap` | Let last month's `night_balance` / `friday_balance` shift this month's fair targets, by at most `carry_cap` shifts. |
| `max_consecutive_shifts` | Hard: longest run of worked days (a "cycle"); 0 = no limit. |
| `double_cycle_rest` | Hard: cycle, one day off, cycle ⇒ at least this many days off afterwards. |
| `max_weekends` | Soft: weekend days a nurse may work per month before `excess_weekend` applies. |
| `no_mixed_blocks` | Hard: consecutive worked days are all day shifts or all night shifts. |
| `max_switches`, `switches_hard` | Day/night switches allowed per month (the month boundary counts); hard, or priced by `shift_switch`. |

The rules must not look back further than a carried history can hold: with
`max_consecutive_shifts`, `double_cycle_rest` and `night_rest_days` combined, the look-back must
stay within 62 days (a run limit of 27 with a double-cycle rest of 7 is the extreme). The
request is refused with a clear message otherwise.

### 2.4 `nurses`

```json
{
  "id": "N01", "gender": "M", "team_leader": true, "score": 0.99,
  "ramadan_reduced": false, "breastfeeding": false,
  "ytd_overtime": 100, "hours_balance": 0, "night_balance": 0.0, "friday_balance": 0.0,
  "last_shift_kind": null, "rest_owed": 0,
  "leave": ["2026-03-04"], "undesired_days": [], "desired_days": [],
  "pinned": {"2026-03-01": "D"}, "allowed_shifts": null,
  "previous": ["D", "D", "", "N", "N", "N", "", "", "D", "D"]
}
```

The twelve scalars are required; the six lists may be left out (absent = none).

| Field | Meaning |
|---|---|
| `id` | Unique name. |
| `gender` | `"M"` or `"F"`. |
| `team_leader` | Counts for `require_team_leader`. |
| `score` | Performance score, 0 to 1. |
| `ramadan_reduced` | Owes `ramadan_hours_per_day` on Ramadan days. |
| `breastfeeding` | Owes `breastfeeding_reduction` fewer hours per working day. |
| `ytd_overtime` | Overtime hours already worked this year (for `overtime_year_cap`). |
| `hours_balance` | Hours still owed from earlier months (+) or worked ahead (−). Comes from last month's carry-over. |
| `night_balance`, `friday_balance` | Nights / weekend days above (+) or below (−) her fair share so far this year, in shifts. From the carry-over. |
| `last_shift_kind` | `"night"`, `"day"` (any other work) or `null`: the kind of the last shift she worked *before* `previous` begins. The switch rule's memory across any number of off days. From the carry-over; `null` for a new nurse. |
| `rest_owed` | Off days she still owes to her last night shift *before* `previous` begins; `0` when none. From the carry-over. |
| `leave` | Dates she is off (sick, educational, marriage, bereavement…). They are credited as worked at her regular daily rate, so leave never creates a debt. |
| `undesired_days`, `desired_days` | Requests: dates she would rather not work / would like to work (soft). |
| `pinned` | `{date: shift}` cells fixed by the admin, or already worked (`""` = pinned off). Hard. |
| `allowed_shifts` | `null` = any of the unit's shifts, or a list of the only shifts she works. |
| `previous` | Her last days before the month, oldest first, shift name or `""` for off. From the carry-over (last month's whole row). A name the unit no longer defines is accepted as work of no kind, see section 9. |

For a **brand-new unit** or nurse: `previous: []`, `last_shift_kind: null`, `rest_owed: 0`,
`hours_balance: 0`, the balances `0.0`, `ytd_overtime` as of today.

### 2.5 A complete minimal request

Four nurses, two 12-hour shifts, one nurse on days and one or two on nights, June 2026, most
soft rules off. Save it as `small.json` and solve it.

```json
{
  "version": 1, "month": "2026-06", "ramadan_days": [], "public_holidays": [],
  "general": {
    "shift_hours": {"D": 12, "N": 12}, "hours_per_day": 8, "ramadan_hours_per_day": 6,
    "breastfeeding_reduction": 1, "weekend_weekdays": [4],
    "forbidden_successions": [["N", "D"]], "forbidden_successions_enabled": true,
    "hours_rule_enabled": true, "overtime_caps_enabled": true,
    "overtime_month_cap": 40, "overtime_year_cap": 720, "dept_overtime_cap": 400,
    "weights": {"night_rest": 0, "dept_overtime": 1, "nurse_overtime": 1, "nurse_shortfall": 1,
                "avoidable_shortfall": 1000, "fair_day": 1, "fair_night": 1, "fair_weekend": 1,
                "score_deficit": 0, "score_spread": 0, "excess_weekend": 0, "shift_switch": 8,
                "undesired_day": 2, "desired_day": 1, "change": 3}
  },
  "department": {
    "name": "Ward A", "shifts": ["D", "N"],
    "headcounts": [{"shift": "D", "weekday_min": 1, "weekday_max": 1, "weekend_min": 1, "weekend_max": 1, "also_counts": []},
                   {"shift": "N", "weekday_min": 1, "weekday_max": 2, "weekend_min": 1, "weekend_max": 2, "also_counts": []}],
    "headcount_enabled": true, "require_team_leader": false, "require_both_genders": false,
    "score_target": 0.0, "score_target_weekend": 0.0, "score_balance": false, "score_balance_mode": "band",
    "score_band_hi": 1.0, "score_band_hi_weekend": 1.0,
    "night_shift": "N", "day_shift": "D", "night_rest_days": 2, "night_rest_hard": true,
    "fair_shifts": ["D", "N"], "fair_tolerance": 0.5, "fair_weekends": true,
    "carry_fairness": true, "carry_cap": 2.0,
    "max_consecutive_shifts": 4, "double_cycle_rest": 2, "max_weekends": 3,
    "no_mixed_blocks": true, "max_switches": 2, "switches_hard": false
  },
  "nurses": [
    {"id": "Amal", "gender": "F", "team_leader": true, "score": 0.9, "ramadan_reduced": false, "breastfeeding": false,
     "ytd_overtime": 0, "hours_balance": 0, "night_balance": 0.0, "friday_balance": 0.0, "last_shift_kind": null, "rest_owed": 0},
    {"id": "Badr", "gender": "M", "team_leader": false, "score": 0.8, "ramadan_reduced": false, "breastfeeding": false,
     "ytd_overtime": 0, "hours_balance": 0, "night_balance": 0.0, "friday_balance": 0.0, "last_shift_kind": null, "rest_owed": 0,
     "leave": ["2026-06-10", "2026-06-11"]},
    {"id": "Dana", "gender": "F", "team_leader": false, "score": 0.7, "ramadan_reduced": false, "breastfeeding": true,
     "ytd_overtime": 0, "hours_balance": 0, "night_balance": 0.0, "friday_balance": 0.0, "last_shift_kind": null, "rest_owed": 0,
     "undesired_days": ["2026-06-05"]},
    {"id": "Emad", "gender": "M", "team_leader": true, "score": 0.6, "ramadan_reduced": false, "breastfeeding": false,
     "ytd_overtime": 0, "hours_balance": 0, "night_balance": 0.0, "friday_balance": 0.0, "last_shift_kind": null, "rest_owed": 0,
     "allowed_shifts": ["D"]}
  ],
  "solver": {"time_limit_seconds": 10, "reproducible": false}
}
```

```bash
uv run python -m nurse_roster solve small.json --out small_result.json --csv small.csv
```

---

## 3. Run the solver

```bash
uv run python -m nurse_roster solve REQUEST.json [--out RESULT.json] [--csv ROSTER.csv] [--workers N] [--explain] [--explain-json PATH] [--progress] [--log]
```

| Option | Effect |
|---|---|
| `--out RESULT.json` | Write the result (section 4). Written whenever a solve ran, even without a roster; never for a malformed request. |
| `--csv ROSTER.csv` | Also export the roster as a spreadsheet: one row per nurse with her history, the month's cells (`L` marks leave), hours, balances and shift counts, then headcount, team-leader and score rows per shift. Only when there is a roster. |
| `--workers N` | Solver threads, 1 to 128. Default: the `NURSE_ROSTER_WORKERS` environment variable, else 8. A reproducible request always uses one. |
| `--explain` | Print each soft rule's largest violations and the cost per nurse; in a re-plan, also the comparison with the published roster. |
| `--explain-json PATH` | Write that full analysis as JSON. |
| `--progress` | Print each improving roster's cost while the search runs. |
| `--log` | CP-SAT's own search log (noisy; for debugging). |

What the console shows, in order: `precheck:` lines (plain-language reasons the month may be
infeasible or a rule may be meaningless; warnings, not errors), the re-planning line when there
is a cutoff, `build` and `solve` timings with the status, `cost=` with the solver's objective and
bound, `penalties:` per soft rule, recorded facts (section 6), an `avoidable shortfall:` line when
some nurse still ends a shift or more short (section 10), the validator's line, and the files
written.

Exit codes:

| Code | Meaning |
|---|---|
| 0 | A roster that satisfies every hard rule. `ok: true` in the result. |
| 1 | No roster found (INFEASIBLE, or nothing within the time limit). Read the `precheck` lines and the result's `message`. |
| 2 | The roster breaks hard rules (should not happen; the result lists them under `violations`). |
| 3 | The model and the independent validator disagree on the roster's cost (a bug; the result's `message` says what disagreed). |
| 4 | Malformed request or arguments. The message starts with `error: request:` and names the field, e.g. `error: request: general.weights: missing field(s) ['change']`. |

Choose the time limit by the size of the unit: 25 nurses and all ER rules give a rough roster in
20 seconds and a good one in about two minutes; the four-nurse sample is proven optimal in well
under a second. A FEASIBLE status means the time limit stopped the search; OPTIMAL means it was
proven best for the weighted objective.

---

## 4. Read the result

```json
{
  "version": 1, "month": "2026-06", "ok": true, "status": "OPTIMAL", "message": "",
  "fingerprint": "…", "precheck": [],
  "roster": {"Amal": {"2026-06-01": "D", "2026-06-02": "", "…": "…"}, "Badr": {"…": "…"}},
  "violations": [], "elapsed_violations": [],
  "cost": 23, "penalties": {"night_rest": 0, "shift_switch": 8, "…": 0}, "department_cost": 0,
  "solver": {"objective": 23.0, "best_bound": 23.0, "solve_seconds": 0.4, "build_seconds": 0.01,
             "deterministic_time": 0.2, "improvements": 3, "workers": 8, "reproducible": false,
             "time_limit_seconds": 10, "stopped_by": "proof", "deterministic": false,
             "model": {"variables": 480, "constraints": 900, "objective_terms": 60}},
  "replan": null,
  "nurses": {
    "Amal": {"leave": [], "contract": 208, "leave_credit": 0, "required": 208,
             "hours_worked": 204, "overtime": 0, "shortfall": 4, "shifts": {"D": 9, "N": 8}, "cost": 8,
             "carry_over": {"hours_balance": 4, "night_balance": 0.5, "friday_balance": 0.0,
                            "ytd_overtime": 0, "previous": ["D", "", "N", "…"],
                            "last_shift_kind": null, "rest_owed": 0}}
  }
}
```

| Field | Meaning |
|---|---|
| `ok` | True exactly when the command exits 0. |
| `status`, `message` | CP-SAT's status (OPTIMAL, FEASIBLE, INFEASIBLE, UNKNOWN, MODEL_INVALID) and, when there is no usable roster, why. |
| `fingerprint` | Identifies the exact problem the roster was scored against (month included). Opaque; comparable only within one version of the code. |
| `precheck` | The same warnings the console printed. |
| `roster` | Nurse → date → shift name, `""` for off *or on leave* (leave dates are listed per nurse under `nurses[id].leave`). `"L"` never appears in JSON. This block has exactly the shape `published` takes in a re-plan. |
| `violations` | Hard rules the roster breaks: `rule`, `nurse` (null for a unit-level rule), `date` (null for a monthly total), `text`. Empty when `ok`. |
| `elapsed_violations` | Hard rules broken by recorded facts the solver could not change (days before the cutoff). Reported, not errors. |
| `cost`, `penalties`, `department_cost` | The validated cost, its split per soft rule, and the share charged to the unit as a whole (headcount scores, unit overtime). |
| `solver.stopped_by` | What ended the search: `proof` (OPTIMAL or INFEASIBLE), `deterministic_budget`, `time_limit`, `cancelled`, `model_invalid`. |
| `solver.deterministic` | True only under `reproducible` and when a proof or the deterministic budget ended the search (section 8). |
| `replan` | `{"from": date, "recorded_cells_differ": n}` when the month was re-planned, else null. |
| `nurses[id]` | Her hours accounting for the month (`contract` owed, `leave_credit`, `required` = contract − credit + incoming balance, `hours_worked`, `overtime`, `shortfall`), her shift counts, her share of the cost, and the `carry_over` block for next month. |

With no roster at all, `roster`, `nurses` and `cost` are null and `ok` is false.

---

## 5. Month to month: the carry-over

Next month's request is this month's **static nurse fields plus the `carry_over` block**, with
fresh day lists. For each nurse:

1. keep `id`, `gender`, `team_leader`, `score`, `ramadan_reduced`, `breastfeeding`, `allowed_shifts`;
2. copy every key of `carry_over` as it is: `hours_balance`, `night_balance`, `friday_balance`,
   `ytd_overtime`, `previous`, `last_shift_kind`, `rest_owed`;
3. enter next month's `leave`, `undesired_days`, `desired_days` and `pinned` (dates of the new month).

Then set `month` to the new month and `ramadan_days` / `public_holidays` for it. Rules and
weights carry over unchanged unless the unit changes them.

What the carried values mean:

* `hours_balance`: the remainder she still owes (+) or worked ahead (−). Normally below one
  shift; after a month whose recorded days could not reach her requirement it is the whole debt.
* `night_balance`, `friday_balance`: her running fairness position; `carry_fairness` lets them
  adjust next month's targets.
* `ytd_overtime`: input plus this month's overtime.
* `previous`: this month's whole row, so next month's rules see the month boundary.
* `last_shift_kind`, `rest_owed`: the two memories that reach further back than a month (the
  kind of the last shift ever worked, the night rest still owed), already walked up to where
  `previous` begins. They are what keep a nurse returning from a long leave honest with the
  switch and night-rest rules.

**At the start of a year** the app (or you) resets `ytd_overtime` to 0 and the two balances to
0.0; the solver never does that itself.

---

## 6. Re-plan a month that has started

When something changes mid-month (sick leave, a swap, a shortage), re-plan from a date:

1. put the roster currently in force under `published` (a previous result's `roster` pastes
   straight in);
2. set `replan_from` to the first date to plan again;
3. record what really happened before that date where it differs from the plan: a nurse who
   fell sick gets the dates in `leave`; a completed swap or a cover is a `pinned` cell;
4. keep a `change` weight above zero so the new roster stays close to the published one.

Days before the cutoff become recorded facts (every cell pinned, from your pins and leave, the
rest from the published roster). A hard rule those facts broke (an uncovered shift on the day a
nurse fell sick, a run that got too long) is reported under `elapsed_violations` and on the
console as `recorded before DATE (facts, not errors)`, never enforced; obligations that reach
into the free days (rest after a night, the run limit, the hours) still are. The console's
re-planning line says how many days were pinned and how many recorded cells differ from the
plan; the result repeats that under `replan`. The `--explain` option then also shows the cost
and the number of cells changed against the published roster.

A pinned cell before the cutoff may name a shift the nurse may no longer work (a fact is a
fact); a pinned cell from the cutoff on may not.

---

## 7. Close a month: the month-end reconciliation

Once the month is over, solve it one last time with `replan_from` set to the **first day after
the month** (`"2026-07-01"` for June) and the final roster under `published`, with every
late change recorded as pins and leave. Every day is then a fact: the solver validates the
record, reports what it broke as facts, and computes the carry-over from what really happened.
That result's `carry_over` is what next month's request should be built from.

A nurse whose recorded days leave her short by a shift or more is not an infeasibility: the
hours she could not have worked are reported, and the whole debt goes into her `hours_balance`
(section 10).

---

## 8. Reproducible runs

`"reproducible": true` makes the roster a function of the request alone: one worker, a fixed
seed, and a budget of `time_limit_seconds` units on CP-SAT's own *deterministic* clock instead of
the wall clock. The same request then gives the same roster on any machine. The price is speed:
the deterministic clock runs several times slower than the wall clock with one worker, and
single-worker search on the full ER instance needs about 40 seconds for its first roster. The
wall clock still stops a runaway search at ten times the budget; the result says what
happened: `stopped_by` is `deterministic_budget` or `proof` and `deterministic` is true when
the run is reproducible, `time_limit` or `cancelled` with `deterministic` false when it is not.

With `reproducible: false`, `time_limit_seconds` is the wall-clock limit and `--workers`
threads search in parallel; two runs of the same request may differ.

---

## 9. Renaming or retiring a shift

Histories (`previous`) name shifts, and a nurse's history can be older than the unit's shift
list.

* **Renamed shift** (`N` becomes `Night`): add `"renamed_shifts": {"N": "Night"}` to the request
  for as long as any history still names `N`. The mapping is applied to every nurse's
  `previous`; an off day is never renamed. `last_shift_kind` needs nothing: it is a kind, not a
  name.
* **Retired shift** (`C` is gone): a history that still names `C` loads. Those days count as
  worked (for run limits) but as neither the night nor the day shift (no rest owed to them, no
  switch counted from them), and `precheck` says so. Pins, leave and `published` cells must name
  current shifts; only histories may name old ones.

---

## 10. The hours rule, explained

For each nurse the solver computes:

* `contract` = `hours_per_day` for every working day of the month (fewer on Ramadan days for a
  `ramadan_reduced` nurse, minus `breastfeeding_reduction` per working day for a breastfeeding
  nurse; nothing on weekend days and public holidays);
* `leave_credit` = the same rate for every leave day, so leave is paid, not owed;
* `required` = `contract` − `leave_credit` + incoming `hours_balance`, never below zero (an
  advance credit the month cannot absorb is carried on, not turned into overtime).

Hours worked in shifts above `required` are **overtime**: priced per hour, capped per month and
per year (hard), and the unit's total is priced above `dept_overtime_cap`. Hours below
`required` are the **shortfall**: priced per hour (`nurse_shortfall`) and carried over as
`hours_balance`.

A shortfall beyond a remainder below one shift is **avoidable shortfall**, priced per hour by
`avoidable_shortfall`. It is a soft rule with a weight meant to dominate, not a hard one, for a
reason: what a nurse can still work is bounded by every other hard rule at once (run limits,
rest, headcount maxima shared with her colleagues), so no hard floor could be computed per nurse
without making some re-plans infeasible. Hours her recorded and free days could not give
anyway (a month that has ended, a nurse on leave for the rest of it) are exempt from the
penalty and simply become her debt.

Two consequences to keep in mind:

* a search stopped by its time limit may still leave avoidable shortfall; the console's
  `avoidable shortfall:` line names the nurses, the result shows it under `penalties` and per
  nurse under `shortfall`, and a longer time limit usually removes it;
* with `avoidable_shortfall` set too low against another weight (an `undesired_day` worth more
  than a whole shift's worth of shortfall), the solver will honour the preference and leave
  the nurse short. Keep it the largest weight by a wide margin.

---

## 11. Troubleshooting

| You see | What it means | What to do |
|---|---|---|
| `error: request: … missing field(s) [...]` (exit 4) | A rule, weight or nurse scalar is absent. | Add it; every field is required on purpose. |
| `error: request: … is outside 2026-06` | A date outside the month. | Fix the date; only `replan_from` may be the day after the month. |
| `error: request: … is not a department shift` | A pin, leave or published cell names a shift the unit does not have. | Use a current shift name; old names are allowed in `previous` only. |
| `error: request: the pattern rules look back N days … more than a history may hold (62)` | `max_consecutive_shifts`, `double_cycle_rest` and `night_rest_days` combine into a look-back a carried history could not preserve. | Lower them. |
| exit 1, `no roster satisfies the hard rules` | The hard rules cannot all be met. | Read the `precheck:` lines: they name the capacity, headcount, eligibility and history problems in plain words. Typical causes: too few eligible nurses for a headcount, a run limit that cannot fit the owed shifts, pins that contradict each other. |
| exit 1, `no roster found within the time limit` | The search ran out of time before any roster. | Raise `time_limit_seconds` or `--workers`, or simplify (soft rules with large weights slow convergence). |
| `avoidable shortfall: … not proven optimal` | A nurse still ends a shift or more short although her days were free. | Give the search more time; check `avoidable_shortfall` is the largest weight. |
| `recorded before … (facts, not errors)` | Recorded days broke a hard rule. | Nothing to fix in the solver; it is the record. |
| exit 2 or 3 | A hard violation in the returned roster, or model and validator disagree. | This is a solver bug: keep the request file and report it. |
| A result for a nurse back from months of leave ignores her last shift | `last_shift_kind` or `rest_owed` was not carried from the previous result. | Always copy the whole `carry_over` block. |
