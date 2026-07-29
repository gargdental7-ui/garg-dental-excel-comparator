"""Phase 4 persistence tests. Uses a fake DB connection (records executed
queries/params rather than evaluating real SQL) since there's no dedicated
test database for this project - the actual end-to-end behavior (real
Supabase + real CloudConvert) was verified manually once during
development; see [[project_platform_upgrade]] memory. These tests lock in
the two properties that matter most and are cheap to verify without a real
DB: (1) generate() always returns the DOCX response even if persistence or
PDF conversion fails entirely - the user must never lose their document to
a backend outage - and (2) the WHERE clause _quotation_history_routes.py
builds actually differs by role, since that's the real authorization
boundary for "staff only sees their own quotations"."""
import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SESSION_SECRET", "test-session-secret")

import _auth
import _quotation_history_routes
import _quotation_routes
import index

ADMIN = _auth.CurrentUser(id="admin-1", company_id="company-1", username="admin", full_name="Admin", role="admin", active=True)
STAFF = _auth.CurrentUser(id="staff-1", company_id="company-1", username="staff", full_name="Staff", role="staff", active=True)

VALID_PAYLOAD = {
    "company_id": "garg_dental",
    "customer": {"customer_name": "Test Customer"},
    "proposal": {"title": "Equipment Proposal"},
    "items": [{"product_name": "Autoclave", "price": 1000, "quantity": 1}],
}


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
            "password_hash": "x",
        },
    )
    monkeypatch.setattr("bcrypt.checkpw", lambda password, hashed: True)
    monkeypatch.setattr(_auth, "_load_user_by_id", lambda user_id: user if user_id == user.id else None)
    res = client.post("/api/auth/login", json={"username": user.username, "password": "whatever"})
    assert res.status_code == 200


class _RecordingCursor:
    def __init__(self, state):
        self.state = state
        self._last = None

    def execute(self, query, params=None):
        q = " ".join(query.split())
        self.state["executed"].append((q, params))
        if "quote_number_counters" in q:
            self.state["counter"] += 1
            self._last = {"quote_number": self.state["counter"]}
        elif q.startswith("insert into quotations"):
            self._last = {"id": "quotation-1"}
        elif "count(*)" in q:
            self._last = {"total": 0}
        else:
            self._last = None

    def fetchone(self):
        return self._last

    def fetchall(self):
        return []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _RecordingConnection:
    def __init__(self, state):
        self.state = state

    def cursor(self):
        return _RecordingCursor(self.state)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def fake_db_state(monkeypatch):
    state = {"executed": [], "counter": 0}
    monkeypatch.setattr(_quotation_routes, "get_connection", lambda **kwargs: _RecordingConnection(state))
    return state


def test_generate_returns_docx_and_saves_final_status_when_pdf_succeeds(client, monkeypatch, fake_db_state):
    _login_as(client, monkeypatch, STAFF)
    monkeypatch.setattr(_quotation_routes, "convert_docx_to_pdf", lambda docx_bytes, filename: b"%PDF-fake")
    monkeypatch.setattr(_quotation_routes, "storage_upload", lambda bucket, path, content, media_type: None)

    res = client.post("/api/quotation/generate", json=VALID_PAYLOAD)
    assert res.status_code == 200
    assert res.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert len(res.content) > 0

    insert_call = next(p for q, p in fake_db_state["executed"] if q.startswith("insert into quotations"))
    assert insert_call[4] == "final"  # status column


def test_generate_still_returns_docx_when_pdf_conversion_fails(client, monkeypatch, fake_db_state):
    _login_as(client, monkeypatch, STAFF)

    def raise_conversion_error(docx_bytes, filename):
        raise RuntimeError("CloudConvert is down")

    monkeypatch.setattr(_quotation_routes, "convert_docx_to_pdf", raise_conversion_error)
    monkeypatch.setattr(_quotation_routes, "storage_upload", lambda bucket, path, content, media_type: None)

    res = client.post("/api/quotation/generate", json=VALID_PAYLOAD)
    assert res.status_code == 200
    assert len(res.content) > 0

    insert_call = next(p for q, p in fake_db_state["executed"] if q.startswith("insert into quotations"))
    assert insert_call[4] == "pdf_pending"
    assert insert_call[6] is None  # pdf_storage_path


def test_generate_still_returns_docx_when_persistence_entirely_fails(client, monkeypatch):
    _login_as(client, monkeypatch, STAFF)

    def raise_db_error(**kwargs):
        raise RuntimeError("DB is unreachable")

    monkeypatch.setattr(_quotation_routes, "get_connection", raise_db_error)
    monkeypatch.setattr(_quotation_routes, "convert_docx_to_pdf", lambda docx_bytes, filename: b"%PDF-fake")

    res = client.post("/api/quotation/generate", json=VALID_PAYLOAD)
    assert res.status_code == 200
    assert len(res.content) > 0


def test_history_query_scopes_to_own_quotations_for_staff(monkeypatch):
    state = {"executed": [], "counter": 0}
    monkeypatch.setattr(_quotation_history_routes, "get_connection", lambda **kwargs: _RecordingConnection(state))

    # Directly exercise the route function rather than going through the
    # HTTP layer, since we only care about the SQL shape it builds.
    _quotation_history_routes.list_history.__wrapped__(
        customer=None, quote_number=None, staff_id=None, date_from=None, date_to=None, page=1, current_user=STAFF
    )
    executed_queries = " ".join(q for q, _ in state["executed"])
    assert "q.created_by = %s" in executed_queries


def test_history_query_does_not_scope_by_created_by_for_admin_without_staff_filter(monkeypatch):
    state = {"executed": [], "counter": 0}
    monkeypatch.setattr(_quotation_history_routes, "get_connection", lambda **kwargs: _RecordingConnection(state))

    _quotation_history_routes.list_history.__wrapped__(
        customer=None, quote_number=None, staff_id=None, date_from=None, date_to=None, page=1, current_user=ADMIN
    )
    executed_queries = " ".join(q for q, _ in state["executed"])
    assert "q.created_by = %s" not in executed_queries
