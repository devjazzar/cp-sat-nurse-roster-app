"""The real queue on real connections, with the scripted solver."""
import pytest
from django.db import connection

from accounts.models import Role, User
from conftest import post
from ops import solver_client
from solves.models import Solve
from solves.tasks import recover_lost_jobs
from solves.tests.conftest import NURSES, job, make_sample_unit, result_of, roster_of, run_the_queue, started
from solves.tests.test_flow import url

pytestmark = pytest.mark.usefixtures("empty_queue")


@pytest.fixture
def icu_manager(client_of):
    return client_of("omar", Role.UNIT_MANAGER, full_name="Omar Said")


@pytest.fixture
def icu(icu_manager, make_user, catalogue):
    return make_sample_unit("ICU", User.objects.get(username="omar"), make_user, prefix="i")


def finished():
    return [job("finished", result=result_of(roster_of(NURSES)))]


def test_first_come_first_served_across_two_units_one_at_a_time(mona, er, icu_manager, icu, solver, before_june, monkeypatch):
    """Three solves, so the middle one belongs to the other unit. The scripted solver proves none overlapped: each `start_solve`
    finds the row before it ended."""
    solver.script(finished(), finished(), finished())
    first, second, third = started(mona, er), started(icu_manager, icu), started(mona, er, "2026-07")
    assert [first["queue_ahead"], second["queue_ahead"], third["queue_ahead"]] == [0, 1, 2]
    order = []
    original = solver.start_solve

    def seen(solve_input):
        order.append(solve_input["department"]["name"])
        assert Solve.objects.filter(state="running").count() == 1
        return original(solve_input)
    monkeypatch.setattr(solver_client, "start_solve", seen)

    run_the_queue()

    assert order == ["ER", "ICU", "ER"]
    ended = [Solve.objects.get(pk=row["id"]) for row in (first, second, third)]
    assert all(row.state == "succeeded" for row in ended)
    assert ended[0].finished_at <= ended[1].started_at and ended[1].finished_at <= ended[2].started_at


def test_stopping_the_one_ahead_moves_the_next_one_up(mona, er, icu_manager, icu, solver, before_june):
    first, second = started(mona, er), started(icu_manager, icu)
    assert icu_manager.get(url(icu, f"/solves/{second['id']}")).json()["queue_ahead"] == 1

    assert post(mona, url(er, f"/solves/{first['id']}/stop"), {}).status_code == 200

    assert icu_manager.get(url(icu, f"/solves/{second['id']}")).json()["queue_ahead"] == 0
    solver.script(finished())
    run_the_queue()
    assert [input_["department"]["name"] for input_ in solver.started] == ["ICU"]


def test_a_retry_keeps_its_place_in_line(mona, er, icu_manager, icu, solver, before_june):
    solver.script([job("failed", error="crashed")], finished(), finished())
    started(mona, er), started(icu_manager, icu)

    run_the_queue()

    assert [input_["department"]["name"] for input_ in solver.started] == ["ER", "ER", "ICU"]


def test_a_worker_that_dies_is_recovered_by_the_periodic_job(mona, er, solver, before_june):
    """Its job holds the hospital-wide lock, so until the recovery nothing else would run."""
    solve = started(mona, er)
    with connection.cursor() as cursor:
        cursor.execute("INSERT INTO procrastinate_workers (last_heartbeat) VALUES (now() - interval '5 minutes') RETURNING id")
        worker = cursor.fetchone()[0]
        cursor.execute("UPDATE procrastinate_jobs SET status = 'doing', worker_id = %s", [worker])
    Solve.objects.filter(pk=solve["id"]).update(state="running", attempts=1, solver_job_id="job-gone")
    solver.script(finished())

    recover_lost_jobs(timestamp=0)
    run_the_queue()
    assert Solve.objects.get(pk=solve["id"]).state == "succeeded"


def test_a_solve_and_its_job_arrive_together(mona, er, before_june, solver):
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM procrastinate_jobs")
        assert cursor.fetchone()[0] == 0
    started(mona, er)
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*), max(id) FROM procrastinate_jobs WHERE task_name LIKE '%run_solve'")
        count, job_id = cursor.fetchone()
    assert count == 1 and Solve.objects.get().job_id == job_id
