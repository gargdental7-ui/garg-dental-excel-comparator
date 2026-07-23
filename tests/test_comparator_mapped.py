import pytest

from app import comparator
from app.comparator import ADDED, CHANGED, REMOVED, UNCHANGED, ColumnMapping
from app.exceptions import NoColumnMappingError, NoMatchingCodesError
from app.workbook_reader import load_sheet

from .factories import write_simple_workbook


def _load(tmp_path, name, headers, rows):
    path = tmp_path / name
    write_simple_workbook(path, headers, rows)
    return load_sheet(path, name)


def test_maps_differently_named_columns(tmp_path):
    current = _load(tmp_path, "current.xlsx", ["Code", "Balance", "Price"], [["A1", 10, 100]])
    oms = _load(tmp_path, "oms.xlsx", ["Code", "Available Stock", "Selling Price"], [["A1", 10, 120]])
    mappings = [
        ColumnMapping(current_column="Balance", latest_column="Available Stock"),
        ColumnMapping(current_column="Price", latest_column="Selling Price"),
    ]
    result = comparator.compare_mapped(current, oms, mappings)
    assert result.total_compared == 1
    assert result.total_changed == 1
    row = result.rows[0]
    assert row.status == CHANGED
    assert row.changed_field_labels == ["Price"]
    balance_field = row.fields[0]
    assert balance_field.current_value == 10
    assert balance_field.latest_value == 10
    assert balance_field.changed is False
    price_field = row.fields[1]
    assert price_field.current_value == 100
    assert price_field.latest_value == 120
    assert price_field.changed is True


def test_unchanged_row_when_all_mapped_fields_match(tmp_path):
    current = _load(tmp_path, "current.xlsx", ["Code", "Balance"], [["A1", 10]])
    oms = _load(tmp_path, "oms.xlsx", ["Code", "Stock"], [["A1", 10]])
    mappings = [ColumnMapping(current_column="Balance", latest_column="Stock")]
    result = comparator.compare_mapped(current, oms, mappings)
    assert result.total_changed == 0
    assert result.total_unchanged == 1
    assert result.rows[0].status == UNCHANGED
    assert result.rows[0].changed_field_labels == []


def test_added_product_classified_correctly(tmp_path):
    current = _load(tmp_path, "current.xlsx", ["Code", "Balance"], [["A1", 10]])
    oms = _load(tmp_path, "oms.xlsx", ["Code", "Balance"], [["A1", 10], ["B2", 5]])
    mappings = [ColumnMapping(current_column="Balance", latest_column="Balance")]
    result = comparator.compare_mapped(current, oms, mappings)
    assert result.total_added == 1
    assert result.added[0].code == "B2"
    assert result.added[0].status == ADDED
    assert result.added[0].fields[0].current_value is None
    assert result.added[0].fields[0].latest_value == 5
    assert result.added[0].fields[0].missing is True


def test_removed_product_classified_correctly(tmp_path):
    current = _load(tmp_path, "current.xlsx", ["Code", "Balance"], [["A1", 10], ["B2", 5]])
    oms = _load(tmp_path, "oms.xlsx", ["Code", "Balance"], [["A1", 10]])
    mappings = [ColumnMapping(current_column="Balance", latest_column="Balance")]
    result = comparator.compare_mapped(current, oms, mappings)
    assert result.total_removed == 1
    assert result.removed[0].code == "B2"
    assert result.removed[0].status == REMOVED
    assert result.removed[0].fields[0].current_value == 5
    assert result.removed[0].fields[0].latest_value is None


def test_missing_value_flagged_even_when_not_changed(tmp_path):
    current = _load(tmp_path, "current.xlsx", ["Code", "Notes"], [["A1", None]])
    oms = _load(tmp_path, "oms.xlsx", ["Code", "Remarks"], [["A1", None]])
    mappings = [ColumnMapping(current_column="Notes", latest_column="Remarks")]
    result = comparator.compare_mapped(current, oms, mappings)
    field = result.rows[0].fields[0]
    assert field.changed is False
    assert field.missing is True


def test_empty_mappings_raises():
    with pytest.raises(NoColumnMappingError):
        comparator.compare_mapped(object(), object(), [])


def test_no_matching_codes_raises(tmp_path):
    current = _load(tmp_path, "current.xlsx", ["Code", "Balance"], [])
    oms = _load(tmp_path, "oms.xlsx", ["Code", "Balance"], [])
    mappings = [ColumnMapping(current_column="Balance", latest_column="Balance")]
    with pytest.raises(NoMatchingCodesError):
        comparator.compare_mapped(current, oms, mappings)


def test_duplicate_codes_excluded_with_warning(tmp_path):
    current = _load(tmp_path, "current.xlsx", ["Code", "Balance"], [["A1", 10], ["A1", 20]])
    oms = _load(tmp_path, "oms.xlsx", ["Code", "Balance"], [["A1", 10]])
    mappings = [ColumnMapping(current_column="Balance", latest_column="Balance")]
    result = comparator.compare_mapped(current, oms, mappings)
    assert result.total_compared == 0
    assert len(result.duplicate_warnings) == 1
    assert "A1" in result.duplicate_warnings[0]
