# Ticket 48: the cloud session's hand-over

Branch `claude/ticket-48-full-runs-app-b6c39c`, draft pull request Nurse-Fold/cp-sat-nurse-roster-app#11. The code was written
on the user's Mac with single test files only. This file tells the cloud session what to run. Write your results into
**Results** at the end and into the ticket's comment
(`.scratch/nurse-rostering-v2/issues/48-full-runs-the-unit-rule-the-weight-and-the-explanation.md`, under `## Comments`, in the
shape of appendix B of `docs/guides/local-development.md`; the Mac session finishes it). Fix what fails, commit to this branch
and push. Merge only: never rebase or force-push.

## What changed, in short

- **Solver** (`solver/`): a full run reaching the month's last day is now priced in that month. In `nurse_roster/model.py`
  the "off on t + 1" literal is left out at the last day; `validate.count_full_runs` counts the run. The tests are in
  `tests/test_full_runs.py`. The service sample `service_tests/fixtures/four_nurses.json` now carries
  `department.max_full_runs: 3` and `general.weights.excess_full_run: 4`; the contract test uses it as is (its `capped`
  fixture is gone). The backend and `e2e/seed.py` load that file as a unit's rules, so the app's new required field must
  be in it.
- **Backend:** `UnitRules.max_full_runs` (0..31, required), `Weights.excess_full_run`, with defaults 3 and 4. The data
  migrations are `units/0004_max_full_runs` and `hospital/0004_excess_full_run_weight`. There are new tests in
  `units/tests/test_rules_api.py`, `units/tests/test_unit_rules.py`, `hospital/tests/test_rules.py`,
  `solves/tests/test_input.py` (`TestFullRuns`), `rosters/tests/test_replan.py` and `closes/tests/test_close.py`.
- **Frontend:** the field on Unit rules beside the longest run, the weight in `src/lib/weights.ts`, and tests in
  `src/app.test.tsx`.
- **Playwright files changed: none.** `e2e/tests/journey/journey.spec.ts` sets the longest run to 4 on a new unit, which now
  starts with a cap of 3 at a weight of 4. That is priced, never refused, so the journey's solve should still succeed. Watch
  it in `e2e/ci.sh`.

## 1. The full suites

Run them from the repository root.

```bash
uv sync --locked --all-packages --python 3.14
```

**Solver**, its whole suite with the service tests:

```bash
cd solver && uv run --no-sync pytest -q
```

**Backend**, on a throwaway PostgreSQL 18:

```bash
docker run -d --rm --name t48-pg -p 127.0.0.1:55448:5432 -e POSTGRES_USER=nurse_roster -e POSTGRES_DB=nurse_roster -e POSTGRES_PASSWORD=t48only postgres:18
```

```bash
cd backend && POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=55448 POSTGRES_PASSWORD=t48only uv run --no-sync pytest -q
```

```bash
cd backend && SECRET_KEY=x POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=55448 POSTGRES_PASSWORD=t48only SOLVER_TOKEN=x uv run --no-sync python manage.py makemigrations --check --dry-run
```

The OpenAPI document must match the export, with no diff afterwards:

```bash
cd backend && SECRET_KEY=x POSTGRES_PASSWORD=x SOLVER_TOKEN=x uv run --no-sync python manage.py export_openapi_schema --api config.api.api --indent 2 --output ../frontend/openapi.json && cd ../frontend && npm run generate:api && git diff --exit-code -- openapi.json src/api/generated
```

**Frontend**: one run, the build, then six runs at once as CI runs them:

```bash
cd frontend && npm ci --no-audit --no-fund && npm test && npm run build
```

```bash
cd frontend && pids=(); for i in 1 2 3 4 5 6; do npm test -- --maxWorkers=1 > "run-$i.log" 2>&1 & pids+=($!); done; for p in "${pids[@]}"; do wait $p || echo "a run failed"; done
```

**Browser checks and operations**: everything the browser-checks workflow runs. It uses fixed ports 18180–18183 and
18543–18545.

```bash
e2e/ci.sh
```

## 2. A scratch stack seeded like ER's December

The dev stack's ER (25 nurses, longest run 3) is the solver's ER sample, `solver/tests/fixtures/er_request_2026-03.json`.
Bring up a seeded scratch stack, then add that unit to it as `ER25` for December 2026. The measurement script below does
the adding and leaves the unit in place. "Like ER's December" means the sample's nurses (attributes, opening values) and
rules. The sample's leave is not carried, since its dates are in March, so December has no leave and no history. Its manager is `er25mgr`, created with a random password; set one for the drive
through the System Admin's Users page.

