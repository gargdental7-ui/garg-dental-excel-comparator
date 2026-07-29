"""Company profile registry for the Smart Quotation Generator.

Historically a hardcoded dict; Phase 1 of the platform upgrade makes this
DB-backed via the `companies` table, but keeps the exact same public API
(get_company, list_companies, CompanyProfile) so every existing caller -
app/quotation_docx.py, server/_quotation_routes.py, and the pre-existing
test suite - is unaffected. Falls back to the original hardcoded entry
below when DATABASE_URL isn't configured (e.g. local dev before Supabase
env vars are set) or the DB is unreachable, so nothing breaks mid-migration
or in environments (like this package's own test suite, or the Tkinter
desktop app, which never had a DB dependency) that don't have server/ on
their Python path at all.

Adding a second company means adding one row to the `companies` table (or,
before Phase 1's DB is live anywhere, one more _FALLBACK_COMPANIES entry)
plus one template file - never touching the rendering engine, validation,
or totals math in quotation.py / quotation_docx.py.
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .exceptions import UnknownCompanyError

TEMPLATES_DIR = Path(__file__).parent / "quotation_templates"

logger = logging.getLogger("gargdental.quotation_companies")


@dataclass
class CompanyProfile:
    id: str
    display_name: str
    template_filename: str
    terms_and_conditions: list = field(default_factory=list)  # [(label, text), ...]
    default_currency: str = "NRs"
    default_vat_rate: float = 0.0
    default_validity: str = "30 days from the date of this quotation"

    @property
    def template_path(self) -> Path:
        return TEMPLATES_DIR / self.template_filename


# Fallback seed data - kept in sync with server/migrations/0001_initial_schema.sql's
# seed insert. Used whenever the DB isn't configured/reachable or has no
# matching row yet.
_FALLBACK_COMPANIES = {
    "garg_dental": CompanyProfile(
        id="garg_dental",
        display_name="Garg Dental Pvt. Ltd",
        template_filename="equipment_proposal_garg_dental.docx",
        default_currency="NRs",
        default_vat_rate=0.0,
        terms_and_conditions=[
            ("Prices", "Prices are in NRs on door delivery basis."),
            ("Taxes", "VAT is Inclusive as applicable."),
            ("Payment", "50% advance & balance remaining against delivery."),
            ("Delivery", "After 6-8 weeks after your confirmed order subject to meet the payment terms."),
            (
                "Shipment From",
                "Our warehouse in Kathmandu or from the location/company if it's a direct shipment.",
            ),
            (
                "Purchase Order",
                "Must be in the name of Garg Dental Pvt. Ltd or in the name of the principal co.",
            ),
            (
                "Installation",
                "Installation of the equipment will be done by our engineers based in Kathmandu at no extra cost.",
            ),
            (
                "Warranty",
                "The equipment are warranted against manufacturing defects for a period of 24 months from "
                "the date of installation. All warranty replacement is subject to conditions.",
            ),
            (
                "Scope of Warranty",
                "Consumables, semi consumable, bulbs, probes, cables etc. are not covered under warranty. "
                "Reusable accessories are covered under limited warranty (Condition apply).",
            ),
        ],
    )
}

_cache: Optional[dict] = None


def _row_to_profile(row: dict) -> CompanyProfile:
    return CompanyProfile(
        id=row["slug"],
        display_name=row["display_name"],
        template_filename=row["template_filename"],
        terms_and_conditions=[tuple(pair) for pair in row["terms_and_conditions"]],
        default_currency=row["default_currency"],
        default_vat_rate=float(row["default_vat_rate"]),
        default_validity=row["default_validity"],
    )


def _load_from_db() -> Optional[dict]:
    try:
        from _db import get_connection, is_configured  # server-only module; absent for the desktop app / this package's own tests
    except ImportError:
        return None

    if not is_configured():
        return None

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "select slug, display_name, template_filename, default_currency, "
                    "default_vat_rate, default_validity, terms_and_conditions from companies"
                )
                rows = cur.fetchall()
        if not rows:
            return None
        return {row["slug"]: _row_to_profile(row) for row in rows}
    except Exception:
        logger.exception("Failed to load companies from the database; falling back to built-in defaults.")
        return None


def _companies() -> dict:
    global _cache
    if _cache is None:
        _cache = _load_from_db() or dict(_FALLBACK_COMPANIES)
    return _cache


def get_company(company_id: str) -> CompanyProfile:
    company = _companies().get(company_id)
    if company is None:
        raise UnknownCompanyError(company_id)
    return company


def list_companies():
    return list(_companies().values())
