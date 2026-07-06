"""Writes the comparison result workbook, copying rows and styling directly
from the source worksheets so complete OMS rows are preserved byte-for-byte
rather than reconstructed from selected fields."""
import logging
from copy import copy
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)


def _copy_row(dest_ws, dest_row, src_ws, src_row, num_cols):
    for col in range(1, num_cols + 1):
        src_cell = src_ws.cell(row=src_row, column=col)
        dest_cell = dest_ws.cell(row=dest_row, column=col, value=src_cell.value)
        if src_cell.has_style:
            # openpyxl wraps font/fill/border/alignment in a StyleProxy that
            # is not hashable; copy() unwraps it to the real style object
            # before assigning to another cell.
            dest_cell.font = copy(src_cell.font)
            dest_cell.border = copy(src_cell.border)
            dest_cell.fill = copy(src_cell.fill)
            dest_cell.alignment = copy(src_cell.alignment)
            dest_cell.number_format = src_cell.number_format


def _copy_presentation(dest_ws, src_ws, num_cols):
    for col in range(1, num_cols + 1):
        letter = get_column_letter(col)
        src_dim = src_ws.column_dimensions.get(letter)
        if src_dim and src_dim.width:
            dest_ws.column_dimensions[letter].width = src_dim.width
    if src_ws.freeze_panes:
        dest_ws.freeze_panes = src_ws.freeze_panes


def _write_sheet(dest_ws, source_sheet, row_records):
    num_cols = source_sheet.num_columns
    for offset in range(source_sheet.header_row_count):
        dest_r = offset + 1
        src_r = source_sheet.header_row_start + offset
        _copy_row(dest_ws, dest_r, source_sheet.worksheet, src_r, num_cols)

    dest_row = source_sheet.header_row_count + 1
    for row in row_records:
        _copy_row(dest_ws, dest_row, source_sheet.worksheet, row.excel_row_index, num_cols)
        dest_row += 1

    _copy_presentation(dest_ws, source_sheet.worksheet, num_cols)


def _write_field_changes_sheet(dest_ws, cell_differences):
    dest_ws.append(["Code", "Column", "Old Value (Current File)", "New Value (OMS File)"])
    for cell in dest_ws[1]:
        cell.font = Font(bold=True)
    for diff in cell_differences:
        dest_ws.append([diff.code, diff.column, diff.old_value, diff.new_value])


def write_result(output_path, current_sheet, oms_sheet, result):
    """Write FIELD_CHANGES + DIFFERENCES (+ NEW_CODES, + MISSING_FROM_OMS if
    any) to output_path."""
    wb = Workbook()

    ws_fields = wb.active
    ws_fields.title = "FIELD_CHANGES"
    _write_field_changes_sheet(ws_fields, result.cell_differences)

    ws_diff = wb.create_sheet("DIFFERENCES")
    _write_sheet(ws_diff, oms_sheet, result.changed_rows)

    ws_new = wb.create_sheet("NEW_CODES")
    _write_sheet(ws_new, oms_sheet, result.new_codes)

    if result.missing_from_oms:
        ws_missing = wb.create_sheet("MISSING_FROM_OMS")
        _write_sheet(ws_missing, current_sheet, result.missing_from_oms)

    output_path = Path(output_path)
    wb.save(str(output_path))
    logger.info("Wrote comparison result to %s", output_path)
    return output_path


def default_output_filename():
    date_str = datetime.now().strftime("%Y-%m-%d")
    return f"Garg_Dental_Comparison_{date_str}.xlsx"
