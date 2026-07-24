"""Converts dataclass results from the business logic (CustomerSummary,
ProductMovement, CellDifference, etc.) and raw Excel cell values (which can
be dates, datetimes, or anything openpyxl returns) into plain JSON-safe
values for API responses."""
from dataclasses import fields, is_dataclass
from datetime import date, datetime


def dataclass_kwargs(cls, data: dict) -> dict:
    """Filter an arbitrary dict (e.g. client JSON) down to only the given
    dataclass's field names, so extra/unexpected keys don't raise a
    TypeError when constructing it. Use for dataclasses whose fields all
    have real defaults (e.g. CollectionThresholds) - an absent key means
    "use that field's own default", not None."""
    valid_keys = {f.name for f in fields(cls)}
    return {k: v for k, v in (data or {}).items() if k in valid_keys}


def mapping_kwargs(cls, data: dict) -> dict:
    """Like dataclass_kwargs, but explicitly supplies None for every field
    missing from the client payload - including fields with no dataclass
    default (e.g. CollectionColumnMapping.customer/amount). Without this, an
    entirely-omitted required field raises a bare TypeError before
    analyze_collections/analyze_inventory's own MissingColumnMappingError
    check ever runs, surfacing as a generic 500 instead of the correct
    user-facing 400."""
    valid_keys = {f.name for f in fields(cls)}
    return {k: (data or {}).get(k) for k in valid_keys}


def json_safe(value):
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: json_safe(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
