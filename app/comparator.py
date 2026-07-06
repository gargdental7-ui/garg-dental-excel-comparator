"""Core comparison logic: match rows by Code, compare every shared column.

Matching is dictionary-based (O(n + m)) - no nested loops. Every column
shared by both files (other than Code) is compared; a matched row is
included if any of those columns differ, and each differing column is
reported individually with its Current File (old) and OMS File (new) value.
"""
import logging
from dataclasses import dataclass, field

from .exceptions import NoComparableColumnsError, NoMatchingCodesError
from .normalizers import values_equal

logger = logging.getLogger(__name__)


@dataclass
class CellDifference:
    code: str
    column: str
    excel_row_index: int
    old_value: object
    new_value: object


@dataclass
class ComparisonResult:
    cell_differences: list
    changed_rows: list
    new_codes: list
    missing_from_oms: list
    compared_columns: list
    duplicate_warnings: list = field(default_factory=list)
    total_compared: int = 0
    total_differences: int = 0
    total_field_differences: int = 0


def find_shared_columns(current_headers, oms_headers):
    """Columns present in both files (case-insensitive, trimmed), in OMS order."""
    current_lookup = {h.strip().lower() for h in current_headers if h.strip()}
    return [h for h in oms_headers if h.strip() and h.strip().lower() in current_lookup]


def _resolve_column_index(headers, target_lower):
    for i, h in enumerate(headers):
        if h.strip().lower() == target_lower:
            return i
    return None


def _index_rows_by_code(rows):
    by_code = {}
    duplicates = set()
    for row in rows:
        if row.code_key in by_code:
            duplicates.add(row.code_key)
        else:
            by_code[row.code_key] = row
    for dup in duplicates:
        by_code.pop(dup, None)
    return by_code, duplicates


def compare(current, oms):
    """Compare `current` and `oms` on every column they share except Code.

    Returns a ComparisonResult listing every changed field individually.
    Raises NoComparableColumnsError if the files share no columns besides
    Code, or NoMatchingCodesError if they share no product Codes at all.
    """
    shared = find_shared_columns(current.headers, oms.headers)
    compare_columns = [c for c in shared if c.strip().lower() != "code"]
    if not compare_columns:
        raise NoComparableColumnsError()

    oms_indexes = {col: _resolve_column_index(oms.headers, col.strip().lower()) for col in compare_columns}
    current_indexes = {
        col: _resolve_column_index(current.headers, col.strip().lower()) for col in compare_columns
    }

    current_by_code, current_dupes = _index_rows_by_code(current.rows)
    oms_by_code, oms_dupes = _index_rows_by_code(oms.rows)
    excluded = current_dupes | oms_dupes

    warnings = []
    for code in sorted(current_dupes):
        warnings.append(f'Duplicate Code "{code}" found in the Current File. These rows were skipped.')
    for code in sorted(oms_dupes):
        warnings.append(f'Duplicate Code "{code}" found in the OMS File. These rows were skipped.')

    cell_differences = []
    changed_rows = []
    new_codes = []
    total_compared = 0

    for code, oms_row in oms_by_code.items():
        if code in excluded:
            continue
        current_row = current_by_code.get(code)
        if current_row is None:
            new_codes.append(oms_row)
            continue
        total_compared += 1
        row_changed = False
        for col in compare_columns:
            c_idx = current_indexes[col]
            o_idx = oms_indexes[col]
            current_val = current_row.values[c_idx] if c_idx < len(current_row.values) else None
            oms_val = oms_row.values[o_idx] if o_idx < len(oms_row.values) else None
            if not values_equal(current_val, oms_val):
                cell_differences.append(
                    CellDifference(
                        code=code,
                        column=oms.headers[o_idx],
                        excel_row_index=oms_row.excel_row_index,
                        old_value=current_val,
                        new_value=oms_val,
                    )
                )
                row_changed = True
        if row_changed:
            changed_rows.append(oms_row)

    missing_from_oms = [
        row for code, row in current_by_code.items()
        if code not in oms_by_code and code not in excluded
    ]

    if total_compared == 0 and not new_codes and not missing_from_oms and not warnings:
        raise NoMatchingCodesError()

    changed_rows.sort(key=lambda r: r.excel_row_index)
    new_codes.sort(key=lambda r: r.excel_row_index)
    missing_from_oms.sort(key=lambda r: r.excel_row_index)

    if warnings:
        logger.warning("Duplicate codes detected: %s", "; ".join(warnings))

    return ComparisonResult(
        cell_differences=cell_differences,
        changed_rows=changed_rows,
        new_codes=new_codes,
        missing_from_oms=missing_from_oms,
        compared_columns=compare_columns,
        duplicate_warnings=warnings,
        total_compared=total_compared,
        total_differences=len(changed_rows),
        total_field_differences=len(cell_differences),
    )
