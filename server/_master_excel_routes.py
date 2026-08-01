"""Company Master Excel: a permanent, Super-Admin-managed product-list
Excel per company, stored in Supabase Storage so the quotation generator
can reuse it without a fresh upload every time. master_excel.company_id
is unique in the schema, so "replace" is just re-running the same upload
(an upsert), not a separate endpoint - matching the spec's "only one
active master Excel per company" rule at the DB level, not just in
application logic."""
from typing import Optional

from app.exceptions import NoMasterExcelError
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response

from _audit import log_action
from _auth import CurrentUser, require_auth, require_super_admin
from _db import get_connection
from _errors import handle_app_errors
from _excel_loading import open_workbook
from _storage import delete as storage_delete
from _storage import download as storage_download
from _storage import upload as storage_upload
from _tempfiles import temp_upload_path
from _tenancy import resolve_company_scope

router = APIRouter(prefix="/api/master-excel", tags=["master-excel"])

BUCKET = "master-excel"


def _storage_path(company_id: str, filename: str) -> str:
    return f"{company_id}/{filename}"


def _fetch_row(current_user: CurrentUser, scope: str):
    # left join, not join: uploaded_by is always a super_admin (upload
    # requires require_super_admin), whose own users row has company_id
    # NULL - when this query runs in a staff session, the users RLS policy
    # hides that row, so an inner join silently returned zero rows here
    # (breaking "Use Company's Master Excel" for every staff member) even
    # though the master_excel row itself was visible. This function backs
    # fetch_master_excel_bytes(), which staff call on every generate().
    with get_connection(company_id=scope, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select m.storage_path, m.original_filename, m.uploaded_at, m.file_size, m.version, "
                "u.full_name as uploaded_by_name "
                "from master_excel m left join users u on u.id = m.uploaded_by "
                "where m.company_id = %s",
                (scope,),
            )
            return cur.fetchone()


def fetch_master_excel_version(current_user: CurrentUser, company_id: str) -> Optional[int]:
    """Used internally by _quotation_routes.py to record which master
    Excel version was active when a quotation was generated - not an HTTP
    endpoint. None if no master Excel has been uploaded yet."""
    row = _fetch_row(current_user, company_id)
    return row["version"] if row else None


def fetch_master_excel_bytes(current_user: CurrentUser, company_id: Optional[str] = None) -> bytes:
    """Used internally by _quotation_routes.py's excel_source=company_master
    path - not an HTTP endpoint. Raises NoMasterExcelError (an AppError, so
    handle_app_errors turns it into the same 400 shape as any other
    validation failure) rather than a bare None, since the quotation route
    calling this has no sensible "unset" state to fall back to."""
    scope = resolve_company_scope(current_user, company_id)
    row = _fetch_row(current_user, scope)
    if row is None:
        raise NoMasterExcelError()
    return storage_download(BUCKET, row["storage_path"])


@router.get("")
@handle_app_errors
def get_metadata(company_id: Optional[str] = None, current_user: CurrentUser = Depends(require_auth)):
    scope = resolve_company_scope(current_user, company_id)
    row = _fetch_row(current_user, scope)
    if row is None:
        return {"exists": False}
    return {
        "exists": True,
        "filename": row["original_filename"],
        "uploadedAt": row["uploaded_at"].isoformat(),
        "uploadedBy": row["uploaded_by_name"],
        "fileSize": row["file_size"],
    }


@router.put("")
@handle_app_errors
def upload_master_excel(
    request: Request,
    company_id: str,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_super_admin),
):
    scope = resolve_company_scope(current_user, company_id)
    with temp_upload_path(file) as path:
        open_workbook(path)  # validates it's a real, openable workbook - reuses existing error handling
        content = path.read_bytes()

    filename = file.filename or "master.xlsx"
    storage_path = _storage_path(scope, filename)
    storage_upload(BUCKET, storage_path, content, file.content_type or "application/octet-stream")

    with get_connection(company_id=scope, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "insert into master_excel (company_id, storage_path, original_filename, uploaded_by, file_size) "
                "values (%s, %s, %s, %s, %s) "
                "on conflict (company_id) do update set "
                "storage_path = excluded.storage_path, original_filename = excluded.original_filename, "
                "uploaded_by = excluded.uploaded_by, file_size = excluded.file_size, uploaded_at = now(), "
                "version = master_excel.version + 1",
                (scope, storage_path, filename, current_user.id, len(content)),
            )
    log_action(current_user, scope, "upload_master_excel", "master_excel", scope, request, {"filename": filename})
    return get_metadata(scope, current_user)


@router.delete("")
@handle_app_errors
def delete_master_excel(request: Request, company_id: str, current_user: CurrentUser = Depends(require_super_admin)):
    scope = resolve_company_scope(current_user, company_id)
    with get_connection(company_id=scope, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "delete from master_excel where company_id = %s returning storage_path, original_filename",
                (scope,),
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail={"message": "No master Excel exists."})
    storage_delete(BUCKET, row["storage_path"])
    log_action(
        current_user, scope, "delete_master_excel", "master_excel", scope, request,
        {"filename": row["original_filename"]},
    )
    return {"ok": True}


@router.get("/download")
@handle_app_errors
def download_master_excel(company_id: str, current_user: CurrentUser = Depends(require_super_admin)):
    scope = resolve_company_scope(current_user, company_id)
    row = _fetch_row(current_user, scope)
    if row is None:
        raise HTTPException(status_code=404, detail={"message": "No master Excel exists."})
    content = storage_download(BUCKET, row["storage_path"])
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{row["original_filename"]}"'},
    )
