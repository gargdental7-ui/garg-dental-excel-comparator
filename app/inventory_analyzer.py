"""Inventory Movement Analyzer: rule-based, transparent classification of
product movement from a single uploaded stock report period.

A single snapshot cannot prove long-term dead stock, so classifications are
always period-scoped ("no movement during the uploaded period"), never
labeled as a permanent business conclusion. No AI, no ML - every rule is a
plain arithmetic comparison against a user-configurable threshold.
"""
from dataclasses import dataclass

from .exceptions import MissingColumnMappingError, NoDataRowsError
from .normalizers import is_no_group_row, normalize_code

FAST_MOVING = "FAST MOVING"
NORMAL_MOVING = "NORMAL MOVING"
SLOW_MOVING = "SLOW MOVING"
NO_MOVEMENT = "NO MOVEMENT"
NEGATIVE_STOCK = "NEGATIVE STOCK"
OUT_OF_STOCK = "OUT OF STOCK"

ALL_CLASSIFICATIONS = [
    FAST_MOVING,
    NORMAL_MOVING,
    SLOW_MOVING,
    NO_MOVEMENT,
    NEGATIVE_STOCK,
    OUT_OF_STOCK,
]


@dataclass
class InventoryColumnMapping:
    code: str
    opening: str
    received: str
    delivered: str
    balance: str
    description: str = None
    unit: str = None
    unit_cost: str = None
    stock_value: str = None
    brand: str = None
    category: str = None


@dataclass
class MovementThresholds:
    fast_ratio: float = 0.70
    normal_ratio: float = 0.30


@dataclass
class ProductMovement:
    code: str
    description: object
    unit: object
    opening: float
    received: float
    delivered: float
    balance: float
    movement_ratio: float
    classification: str
    inventory_value: object
    row: dict
    excel_row_index: int


@dataclass
class StockException:
    code: str
    reason: str
    row: dict
    excel_row_index: int


@dataclass
class InventoryAnalysisResult:
    products: list
    exceptions: list
    counts: dict
    has_value_data: bool
    total_inventory_value: object
    value_no_movement: object
    value_slow_moving: object
    thresholds: MovementThresholds


def _to_number(value):
    """Return (value, is_valid). Blank/None is treated as 0 and valid; text
    that doesn't parse as a number is flagged invalid rather than guessed."""
    if value is None:
        return 0.0, True
    if isinstance(value, bool):
        return None, False
    if isinstance(value, (int, float)):
        return float(value), True
    text = str(value).strip()
    if text == "":
        return 0.0, True
    try:
        return float(text.replace(",", "")), True
    except ValueError:
        return None, False


def classify_movement(opening, received, delivered, balance, thresholds):
    """Pure classification for one uploaded period. Returns (classification,
    movement_ratio). Precedence: Negative Balance > Out Of Stock > No
    Movement > ratio-based Fast/Normal/Slow."""
    if balance < 0:
        return NEGATIVE_STOCK, 0.0

    available = opening + received

    if balance == 0:
        ratio = (delivered / available) if available > 0 else 0.0
        return OUT_OF_STOCK, ratio

    if delivered == 0:
        return NO_MOVEMENT, 0.0

    ratio = (delivered / available) if available > 0 else 0.0
    if ratio >= thresholds.fast_ratio:
        return FAST_MOVING, ratio
    if ratio >= thresholds.normal_ratio:
        return NORMAL_MOVING, ratio
    return SLOW_MOVING, ratio


def analyze_inventory(headers, rows, row_excel_indexes, mapping, thresholds=None):
    """Classify movement for `rows` (list of dict keyed by header). Raises
    MissingColumnMappingError if required fields aren't mapped,
    NoDataRowsError if nothing usable is found."""
    thresholds = thresholds or MovementThresholds()

    missing = []
    if not mapping.code:
        missing.append("Product Code")
    if not mapping.opening:
        missing.append("Opening Quantity")
    if not mapping.received:
        missing.append("Received Quantity")
    if not mapping.delivered:
        missing.append("Delivered Quantity")
    if not mapping.balance:
        missing.append("Balance")
    if missing:
        raise MissingColumnMappingError(missing)

    if not rows:
        raise NoDataRowsError()

    has_value_data = bool(mapping.unit_cost or mapping.stock_value)

    exceptions = []
    parsed_rows = []
    seen_codes = {}

    for row, excel_idx in zip(rows, row_excel_indexes):
        code_raw = row.get(mapping.code)
        code_key = normalize_code(code_raw)
        if code_key is None:
            exceptions.append(
                StockException(code="", reason="Missing Code", row=row, excel_row_index=excel_idx)
            )
            continue
        if is_no_group_row(code_key):
            # Group/summary row (e.g. "No Group"), not a real product.
            continue
        code_text = str(code_raw).strip()

        opening, opening_ok = _to_number(row.get(mapping.opening))
        received, received_ok = _to_number(row.get(mapping.received))
        delivered, delivered_ok = _to_number(row.get(mapping.delivered))
        balance, balance_ok = _to_number(row.get(mapping.balance))

        if not (opening_ok and received_ok and delivered_ok and balance_ok):
            exceptions.append(
                StockException(
                    code=code_text, reason="Invalid numeric values", row=row, excel_row_index=excel_idx
                )
            )
            continue

        parsed_rows.append((code_text, opening, received, delivered, balance, row, excel_idx))
        seen_codes.setdefault(code_text, []).append(excel_idx)

    duplicate_codes = {code for code, idxs in seen_codes.items() if len(idxs) > 1}

    products = []
    counts = {name: 0 for name in ALL_CLASSIFICATIONS}
    total_value = 0.0
    value_no_movement = 0.0
    value_slow_moving = 0.0

    for code_text, opening, received, delivered, balance, row, excel_idx in parsed_rows:
        if code_text in duplicate_codes:
            exceptions.append(
                StockException(code=code_text, reason="Duplicate Code", row=row, excel_row_index=excel_idx)
            )
            continue

        classification, ratio = classify_movement(opening, received, delivered, balance, thresholds)
        counts[classification] += 1

        inventory_value = None
        if has_value_data:
            if mapping.stock_value:
                value, ok = _to_number(row.get(mapping.stock_value))
                inventory_value = value if ok else None
            elif mapping.unit_cost:
                unit_cost, ok = _to_number(row.get(mapping.unit_cost))
                inventory_value = balance * unit_cost if ok else None
            if inventory_value is not None:
                total_value += inventory_value
                if classification == NO_MOVEMENT:
                    value_no_movement += inventory_value
                elif classification == SLOW_MOVING:
                    value_slow_moving += inventory_value

        products.append(
            ProductMovement(
                code=code_text,
                description=row.get(mapping.description) if mapping.description else "",
                unit=row.get(mapping.unit) if mapping.unit else "",
                opening=opening,
                received=received,
                delivered=delivered,
                balance=balance,
                movement_ratio=ratio,
                classification=classification,
                inventory_value=inventory_value,
                row=row,
                excel_row_index=excel_idx,
            )
        )

    if not products and not exceptions:
        raise NoDataRowsError()

    return InventoryAnalysisResult(
        products=products,
        exceptions=exceptions,
        counts=counts,
        has_value_data=has_value_data,
        total_inventory_value=total_value if has_value_data else None,
        value_no_movement=value_no_movement if has_value_data else None,
        value_slow_moving=value_slow_moving if has_value_data else None,
        thresholds=thresholds,
    )
