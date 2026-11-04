# nurse-roster

CP-SAT (Google OR-Tools) solver for monthly nurse rosters with hospital-wide and per-unit
rules. See how-to.md for using it (requests, results, carry-over, re-plans) and DESIGN.md for
the rules, encodings, benchmark results and the data contract.

    uv sync
    uv run python -m nurse_roster solve tests/fixtures/er_request_2026-03.json --out result.json --csv roster.csv
    uv run python -m pytest -q                                # regression tests (audit findings)

The solver is a pure function of one **request** (`nurse_roster/request.py`): one unit, one
month, every rule and weight explicit, dates not indices, the time limit and a `reproducible`
flag in its `solver` block. It writes one **result** (`nurse_roster/result.py`): the roster as
nurse × date, violations, penalties, and a per-nurse `carry_over` block in the request's own
field names, so next month's request is this month's nurse records plus that block. The CSV
is an optional export. The worker count is a server setting: `--workers N` or the
`NURSE_ROSTER_WORKERS` environment variable (default 8). The ER instance the solver was shaped
on is test data only (`tests/er_fixture.py`, `tests/fixtures/er_request_2026-03.json`).
