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
    """The dashboard route now issues a single combined query (LEFT JOIN
    LATERAL) instead of 8 sequential ones - one execute() per test, so this
    just returns one merged row rather than dispatching per SQL substring."""

    def __init__(self, company_exists=True):
        self.company_exists = company_exists
        self.last_query = ""

    def execute(self, query, params=None):
        self.last_query = " ".join(query.split())

    def fetchone(self):
        if not self.company_exists:
            return {
                "company_exists": False,
                "today": 0,
                "this_month": 0,
                "customers": 0,
                "most_active_full_name": None,
                "last_quote_number": None,
                "last_customer_name": None,
                "last_created_at": None,
                "master_excel_version": None,
                "master_excel_file_size": None,
                "template_version": None,
                "template_file_size": None,
                "active_signatures": 0,
                "quotation_files_bytes": 0,
            }
        return {
            "company_exists": True,
            "today": 2,
            "this_month": 5,
            "customers": 3,
            "most_active_full_name": "Jane Staff",
            "last_quote_number": 7,
            "last_customer_name": "Acme Clinic",
            "last_created_at": datetime.now(timezone.utc),
            "master_excel_version": 3,
            "master_excel_file_size": 1000,
            "template_version": 2,
            "template_file_size": 2000,
            "active_signatures": 4,
            "quotation_files_bytes": 500,
        }

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeDashboardConnection:
    def __init__(self, company_exists=True):
        self.company_exists = company_exists

    def cursor(self):
        return _FakeDashboardCursor(company_exists=self.company_exists)

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


def test_dashboard_404s_when_company_missing(client, monkeypatch):
    _login_as(client, monkeypatch, SUPER_ADMIN)
    monkeypatch.setattr(
        _companies_routes, "get_connection", lambda **kwargs: _FakeDashboardConnection(company_exists=False)
    )

    res = client.get("/api/companies/company-1/dashboard")
    assert res.status_code == 404
