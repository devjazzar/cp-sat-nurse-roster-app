"""Walks every endpoint the API has, so an endpoint a later ticket adds is held to this too."""
import re
from uuid import uuid4

import pytest
from django.test import Client

from accounts.authz import SignedIn
from accounts.models import Role
from config.api import api
from conftest import PASSWORD

pytestmark = pytest.mark.django_db

PUBLIC = {"GET /api/health", "GET /api/auth/session", "POST /api/auth/login"}
# The catalogue: the ticket gives every role its reading, and it is neither a roster nor a rostering attribute.
ANY_ROLE = {"POST /api/auth/logout", "POST /api/auth/change-password",
            "GET /api/hospital/shifts", "GET /api/hospital/leave-types", "GET /api/hospital/public-holidays",
            "GET /api/hospital/ramadan"}


def endpoints():
    """(method, path, the SignedIn guarding it or None), one per method of every operation."""
    found = []
    for router in api._get_bound_routers():  # private, but only these have the inherited auth applied
        prefix = router.prefix
        for path, view in router.path_operations.items():
            for operation in view.operations:
                guards = [auth for auth in operation.auth_callbacks if isinstance(auth, SignedIn)]
                full = "/api" + (f"/{prefix.strip('/')}" if prefix.strip("/") else "") + path
                found += [(method, full, guards[0] if guards else None) for method in operation.methods]
    return found


ENDPOINTS = endpoints()
RESTRICTED = [(method, path, guard) for method, path, guard in ENDPOINTS if guard and guard.roles]
REFUSED_ROLES = [(method, path, role) for method, path, guard in RESTRICTED for role in Role if role not in guard.roles]


def call(client, method, path):
    url = re.sub(r"\{[^}]*\}", str(uuid4()), path)
    return getattr(client, method.lower())(url, {}, content_type="application/json")


def label(method, path):
    return f"{method} {path}"


def test_the_walk_found_the_endpoints():
    assert {"GET /api/users", "PUT /api/users/{user_id}/full-name", "GET /api/audit/entries", "PUT /api/ops/technical-settings",
            "PUT /api/hospital/rules", "GET /api/units", "POST /api/units/{unit_id}/archive"} <= {
        label(method, path) for method, path, _ in ENDPOINTS}


def test_only_the_named_endpoints_are_public():
    assert {label(method, path) for method, path, guard in ENDPOINTS if guard is None} == PUBLIC


def test_only_the_named_endpoints_leave_the_role_open():
    assert {label(method, path) for method, path, guard in ENDPOINTS if guard and not guard.roles} == ANY_ROLE


def test_every_role_is_refused_somewhere():
    assert {role for _, _, role in REFUSED_ROLES} == set(Role)


@pytest.mark.parametrize("method, path, role", REFUSED_ROLES)
def test_a_role_gets_403_where_it_has_no_business(signed_in, method, path, role):
    assert call(signed_in(role), method, path).status_code == 403


@pytest.mark.parametrize("method, path, guard", RESTRICTED, ids=lambda value: value if isinstance(value, str) else "")
def test_signed_out_gets_401(method, path, guard):
    assert call(Client(), method, path).status_code == 401


@pytest.mark.parametrize("method, path, guard", RESTRICTED, ids=lambda value: value if isinstance(value, str) else "")
def test_a_pending_forced_change_gets_403_even_with_the_right_role(signed_in, method, path, guard):
    client = signed_in(guard.roles[0], must_change_password=True)

    assert call(client, method, path).status_code == 403


@pytest.mark.parametrize("method, path, guard", [e for e in RESTRICTED if e[0] != "GET"],
                         ids=lambda value: value if isinstance(value, str) else "")
def test_a_write_without_the_csrf_token_gets_403_even_with_the_right_role(make_user, method, path, guard):
    make_user(role=guard.roles[0])
    client = Client(enforce_csrf_checks=True)
    client.get("/api/auth/session")
    token = client.cookies["csrftoken"].value
    assert client.post("/api/auth/login", {"username": "someone", "password": PASSWORD},
                       content_type="application/json", headers={"X-CSRFToken": token}).status_code == 200

    assert call(client, method, path).status_code == 403