```bash
E2E_PORT=18280 E2E_HTTPS_PORT=18643 e2e/stack.sh up nr48
```

The stack's admin password is in `e2e/.stack/nr48.json` (`password`), and its compose command line is `stack.sh`'s
`compose()`:

```bash
COMPOSE_PROJECT_NAME=nr48 COMPOSE_FILE=deploy/compose.yaml:e2e/compose.e2e.yaml COMPOSE_ENV_FILES=e2e/.stack/nr48.env docker compose ps
```

When everything is done:

```bash
e2e/stack.sh down nr48
```

## 3. The weight measurement (the user's ask at ticket 47's review)

The script is `.scratch/nurse-rostering-v2/issues/48-measure.py`. It sets the cap at 3 on `ER25` and the hospital rules to
the reviewed defaults. For each weight it solves December `RUNS` times in the web container, at the unit's solve time
(60 s) with as many workers as the solver service would use. Each solve's input is built by `solves.input.assemble`, as a
real solve's is. For each solve it prints a `MEASURE` line with:
- the status and the month's cost;
- the full-run penalty;
- the nurses above the cap, with their counts, counted from the grid as text;
- the most full runs any nurse has.

At the end it puts the hospital rules back.

```bash
C="docker compose"; export COMPOSE_PROJECT_NAME=nr48 COMPOSE_FILE=deploy/compose.yaml:e2e/compose.e2e.yaml COMPOSE_ENV_FILES=e2e/.stack/nr48.env
$C cp solver/tests/fixtures/er_request_2026-03.json web:/tmp/er_request.json
$C exec -T -e WEIGHTS=4,20,50,200 -e RUNS=3 web python manage.py shell < .scratch/nurse-rostering-v2/issues/48-measure.py | grep '^MEASURE'
```

That is 12 solves of about a minute each. Put every `MEASURE` line under **Results**, and say:
- the machine's CPU count;
- for each weight, how many solves held every nurse at 3 or fewer;
- how the month's cost moved.

The Mac session sets the default from these numbers.

**Where the default weight lives** (all at 4 now; the Mac session moves them together):
- `backend/hospital/rules.py`, `DEFAULT_RULES["weights"]["excess_full_run"]`;
- the migration `backend/hospital/migrations/0004_excess_full_run_weight.py`, which writes the literal;
- `backend/hospital/tests/test_rules.py`: `test_the_defaults_are_the_reviewed_set_the_solver_was_shaped_on`,
  `test_a_full_run_above_the_most_costs_4_by_default`, the migration test and the audit test's `before`;
- `frontend/src/app.test.tsx`: `RULES.weights.excess_full_run` and the weights test's `toHaveValue(4)`;
- `docs/ARCHITECTURE.md` section 9, and the spec's and the ticket's text.

The service sample (`four_nurses.json`, `solver/how-to.md` 2.5) keeps 4 either way: it is the solver's sample, not the app's
default.

## 4. The scratch-stack drive of the criteria

Open the stack at `http://localhost:18280`. The seeded users are in `e2e/seed.py`: Mona manages the four-nurse ER, Carla is
the CNO and Hala the Deputy CNO; the password is the stack's own. Check each of these:

1. **Unit rules, as Mona (ER).**
   - "Most full runs in a month" shows 3, right after "Longest run of shifts", with the ticket's help text.
   - Set the longest run to 1, then 0: the field goes. Set it back to 4: the field returns with its value.
   - 32 is refused beside the field.
   - Save 2: the audit log (as `admin`) shows `unit_rules.changed` with `max_full_runs` 3 → 2.
2. **As Carla and as Hala, Unit rules:** the cap shows read-only. As Mona, it is editable.
3. **Weights, as Carla.** "Full run above the most" shows 4 with its description. Save 0, then the default again: the audit
   log shows `weights.excess_full_run` both times.
4. **The real thing, as `er25mgr`, on `ER25`, December 2026.** Start a solve from the Roster page at the default 60 s.
   - No nurse should have more than three full runs where the month allows it; count a few rows by eye, or use the
     measurement's counts.
   - Where the month does not allow it, "Penalties per rule" beside the draft shows "Full run above the most" with lines
     like "ER25 N13: er25-N13: 4 full runs of 3 shifts, max 3" (the solver's id is the username).
   - Start a re-plan if the month allows one (it may need approving first; skip it if that is too much) and check that its
     input carries `max_full_runs`.
5. **Nothing for nurses:** as a staff nurse of ER, My month and My roster show nothing about full runs.

Take screenshots of 1, 3 and 4 if you can, and say what was seen in **Results**.

## Results

(The cloud session writes here.)
