"""Tests for the audit logging helper itself. The "does every mutating
route actually call log_action with the right action/entity_type" property
is exercised implicitly by test_auth.py/test_master_excel_routes.py/
test_quotation_persistence.py's existing fixtures (none of them mock
_audit.log_action, so its real implementation runs against a fake/failing
DB connection and is swallowed - see those files' fixtures). This file
covers log_action's own contract in isolation: it builds the right insert,
and never raises even when the DB call fails."""
import os

os.environ.setdefault("SESSION_SECRET", "test-session-secret")

import _audit
import _auth


class _RecordingCursor:
    def __init__(self, state):
        self.state = state

    def execute(self, query, params=None):
        self.state.append((" ".join(query.split()), params))

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


class _FakeRequest:
    def __init__(self, headers=None, client_host="127.0.0.1"):
        self.headers = headers or {}

        class _Client:
            host = client_host

        self.client = _Client()


USER = _auth.CurrentUser(id="user-1", company_id="company-1", username="staff", full_name="Staff", role="staff", active=True)


def test_log_action_writes_expected_row(monkeypatch):
    state = []
    monkeypatch.setattr(_audit, "get_connection", lambda **kwargs: _RecordingConnection(state))

    _audit.log_action(USER, USER.company_id, "create_quotation", "quotation", "quote-1", _FakeRequest(), {"quote_number": 5})

    assert len(state) == 1
    query, params = state[0]
    assert query.startswith("insert into audit_logs")
    assert params[0] == USER.company_id
    assert params[1] == USER.id
    assert params[2] == "create_quotation"
    assert params[3] == "quotation"
    assert params[4] == "quote-1"


def test_log_action_uses_x_forwarded_for_when_present(monkeypatch):
    state = []
    monkeypatch.setattr(_audit, "get_connection", lambda **kwargs: _RecordingConnection(state))

    request = _FakeRequest(headers={"x-forwarded-for": "203.0.113.5, 10.0.0.1"})
    _audit.log_action(USER, USER.company_id, "login", "user", USER.id, request)

    _, params = state[0]
    assert params[5] == "203.0.113.5"


def test_log_action_never_raises_when_db_fails(monkeypatch):
    def raise_error(**kwargs):
        raise RuntimeError("DB unreachable")

    monkeypatch.setattr(_audit, "get_connection", raise_error)

    # Must not raise - a broken audit write must never break the caller's
    # already-succeeded primary action.
    _audit.log_action(USER, USER.company_id, "login", "user", USER.id, _FakeRequest())
