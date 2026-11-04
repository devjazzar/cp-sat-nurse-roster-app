import pytest
from django.test import Client

from accounts.models import Role, User

PASSWORD = "correct-horse-battery"


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


def post(client, path, body):
    return client.post(path, body, content_type="application/json")
