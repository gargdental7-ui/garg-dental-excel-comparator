"""Detects single-row and known two-row header layouts used in Garg Dental reports."""
from dataclasses import dataclass

from .exceptions import CodeColumnNotFoundError, HeaderDetectionError


MAX_HEADER_SCAN_ROWS = 50


@dataclass
class HeaderInfo:
    header_row_start: int
    header_row_count: int
    headers: list
    num_columns: int


def _clean(value):
    if value is None:
        return ""
    return str(value).strip()


def _row_values(ws, row_idx, max_col):
    return [ws.cell(row=row_idx, column=c).value for c in range(1, max_col + 1)]


def _find_header_row(ws, max_col):
    """Locate the row holding the real column names by scanning for a cell
    that reads exactly "Code". Garg Dental reports often prepend a report
    title block (company name, date range, filters) of a few blank/label
    rows before the actual header row, so it cannot be assumed to be row 1."""
    scan_limit = min(ws.max_row, MAX_HEADER_SCAN_ROWS)
    for row_idx in range(1, scan_limit + 1):
        row_clean = [_clean(v) for v in _row_values(ws, row_idx, max_col)]
        if any(h.lower() == "code" for h in row_clean):
            return row_idx, row_clean
    return None, None


def detect_header(ws, file_label):
    """Identify the header row(s) and the primary selectable column names.

    The header row holds the real column names (Code, Description, Balance,
    ...) but may be preceded by a report title block. Some Garg Dental
    reports also add a second row of unit sub-labels (e.g. "Qty") under the
    numeric columns while leaving it blank under Code - that is treated as a
    two-row header, with the detected row remaining the selectable names.
    """
    if ws.max_row == 0 or ws.max_column == 0:
        raise HeaderDetectionError(file_label)

    max_col = ws.max_column
    header_row_start, row1_clean = _find_header_row(ws, max_col)

    if header_row_start is None:
        raise CodeColumnNotFoundError(file_label)

    # Trim trailing blank header columns so we don't drag empty columns along.
    last_named = 0
    for i, h in enumerate(row1_clean, start=1):
        if h:
            last_named = i
    max_col = last_named
    row1_clean = row1_clean[:max_col]

    header_row_count = 1
    next_row_idx = header_row_start + 1
    if ws.max_row >= next_row_idx:
        code_col_index = next(i for i, h in enumerate(row1_clean) if h.lower() == "code")
        row2_clean = [_clean(v) for v in _row_values(ws, next_row_idx, max_col)]
        row2_code_cell = row2_clean[code_col_index] if code_col_index < len(row2_clean) else ""
        row2_has_content = any(row2_clean)
        if row2_has_content and row2_code_cell == "":
            header_row_count = 2

    return HeaderInfo(
        header_row_start=header_row_start,
        header_row_count=header_row_count,
        headers=row1_clean,
        num_columns=max_col,
    )
