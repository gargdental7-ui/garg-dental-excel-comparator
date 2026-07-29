import pytest

from app.exceptions import CompanyDataUnavailableError, UnknownCompanyError
from app.quotation_companies import _load_from_db, get_company, get_company_by_slug, list_companies

import _db


def test_get_company_by_slug_returns_garg_dental():
    company = get_company_by_slug("garg_dental")
    assert company.display_name == "Garg Dental Pvt. Ltd"
    assert company.template_filename == "equipment_proposal_garg_dental.docx"
    assert len(company.terms_and_conditions) > 0


def test_get_company_by_id_matches_slug_lookup():
    by_slug = get_company_by_slug("garg_dental")
    by_id = get_company(by_slug.id)
    assert by_id.slug == "garg_dental"
    assert by_id.display_name == by_slug.display_name


def test_get_company_unknown_id_raises():
    with pytest.raises(UnknownCompanyError):
        get_company("not-a-real-company-id")


def test_get_company_by_slug_unknown_raises():
    with pytest.raises(UnknownCompanyError):
        get_company_by_slug("not_a_real_slug")


def test_list_companies_includes_garg_dental():
    slugs = [c.slug for c in list_companies()]
    assert "garg_dental" in slugs


def test_load_from_db_returns_none_when_not_configured(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert _load_from_db() is None


def test_load_from_db_returns_none_instead_of_raising_when_unreachable(monkeypatch):
    # Points at a valid-looking but unreachable Postgres instance - proves
    # _load_from_db() itself degrades to None rather than raising, even
    # when the DB is configured but the connection fails, not just unset.
    # _db._pool is a cached module-level singleton (by design - a real
    # process shouldn't reopen its pool per request), so it has to be reset
    # here or this test would silently reuse whatever real pool an earlier
    # test already created against the real DATABASE_URL. monkeypatch
    # restores the original value automatically after this test.
    monkeypatch.setattr(_db, "_pool", None)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@127.0.0.1:1/nonexistent")
    assert _load_from_db() is None


def test_get_company_raises_clear_error_when_db_unreachable(monkeypatch):
    # The public API no longer silently falls back to stale hardcoded data
    # when the DB can't be reached - with real multi-tenant companies,
    # there's no single hardcoded profile that could stand in for
    # "whichever company was actually being asked for."
    import app.quotation_companies as quotation_companies

    monkeypatch.setattr(quotation_companies, "_cache", None)
    monkeypatch.setattr(quotation_companies, "_load_from_db", lambda: None)
    with pytest.raises(CompanyDataUnavailableError):
        get_company("any-id")
