"""First FastAPI route-level test in the suite (see tests/conftest.py for
why server/ needs sys.path help). DB-dependent lookups (_load_user_by_id,
_load_user_for_login) are monkeypatched rather than hitting a real
Postgres instance - this is a unit-level test of the auth *contract*
(cookie shape, signature checks, role gating), not an integration test of
_db.py's SQL, which has no test coverage yet since no test database exists
for this project."""
import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SESSION_SECRET", "test-session-secret")

import _auth
import _users_routes
import index

SUPER_ADMIN = _auth.CurrentUser(
    id="super-1", company_id=None, username="admin", full_name="Admin", role="super_admin", active=True
)
STAFF = _auth.CurrentUser(id="staff-1", company_id="company-1", username="staff", full_name="Staff", role="staff", active=True)
DISABLED = _auth.CurrentUser(
    id="disabled-1", company_id="company-1", username="disabled", full_name="Disabled", role="staff", active=False
)


@pytest.fixture
def client():
    # https:// (not the default http://testserver) so the session cookie's
    # Secure attribute doesn't get silently dropped by httpx's cookie jar,
    # matching how it actually round-trips in real (HTTPS) deployment.
    return TestClient(index.app, base_url="https://testserver")


class _FakeCursor:
    """Enough of a psycopg cursor to exercise list_users' happy path
    without a real Postgres connection - no live test DB exists for this
    project yet."""

    def execute(self, *args, **kwargs):
        pass

    def fetchall(self):
        return []

    def fetchone(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeConnection:
    def cursor(self):
        return _FakeCursor()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def fake_db(monkeypatch):
    monkeypatch.setattr(_users_routes, "get_connection", lambda **kwargs: _FakeConnection())
    # resolve_company_scope normally validates the company against the DB -
    # bypassed here since these tests are about auth/role gating, not
    # tenancy resolution (that has its own dedicated tests).
    monkeypatch.setattr(_users_routes, "resolve_company_scope", lambda current_user, requested: requested or current_user.company_id)


def _login_as(client, monkeypatch, user: _auth.CurrentUser, password_hash: str = "irrelevant"):
    def fake_login_lookup(username):
        if username != user.username:
            return None
        return {
            "id": user.id,
            "company_id": user.company_id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "active": user.active,
            "company_active": True,
            "password_hash": password_hash,
        }

    monkeypatch.setattr(_auth, "_load_user_for_login", fake_login_lookup)
    monkeypatch.setattr("bcrypt.checkpw", lambda password, hashed: True)
    monkeypatch.setattr(_auth, "_load_user_by_id", lambda user_id: user if user_id == user.id else None)

    res = client.post("/api/auth/login", json={"username": user.username, "password": "whatever"})
    assert res.status_code == 200
    return res


def test_login_wrong_password_401s(client, monkeypatch):
    monkeypatch.setattr(_auth, "_load_user_for_login", lambda username: None)
    res = client.post("/api/auth/login", json={"username": "nobody", "password": "wrong"})
    assert res.status_code == 401


def test_login_disabled_user_401s(client, monkeypatch):
    monkeypatch.setattr(
        _auth,
        "_load_user_for_login",
        lambda username: {
            "id": DISABLED.id,
            "company_id": DISABLED.company_id,
            "username": DISABLED.username,
            "full_name": DISABLED.full_name,
            "role": DISABLED.role,
            "active": False,
            "company_active": True,
            "password_hash": "x",
        },
    )
    res = client.post("/api/auth/login", json={"username": "disabled", "password": "whatever"})
    assert res.status_code == 401


def test_login_disabled_company_401s(client, monkeypatch):
    # A staff member whose own account is active but whose company was
    # disabled by the Super Admin must also be blocked - either one alone
    # is sufficient to lock a login out.
    monkeypatch.setattr(
        _auth,
        "_load_user_for_login",
        lambda username: {
            "id": STAFF.id,
            "company_id": STAFF.company_id,
            "username": STAFF.username,
            "full_name": STAFF.full_name,
            "role": STAFF.role,
            "active": True,
            "company_active": False,
            "password_hash": "x",
        },
    )
    res = client.post("/api/auth/login", json={"username": "staff", "password": "whatever"})
    assert res.status_code == 401


def test_valid_login_sets_cookie_and_status_reports_authenticated(client, monkeypatch):
    _login_as(client, monkeypatch, SUPER_ADMIN)
    assert "gd_session" in client.cookies

    res = client.get("/api/auth/status")
    assert res.status_code == 200
    body = res.json()
    assert body["authenticated"] is True
    assert body["user"]["role"] == "super_admin"
    assert body["user"]["companyId"] is None


def test_no_cookie_401s_protected_route(client):
    res = client.get("/api/users?company_id=company-1")
    assert res.status_code == 401


def test_staff_hitting_super_admin_route_403s(client, monkeypatch, fake_db):
    _login_as(client, monkeypatch, STAFF)
    res = client.get("/api/users?company_id=company-1")
    assert res.status_code == 403


def test_super_admin_can_reach_super_admin_route(client, monkeypatch, fake_db):
    _login_as(client, monkeypatch, SUPER_ADMIN)
    res = client.get("/api/users?company_id=company-1")
    assert res.status_code == 200


def test_tampered_cookie_401s(client, monkeypatch):
    _login_as(client, monkeypatch, SUPER_ADMIN)
    good_cookie = client.cookies["gd_session"]
    issued_at, user_id, _signature = good_cookie.split(".", 2)
    tampered = f"{issued_at}.{user_id}.deadbeef"
    client.cookies.set("gd_session", tampered)
    res = client.get("/api/auth/status")
    assert res.json()["authenticated"] is False


def test_logout_clears_session(client, monkeypatch):
    _login_as(client, monkeypatch, SUPER_ADMIN)
    res = client.post("/api/auth/logout")
    assert res.status_code == 200
    res = client.get("/api/auth/status")
    assert res.json()["authenticated"] is False
