"""Smart Quotation Generator: turns customer/proposal details plus a list of
products (imported from an arbitrary product Excel, entered manually, or a
mix of both) into a validated, fully-totaled quotation ready to render into
a Word document. Products never need to exist in the uploaded Excel - a
manual product carries exactly the same fields and flows through the same
totals/validation/rendering path as an Excel-imported one.
"""
from dataclasses import dataclass, field

from .exceptions import (
    DuplicateQuotationItemError,
    InvalidQuotationItemError,
    MissingCustomerNameError,
    NoQuotationProductsError,
)


@dataclass
class ProductColumnMapping:
    """Maps arbitrary uploaded-Excel headers to the logical product fields
    this tool understands. Only product_name and price are required - any
    other field left unmapped simply stays blank for manual completion,
    per the "auto-fill is only a convenience" rule."""

    product_name: str
    price: str
    code: str = None
    description: str = None
    brand: str = None
    model: str = None
    origin: str = None
    category: str = None
    warranty: str = None
    mrp: str = None
    image_path: str = None


@dataclass
class QuotationCustomer:
    customer_name: str
    contact_person: str = ""
    designation: str = ""
    company_name: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
    reference_number: str = ""
    notes: str = ""


@dataclass
class QuotationProposal:
    title: str = ""
    subject: str = ""
    quotation_date: str = ""
    validity: str = ""
    prepared_by: str = ""
    currency: str = "NRs"


@dataclass
class QuotationItem:
    product_name: str
    price: float
    quantity: float = 1
    code: str = ""
    description: str = ""
    brand: str = ""
    model: str = ""
    origin: str = ""
    category: str = ""
    warranty: str = ""
    mrp: float = 0
    discount_percent: float = 0
    discount_amount: float = 0
    image: str = None  # base64 data URL, or None
    features: list = field(default_factory=list)
    specifications: list = field(default_factory=list)
    installation_notes: str = ""
    additional_notes: str = ""
    accessories: list = field(default_factory=list)
    brochure_note: str = ""


@dataclass
class ItemTotal:
    line_subtotal: float
    discount: float
    line_total: float


@dataclass
class QuotationTotals:
    subtotal: float
    discount: float
    vat: float
    grand_total: float


def _clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _parse_price(value):
    """Same tolerant currency parsing as collection_analyzer._parse_amount -
    a malformed price cell shouldn't block import; it just comes through as
    0 and gets caught by validation before generation."""
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if text == "":
        return 0.0
    cleaned = text.replace(",", "")
    for token in ("Rs.", "Rs", "NRs", "₹", "$"):
        cleaned = cleaned.replace(token, "")
    cleaned = cleaned.strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def map_product_rows(headers, rows, mapping):
    """Turn arbitrary uploaded-Excel rows (dicts keyed by header, as
    returned by generic_excel.load_generic_sheet) into normalized product
    dicts using `mapping`. Unmapped optional fields come through as "" so
    the Product Form can prefill from them without special-casing None."""
    products = []
    for row in rows:
        name = _clean_text(row.get(mapping.product_name))
        if not name:
            continue
        products.append(
            {
                "product_name": name,
                "price": _parse_price(row.get(mapping.price)),
                "code": _clean_text(row.get(mapping.code)) if mapping.code else "",
                "description": _clean_text(row.get(mapping.description)) if mapping.description else "",
                "brand": _clean_text(row.get(mapping.brand)) if mapping.brand else "",
                "model": _clean_text(row.get(mapping.model)) if mapping.model else "",
                "origin": _clean_text(row.get(mapping.origin)) if mapping.origin else "",
                "category": _clean_text(row.get(mapping.category)) if mapping.category else "",
                "warranty": _clean_text(row.get(mapping.warranty)) if mapping.warranty else "",
                "mrp": _parse_price(row.get(mapping.mrp)) if mapping.mrp else 0.0,
                # Metadata only, never resolved server-side (an uploaded
                # Excel's image path is relative to the *client's*
                # filesystem, not this server) - the browser offers to load
                # it only when it looks like an http(s) URL.
                "image_path": _clean_text(row.get(mapping.image_path)) if mapping.image_path else "",
            }
        )
    return products


def compute_item_total(item: QuotationItem) -> ItemTotal:
    """discount_amount wins when set (non-zero); otherwise discount_percent
    is applied to price * quantity. The two are never stacked."""
    line_subtotal = item.price * item.quantity
    discount = item.discount_amount if item.discount_amount else line_subtotal * item.discount_percent / 100
    return ItemTotal(line_subtotal=line_subtotal, discount=discount, line_total=line_subtotal - discount)


def compute_totals(items, vat_rate: float = 0) -> QuotationTotals:
    subtotal = 0.0
    discount = 0.0
    for item in items:
        item_total = compute_item_total(item)
        subtotal += item_total.line_subtotal
        discount += item_total.discount
    taxable = subtotal - discount
    vat = taxable * vat_rate / 100
    return QuotationTotals(subtotal=subtotal, discount=discount, vat=vat, grand_total=taxable + vat)


def find_duplicate_products(items):
    """Returns the display names of products added more than once
    (case-insensitive match on product_name + code - a bare name repeat
    with a different code is treated as a distinct product, e.g. two
    different pack sizes sharing a generic name)."""
    seen = {}
    duplicates = []
    for item in items:
        key = (_clean_text(item.product_name).lower(), _clean_text(item.code).lower())
        if key[0] == "":
            continue
        if key in seen:
            if seen[key] not in duplicates:
                duplicates.append(seen[key])
        else:
            seen[key] = item.product_name
    return duplicates


def validate_quotation(customer: QuotationCustomer, items):
    """Raises MissingCustomerNameError, NoQuotationProductsError,
    DuplicateQuotationItemError, or InvalidQuotationItemError (bundling
    every problem found) - mirrors collection_analyzer/inventory_analyzer's
    fail-fast-with-one-clear-message style."""
    if not _clean_text(customer.customer_name):
        raise MissingCustomerNameError()

    if not items:
        raise NoQuotationProductsError()

    duplicates = find_duplicate_products(items)
    if duplicates:
        raise DuplicateQuotationItemError(duplicates)

    problems = []
    for index, item in enumerate(items, start=1):
        label = _clean_text(item.product_name) or f"item {index}"
        if item.price is None or item.price <= 0:
            problems.append(f"{label}: price must be greater than 0")
        if item.quantity is None or item.quantity <= 0:
            problems.append(f"{label}: quantity must be greater than 0")
        if item.discount_percent is not None and not (0 <= item.discount_percent <= 100):
            problems.append(f"{label}: discount % must be between 0 and 100")
        if item.discount_amount is not None and item.discount_amount < 0:
            problems.append(f"{label}: discount amount cannot be negative")
        if item.discount_amount and item.price is not None and item.quantity is not None:
            if item.discount_amount > item.price * item.quantity:
                problems.append(f"{label}: discount amount cannot exceed the line price")

    if problems:
        raise InvalidQuotationItemError(problems)
