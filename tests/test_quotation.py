import pytest

from app import quotation
from app.exceptions import InvalidQuotationItemError, MissingCustomerNameError, NoQuotationProductsError
from app.quotation import ProductColumnMapping, QuotationCustomer, QuotationItem

HEADERS = ["Item", "Cost", "Code No", "Make", "Model No"]


def _mapping(**overrides):
    base = dict(product_name="Item", price="Cost", code="Code No", brand="Make", model="Model No")
    base.update(overrides)
    return ProductColumnMapping(**base)


def _row(item, cost, code=None, make=None, model=None):
    return {"Item": item, "Cost": cost, "Code No": code, "Make": make, "Model No": model}


def test_map_product_rows_uses_arbitrary_headers():
    rows = [_row("RVG Sensor", "108,000.00", "RVG-01", "Woodpecker", "H1")]
    products = quotation.map_product_rows(HEADERS, rows, _mapping())
    assert products == [
        {
            "product_name": "RVG Sensor",
            "price": 108000.0,
            "code": "RVG-01",
            "description": "",
            "brand": "Woodpecker",
            "model": "H1",
            "origin": "",
            "category": "",
            "warranty": "",
        }
    ]


def test_map_product_rows_skips_blank_names():
    rows = [_row("", "100"), _row("Real Product", "200")]
    products = quotation.map_product_rows(HEADERS, rows, _mapping())
    assert len(products) == 1
    assert products[0]["product_name"] == "Real Product"


def test_map_product_rows_tolerates_unparsable_price():
    rows = [_row("Widget", "not a number")]
    products = quotation.map_product_rows(HEADERS, rows, _mapping())
    assert products[0]["price"] == 0.0


def test_discount_amount_wins_over_percent():
    item = QuotationItem(product_name="A", price=1000, quantity=2, discount_percent=50, discount_amount=100)
    total = quotation.compute_item_total(item)
    assert total.line_subtotal == 2000
    assert total.discount == 100
    assert total.line_total == 1900


def test_discount_percent_applies_when_no_amount_set():
    item = QuotationItem(product_name="A", price=1000, quantity=2, discount_percent=10)
    total = quotation.compute_item_total(item)
    assert total.discount == 200
    assert total.line_total == 1800


def test_compute_totals_with_vat():
    items = [
        QuotationItem(product_name="A", price=1000, quantity=1, discount_percent=10),
        QuotationItem(product_name="B", price=500, quantity=2),
    ]
    totals = quotation.compute_totals(items, vat_rate=13)
    assert totals.subtotal == 2000
    assert totals.discount == 100
    assert totals.vat == pytest.approx(1900 * 0.13)
    assert totals.grand_total == pytest.approx(1900 + 1900 * 0.13)


def test_compute_totals_no_items_is_zero():
    totals = quotation.compute_totals([], vat_rate=13)
    assert totals == quotation.QuotationTotals(subtotal=0.0, discount=0.0, vat=0.0, grand_total=0.0)


def test_validate_requires_customer_name():
    with pytest.raises(MissingCustomerNameError):
        quotation.validate_quotation(QuotationCustomer(customer_name=""), [QuotationItem("A", 100)])


def test_validate_requires_at_least_one_product():
    with pytest.raises(NoQuotationProductsError):
        quotation.validate_quotation(QuotationCustomer(customer_name="Acme"), [])


def test_validate_rejects_invalid_price_and_quantity():
    items = [
        QuotationItem(product_name="Bad Price", price=0, quantity=1),
        QuotationItem(product_name="Bad Qty", price=100, quantity=-1),
    ]
    with pytest.raises(InvalidQuotationItemError) as exc_info:
        quotation.validate_quotation(QuotationCustomer(customer_name="Acme"), items)
    message = str(exc_info.value)
    assert "Bad Price" in message
    assert "Bad Qty" in message


def test_validate_rejects_invalid_discount():
    items = [QuotationItem(product_name="A", price=100, quantity=1, discount_percent=150)]
    with pytest.raises(InvalidQuotationItemError):
        quotation.validate_quotation(QuotationCustomer(customer_name="Acme"), items)

    items = [QuotationItem(product_name="A", price=100, quantity=1, discount_amount=-5)]
    with pytest.raises(InvalidQuotationItemError):
        quotation.validate_quotation(QuotationCustomer(customer_name="Acme"), items)

    items = [QuotationItem(product_name="A", price=100, quantity=1, discount_amount=1000)]
    with pytest.raises(InvalidQuotationItemError):
        quotation.validate_quotation(QuotationCustomer(customer_name="Acme"), items)


def test_validate_passes_for_well_formed_quotation():
    items = [QuotationItem(product_name="A", price=100, quantity=2, discount_percent=10)]
    quotation.validate_quotation(QuotationCustomer(customer_name="Acme"), items)
