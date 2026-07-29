"""Signature Library: Super-Admin-managed per-company signatures (name +
designation + image), selectable by staff at quotation generation time.
Unlike Master Excel/Quotation Template (one active version per company),
a company can have several active signatures - one authorized signatory
is picked per quotation, so this is a list, not a single-row upsert."""
import io
from typing import Optional

from app.exceptions import InvalidLogoError
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

from _audit import log_action
from _auth import CurrentUser, require_auth, require_super_admin
from _db import get_connection
from _errors import handle_app_errors
from _storage import delete as storage_delete
from _storage import download as storage_download
from _storage import upload as storage_upload
from _tenancy import resolve_company_scope

router = APIRouter(prefix="/api/signatures", tags=["signatures"])

BUCKET = "signatures"


def _storage_path(company_id: str, signature_id: str, filename: str) -> str:
    return f"{company_id}/{signature_id}/{filename}"


def _row_to_dict(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "designation": row["designation"],
        "active": row["active"],
        "createdAt": row["created_at"].isoformat(),
    }


@router.get("")
@handle_app_errors
def list_signatures(company_id: Optional[str] = None, current_user: CurrentUser = Depends(require_auth)):
    """Used both by the Company Assets management page (super_admin, sees
    every signature including inactive ones) and the quotation generator's
    signature picker (any authenticated staff member, active only)."""
    scope = resolve_company_scope(current_user, company_id)
    with get_connection(company_id=scope, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select id, name, designation, active, created_at from signatures "
                "where company_id = %s order by created_at",
                (scope,),
            )
            rows = cur.fetchall()
    if current_user.role != "super_admin":
        rows = [row for row in rows if row["active"]]
    return {"signatures": [_row_to_dict(row) for row in rows]}


@router.put("")
@handle_app_errors
def create_signature(
    request: Request,
    company_id: str,
    name: str,
    designation: str = "",
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_super_admin),
):
    scope = resolve_company_scope(current_user, company_id)
    content = file.file.read()
    try:
        with Image.open(io.BytesIO(content)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidLogoError() from exc

    with get_connection(company_id=scope, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "insert into signatures (company_id, name, designation, image_storage_path, created_by) "
                "values (%s, %s, %s, %s, %s) returning id, name, designation, active, created_at",
                (scope, name, designation, "", current_user.id),
            )
            row = cur.fetchone()
            signature_id = str(row["id"])
            storage_path = _storage_path(scope, signature_id, file.filename or "signature.png")
            storage_upload(BUCKET, storage_path, content, file.content_type or "image/png")
            cur.execute("update signatures set image_storage_path = %s where id = %s", (storage_path, signature_id))

    log_action(current_user, scope, "create_signature", "signature", signature_id, request, {"name": name})
    return _row_to_dict(row)


class UpdateSignatureRequest(BaseModel):
    company_id: str
    name: Optional[str] = None
    designation: Optional[str] = None
    active: Optional[bool] = None


@router.patch("/{signature_id}")
@handle_app_errors
def update_signature(
    signature_id: str,
    payload: UpdateSignatureRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_super_admin),
):
    scope = resolve_company_scope(current_user, payload.company_id)
    fields, params = [], []
    if payload.name is not None:
        fields.append("name = %s")
        params.append(payload.name)
    if payload.designation is not None:
        fields.append("designation = %s")
        params.append(payload.designation)
    if payload.active is not None:
        fields.append("active = %s")
        params.append(payload.active)
    if not fields:
        raise HTTPException(status_code=400, detail={"message": "No fields to update."})

    params.extend([signature_id, scope])
    with get_connection(company_id=scope, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"update signatures set {', '.join(fields)} where id = %s and company_id = %s "
                "returning id, name, designation, active, created_at",
                params,
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail={"message": "Signature not found."})

    log_action(current_user, scope, "update_signature", "signature", signature_id, request)
    return _row_to_dict(row)


@router.delete("/{signature_id}")
@handle_app_errors
def delete_signature(signature_id: str, company_id: str, request: Request, current_user: CurrentUser = Depends(require_super_admin)):
    scope = resolve_company_scope(current_user, company_id)
    with get_connection(company_id=scope, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "delete from signatures where id = %s and company_id = %s returning image_storage_path, name",
                (signature_id, scope),
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail={"message": "Signature not found."})
    storage_delete(BUCKET, row["image_storage_path"])
    log_action(current_user, scope, "delete_signature", "signature", signature_id, request, {"name": row["name"]})
    return {"ok": True}


def fetch_signature_for_render(current_user: CurrentUser, company_id: str, signature_id: str) -> Optional[dict]:
    """Used internally by _quotation_routes.py::generate() - not an HTTP
    endpoint. Returns None if the signature doesn't exist, isn't active, or
    doesn't belong to the resolved company (rather than a generic
    UnknownCompanyError-style raise, since a stale/removed signature_id
    from an older page load shouldn't hard-fail quotation generation)."""
    with get_connection(company_id=company_id, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select name, designation, image_storage_path from signatures "
                "where id = %s and company_id = %s and active",
                (signature_id, company_id),
            )
            row = cur.fetchone()
    if row is None:
        return None
    image_bytes = storage_download(BUCKET, row["image_storage_path"])
    return {"image_bytes": image_bytes, "name": row["name"], "designation": row["designation"]}
