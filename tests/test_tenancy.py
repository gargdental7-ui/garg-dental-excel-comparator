"""Unit tests for resolve_company_scope() - the one function every
company-scoped route delegates "which company is this request acting on"
to (see server/_tenancy.py's own docstring). Everything else in the
multi-tenant redesign - RLS isolation, staff/super_admin route behavior -
depends on this function making the right call, so it gets its own
dedicated, DB-independent test file rather than being re-verified
piecemeal in every route's test module."""
import os

import pytest
from fastapi import HTTPException

os.environ.setdefault("SESSION_SECRET", "test-session-secret")

import _auth
import _tenancy

SUPER_ADMIN = _auth.CurrentUser(
    id="super-1", company_id=None, username="admin", full_name="Admin", role="super_admin", active=True
)
STAFF = _auth.CurrentUser(id="staff-1", company_id="company-a", username="staff", full_name="Staff", role="staff", active=True)


class _FakeCursor:
    def __init__(self, row):
        self.row = row

    def execute(self, query, params=None):
        pass

    def fetchone(self):
        return self.row

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeConnection:
    def __init__(self, row):
        self.row = row

    def cursor(self):
        return _FakeCursor(self.row)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_staff_always_gets_own_company_ignoring_request(monkeypatch):
    def fail_if_called(**kwargs):
        raise AssertionError("staff should never hit the DB to resolve their own company")

    monkeypatch.setattr(_tenancy, "get_connection", fail_if_called)
    assert _tenancy.resolve_company_scope(STAFF, None) == "company-a"
    assert _tenancy.resolve_company_scope(STAFF, "company-b") == "company-a"
    assert _tenancy.resolve_company_scope(STAFF, "anything-else-entirely") == "company-a"


def test_super_admin_without_company_id_gets_400(monkeypatch):
    def fail_if_called(**kwargs):
        raise AssertionError("shouldn't hit the DB when company_id is missing")

    monkeypatch.setattr(_tenancy, "get_connection", fail_if_called)
    with pytest.raises(HTTPException) as exc:
        _tenancy.resolve_company_scope(SUPER_ADMIN, None)
    assert exc.value.status_code == 400


def test_super_admin_with_nonexistent_company_gets_404(monkeypatch):
    monkeypatch.setattr(_tenancy, "get_connection", lambda **kwargs: _FakeConnection(None))
    with pytest.raises(HTTPException) as exc:
        _tenancy.resolve_company_scope(SUPER_ADMIN, "company-ghost")
    assert exc.value.status_code == 404


def test_super_admin_with_disabled_company_gets_400(monkeypatch):
    monkeypatch.setattr(_tenancy, "get_connection", lambda **kwargs: _FakeConnection({"active": False}))
    with pytest.raises(HTTPException) as exc:
        _tenancy.resolve_company_scope(SUPER_ADMIN, "company-disabled")
    assert exc.value.status_code == 400


def test_super_admin_with_active_company_gets_it_back(monkeypatch):
    monkeypatch.setattr(_tenancy, "get_connection", lambda **kwargs: _FakeConnection({"active": True}))
    assert _tenancy.resolve_company_scope(SUPER_ADMIN, "company-b") == "company-b"
