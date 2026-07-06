import pytest

from app import comparator
from app.exceptions import NoComparableColumnsError, NoMatchingCodesError
from app.workbook_reader import load_sheet

from .factories import write_two_row_workbook


def _load(tmp_path, name, rows):
    path = tmp_path / name
    write_two_row_workbook(path, rows)
    return load_sheet(path, name)


def test_identical_rows_produce_no_differences(tmp_path):
    current = _load(tmp_path, "current.xlsx", [["AD00668", "AD AIR MOTER", "EA", 22, 2, 20, 4]])
    oms = _load(tmp_path, "oms.xlsx", [["AD00668", "AD AIR MOTER", "EA", 22, 2, 20, 4]])
    result = comparator.compare(current, oms)
    assert result.total_differences == 0
    assert result.total_field_differences == 0
    assert result.cell_differences == []


def test_single_column_difference_reported_with_old_and_new_value(tmp_path):
    current = _load(tmp_path, "current.xlsx", [["AD00668", "AD AIR MOTER", "EA", 22, 2, 20, 4]])
    oms = _load(tmp_path, "oms.xlsx", [["AD00668", "AD AIR MOTER", "EA", 22, 2, 20, 3]])
    result = comparator.compare(current, oms)
    assert result.total_differences == 1
    assert result.total_field_differences == 1
    diff = result.cell_differences[0]
    assert diff.code == "AD00668"
    assert diff.column == "Balance"
    assert diff.old_value == 4
    assert diff.new_value == 3


def test_multiple_changed_columns_all_reported_for_same_row(tmp_path):
    current = _load(tmp_path, "current.xlsx", [["AD00668", "AD AIR MOTER", "EA", 22, 2, 20, 4]])
    oms = _load(tmp_path, "oms.xlsx", [["AD00668", "NEW DESC", "EA", 22, 2, 22, 6]])
    result = comparator.compare(current, oms)
    assert result.total_differences == 1
    assert result.total_field_differences == 3
    changed_columns = {d.column for d in result.cell_differences}
    assert changed_columns == {"Description", "Delivered", "Balance"}
    by_column = {d.column: (d.old_value, d.new_value) for d in result.cell_differences}
    assert by_column["Description"] == ("AD AIR MOTER", "NEW DESC")
    assert by_column["Delivered"] == (20, 22)
    assert by_column["Balance"] == (4, 6)


def test_row_order_independent_matching(tmp_path):
    current = _load(
        tmp_path,
        "current.xlsx",
        [
            ["B00002", "Item B", "EA", 1, 1, 1, 1],
            ["A00001", "Item A", "EA", 5, 0, 0, 5],
        ],
    )
    oms = _load(
        tmp_path,
        "oms.xlsx",
        [
            ["A00001", "Item A", "EA", 5, 0, 0, 9],
            ["B00002", "Item B", "EA", 1, 1, 1, 1],
        ],
    )
    result = comparator.compare(current, oms)
    assert result.total_differences == 1
    assert result.cell_differences[0].code == "A00001"


def test_code_whitespace_and_case_still_match(tmp_path):
    current = _load(tmp_path, "current.xlsx", [["  ad00668  ", "Desc", "EA", 1, 1, 1, 1]])
    oms = _load(tmp_path, "oms.xlsx", [["AD00668", "Desc", "EA", 1, 1, 1, 2]])
    result = comparator.compare(current, oms)
    assert result.total_compared == 1
    assert result.total_differences == 1


def test_hyphenated_codes_match(tmp_path):
    current = _load(tmp_path, "current.xlsx", [["021-55", "Desc", "EA", 1, 1, 1, 1]])
    oms = _load(tmp_path, "oms.xlsx", [["021-55", "Desc", "EA", 1, 1, 1, 2]])
    result = comparator.compare(current, oms)
    assert result.total_differences == 1


