# The data the browser checks need, on a scratch stack's empty database: run by e2e/stack.sh, never on an installation's own.
#
#   docker compose exec -T -e SEED_PASSWORD=… web python manage.py shell < e2e/seed.py
#
# The solver's four-nurse sample as ER (its JSON copied to /tmp/four_nurses.json first), Mona its manager and Carla the CNO.
# The System Admin `admin` that `prepare` made takes the seed's password too, with no change due, so a check can sign in.
# Next month is solved for real in-process, submitted and approved, on the real clock. The month after has a request window
# open from today. A two-cell swap the app's own judging finds sound on the approved month is printed last, for the swap check:
# one line, `E2E_SEED {...}`.
import copy
import datetime as dt
import json
import os

from django.db import transaction
from django.utils import timezone
from nurse_roster.model import build_model, solve
from nurse_roster.precheck import precheck
from nurse_roster.request import load_request
from nurse_roster.result import build_result

from accounts.models import Role, User
from hospital.catalogue import seed_catalogue
from hospital.models import HospitalSettings
from nurses import membership
from nurses.models import NurseProfile, Placement
from requesting import making
from rosters import drafts, review
from rosters.models import Roster
from solves.input import assemble
from solves.models import Solve, SolveState
from swaps.judging import Change, judge
from units.models import Unit

PASSWORD = os.environ["SEED_PASSWORD"]
SAMPLE = json.load(open("/tmp/four_nurses.json"))
NAMES = {"Amal": "Amal Saleh", "Badr": "Badr Harbi", "Dana": "Dana Odeh", "Emad": "Emad Nasser", "mona": "Mona Ali",
         "carla": "Carla Haddad"}

assert not Unit.objects.exists(), "e2e/seed.py runs once, on an empty scratch database"

today = membership.today()
this_month = today.replace(day=1)
approved_month = (this_month + dt.timedelta(days=32)).replace(day=1)
window_month = (approved_month + dt.timedelta(days=32)).replace(day=1)

with transaction.atomic():
    seed_catalogue()
    admin = User.objects.get(role=Role.SYSTEM_ADMIN)
    admin.set_password(PASSWORD)
    admin.must_change_password = False
    admin.save()
    mona = User.objects.create_user("mona", PASSWORD, Role.UNIT_MANAGER, full_name=NAMES["mona"])
    carla = User.objects.create_user("carla", PASSWORD, Role.CNO, full_name=NAMES["carla"])
    settings = HospitalSettings.load()
    settings.rules = {k: v for k, v in copy.deepcopy(SAMPLE["general"]).items() if k != "shift_hours"}
    settings.save()
    unit = Unit.objects.create(name="ER", manager=mona,
                               rules={k: v for k, v in copy.deepcopy(SAMPLE["department"]).items() if k != "name"})
    for row in SAMPLE["nurses"]:
        user = User.objects.create_user(row["id"], PASSWORD, Role.STAFF_NURSE, full_name=NAMES[row["id"]])
        nurse = NurseProfile.objects.create(user=user, gender=row["gender"], start_date=this_month, team_leader=row["team_leader"],
                                            score=row["score"], attributes_saved=True)
        Placement.objects.create(nurse=nurse, unit=unit, from_month=this_month, allowed_shifts=row.get("allowed_shifts"))

with transaction.atomic():
    raw = assemble(unit, approved_month, time_limit=10).input
    req = load_request(raw)
    model = build_model(req.problem)
    solution = solve(model, req.problem, **req.solver.solve_kwargs(4))
    result = build_result(req, model, solution, precheck=precheck(req.problem), workers=4)
    assert result["ok"], result["message"]
    now = timezone.now()
    solved = Solve.objects.create(unit=unit, month=approved_month, requested_by=mona, time_limit_seconds=10,
                                  state=SolveState.SUCCEEDED, input=raw, result=result, started_at=now, finished_at=now,
                                  best_cost=result["cost"])
    roster = drafts.replace_grid(solved, result["roster"])
    review.submit(roster, mona)
    review.approve(Roster.objects.get(pk=roster.pk), carla)

with transaction.atomic():
    closes = min(today + dt.timedelta(days=14), window_month - dt.timedelta(days=1))
    making.open_window(Unit.objects.select_for_update().get(pk=unit.pk), window_month, today, closes, mona, None)


def a_sound_swap() -> dict:
    """The first day, from tomorrow, on which one nurse works a shift and a colleague is off, and giving the shift to the colleague
    breaks nothing: the proposer's cell first."""
    roster = Roster.objects.get(unit=unit, month=approved_month)
    grid = roster.grid  # {hospital ID: {ISO date: shift code, "" for off}}
    ids = list(grid)
    first = max(today + dt.timedelta(days=1), approved_month)
    for offset in range(31):
        day = first + dt.timedelta(days=offset)
        if day.month != approved_month.month:
            break
        for proposer in ids:
            shift = grid[proposer].get(day.isoformat(), "")
            if not shift:
                continue
            for colleague in ids:
                if colleague == proposer or grid[colleague].get(day.isoformat(), ""):
                    continue
                changes = [Change(proposer, day, None), Change(colleague, day, shift)]
                if not judge(roster, changes, NurseProfile.objects.get(user__username=proposer)).problems:
                    return {"proposer": proposer, "colleague": colleague, "date": day.isoformat(), "shift": shift}
    raise SystemExit("no sound two-cell swap on the approved month")


print("E2E_SEED " + json.dumps({
    "unit": "ER",
    "names": {**NAMES, "admin": admin.full_name},
    "approved_month": approved_month.strftime("%Y-%m"),
    "window_month": window_month.strftime("%Y-%m"),
    "swap": a_sound_swap(),
}))
