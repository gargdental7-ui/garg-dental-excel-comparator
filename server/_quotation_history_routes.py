"""Quotation history: Super Admin can search/filter across whichever
company they specify; staff can only see quotations they created
themselves - enforced in the SQL WHERE clause (not just hidden
client-side), same pattern as _master_excel_routes.py's admin-only
endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from _audit import log_action
from _auth import CurrentUser, require_auth
from _db import get_connection
from _errors import handle_app_errors
from _storage import download as storage_download
from _tenancy import resolve_company_scope

router = APIRouter(prefix="/api/quotation/history", tags=["quotation-history"])

PAGE_SIZE = 25
DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MEDIA_TYPE = "application/pdf"


def _row_out(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "quoteNumber": row["quote_number"],
        "customerName": row["customer_name"],
        "createdBy": row["created_by_name"],
        "createdAt": row["created_at"].isoformat(),
        "status": row["status"],
        "hasPdf": row["pdf_storage_path"] is not None,
    }


@router.get("")
@handle_app_errors
def list_history(
    company_id: Optional[str] = None,
    customer: Optional[str] = None,
    quote_number: Optional[int] = None,
    staff_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    current_user: CurrentUser = Depends(require_auth),
):
    scope = resolve_company_scope(current_user, company_id)
    conditions = ["q.company_id = %s"]
    params: list = [scope]

    # Staff can only ever see their own quotations - the request's own
    # identity decides this, never a client-supplied filter, so a staff
    # user can't pass a different staff_id to see someone else's history.
    if current_user.role != "super_admin":
        conditions.append("q.created_by = %s")
        params.append(current_user.id)
    elif staff_id:
        conditions.append("q.created_by = %s")
        params.append(staff_id)

    if customer:
        conditions.append("q.customer_name ilike %s")
        params.append(f"%{customer}%")
    if quote_number is not None:
        conditions.append("q.quote_number = %s")
        params.append(quote_number)
    if date_from:
        conditions.append("q.created_at >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("q.created_at <= %s")
        params.append(date_to)

    where_clause = " and ".join(conditions)
    offset = max(page - 1, 0) * PAGE_SIZE

    with get_connection(company_id=scope, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(f"select count(*) as total from quotations q where {where_clause}", params)
            total = cur.fetchone()["total"]

            cur.execute(
                f"select q.id, q.quote_number, q.customer_name, q.created_at, q.status, q.pdf_storage_path, "
                f"u.full_name as created_by_name "
                f"from quotations q join users u on u.id = q.created_by "
                f"where {where_clause} "
                f"order by q.created_at desc "
                f"limit %s offset %s",
                params + [PAGE_SIZE, offset],
            )
            rows = cur.fetchall()

    return {
        "quotations": [_row_out(row) for row in rows],
        "total": total,
        "page": page,
        "pageSize": PAGE_SIZE,
    }


def _fetch_quotation_for_download(quotation_id: str, company_id: Optional[str], current_user: CurrentUser) -> tuple[dict, str]:
    scope = resolve_company_scope(current_user, company_id)
    with get_connection(company_id=scope, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select id, customer_name, quote_number, created_by, docx_storage_path, pdf_storage_path "
                "from quotations where company_id = %s and id = %s",
                (scope, quotation_id),
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail={"message": "Quotation not found."})
    # Re-checked here, not just filtered out of the list view - staff must
    # not be able to download another staff member's quotation by guessing
    # or reusing a quotation_id from elsewhere.
    if current_user.role != "super_admin" and str(row["created_by"]) != current_user.id:
        raise HTTPException(status_code=403, detail={"message": "You can only download your own quotations."})
    return row, scope


@router.get("/{quotation_id}/download/docx")
@handle_app_errors
def download_docx(
    quotation_id: str, request: Request, company_id: Optional[str] = None, current_user: CurrentUser = Depends(require_auth)
):
    row, scope = _fetch_quotation_for_download(quotation_id, company_id, current_user)
    content = storage_download("quotations-docx", row["docx_storage_path"])
    filename = f"Quote-{row['quote_number']:04d}-{row['customer_name']}.docx"
    log_action(current_user, scope, "download_quotation", "quotation", str(row["id"]), request, {"format": "docx"})
    return Response(
        content=content,
        media_type=DOCX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{quotation_id}/download/pdf")
@handle_app_errors
def download_pdf(
    quotation_id: str, request: Request, company_id: Optional[str] = None, current_user: CurrentUser = Depends(require_auth)
):
    row, scope = _fetch_quotation_for_download(quotation_id, company_id, current_user)
    if row["pdf_storage_path"] is None:
        raise HTTPException(status_code=404, detail={"message": "No PDF was saved for this quotation."})
    content = storage_download("quotations-pdf", row["pdf_storage_path"])
    filename = f"Quote-{row['quote_number']:04d}-{row['customer_name']}.pdf"
    log_action(current_user, scope, "download_quotation", "quotation", str(row["id"]), request, {"format": "pdf"})
    return Response(
        content=content,
        media_type=PDF_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
