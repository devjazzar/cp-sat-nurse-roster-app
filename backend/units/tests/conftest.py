import pytest
from django.test import Client

from conftest import PASSWORD, post
from hospital.catalogue import seed_catalogue


@pytest.fixture(autouse=True)
def catalogue(db):
    """What `bootstrap` seeds on first start: a unit's defaults name its shifts."""
    seed_catalogue()


@pytest.fixture
def client_of(make_user):
    """A client signed in as a new user of the given role, under a username the test chooses."""
    def sign_in(username, role, **fields):
        make_user(username, role, **fields)
        client = Client()
        assert post(client, "/api/auth/login", {"username": username, "password": PASSWORD}).status_code == 200
        return client
    return sign_in
