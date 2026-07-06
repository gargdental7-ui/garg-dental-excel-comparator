import openpyxl
import pytest

from app.exceptions import CodeColumnNotFoundError
from app.header_detector import detect_header


def _ws_from_rows(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    return ws


def test_single_row_header_detected():
    ws = _ws_from_rows(
        [
            ["Code", "Description", "Balance"],
            ["AD00668", "AD AIR MOTER", 4],
        ]
    )
    info = detect_header(ws, "Test File")
    assert info.header_row_count == 1
    assert info.headers == ["Code", "Description", "Balance"]


def test_two_row_header_detected():
    ws = _ws_from_rows(
        [
            ["Code", "Description", "Unit", "Opening", "Received", "Delivered", "Balance"],
            [None, None, None, "Qty", "Qty", "Qty", "Qty"],
            ["AD00668", "AD AIR MOTER", "EA", 22, 2, 20, 4],
        ]
    )
    info = detect_header(ws, "Test File")
    assert info.header_row_count == 2
    assert info.headers == ["Code", "Description", "Unit", "Opening", "Received", "Delivered", "Balance"]


def test_balance_selectable_after_two_row_header():
    ws = _ws_from_rows(
        [
            ["Code", "Description", "Unit", "Opening", "Received", "Delivered", "Balance"],
            [None, None, None, "Qty", "Qty", "Qty", "Qty"],
            ["AD00668", "AD AIR MOTER", "EA", 22, 2, 20, 4],
        ]
    )
    info = detect_header(ws, "Test File")
    assert "Balance" in info.headers


def test_missing_code_column_raises():
    ws = _ws_from_rows(
        [
            ["Item", "Description"],
            ["AD00668", "AD AIR MOTER"],
        ]
    )
    with pytest.raises(CodeColumnNotFoundError):
        detect_header(ws, "Test File")


def test_second_row_of_real_data_is_not_treated_as_header():
    ws = _ws_from_rows(
        [
            ["Code", "Description", "Balance"],
            ["AD00668", "AD AIR MOTER", 4],
            ["AI00001", "AIR PIPE", 2],
        ]
    )
    info = detect_header(ws, "Test File")
    assert info.header_row_count == 1


def test_header_after_report_title_block_is_detected():
    ws = _ws_from_rows(
        [
            [None, None, None],
            ["FY : 01/04/2082-32/03/2083", None, None],
            [None, None, None],
            ["Garg Dental Pvt. Ltd. F/Y 82-83", None, None],
            ["Stock Ledger With Value - Product Group Wise", None, None],
            [None, None, None],
            ["Code", "Description", "Balance"],
            ["AD00668", "AD AIR MOTER", 4],
        ]
    )
    info = detect_header(ws, "Test File")
    assert info.header_row_start == 7
    assert info.header_row_count == 1
    assert info.headers == ["Code", "Description", "Balance"]


def test_two_row_header_after_report_title_block_is_detected():
    ws = _ws_from_rows(
        [
            [None, None, None, None],
            ["Garg Dental Pvt. Ltd. F/Y 82-83", None, None, None],
            [None, None, None, None],
            ["Code", "Description", "Delivered", "Balance"],
            [None, None, "Qty", "Qty"],
            ["AD00668", "AD AIR MOTER", 20, 4],
        ]
    )
    info = detect_header(ws, "Test File")
    assert info.header_row_start == 4
    assert info.header_row_count == 2
