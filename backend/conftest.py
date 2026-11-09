import importlib

import pytest
from django.test import Client

from accounts.models import Role, User

PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def no_real_backups(settings, tmp_path, monkeypatch):
    """A real worker in a test runs the periodic `backup` too, which would reach for `/backups` and a `pg_dump` that may be
    older than the server. Here it writes a few bytes into the test's own directory; `deploy/tests/operations.sh` runs the real
    one."""
    from ops import backups
    settings.BACKUPS_DIR = tmp_path / "backups"
    settings.BACKUPS_DIR.mkdir()
    monkeypatch.setattr(backups, "dump_database", lambda out: out.write(b"PGDMP-in-a-test"))


class _NoPushService:
    def post(self, url, **_):
        raise AssertionError(f"a push left the test for a real push service: {url}")


@pytest.fixture(autouse=True)
def no_real_push_service(monkeypatch):
    """Any test whose change is pushed (a swap proposed, a window opened, a roster submitted) defers a push job, and a test that
    runs the real worker runs it. No send leaves the test: `notifications.tests.conftest.push_service` scripts the answers."""
    from notifications import pushing
    monkeypatch.setattr(pushing, "push_service", _NoPushService())


@pytest.fixture
def make_user(db):
    def make(username="someone", role=Role.STAFF_NURSE, password=PASSWORD, **fields):
        return User.objects.create_user(username, password, role, **fields)
    return make


@pytest.fixture
def signed_in(make_user):
    """A client signed in as a new user of the given role, through the real endpoint."""
    def sign_in(role=Role.SYSTEM_ADMIN, username="someone", **fields):
        make_user(username, role, **fields)
        client = Client()
        response = post(client, "/api/auth/login", {"username": username, "password": PASSWORD})
        assert response.status_code == 200, response.content
        return client
    return sign_in


@pytest.fixture
def client_of(make_user):
    """A client signed in as a new user of the given role, under a username the test chooses."""
    def sign_in(username, role, **fields):
        make_user(username, role, **fields)
        client = Client()
        assert post(client, "/api/auth/login", {"username": username, "password": PASSWORD}).status_code == 200
        return client
    return sign_in


def post(client, path, body):
    return client.post(path, body, content_type="application/json")


def migration(app: str, name: str):
    """A migration's module, whose own functions a test can run against rows written as an older release left them."""
    return importlib.import_module(f"{app}.migrations.{name}")

