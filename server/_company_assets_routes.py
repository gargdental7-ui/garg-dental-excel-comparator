"""Company Quotation Template + Logo: Super-Admin-managed assets stored in
Supabase Storage. Templates are a fully free-form upload - the system
validates only that the file is a real, openable Word document (matching
Master Excel's validation depth via _excel_loading.open_workbook), not
that it contains the right Jinja placeholder tags. See
docs/quotation-template-tags.md for the documented (not enforced)
contract. Logo is simple enough to live as columns on companies rather
than its own table, unlike the template's one-row-per-company table."""
import io
from typing import Optional

from app.exceptions import InvalidLogoError, InvalidTemplateError
from docx import Document
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response
from PIL import Image, UnidentifiedImageError

import app.quotation_companies as quotation_companies
from _audit import log_action
from _auth import CurrentUser, require_super_admin
from _db import get_connection
from _errors import handle_app_errors
from _storage import delete as storage_delete
from _storage import download as storage_download
from _storage import upload as storage_upload
from _tempfiles import temp_upload_path
from _tenancy import resolve_company_scope

router = APIRouter(prefix="/api/company-assets", tags=["company-assets"])

TEMPLATE_BUCKET = "quotation-templates"
LOGO_BUCKET = "company-logos"
DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _storage_path(company_id: str, filename: str) -> str:
    return f"{company_id}/{filename}"


# ---------------------------------------------------------------- Template


def _fetch_template_row(current_user: CurrentUser, scope: str):
    with get_connection(company_id=scope, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select t.storage_path, t.original_filename, t.uploaded_at, t.file_size, u.full_name as uploaded_by_name "
                "from quotation_templates t join users u on u.id = t.uploaded_by "
                "where t.company_id = %s",
                (scope,),
            )
            return cur.fetchone()


def fetch_company_template_bytes(current_user: CurrentUser, company_id: Optional[str] = None) -> Optional[bytes]:
    """Used internally by _quotation_routes.py::generate() - not an HTTP
    endpoint. Returns None (not an error) when no template has been
    uploaded yet, since the caller has a clearer, company-name-specific
    message to show (NoQuotationTemplateError)."""
    scope = resolve_company_scope(current_user, company_id)
    row = _fetch_template_row(current_user, scope)
    if row is None:
        return None
    return storage_download(TEMPLATE_BUCKET, row["storage_path"])


@router.get("/template")
@handle_app_errors
def get_template_metadata(company_id: str, current_user: CurrentUser = Depends(require_super_admin)):
    scope = resolve_company_scope(current_user, company_id)
    row = _fetch_template_row(current_user, scope)
    if row is None:
        return {"exists": False}
    return {
        "exists": True,
        "filename": row["original_filename"],
        "uploadedAt": row["uploaded_at"].isoformat(),
        "uploadedBy": row["uploaded_by_name"],
        "fileSize": row["file_size"],
    }


@router.put("/template")
@handle_app_errors
def upload_template(
    request: Request,
    company_id: str,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_super_admin),
):
    scope = resolve_company_scope(current_user, company_id)
    with temp_upload_path(file) as path:
        try:
            Document(str(path))  # validates it's a real, openable Word document - no deeper tag validation
        except Exception as exc:
            raise InvalidTemplateError() from exc
        content = path.read_bytes()

    filename = file.filename or "template.docx"
    storage_path = _storage_path(scope, filename)
    storage_upload(TEMPLATE_BUCKET, storage_path, content, file.content_type or DOCX_MEDIA_TYPE)

    with get_connection(company_id=scope, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "insert into quotation_templates (company_id, storage_path, original_filename, uploaded_by, file_size) "
                "values (%s, %s, %s, %s, %s) "
                "on conflict (company_id) do update set "
                "storage_path = excluded.storage_path, original_filename = excluded.original_filename, "
                "uploaded_by = excluded.uploaded_by, file_size = excluded.file_size, uploaded_at = now()",
                (scope, storage_path, filename, current_user.id, len(content)),
            )
    quotation_companies.invalidate_cache()
    log_action(current_user, scope, "upload_template", "quotation_template", scope, request, {"filename": filename})
    return get_template_metadata(scope, current_user)


