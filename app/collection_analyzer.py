"""Collection Priority Analyzer: aggregates receivables by customer and
ranks them with a transparent, rule-based priority (no AI, no ML).

The scoring rule considers three factors, in order: outstanding amount,
days overdue, and number of open invoices. Every threshold is a plain,
user-configurable number so the rule can always be explained in one
sentence to office staff.
"""
from dataclasses import dataclass, field
from datetime import date, datetime

from .exceptions import MissingColumnMappingError, NoDataRowsError

CRITICAL = "CRITICAL"
HIGH = "HIGH"
MEDIUM = "MEDIUM"
NORMAL = "NORMAL"
_PRIORITY_ORDER = [NORMAL, MEDIUM, HIGH, CRITICAL]


@dataclass
class CollectionColumnMapping:
    customer: str
    amount: str
    days_overdue: str = None
    due_date: str = None
    last_payment_date: str = None
    salesperson: str = None
    invoice_number: str = None


@dataclass
class CollectionThresholds:
    critical_days: int = 90
    high_days: int = 60
    medium_days: int = 30
    critical_amount: float = 100000.0
    high_amount: float = 50000.0
    many_invoices_count: int = 3


@dataclass
class CustomerSummary:
    customer: str
    total_outstanding: float
    invoice_count: int
    max_days_overdue: float
    avg_days_overdue: float
    oldest_due_date: object
    salesperson: object
    priority: str
    invoice_indexes: list = field(default_factory=list)


@dataclass
class CollectionResult:
    customers: list
    rows: list
    headers: list
    total_outstanding: float
    total_customers: int
    critical_count: int
    high_count: int
    critical_amount: float
    high_priority_amount: float
    amount_over_30: float
    amount_over_60: float
    amount_over_90: float
    thresholds: CollectionThresholds


def _clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _parse_amount(value):
    """Blank/unparsable amounts are treated as 0.0 rather than raising -
    a malformed cell shouldn't block the whole analysis."""
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
    for token in ("Rs.", "Rs", "₹", "$"):
        cleaned = cleaned.replace(token, "")
    cleaned = cleaned.strip()
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    if negative:
        cleaned = cleaned[1:-1]
    try:
        result = float(cleaned)
    except ValueError:
        return 0.0
    return -result if negative else result


def _parse_optional_number(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if text == "":
        return None
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def _parse_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if text == "":
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def classify_priority(total_outstanding, max_days_overdue, invoice_count, thresholds):
    """Pure, deterministic priority rule - explainable in one sentence:
    CRITICAL if overdue days or amount clear the critical bar, HIGH if they
    clear the high bar, MEDIUM if overdue days clear the medium bar,
    otherwise NORMAL; 3+ open invoices bump the result up one level.
    Accounts with nothing owed (<= 0) are always NORMAL."""
    if total_outstanding <= 0:
        return NORMAL

    days = max_days_overdue or 0
    if days >= thresholds.critical_days or total_outstanding >= thresholds.critical_amount:
        priority = CRITICAL
    elif days >= thresholds.high_days or total_outstanding >= thresholds.high_amount:
        priority = HIGH
    elif days >= thresholds.medium_days:
        priority = MEDIUM
    else:
        priority = NORMAL

    if invoice_count >= thresholds.many_invoices_count and priority != CRITICAL:
        priority = _PRIORITY_ORDER[_PRIORITY_ORDER.index(priority) + 1]
    return priority


def analyze_collections(headers, rows, mapping, thresholds=None):
    """Aggregate `rows` (list of dict keyed by header) by customer and rank
    them by collection priority. Raises MissingColumnMappingError if the
    required fields aren't mapped, NoDataRowsError if nothing usable is
    found."""
    thresholds = thresholds or CollectionThresholds()

    missing = []
    if not mapping.customer:
        missing.append("Customer/Party Name")
    if not mapping.amount:
        missing.append("Outstanding Amount")
    if missing:
        raise MissingColumnMappingError(missing)

    if not rows:
        raise NoDataRowsError()

    today = date.today()
    groups = {}
    order = []

    for row in rows:
        customer = _clean_text(row.get(mapping.customer))
        if not customer:
            continue

        amount = _parse_amount(row.get(mapping.amount))

        days_overdue = None
        if mapping.days_overdue:
            days_overdue = _parse_optional_number(row.get(mapping.days_overdue))

        due_date = _parse_date(row.get(mapping.due_date)) if mapping.due_date else None
        if days_overdue is None and due_date is not None:
            days_overdue = max((today - due_date).days, 0)
        if days_overdue is None:
            days_overdue = 0.0

        salesperson = _clean_text(row.get(mapping.salesperson)) if mapping.salesperson else ""

        if customer not in groups:
            groups[customer] = {
                "total": 0.0,
                "count": 0,
                "days_list": [],
                "max_days": 0.0,
                "oldest_due": None,
                "salesperson": salesperson,
                "row_indexes": [],
            }
            order.append(customer)

        g = groups[customer]
        g["total"] += amount
        g["count"] += 1
        g["days_list"].append(days_overdue)
        g["max_days"] = max(g["max_days"], days_overdue)
        if due_date is not None and (g["oldest_due"] is None or due_date < g["oldest_due"]):
            g["oldest_due"] = due_date
        if salesperson and not g["salesperson"]:
            g["salesperson"] = salesperson

    if not groups:
        raise NoDataRowsError()

    customers = []
    total_outstanding = 0.0
    critical_amount = 0.0
    high_priority_amount = 0.0
    amount_over_30 = 0.0
    amount_over_60 = 0.0
    amount_over_90 = 0.0
    critical_count = 0
    high_count = 0

    for customer in order:
        g = groups[customer]
        avg_days = sum(g["days_list"]) / len(g["days_list"]) if g["days_list"] else 0.0
        priority = classify_priority(g["total"], g["max_days"], g["count"], thresholds)

        customers.append(
            CustomerSummary(
                customer=customer,
                total_outstanding=g["total"],
                invoice_count=g["count"],
                max_days_overdue=g["max_days"],
                avg_days_overdue=avg_days,
                oldest_due_date=g["oldest_due"],
                salesperson=g["salesperson"] or None,
                priority=priority,
            )
        )

        total_outstanding += g["total"]
        if g["total"] > 0:
            if priority == CRITICAL:
                critical_amount += g["total"]
                critical_count += 1
            elif priority == HIGH:
                high_priority_amount += g["total"]
                high_count += 1
            if g["max_days"] >= 30:
                amount_over_30 += g["total"]
            if g["max_days"] >= 60:
                amount_over_60 += g["total"]
            if g["max_days"] >= 90:
                amount_over_90 += g["total"]

    priority_rank = {CRITICAL: 0, HIGH: 1, MEDIUM: 2, NORMAL: 3}
    customers.sort(key=lambda c: (priority_rank[c.priority], -c.total_outstanding))

    return CollectionResult(
        customers=customers,
        rows=rows,
        headers=headers,
        total_outstanding=total_outstanding,
        total_customers=len(customers),
        critical_count=critical_count,
        high_count=high_count,
        critical_amount=critical_amount,
        high_priority_amount=high_priority_amount,
        amount_over_30=amount_over_30,
        amount_over_60=amount_over_60,
        amount_over_90=amount_over_90,
        thresholds=thresholds,
    )
