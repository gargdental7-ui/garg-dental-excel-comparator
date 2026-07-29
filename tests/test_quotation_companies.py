import pytest

from app.exceptions import UnknownCompanyError
from app.quotation_companies import _load_from_db, get_company, list_companies

import _db


def test_get_company_returns_garg_dental():
    company = get_company("garg_dental")
    assert company.display_name == "Garg Dental Pvt. Ltd"
    assert company.template_filename == "equipment_proposal_garg_dental.docx"
    assert len(company.terms_and_conditions) > 0


def test_get_company_unknown_id_raises():
    with pytest.raises(UnknownCompanyError):
        get_company("not_a_real_company")


def test_list_companies_includes_garg_dental():
    ids = [c.id for c in list_companies()]
    assert "garg_dental" in ids


def test_load_from_db_returns_none_when_not_configured(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert _load_from_db() is None


def test_load_from_db_returns_none_instead_of_raising_when_unreachable(monkeypatch):
    # Points at a valid-looking but unreachable Postgres instance - proves
    # the fallback-to-hardcoded-defaults contract holds even when the DB is
    # configured but the connection itself fails, not just when it's unset.
    # _db._pool is a cached module-level singleton (by design - a real
    # process shouldn't reopen its pool per request), so it has to be reset
    # here or this test would silently reuse whatever real pool an earlier
    # test already created against the real DATABASE_URL. monkeypatch
    # restores the original value automatically after this test.
    monkeypatch.setattr(_db, "_pool", None)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@127.0.0.1:1/nonexistent")
    assert _load_from_db() is None