def test_all_shared_columns_except_code_are_compared(tmp_path):
    current = _load(tmp_path, "current.xlsx", [["A1", "Desc", "EA", 1, 1, 1, 1]])
    oms = _load(tmp_path, "oms.xlsx", [["A1", "Desc", "EA", 9, 9, 9, 9]])
    result = comparator.compare(current, oms)
    assert set(result.compared_columns) == {
        "Description",
        "Unit",
        "Opening",
        "Received",
        "Delivered",
        "Balance",
    }
    assert "Code" not in result.compared_columns
    assert result.total_field_differences == 4  # Opening, Received, Delivered, Balance changed


def test_no_comparable_columns_raises(tmp_path):
    current_path = tmp_path / "current.xlsx"
    oms_path = tmp_path / "oms.xlsx"
    from .factories import write_simple_workbook

    write_simple_workbook(current_path, ["Code", "Foo"], [["A1", 1]])
    write_simple_workbook(oms_path, ["Code", "Bar"], [["A1", 2]])
    current = load_sheet(current_path, "Current File")
    oms = load_sheet(oms_path, "OMS File")
    with pytest.raises(NoComparableColumnsError):
        comparator.compare(current, oms)


def test_new_code_goes_to_new_codes(tmp_path):
    current = _load(tmp_path, "current.xlsx", [["A1", "Desc", "EA", 1, 1, 1, 1]])
    oms = _load(
        tmp_path,
        "oms.xlsx",
        [
            ["A1", "Desc", "EA", 1, 1, 1, 1],
            ["A2", "Desc2", "EA", 1, 1, 1, 1],
        ],
    )
    result = comparator.compare(current, oms)
    assert len(result.new_codes) == 1
    assert result.new_codes[0].code_key == "A2"


def test_missing_from_oms(tmp_path):
    current = _load(
        tmp_path,
        "current.xlsx",
        [
            ["A1", "Desc", "EA", 1, 1, 1, 1],
            ["A2", "Desc2", "EA", 1, 1, 1, 1],
        ],
    )
    oms = _load(tmp_path, "oms.xlsx", [["A1", "Desc", "EA", 1, 1, 1, 1]])
    result = comparator.compare(current, oms)
    assert len(result.missing_from_oms) == 1
    assert result.missing_from_oms[0].code_key == "A2"


def test_no_group_rows_ignored(tmp_path):
    current = _load(
        tmp_path,
        "current.xlsx",
        [
            ["No Group", "", "", "", "", "", ""],
            ["A1", "Desc", "EA", 1, 1, 1, 1],
        ],
    )
    oms = _load(tmp_path, "oms.xlsx", [["A1", "Desc", "EA", 1, 1, 1, 2]])
    result = comparator.compare(current, oms)
    assert result.total_compared == 1


def test_blank_rows_ignored(tmp_path):
    current = _load(
        tmp_path,
        "current.xlsx",
        [
            [None, None, None, None, None, None, None],
            ["A1", "Desc", "EA", 1, 1, 1, 1],
        ],
    )
    oms = _load(tmp_path, "oms.xlsx", [["A1", "Desc", "EA", 1, 1, 1, 2]])
    result = comparator.compare(current, oms)
    assert result.total_compared == 1


def test_duplicate_codes_detected_and_excluded(tmp_path):
    current = _load(tmp_path, "current.xlsx", [["A1", "Desc", "EA", 1, 1, 1, 1]])
    oms = _load(
        tmp_path,
        "oms.xlsx",
        [
            ["A1", "Desc", "EA", 1, 1, 1, 1],
            ["A1", "Desc dup", "EA", 1, 1, 1, 2],
        ],
    )
    result = comparator.compare(current, oms)
    assert any("A1" in w for w in result.duplicate_warnings)
    assert result.total_compared == 0
    assert result.cell_differences == []
    assert result.changed_rows == []
    assert result.new_codes == []
    assert result.missing_from_oms == []


def test_no_matching_codes_raises(tmp_path):
    current = _load(tmp_path, "current.xlsx", [])
    oms = _load(tmp_path, "oms.xlsx", [])
    with pytest.raises(NoMatchingCodesError):
        comparator.compare(current, oms)
