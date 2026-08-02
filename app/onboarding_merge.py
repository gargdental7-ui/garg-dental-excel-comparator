"""AI Company Onboarding - cross-document merge logic. Pure functions (no
DB access), so they're directly unit-testable. When more than one uploaded
document mentions the same company field or the same product, these
decide which extraction wins and which product rows are duplicates of
each other - both keyed on the exact same normalization
app/quotation.py::find_duplicate_products already uses for the quotation
builder's own duplicate-product check, so "duplicate" means the same thing
in both places."""


def _normalize(text: str | None) -> str:
    return (text or "").strip().lower()


def product_dedup_key(product_name: str | None, code: str | None) -> tuple[str, str]:
    """Same (name, code) case-insensitive key as
    app/quotation.py::find_duplicate_products - a bare name repeat with a
    different code is a distinct product (e.g. two pack sizes sharing a
    generic name), not a duplicate."""
    return (_normalize(product_name), _normalize(code))


def find_duplicate_product_groups(products: list[dict]) -> list[list[int]]:
    """products: dicts with at least product_name/code keys, in the same
    order the caller will persist them. Returns groups of list-indices that
    share a dedup key (only groups with 2+ members) so the review wizard
    can show "these look like the same product" without the caller having
    to re-derive the key itself."""
    seen: dict[tuple[str, str], list[int]] = {}
    for index, product in enumerate(products):
        key = product_dedup_key(product.get("product_name"), product.get("code"))
        if not key[0]:
            continue
        seen.setdefault(key, []).append(index)
    return [indices for indices in seen.values() if len(indices) > 1]


def merge_company_field_candidates(candidates: list[dict]) -> dict[str, dict]:
    """candidates: dicts shaped {field_name, value, confidence,
    source_document_id}, one per (field, document) pair - i.e. every
    document's extraction contributes its own candidate for the same
    field. Returns one winning candidate per field_name: the
    highest-confidence non-null value seen across every document. A field
    no document extracted a value for is simply absent from the result
    (left for the wizard to fill in manually)."""
    best: dict[str, dict] = {}
    for candidate in candidates:
        if candidate.get("value") is None:
            continue
        name = candidate["field_name"]
        current = best.get(name)
        if current is None or candidate["confidence"] > current["confidence"]:
            best[name] = candidate
    return best
