"""Safe, predictable normalization rules for product Codes and comparison values."""
from decimal import Decimal, InvalidOperation

_BLANK = object()
_MAX_SAFE_INT_FLOAT = 1e15


def _is_blank(value):
    return value is None or (isinstance(value, str) and value.strip() == "")


def stringify_code(value):
    """Render a cell value as a display-safe string, avoiding scientific notation
    for whole numbers Excel may have coerced (e.g. 626322.0 -> "626322")."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if value.is_integer() and abs(value) < _MAX_SAFE_INT_FLOAT:
            return str(int(value))
        return format(value, "f").rstrip("0").rstrip(".")
    if isinstance(value, int):
        return str(value)
    return str(value)


def normalize_code(value):
    """Return the matching key for a Code cell: trimmed, case-insensitive.
    Internal spaces and hyphens are preserved so distinct codes stay distinct.
    Returns None for blank/missing codes."""
    text = stringify_code(value).strip()
    if text == "":
        return None
    return text.upper()


def is_no_group_row(code_text):
    """True for grouping/summary rows (e.g. "No Group") that are not real products."""
    return code_text is not None and code_text.strip().upper() == "NO GROUP"


def normalize_value(value):
    """Normalize a comparison-column value so numeric 4, 4.0 and text "4" are
    equal, blanks equal only other blanks, and text is trimmed but otherwise
    left untouched."""
    if _is_blank(value):
        return _BLANK
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        text = value.strip()
        if text == "":
            return _BLANK
        try:
            return Decimal(text)
        except InvalidOperation:
            return text
    return value


def values_equal(a, b):
    return normalize_value(a) == normalize_value(b)
