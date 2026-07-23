import pytest

from app.exceptions import UnknownCompanyError
from app.quotation_companies import get_company, list_companies


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
