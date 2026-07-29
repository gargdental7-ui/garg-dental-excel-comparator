"""Company management - Super-Admin-only. Creating/editing a company
invalidates app/quotation_companies.py's in-process cache so changes are
visible immediately instead of only after a cold start (that cache was
never a problem when companies never changed at runtime; now they do)."""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

import app.quotation_companies as quotation_companies
from _audit import log_action
from _auth import CurrentUser, require_super_admin
from _db import get_connection
from _errors import handle_app_errors

router = APIRouter(prefix="/api/companies", tags=["companies"])


def _company_out(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "slug": row["slug"],
        "displayName": row["display_name"],
        "active": row["active"],
        "defaultCurrency": row.get("default_currency"),
        "defaultVatRate": float(row["default_vat_rate"]) if row.get("default_vat_rate") is not None else None,
        "defaultValidity": row.get("default_validity"),
        "termsAndConditions": row.get("terms_and_conditions"),
    }


@router.get("")
@handle_app_errors
def list_companies(current_user: CurrentUser = Depends(require_super_admin)):
    # role="super_admin" here is the actual current_user's role (this route
    # is already super-admin-gated), so this naturally sees every company
    # via the is_super_admin RLS bypass - no per-company company_id needs
    # to be passed to get_connection for a "list every company" operation.
    with get_connection(user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute("select id, slug, display_name, active from companies order by display_name")
            rows = cur.fetchall()
    return {"companies": [_company_out(row) for row in rows]}


class CreateCompanyRequest(BaseModel):
    slug: str = Field(min_length=1, pattern=r"^[a-z0-9_]+$")
    display_name: str = Field(min_length=1)
    default_currency: str = "NRs"
    default_vat_rate: float = 0
    default_validity: str = "30 days from the date of this quotation"
    terms_and_conditions: list[tuple[str, str]] = []


@router.post("")
@handle_app_errors
def create_company(payload: CreateCompanyRequest, request: Request, current_user: CurrentUser = Depends(require_super_admin)):
    with get_connection(user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute("select 1 from companies where slug = %s", (payload.slug,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail={"message": "That company slug is already in use."})
            cur.execute(
                "insert into companies (slug, display_name, default_currency, default_vat_rate, default_validity, terms_and_conditions) "
                "values (%s, %s, %s, %s, %s, %s) "
                "returning id, slug, display_name, active, default_currency, default_vat_rate, default_validity, terms_and_conditions",
                (
                    payload.slug,
                    payload.display_name,
                    payload.default_currency,
                    payload.default_vat_rate,
                    payload.default_validity,
                    json.dumps(payload.terms_and_conditions),
                ),
            )
            row = cur.fetchone()
    quotation_companies.invalidate_cache()
    log_action(current_user, str(row["id"]), "create_company", "company", str(row["id"]), request, {"slug": row["slug"]})
    return _company_out(row)


class UpdateCompanyRequest(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=1)
    default_currency: Optional[str] = None
    default_vat_rate: Optional[float] = None
    default_validity: Optional[str] = None
    terms_and_conditions: Optional[list[tuple[str, str]]] = None
    active: Optional[bool] = None


@router.patch("/{company_id}")
@handle_app_errors
def update_company(
    company_id: str, payload: UpdateCompanyRequest, request: Request, current_user: CurrentUser = Depends(require_super_admin)
):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail={"message": "Nothing to update."})
    if "terms_and_conditions" in updates:
        updates["terms_and_conditions"] = json.dumps(updates["terms_and_conditions"])

    set_clause = ", ".join(f"{column} = %s" for column in updates)
    values = list(updates.values()) + [company_id]

    with get_connection(user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"update companies set {set_clause} where id = %s "
                "returning id, slug, display_name, active, default_currency, default_vat_rate, default_validity, terms_and_conditions",
                values,
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail={"message": "Company not found."})
    quotation_companies.invalidate_cache()
    action = "disable_company" if updates.get("active") is False else ("update_company" if "active" not in updates else "enable_company")
    log_action(current_user, company_id, action, "company", company_id, request, {"slug": row["slug"]})
    return _company_out(row)


@router.get("/{company_id}/dashboard")
@handle_app_errors
def company_dashboard(company_id: str, current_user: CurrentUser = Depends(require_super_admin)):
    with get_connection(company_id=company_id, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute("select 1 from companies where id = %s", (company_id,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail={"message": "Company not found."})

            cur.execute(
                "select "
                "count(*) filter (where created_at >= date_trunc('day', now())) as today, "
                "count(*) filter (where created_at >= date_trunc('month', now())) as this_month, "
                "count(distinct customer_name) as customers "
                "from quotations where company_id = %s",
                (company_id,),
            )
            totals = cur.fetchone()

            cur.execute(
                "select u.full_name, count(*) as n from quotations q join users u on u.id = q.created_by "
                "where q.company_id = %s group by u.full_name order by n desc limit 1",
                (company_id,),
            )
            most_active = cur.fetchone()

            cur.execute(
                "select quote_number, customer_name, created_at from quotations "
                "where company_id = %s order by created_at desc limit 1",
                (company_id,),
            )
            last_quotation = cur.fetchone()

            cur.execute("select version, file_size from master_excel where company_id = %s", (company_id,))
            master_excel = cur.fetchone()

            cur.execute("select version, file_size from quotation_templates where company_id = %s", (company_id,))
            template = cur.fetchone()

            cur.execute("select count(*) as n from signatures where company_id = %s and active", (company_id,))
            active_signatures = cur.fetchone()["n"]

            cur.execute(
                "select coalesce(sum(qf.size_bytes), 0) as total from quotation_files qf "
                "join quotations q on q.id = qf.quotation_id where q.company_id = %s",
                (company_id,),
            )
            quotation_files_bytes = cur.fetchone()["total"]

    # "Rough" by design (see the plan): the company logo's file size isn't
    # persisted anywhere (only its storage path), so it's left out of this
    # total rather than adding a Storage round-trip just for an estimate.
    storage_bytes = (
        quotation_files_bytes
        + (master_excel["file_size"] if master_excel else 0)
        + (template["file_size"] if template else 0)
    )

    return {
        "quotationsToday": totals["today"],
        "quotationsThisMonth": totals["this_month"],
        # Proxy for "customers": there's no dedicated customer/CRM entity in
        # this schema, so this counts distinct customer_name values instead -
        # two quotations for the same customer typed slightly differently
        # would count as two, a known simplification.
        "totalCustomers": totals["customers"],
        "mostActiveStaff": most_active["full_name"] if most_active else None,
        "lastQuotation": (
            {
                "quoteNumber": last_quotation["quote_number"],
                "customerName": last_quotation["customer_name"],
                "createdAt": last_quotation["created_at"].isoformat(),
            }
            if last_quotation
            else None
        ),
        "masterExcelVersion": master_excel["version"] if master_excel else None,
        "templateVersion": template["version"] if template else None,
        "activeSignatureCount": active_signatures,
        "storageBytes": storage_bytes,
    }


@router.delete("/{company_id}")
@handle_app_errors
def delete_company(company_id: str, request: Request, current_user: CurrentUser = Depends(require_super_admin)):
    with get_connection(user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute("select count(*) as n from quotations where company_id = %s", (company_id,))
            if cur.fetchone()["n"] > 0:
                raise HTTPException(
                    status_code=400,
                    detail={"message": "This company has quotations on record and can't be deleted. Disable it instead."},
                )
            cur.execute("delete from companies where id = %s returning slug", (company_id,))
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail={"message": "Company not found."})
    quotation_companies.invalidate_cache()
    log_action(current_user, None, "delete_company", "company", company_id, request, {"slug": row["slug"]})
    return {"ok": True}
