from app.onboarding_merge import find_duplicate_product_groups, merge_company_field_candidates, product_dedup_key


def test_dedup_key_is_case_and_whitespace_insensitive():
    assert product_dedup_key(" Widget A ", "W1") == product_dedup_key("widget a", " w1 ")


def test_find_duplicate_product_groups_groups_matching_name_and_code():
    products = [
        {"product_name": "Widget A", "code": "W1"},
        {"product_name": "widget a", "code": "w1"},
        {"product_name": "Widget B", "code": "W2"},
    ]
    assert find_duplicate_product_groups(products) == [[0, 1]]


def test_find_duplicate_product_groups_treats_different_codes_as_distinct():
    # Same bare name, different codes (e.g. two pack sizes) - not a duplicate,
    # matching app/quotation.py::find_duplicate_products' own behavior.
    products = [
        {"product_name": "Widget", "code": "W1"},
        {"product_name": "Widget", "code": "W2"},
    ]
    assert find_duplicate_product_groups(products) == []


def test_find_duplicate_product_groups_ignores_blank_names():
    products = [{"product_name": "", "code": ""}, {"product_name": "", "code": ""}]
    assert find_duplicate_product_groups(products) == []


def test_find_duplicate_product_groups_handles_no_duplicates():
    products = [{"product_name": "A", "code": ""}, {"product_name": "B", "code": ""}]
    assert find_duplicate_product_groups(products) == []


def test_merge_company_field_candidates_prefers_higher_confidence():
    candidates = [
        {"field_name": "company_name", "value": "CleanTech Pvt Ltd", "confidence": 0.9, "source_document_id": "d1"},
        {"field_name": "company_name", "value": "CleanTech Pvt. Ltd.", "confidence": 0.95, "source_document_id": "d2"},
    ]
    merged = merge_company_field_candidates(candidates)
    assert merged["company_name"]["value"] == "CleanTech Pvt. Ltd."
    assert merged["company_name"]["source_document_id"] == "d2"


def test_merge_company_field_candidates_skips_null_values():
    candidates = [
        {"field_name": "email", "value": None, "confidence": 0, "source_document_id": "d1"},
        {"field_name": "email", "value": "info@example.com", "confidence": 0.6, "source_document_id": "d2"},
    ]
    merged = merge_company_field_candidates(candidates)
    assert merged["email"]["value"] == "info@example.com"


def test_merge_company_field_candidates_omits_fields_with_no_value():
    merged = merge_company_field_candidates([{"field_name": "website", "value": None, "confidence": 0, "source_document_id": "d1"}])
    assert "website" not in merged
