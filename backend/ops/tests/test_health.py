import httpx
import pytest
from django.test import Client


@pytest.fixture
def solver_answers(monkeypatch):
    def fake_get(url, headers, timeout):
        assert url == "http://solver.test/health"
        assert headers == {"Authorization": "Bearer test-token"}
        return httpx.Response(200, json={"status": "ok", "version": "0.1.0", "workers": 8},
                              request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "get", fake_get)


@pytest.fixture
def solver_down(monkeypatch):
    def fake_get(url, headers, timeout):
        raise httpx.ConnectError("no route to solver")
    monkeypatch.setattr(httpx, "get", fake_get)


@pytest.fixture(autouse=True)
def solver_settings(settings):
    settings.SOLVER_URL = "http://solver.test"
    settings.SOLVER_TOKEN = "test-token"


@pytest.mark.django_db
def test_health_reports_the_database_and_the_solver(solver_answers):
    r = Client().get("/api/health")

    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": True, "solver": {"reachable": True}}


@pytest.mark.django_db
def test_health_is_degraded_but_answers_when_the_solver_is_down(solver_down):
    r = Client().get("/api/health")

    assert r.status_code == 200
    assert r.json() == {"status": "degraded", "database": True, "solver": {"reachable": False}}


def test_the_openapi_document_and_docs_are_not_served():
    assert Client().get("/api/openapi.json").status_code == 404
    assert Client().get("/api/docs").status_code == 404
