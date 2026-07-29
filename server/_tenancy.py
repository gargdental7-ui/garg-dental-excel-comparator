"""The one place "which company is this request acting on" gets decided,
used by every route that touches company-scoped data (users, master
excel, templates, logo, signatures, quotation generate/history, audit).
Before this existed, routes read current_user.company_id directly - that
broke the moment super_admin (whose own company_id is always NULL) needed
to act on a specific company, so every one of those call sites now goes
through here instead."""
from fastapi import HTTPException

from _auth import CurrentUser
from _db import get_connection


def resolve_company_scope(current_user: CurrentUser, requested_company_id: str | None) -> str:
    """staff: always their own company, any requested_company_id is
    ignored (a staff member can never act on another company's data no
    matter what a request claims). super_admin: must explicitly say which
    company - there is no sensible default - and that company must
    actually exist and be active."""
    if current_user.role != "super_admin":
        return current_user.company_id

    if not requested_company_id:
        raise HTTPException(status_code=400, detail={"message": "company_id is required."})

    with get_connection(
        company_id=requested_company_id, user_id=current_user.id, role=current_user.role
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("select active from companies where id = %s", (requested_company_id,))
            row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail={"message": "Company not found."})
    if not row["active"]:
        raise HTTPException(status_code=400, detail={"message": "This company is disabled."})
    return requested_company_id
