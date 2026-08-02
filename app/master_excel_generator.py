"""AI Company Onboarding - builds the permanent Master Excel from a
reviewed, deduped onboarding product list. Master Excel has no fixed
schema in this codebase (upload_master_excel in
server/_master_excel_routes.py accepts any openable workbook and lets a
super_admin map its columns at import time via
server/_mapping_heuristics.py) - so the only requirement here is a single
header row Claude's own auto-mapping heuristics recognize. The header
names below are taken verbatim from PRODUCT_CANDIDATES in that file so a
newly onboarded company's Master Excel auto-maps with zero manual mapping
the first time staff use it."""
from pathlib import Path

from openpyxl import Workbook

from .report_style import autofit_columns, style_header_row

# Order matches the field order onboarding review presents; names match
# _mapping_heuristics.py::PRODUCT_CANDIDATES exactly (case-insensitive
# match there, but keeping the exact candidate text avoids any ambiguity).
_COLUMNS = [
    ("product_name", "Product Name"),
    ("price", "Price"),
    ("code", "Code"),
    ("description", "Description"),
    ("brand", "Brand"),
    ("model", "Model"),
    ("origin", "Origin"),
    ("category", "Category"),
    ("warranty", "Warranty"),
    ("mrp", "MRP"),
]


def build_master_excel(output_path, products: list[dict]) -> Path:
    """products: dicts with the keys in _COLUMNS (missing keys default to
    blank/0). Only products the reviewer left `included` (filtered by the
    caller before this is called) should be passed in."""
    wb = Workbook()
    ws = wb.active
    ws.title = "PRODUCTS"

    ws.append([label for _, label in _COLUMNS])
    for product in products:
        ws.append([product.get(key, "") for key, _ in _COLUMNS])

    style_header_row(ws, len(_COLUMNS))
    autofit_columns(ws, len(_COLUMNS))

    output_path = Path(output_path)
    wb.save(str(output_path))
    return output_path
