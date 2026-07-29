"""Auth boundary + aggregation-shape tests for /api/companies/{id}/dashboard
(Phase F). Uses a fake DB connection keyed by recognizable SQL substrings
since there's no dedicated test database for this project - same pattern
as tests/test_quotation_persistence.py."""
import os
from datetime import datetime, timezone

import bcrypt
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SESSION_SECRET", "test-session-secret")

import _auth
import _companies_routes
import index

SUPER_ADMIN = _auth.CurrentUser(
    id="super-1", company_id=None, username="admin", full_name="Admin", role="super_admin", active=True
)
STAFF = _auth.CurrentUser(id="staff-1", company_id="company-1", username="staff", full_name="Staff", role="staff", active=True)


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


class _FakeDashboardCursor:
    def __init__(self):
        self.last_query = ""

    def execute(self, query, params=None):
        self.last_query = " ".join(query.split())

    def fetchone(self):
        q = self.last_query
        if "select 1 from companies" in q:
            return {"exists": 1}
        if "count(*) filter" in q:
            return {"today": 2, "this_month": 5, "customers": 3}
        if "from quotations q join users u" in q:
            return {"full_name": "Jane Staff", "n": 5}
        if "quote_number, customer_name, created_at from quotations" in q:
            return {"quote_number": 7, "customer_name": "Acme Clinic", "created_at": datetime.now(timezone.utc)}
        if "from master_excel" in q:
            return {"version": 3, "file_size": 1000}
        if "from quotation_templates" in q:
            return {"version": 2, "file_size": 2000}
        if "count(*) as n from signatures" in q:
            return {"n": 4}
        if "coalesce(sum(qf.size_bytes)" in q:
            return {"total": 500}
        return None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeDashboardConnection:
    def cursor(self):
        return _FakeDashboardCursor()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_dashboard_requires_super_admin(client, monkeypatch):
    _login_as(client, monkeypatch, STAFF)
    res = client.get("/api/companies/company-1/dashboard")
    assert res.status_code == 403


def test_dashboard_requires_auth(client):
    res = client.get("/api/companies/company-1/dashboard")
    assert res.status_code == 401


def test_dashboard_aggregates_expected_shape(client, monkeypatch):
    _login_as(client, monkeypatch, SUPER_ADMIN)
    monkeypatch.setattr(_companies_routes, "get_connection", lambda **kwargs: _FakeDashboardConnection())

    res = client.get("/api/companies/company-1/dashboard")
    assert res.status_code == 200
    body = res.json()
    assert body["quotationsToday"] == 2
    assert body["quotationsThisMonth"] == 5
    assert body["totalCustomers"] == 3
    assert body["mostActiveStaff"] == "Jane Staff"
    assert body["lastQuotation"] == {"quoteNumber": 7, "customerName": "Acme Clinic", "createdAt": body["lastQuotation"]["createdAt"]}
    assert body["masterExcelVersion"] == 3
    assert body["templateVersion"] == 2
    assert body["activeSignatureCount"] == 4
    # 500 (quotation files) + 1000 (master excel) + 2000 (template)
    assert body["storageBytes"] == 3500