@router.delete("/template")
@handle_app_errors
def delete_template(request: Request, company_id: str, current_user: CurrentUser = Depends(require_super_admin)):
    scope = resolve_company_scope(current_user, company_id)
    with get_connection(company_id=scope, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "delete from quotation_templates where company_id = %s returning storage_path, original_filename", (scope,)
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail={"message": "No template exists."})
    storage_delete(TEMPLATE_BUCKET, row["storage_path"])
    quotation_companies.invalidate_cache()
    log_action(current_user, scope, "delete_template", "quotation_template", scope, request, {"filename": row["original_filename"]})
    return {"ok": True}


@router.get("/template/download")
@handle_app_errors
def download_template(company_id: str, current_user: CurrentUser = Depends(require_super_admin)):
    scope = resolve_company_scope(current_user, company_id)
    row = _fetch_template_row(current_user, scope)
    if row is None:
        raise HTTPException(status_code=404, detail={"message": "No template exists."})
    content = storage_download(TEMPLATE_BUCKET, row["storage_path"])
    return Response(
        content=content,
        media_type=DOCX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{row["original_filename"]}"'},
    )


# --------------------------------------------------------------------- Logo


def fetch_company_logo_bytes(current_user: CurrentUser, company_id: Optional[str] = None) -> Optional[bytes]:
    """Used internally by _quotation_routes.py::generate() - not an HTTP
    endpoint. Returns None when no logo is set (optional, not an error)."""
    scope = resolve_company_scope(current_user, company_id)
    with get_connection(company_id=scope, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute("select logo_storage_path from companies where id = %s", (scope,))
            row = cur.fetchone()
    if row is None or row["logo_storage_path"] is None:
        return None
    return storage_download(LOGO_BUCKET, row["logo_storage_path"])


@router.get("/logo")
@handle_app_errors
def get_logo_metadata(company_id: str, current_user: CurrentUser = Depends(require_super_admin)):
    scope = resolve_company_scope(current_user, company_id)
    with get_connection(company_id=scope, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute("select logo_storage_path, logo_uploaded_at from companies where id = %s", (scope,))
            row = cur.fetchone()
    if row is None or row["logo_storage_path"] is None:
        return {"exists": False}
    return {"exists": True, "uploadedAt": row["logo_uploaded_at"].isoformat()}


@router.put("/logo")
@handle_app_errors
def upload_logo(
    request: Request,
    company_id: str,
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

    filename = file.filename or "logo.png"
    storage_path = _storage_path(scope, filename)
    storage_upload(LOGO_BUCKET, storage_path, content, file.content_type or "image/png")

    with get_connection(company_id=scope, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "update companies set logo_storage_path = %s, logo_uploaded_at = now(), logo_uploaded_by = %s where id = %s",
                (storage_path, current_user.id, scope),
            )
    quotation_companies.invalidate_cache()
    log_action(current_user, scope, "upload_logo", "company_logo", scope, request, {"filename": filename})
    return get_logo_metadata(scope, current_user)


@router.delete("/logo")
@handle_app_errors
def delete_logo(request: Request, company_id: str, current_user: CurrentUser = Depends(require_super_admin)):
    scope = resolve_company_scope(current_user, company_id)
    with get_connection(company_id=scope, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute("select logo_storage_path from companies where id = %s", (scope,))
            row = cur.fetchone()
            if row is None or row["logo_storage_path"] is None:
                raise HTTPException(status_code=404, detail={"message": "No logo exists."})
            storage_path = row["logo_storage_path"]
            cur.execute(
                "update companies set logo_storage_path = null, logo_uploaded_at = null, logo_uploaded_by = null where id = %s",
                (scope,),
            )
    storage_delete(LOGO_BUCKET, storage_path)
    quotation_companies.invalidate_cache()
    log_action(current_user, scope, "delete_logo", "company_logo", scope, request)
    return {"ok": True}
