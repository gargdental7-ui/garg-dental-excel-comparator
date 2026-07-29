"""Auth/authorization checks for the Master Excel routes, plus the
regression check that matters most for this feature: a company_master
excel_source produces identical inspect_products output to the exact same
bytes uploaded the old way (see server/_quotation_routes.py's
_resolve_excel_path, which is the whole point of this feature reusing
open_workbook unmodified)."""
import os

import bcrypt
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SESSION_SECRET", "test-session-secret")

import _auth
import _master_excel_routes
import _quotation_routes
import index

from .factories import write_simple_workbook

ADMIN = _auth.CurrentUser(id="admin-1", company_id="company-1", username="admin", full_name="Admin", role="admin", active=True)
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
            "password_hash": "x",
        },
    )
    monkeypatch.setattr(bcrypt, "checkpw", lambda password, hashed: True)
    monkeypatch.setattr(_auth, "_load_user_by_id", lambda user_id: user if user_id == user.id else None)
    res = client.post("/api/auth/login", json={"username": user.username, "password": "whatever"})
    assert res.status_code == 200


def _sample_xlsx_bytes(tmp_path) -> bytes:
    path = tmp_path / "sample.xlsx"
    write_simple_workbook(
        path,
        headers=["Product Name", "Price"],
        data_rows=[["Autoclave", 1200], ["X-Ray Sensor", 3400]],
    )
    return path.read_bytes()


def test_get_metadata_requires_auth(client):
    res = client.get("/api/master-excel")
    assert res.status_code == 401


def test_upload_requires_admin(client, monkeypatch):
    _login_as(client, monkeypatch, STAFF)
    res = client.put("/api/master-excel", files={"file": ("x.xlsx", b"irrelevant")})
    assert res.status_code == 403


def test_delete_requires_admin(client, monkeypatch):
    _login_as(client, monkeypatch, STAFF)
    res = client.delete("/api/master-excel")
    assert res.status_code == 403


def test_download_requires_admin(client, monkeypatch):
    _login_as(client, monkeypatch, STAFF)
    res = client.get("/api/master-excel/download")
    assert res.status_code == 403


def test_company_master_source_matches_direct_upload(client, monkeypatch, tmp_path):
    """The regression check: feed the same bytes through excel_source=upload
    vs excel_source=company_master and confirm inspect_products returns the
    same headers/row_count - proving the master-Excel path doesn't diverge
    from the existing, unmodified open_workbook pipeline."""
    _login_as(client, monkeypatch, STAFF)
    content = _sample_xlsx_bytes(tmp_path)

    upload_res = client.post(
        "/api/quotation/products/inspect",
        data={"excel_source": "upload"},
        files={"file": ("products.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload_res.status_code == 200
    upload_body = upload_res.json()

    monkeypatch.setattr(_quotation_routes, "fetch_master_excel_bytes", lambda current_user: content)
    master_res = client.post("/api/quotation/products/inspect", data={"excel_source": "company_master"})
    assert master_res.status_code == 200
    master_body = master_res.json()

    assert master_body["headers"] == upload_body["headers"]
    assert master_body["row_count"] == upload_body["row_count"]
    assert master_body["suggested_mapping"] == upload_body["suggested_mapping"]


def test_company_master_source_without_one_uploaded_gives_clear_error(client, monkeypatch):
    _login_as(client, monkeypatch, STAFF)

    def raise_no_master(current_user):
        from app.exceptions import NoMasterExcelError

        raise NoMasterExcelError()

    monkeypatch.setattr(_quotation_routes, "fetch_master_excel_bytes", raise_no_master)
    res = client.post("/api/quotation/products/inspect", data={"excel_source": "company_master"})
    assert res.status_code == 400
    assert "No Company Master Excel" in res.json()["detail"]["message"]


def test_upload_source_without_file_gives_clear_error(client, monkeypatch):
    _login_as(client, monkeypatch, STAFF)
    res = client.post("/api/quotation/products/inspect", data={"excel_source": "upload"})
    assert res.status_code == 400
