from app.normalizers import is_no_group_row, normalize_code, values_equal


def test_normalize_code_trims_and_uppercases():
    assert normalize_code(" ad00668 ") == "AD00668"


def test_normalize_code_case_insensitive_match():
    assert normalize_code("AD00668") == normalize_code("ad00668")


def test_normalize_code_leading_whitespace_matches():
    assert normalize_code("  AD00668") == normalize_code("AD00668")


def test_normalize_code_trailing_whitespace_matches():
    assert normalize_code("AD00668  ") == normalize_code("AD00668")


def test_normalize_code_internal_spaces_stay_distinct():
    assert normalize_code("HFILE") != normalize_code("H 00001")


def test_normalize_code_hyphen_preserved():
    assert normalize_code("021-55") == "021-55"
    assert normalize_code("25-69-345") == "25-69-345"


def test_normalize_code_blank_is_none():
    assert normalize_code("") is None
    assert normalize_code(None) is None
    assert normalize_code("   ") is None


def test_normalize_code_numeric_float_avoids_scientific_notation():
    assert normalize_code(626322.0) == "626322"


def test_is_no_group_row():
    assert is_no_group_row("No Group")
    assert is_no_group_row("no group")
    assert is_no_group_row(" NO GROUP ")
    assert not is_no_group_row("AD00668")


def test_numeric_equals_text():
    assert values_equal(4, "4")


def test_numeric_int_equals_float():
    assert values_equal(4, 4.0)


def test_negative_values_compare_correctly():
    assert values_equal(-8, -8)
    assert not values_equal(-8, 8)
    assert not values_equal(-8, 0)


def test_blank_equals_blank():
    assert values_equal(None, "")
    assert values_equal(None, None)
    assert values_equal("  ", None)


def test_blank_does_not_equal_zero():
    assert not values_equal(None, 0)
    assert not values_equal("", 0)


def test_text_values_trim_whitespace():
    assert values_equal(" abc ", "abc")


def test_text_values_preserve_internal_content():
    assert not values_equal("ab c", "abc")
