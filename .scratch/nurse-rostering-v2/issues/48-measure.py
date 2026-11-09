# Ticket 48's weight measurement, on a scratch stack only (never the installation's `nurse-roster`):
#
#   docker compose -p <scratch> cp solver/tests/fixtures/er_request_2026-03.json web:/tmp/er_request.json
#   docker compose -p <scratch> exec -T -e WEIGHTS=4,20,50,200 -e RUNS=3 web python manage.py shell \
#       < .scratch/nurse-rostering-v2/issues/48-measure.py
#
# It adds a unit "ER25" seeded like ER's December on the dev stack: the solver's ER sample (25 nurses, longest run 3, the
# reviewed hospital rules) as this app holds it, the cap at 3, December 2026. Then, for each weight, RUNS solves in this
# process at the unit's own default time limit (60 s), each built by `solves.input.assemble` as a real solve is and solved with
# as many workers as the solver service would use. For each solve it prints the nurses above the cap (counted from the grid
# as text, apart from the solver's own counter), the full-run penalty, and the month's cost. The hospital rules are put back
# as they were at the end; the unit stays, so the scratch drive can use it too (its manager is `er25mgr`).
import copy
import datetime as dt
import json
import os
import re

from django.db import transaction
from nurse_roster.model import MAX_WORKERS, build_model, solve
from nurse_roster.precheck import precheck
from nurse_roster.request import load_request
from nurse_roster.result import build_result

from accounts.models import Role, User
from hospital.models import HospitalSettings
from hospital.rules import DEFAULT_RULES
from nurses.models import NurseProfile, Placement
from solves.input import assemble
from units.models import Unit

ER = json.load(open("/tmp/er_request.json"))
DECEMBER = dt.date(2026, 12, 1)
CAP = 3
WEIGHTS = [int(w) for w in os.environ.get("WEIGHTS", "4,20,50,200").split(",")]
RUNS = int(os.environ.get("RUNS", "3"))
try:  # The service's own choice, if the web image holds the service's module; the container's CPUs otherwise.
    from solver_service.app import default_workers
except ImportError:
    def default_workers() -> int:
        return min(os.cpu_count() or 1, MAX_WORKERS)
WORKERS = default_workers()

with transaction.atomic():
    unit = Unit.objects.filter(name="ER25").first()
    if unit is None:
        manager = User.objects.create_user("er25mgr", os.urandom(16).hex(), Role.UNIT_MANAGER, full_name="ER25 Manager")
        rules = {k: v for k, v in copy.deepcopy(ER["department"]).items() if k != "name"} | {"max_full_runs": CAP}
        unit = Unit.objects.create(name="ER25", manager=manager, rules=rules, rules_need_review=False)
        for row in ER["nurses"]:
            user = User.objects.create_user(f"er25-{row['id']}", os.urandom(16).hex(), Role.STAFF_NURSE,
                                            full_name=f"ER25 {row['id']}")
            profile = NurseProfile.objects.create(
                user=user, gender=row["gender"], start_date=dt.date(2026, 1, 1), team_leader=row["team_leader"],
                score=row["score"], ramadan_reduced=row["ramadan_reduced"], breastfeeding=row["breastfeeding"],
                ytd_overtime=row["ytd_overtime"], hours_balance=row["hours_balance"], night_balance=row["night_balance"],
                friday_balance=row["friday_balance"], attributes_saved=True)
            Placement.objects.create(nurse=profile, unit=unit, from_month=dt.date(2026, 1, 1),
                                     allowed_shifts=row.get("allowed_shifts"))
    else:
        unit.rules = unit.rules | {"max_full_runs": CAP}
        unit.save()

settings = HospitalSettings.load()
kept = copy.deepcopy(settings.rules)
K = unit.rules["max_consecutive_shifts"]


def full_runs(raw: dict, roster: dict) -> dict[str, int]:
    """Runs of exactly K worked days ending in the month, followed by a day off or the month's end, read off the text."""
    out = {}
    for row in raw["nurses"]:
        history = "".join("W" if code else "." for code in row["previous"])
        month = "".join("W" if code else "." for _, code in sorted(roster[row["id"]].items()))
        text = history + month
        ends = [m.end() - 1 for m in re.finditer(r"(?<!W)W+(?=\.|$)", text) if m.end() - m.start() == K]
        out[row["id"]] = sum(1 for end in ends if end >= len(history))
    return out


try:
    print(f"MEASURE unit ER25, {len(ER['nurses'])} nurses, longest run {K}, cap {CAP}, {unit.default_time_limit} s, "
          f"{WORKERS} workers")
    for weight in WEIGHTS:
        settings.rules = copy.deepcopy(DEFAULT_RULES)
        settings.rules["weights"]["excess_full_run"] = weight
        settings.save()
        for run in range(1, RUNS + 1):
            raw = assemble(unit, DECEMBER, time_limit=unit.default_time_limit).input
            req = load_request(raw)
            model = build_model(req.problem)
            solution = solve(model, req.problem, **req.solver.solve_kwargs(WORKERS))
            result = build_result(req, model, solution, precheck=precheck(req.problem), workers=WORKERS)
            if not result.get("roster"):
                print(f"MEASURE weight {weight} run {run}: no roster ({result['status']}: {result['message']})")
                continue
            counted = full_runs(raw, result["roster"])
            above = {nurse: count for nurse, count in counted.items() if count > CAP}
            print(f"MEASURE weight {weight} run {run}: {result['status']}, cost {result['cost']}, "
                  f"full-run penalty {result['penalties'].get('excess_full_run', 0)}, nurses above the cap {len(above)} "
                  f"{dict(sorted(above.items()))}, most full runs {max(counted.values())}, "
                  f"stopped by {result['solver'].get('stopped_by')}")
finally:
    settings.rules = kept
    settings.save()
