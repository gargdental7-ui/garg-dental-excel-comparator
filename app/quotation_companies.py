"""Company profile registry for the Smart Quotation Generator - DB-backed
via the `companies` table (in-process cached, since company profiles
change rarely), keyed by the company's real UUID (companies.id) to match
every other company-scoped table (users.company_id, master_excel.company_id,
etc.) - a company's `slug` is a separate, human-readable field, not the
lookup key.

Historically (Phase 1 of the original single-company upgrade) this had a
hardcoded fallback dict for when the DB was unreachable. That stopped
making sense once the whole platform became genuinely multi-tenant: auth
itself now requires DB access (users live in the DB), so a DB outage
already breaks login before this module would ever be reached, and there's
no single hardcoded company profile that could stand in for "whichever of
N companies was actually being asked for." A DB load failure now raises a
clear CompanyDataUnavailableError instead of silently serving
possibly-wrong data.
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .exceptions import CompanyDataUnavailableError, UnknownCompanyError

TEMPLATES_DIR = Path(__file__).parent / "quotation_templates"

logger = logging.getLogger("gargdental.quotation_companies")


@dataclass
class CompanyProfile:
    id: str  # companies.id (UUID) - matches every other company-scoped table
    slug: str
    display_name: str
    # None for a newly created company that hasn't had a template uploaded
    # yet (Phase B lets Super Admin create companies before Phase C's
    # per-company template upload exists for them) - template_path is None
    # in that case, and callers (app/quotation_docx.py) must handle it.
    template_filename: Optional[str] = None
    terms_and_conditions: list = field(default_factory=list)  # [(label, text), ...]
    default_currency: str = "NRs"
    default_vat_rate: float = 0.0
    default_validity: str = "30 days from the date of this quotation"

    @property
    def template_path(self) -> Optional[Path]:
        if not self.template_filename:
            return None
        return TEMPLATES_DIR / self.template_filename


_cache: Optional[dict] = None


def _row_to_profile(row: dict) -> CompanyProfile:
    return CompanyProfile(
        id=str(row["id"]),
        slug=row["slug"],
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
        # role="super_admin" is a synthetic assertion, not tied to any real
        # user - this function's job is to load the shared company/template
        # registry cache, which is legitimately a "see every company"
        # operation regardless of who eventually calls get_company(). Now
        # that RLS is enforced by a genuinely restricted DB role (not the
        # bypassing one Supabase's default connection string handed out by
        # default), an unscoped call here would otherwise see zero rows.
        # The real per-request authorization boundary is unaffected - it's
        # still resolve_company_scope()/route logic deciding what a given
        # caller may act on; this only controls what this one process-wide
        # config cache is allowed to read.
        with get_connection(role="super_admin") as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "select id, slug, display_name, template_filename, default_currency, "
                    "default_vat_rate, default_validity, terms_and_conditions from companies where active"
                )
                rows = cur.fetchall()
        if not rows:
            return None
        return {str(row["id"]): _row_to_profile(row) for row in rows}
    except Exception:
        logger.exception("Failed to load companies from the database.")
        return None


def _companies() -> dict:
    global _cache
    if _cache is None:
        loaded = _load_from_db()
        if loaded is None:
            raise CompanyDataUnavailableError()
        _cache = loaded
    return _cache


def invalidate_cache() -> None:
    """Called by server/_companies_routes.py after any company create/edit/
    disable so a Super Admin's changes are visible immediately instead of
    only after a cold start - this module-level cache was never a problem
    when companies never changed at runtime (the original single-company
    design), but now they do."""
    global _cache
    _cache = None


def get_company(company_id: str) -> CompanyProfile:
    company = _companies().get(company_id)
    if company is None:
        raise UnknownCompanyError(company_id)
    return company


def get_company_by_slug(slug: str) -> CompanyProfile:
    for company in _companies().values():
        if company.slug == slug:
            return company
    raise UnknownCompanyError(slug)


def list_companies():
    return list(_companies().values())
