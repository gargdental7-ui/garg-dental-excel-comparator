import openpyxl
import pytest

from app import generic_excel
from app.exceptions import GenericHeaderDetectionError


def _wb_from_rows(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    return wb


def test_simple_single_row_header_detected():
    wb = _wb_from_rows(
        [
            ["Customer", "Outstanding Amount", "Days Overdue"],
            ["Acme Dental", 5000, 45],
            ["Best Smiles", 12000, 10],
        ]
    )
    data = generic_excel.load_generic_sheet(wb, "Sheet", "Test File")
    assert data.headers == ["Customer", "Outstanding Amount", "Days Overdue"]
    assert data.header_row_count == 1
    assert len(data.rows) == 2
    assert data.rows[0]["Customer"] == "Acme Dental"


def test_header_after_report_title_block_detected():
    wb = _wb_from_rows(
        [
            ["Garg Dental Pvt. Ltd. - Outstanding Report"],
            ["Date From: 01/04/2082 To: 32/03/2083"],
            [],
            ["Customer", "Outstanding Amount", "Due Date"],
            ["Acme Dental", 5000, "2026-01-01"],
        ]
    )
    data = generic_excel.load_generic_sheet(wb, "Sheet", "Test File")
    assert data.headers == ["Customer", "Outstanding Amount", "Due Date"]
    assert data.header_row_start == 4
    assert len(data.rows) == 1


def test_known_garg_two_row_header_detected():
    wb = _wb_from_rows(
        [
            ["FY : 01/04/2082-32/03/2083"],
            [],
            ["Code", "Description", "Unit", "Opening", "Received", "Delivered", "Balance"],
            [None, None, None, "Qty", "Qty", "Qty", "Qty"],
            ["AD00668", "AD AIR MOTER", "EA", 22, 2, 20, 4],
        ]
    )
    data = generic_excel.load_generic_sheet(wb, "Sheet", "Test File")
    assert data.headers == ["Code", "Description", "Unit", "Opening", "Received", "Delivered", "Balance"]
    assert data.header_row_count == 2
    assert len(data.rows) == 1
    assert data.rows[0]["Code"] == "AD00668"


def test_blank_rows_between_header_and_data_are_skipped():
    wb = _wb_from_rows(
        [
            ["Customer", "Outstanding Amount"],
            [None, None],
            ["Acme Dental", 5000],
        ]
    )
    data = generic_excel.load_generic_sheet(wb, "Sheet", "Test File")
    assert len(data.rows) == 1


def test_duplicate_headers_are_deduped():
    wb = _wb_from_rows(
        [
            ["Customer", "Amount", "Amount"],
            ["Acme Dental", 100, 200],
        ]
    )
    data = generic_excel.load_generic_sheet(wb, "Sheet", "Test File")
    assert data.headers == ["Customer", "Amount", "Amount (2)"]


def test_trailing_blank_header_column_is_trimmed():
    wb = _wb_from_rows(
        [
            ["Customer", "Amount", None],
            ["Acme Dental", 100, "ignored"],
        ]
    )
    data = generic_excel.load_generic_sheet(wb, "Sheet", "Test File")
    assert data.headers == ["Customer", "Amount"]


def test_no_header_row_raises():
    wb = _wb_from_rows([[None, None], [None, None]])
    with pytest.raises(GenericHeaderDetectionError):
        generic_excel.load_generic_sheet(wb, "Sheet", "Test File")


def test_multiple_sheets_listed():
    wb = _wb_from_rows([["Customer", "Amount"], ["A", 1]])
    wb.create_sheet("Second")
    assert wb.sheetnames == ["Sheet", "Second"]
