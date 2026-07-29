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
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SESSION_SECRET", "test-session-secret")

from app.quotation_companies import CompanyProfile

import _auth
import _quotation_history_routes
import _quotation_routes
import index

FAKE_COMPANY = CompanyProfile(
    id="company-1",
    slug="test-company",
    display_name="Test Company",
    template_filename="equipment_proposal_garg_dental.docx",
)

_TEMPLATE_BYTES = (
    Path(__file__).resolve().parent.parent
    / "app"
    / "quotation_templates"
    / "equipment_proposal_garg_dental.docx"
).read_bytes()

SUPER_ADMIN = _auth.CurrentUser(
    id="super-1", company_id=None, username="admin", full_name="Admin", role="super_admin", active=True
)
STAFF = _auth.CurrentUser(id="staff-1", company_id="company-1", username="staff", full_name="Staff", role="staff", active=True)

VALID_PAYLOAD = {
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
            "company_active": True,
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
    monkeypatch.setattr(_quotation_routes, "get_company", lambda company_id: FAKE_COMPANY)
    monkeypatch.setattr(_quotation_routes, "fetch_company_template_bytes", lambda current_user, company_id=None: _TEMPLATE_BYTES)
    monkeypatch.setattr(_quotation_routes, "fetch_company_logo_bytes", lambda current_user, company_id=None: None)
    monkeypatch.setattr(_quotation_routes, "fetch_template_version", lambda current_user, company_id: 1)
    monkeypatch.setattr(_quotation_routes, "fetch_master_excel_version", lambda current_user, company_id: None)
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
    monkeypatch.setattr(_quotation_routes, "get_company", lambda company_id: FAKE_COMPANY)
    monkeypatch.setattr(_quotation_routes, "fetch_company_template_bytes", lambda current_user, company_id=None: _TEMPLATE_BYTES)
    monkeypatch.setattr(_quotation_routes, "fetch_company_logo_bytes", lambda current_user, company_id=None: None)
    monkeypatch.setattr(_quotation_routes, "fetch_template_version", lambda current_user, company_id: 1)
    monkeypatch.setattr(_quotation_routes, "fetch_master_excel_version", lambda current_user, company_id: None)

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
    monkeypatch.setattr(_quotation_routes, "get_company", lambda company_id: FAKE_COMPANY)
    monkeypatch.setattr(_quotation_routes, "fetch_company_template_bytes", lambda current_user, company_id=None: _TEMPLATE_BYTES)
    monkeypatch.setattr(_quotation_routes, "fetch_company_logo_bytes", lambda current_user, company_id=None: None)
    monkeypatch.setattr(_quotation_routes, "fetch_template_version", lambda current_user, company_id: 1)
    monkeypatch.setattr(_quotation_routes, "fetch_master_excel_version", lambda current_user, company_id: None)

    def raise_db_error(**kwargs):
        raise RuntimeError("DB is unreachable")

    monkeypatch.setattr(_quotation_routes, "get_connection", raise_db_error)
    monkeypatch.setattr(_quotation_routes, "convert_docx_to_pdf", lambda docx_bytes, filename: b"%PDF-fake")

    res = client.post("/api/quotation/generate", json=VALID_PAYLOAD)
    assert res.status_code == 200
    assert len(res.content) > 0


def test_generate_passes_resolved_signature_to_render(client, monkeypatch, fake_db_state):
    _login_as(client, monkeypatch, STAFF)
    monkeypatch.setattr(_quotation_routes, "get_company", lambda company_id: FAKE_COMPANY)
    monkeypatch.setattr(_quotation_routes, "fetch_company_template_bytes", lambda current_user, company_id=None: _TEMPLATE_BYTES)
    monkeypatch.setattr(_quotation_routes, "fetch_company_logo_bytes", lambda current_user, company_id=None: None)
    monkeypatch.setattr(_quotation_routes, "fetch_template_version", lambda current_user, company_id: 1)
    monkeypatch.setattr(_quotation_routes, "fetch_master_excel_version", lambda current_user, company_id: None)
    monkeypatch.setattr(_quotation_routes, "convert_docx_to_pdf", lambda docx_bytes, filename: b"%PDF-fake")
    monkeypatch.setattr(_quotation_routes, "storage_upload", lambda bucket, path, content, media_type: None)

    captured = {}

    def fake_fetch_signature(current_user, company_id, signature_id):
        captured["company_id"] = company_id
        captured["signature_id"] = signature_id
        return {"image_bytes": None, "name": "Dr. Signer", "designation": "Director"}

    monkeypatch.setattr(_quotation_routes, "fetch_signature_for_render", fake_fetch_signature)

    payload = dict(VALID_PAYLOAD, signature_id="sig-1")
    res = client.post("/api/quotation/generate", json=payload)
    assert res.status_code == 200
    assert captured == {"company_id": "company-1", "signature_id": "sig-1"}

    insert_call = next(p for q, p in fake_db_state["executed"] if q.startswith("insert into quotations"))
    assert insert_call[7] == "sig-1"  # signature_id
    assert insert_call[8] == 1  # template_version
    assert insert_call[9] is None  # master_excel_version


def test_generate_without_signature_id_never_calls_signature_lookup(client, monkeypatch, fake_db_state):
    _login_as(client, monkeypatch, STAFF)
    monkeypatch.setattr(_quotation_routes, "get_company", lambda company_id: FAKE_COMPANY)
    monkeypatch.setattr(_quotation_routes, "fetch_company_template_bytes", lambda current_user, company_id=None: _TEMPLATE_BYTES)
    monkeypatch.setattr(_quotation_routes, "fetch_company_logo_bytes", lambda current_user, company_id=None: None)
    monkeypatch.setattr(_quotation_routes, "fetch_template_version", lambda current_user, company_id: 1)
    monkeypatch.setattr(_quotation_routes, "fetch_master_excel_version", lambda current_user, company_id: None)
    monkeypatch.setattr(_quotation_routes, "convert_docx_to_pdf", lambda docx_bytes, filename: b"%PDF-fake")
    monkeypatch.setattr(_quotation_routes, "storage_upload", lambda bucket, path, content, media_type: None)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("fetch_signature_for_render should not be called without a signature_id")

    monkeypatch.setattr(_quotation_routes, "fetch_signature_for_render", fail_if_called)

    res = client.post("/api/quotation/generate", json=VALID_PAYLOAD)
    assert res.status_code == 200

    insert_call = next(p for q, p in fake_db_state["executed"] if q.startswith("insert into quotations"))
    assert insert_call[7] is None  # signature_id


def test_history_query_scopes_to_own_quotations_for_staff(monkeypatch):
    state = {"executed": [], "counter": 0}
    monkeypatch.setattr(_quotation_history_routes, "get_connection", lambda **kwargs: _RecordingConnection(state))

    # Directly exercise the route function rather than going through the
    # HTTP layer, since we only care about the SQL shape it builds.
    # resolve_company_scope isn't mocked here because, for staff, the real
    # function never touches the DB - it just returns current_user.company_id.
    _quotation_history_routes.list_history.__wrapped__(
        company_id=None, customer=None, quote_number=None, staff_id=None, date_from=None, date_to=None, page=1,
        current_user=STAFF,
    )
    executed_queries = " ".join(q for q, _ in state["executed"])
    assert "q.created_by = %s" in executed_queries


class _FakeDownloadCursor:
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


class _FakeDownloadConnection:
    def __init__(self, row):
        self.row = row

    def cursor(self):
        return _FakeDownloadCursor(self.row)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_download_docx_logs_download_quotation_action(monkeypatch):
    row = {
        "id": "quote-1",
        "customer_name": "Test Customer",
        "quote_number": 1,
        "created_by": STAFF.id,
        "docx_storage_path": "path/to.docx",
        "pdf_storage_path": None,
    }
    monkeypatch.setattr(_quotation_history_routes, "get_connection", lambda **kwargs: _FakeDownloadConnection(row))
    monkeypatch.setattr(_quotation_history_routes, "resolve_company_scope", lambda current_user, requested: "company-1")
    monkeypatch.setattr(_quotation_history_routes, "storage_download", lambda bucket, path: b"docx-bytes")

    logged = {}

    def fake_log_action(current_user, company_id, action, entity_type, entity_id, request, metadata=None):
        logged.update(action=action, entity_type=entity_type, entity_id=entity_id, company_id=company_id)

    monkeypatch.setattr(_quotation_history_routes, "log_action", fake_log_action)

    class _FakeRequest:
        headers = {}
        client = None

    _quotation_history_routes.download_docx.__wrapped__(
        quotation_id="quote-1", request=_FakeRequest(), company_id="company-1", current_user=STAFF
    )

    assert logged == {"action": "download_quotation", "entity_type": "quotation", "entity_id": "quote-1", "company_id": "company-1"}


def test_history_query_does_not_scope_by_created_by_for_super_admin_without_staff_filter(monkeypatch):
    state = {"executed": [], "counter": 0}
    monkeypatch.setattr(_quotation_history_routes, "get_connection", lambda **kwargs: _RecordingConnection(state))
    # Unlike staff, a super_admin's resolve_company_scope call does hit the
    # DB to validate the company - mocked here since this test is about the
    # created_by scoping decision, not tenancy resolution (which has its
    # own dedicated tests).
    monkeypatch.setattr(_quotation_history_routes, "resolve_company_scope", lambda current_user, requested: "company-1")

    _quotation_history_routes.list_history.__wrapped__(
        company_id="company-1", customer=None, quote_number=None, staff_id=None, date_from=None, date_to=None, page=1,
        current_user=SUPER_ADMIN,
    )
    executed_queries = " ".join(q for q, _ in state["executed"])
    assert "q.created_by = %s" not in executed_queries
