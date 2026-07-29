"""Auth/authorization checks for the Signature Library routes, plus the
one behavior that's easy to get wrong: staff (picking a signatory for a
quotation) must only ever see active signatures, while super_admin
(managing the library) sees everything including disabled ones."""
import os
from datetime import datetime, timezone

import bcrypt
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SESSION_SECRET", "test-session-secret")

import _auth
import _signatures_routes
import index

SUPER_ADMIN = _auth.CurrentUser(
    id="super-1", company_id=None, username="admin", full_name="Admin", role="super_admin", active=True
)
STAFF = _auth.CurrentUser(id="staff-1", company_id="company-1", username="staff", full_name="Staff", role="staff", active=True)

FAKE_ROWS = [
    {"id": "sig-1", "name": "Active One", "designation": "Manager", "active": True, "created_at": datetime.now(timezone.utc)},
    {"id": "sig-2", "name": "Inactive One", "designation": "Retired", "active": False, "created_at": datetime.now(timezone.utc)},
]


@pytest.fixture
def client():
    return TestClient(index.app, base_url="https://testserver")


def _login_as(client, monkeypatch, user):
    monkeypatch.setattr(
        _auth,
        "_load_user_for_login",
        lambda username: {
            "id": user.id,
            "company_id": user.company_id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "active": user.active,
            "company_active": True,
            "password_hash": "x",
        },
    )
    monkeypatch.setattr(bcrypt, "checkpw", lambda password, hashed: True)
    monkeypatch.setattr(_auth, "_load_user_by_id", lambda user_id: user if user_id == user.id else None)
    res = client.post("/api/auth/login", json={"username": user.username, "password": "whatever"})
    assert res.status_code == 200


class _FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, query, params=None):
        pass

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeConnection:
    def __init__(self, rows):
        self.rows = rows

    def cursor(self):
        return _FakeCursor(self.rows)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_list_requires_auth(client):
    res = client.get("/api/signatures?company_id=company-1")
    assert res.status_code == 401


def test_create_requires_super_admin(client, monkeypatch):
    _login_as(client, monkeypatch, STAFF)
    res = client.put(
        "/api/signatures?company_id=company-1&name=Dr.%20X",
        files={"file": ("sig.png", b"irrelevant", "image/png")},
    )
    assert res.status_code == 403


def test_update_requires_super_admin(client, monkeypatch):
    _login_as(client, monkeypatch, STAFF)
    res = client.patch("/api/signatures/sig-1", json={"company_id": "company-1", "active": False})
    assert res.status_code == 403


def test_delete_requires_super_admin(client, monkeypatch):
    _login_as(client, monkeypatch, STAFF)
    res = client.delete("/api/signatures/sig-1?company_id=company-1")
    assert res.status_code == 403


def test_staff_only_sees_active_signatures(client, monkeypatch):
    _login_as(client, monkeypatch, STAFF)
    monkeypatch.setattr(_signatures_routes, "get_connection", lambda **kwargs: _FakeConnection(FAKE_ROWS))
    res = client.get("/api/signatures")
    assert res.status_code == 200
    names = [s["name"] for s in res.json()["signatures"]]
    assert names == ["Active One"]


def test_super_admin_sees_inactive_signatures_too(client, monkeypatch):
    _login_as(client, monkeypatch, SUPER_ADMIN)
    monkeypatch.setattr(_signatures_routes, "get_connection", lambda **kwargs: _FakeConnection(FAKE_ROWS))
    # super_admin's resolve_company_scope validates the company against the
    # real DB - mocked here since this test is about active-vs-inactive
    # filtering, not tenancy resolution (which has its own dedicated tests).
    monkeypatch.setattr(_signatures_routes, "resolve_company_scope", lambda current_user, requested: "company-1")
    res = client.get("/api/signatures?company_id=company-1")
    assert res.status_code == 200
    names = {s["name"] for s in res.json()["signatures"]}
    assert names == {"Active One", "Inactive One"}
