"""Auto-mapping candidate-header-name lists, ported verbatim from the
Tkinter pages' `_auto_map` (app/pages/collection_page.py,
app/pages/inventory_page.py). These are UI-only guessing heuristics that
never existed in the tested business-logic modules - matching rule: exact
match (trimmed, lowercased) against each candidate in order, first hit wins."""

COLLECTION_CANDIDATES = {
    "customer": ["customer", "party", "party name", "customer name"],
    "amount": ["outstanding amount", "outstanding", "amount", "balance"],
    "days_overdue": ["days overdue", "overdue days"],
    "due_date": ["due date"],
    "last_payment_date": ["last payment date", "last payment"],
    "salesperson": ["salesperson", "sales person", "sales rep"],
    "invoice_number": ["invoice number", "invoice no", "invoice"],
}

INVENTORY_CANDIDATES = {
    "code": ["code", "product code", "item code"],
    "description": ["description", "item description", "product name"],
    "unit": ["unit"],
    "opening": ["opening"],
    "received": ["received"],
    "delivered": ["delivered"],
    "balance": ["balance"],
    "unit_cost": ["unit cost", "cost"],
    "stock_value": ["stock value", "inventory value"],
    "brand": ["brand"],
    "category": ["category"],
}

PRODUCT_CANDIDATES = {
    "product_name": ["product name", "item name", "product", "item", "name"],
    "price": ["price", "selling price", "rate", "unit price", "cost"],
    "code": ["code", "product code", "item code", "sku"],
    "description": ["description", "details", "specification"],
    "brand": ["brand", "manufacturer", "make"],
    "model": ["model", "model no", "model number"],
    "origin": ["origin", "country of origin", "made in"],
    "category": ["category", "type"],
    "warranty": ["warranty", "warranty period"],
}


def suggest_mapping(headers, candidates_by_field):
    lowered = {h.strip().lower(): h for h in headers}
    suggestion = {}
    for field, candidates in candidates_by_field.items():
        match = None
        for candidate in candidates:
            if candidate in lowered:
                match = lowered[candidate]
                break
        suggestion[field] = match
    return suggestion
