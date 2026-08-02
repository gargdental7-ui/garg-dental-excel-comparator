"""AI Company Onboarding - Super-Admin-only. A super_admin uploads whatever
documents a prospective company already has, Claude extracts a company
profile + product catalog per document (app/onboarding_extraction.py),
cross-document results are merged/deduped (app/onboarding_merge.py), the
super_admin reviews/edits in the wizard, and publish() creates the real
company, Master Excel, first admin user, and (optionally) logo/signature
in one pass - reusing the exact same insert/upload paths
_companies_routes.py / _master_excel_routes.py / _company_assets_routes.py
/ _users_routes.py already use for those, so an onboarded company is
indistinguishable from one set up by hand.

Every table here is super_admin-only (see server/migrations/
0012_company_onboarding.sql) - a session has no company_id to scope by
until publish creates one - so every route below uses
get_connection(user_id=..., role=...) with no company_id, same shape
_companies_routes.py already uses for company-less super_admin
operations."""
import io
from typing import Optional

import app.quotation_companies as quotation_companies
from app.exceptions import InvalidLogoError
from app.master_excel_generator import build_master_excel
from app.onboarding_extraction import (
    classify_images,
    extract_embedded_images,
    extract_from_pdf,
)
from app.onboarding_merge import find_duplicate_product_groups
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from PIL import Image
from pydantic import BaseModel, Field

from _audit import log_action
from _auth import CurrentUser, require_super_admin
from _company_assets_routes import LOGO_BUCKET
from _company_assets_routes import _storage_path as _company_asset_storage_path
from _db import get_connection
from _errors import handle_app_errors
from _master_excel_routes import BUCKET as MASTER_EXCEL_BUCKET
from _master_excel_routes import _storage_path as _master_excel_storage_path
from _signatures_routes import BUCKET as SIGNATURES_BUCKET
from _signatures_routes import _storage_path as _signature_storage_path
from _storage import upload as storage_upload
from _tempfiles import temp_output_path
from _users_routes import _hash_password

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

DOCUMENTS_BUCKET = "onboarding-documents"

# The company profile fields onboarding extracts/reviews - drives both the
# extraction schema mapping and the publish-time companies insert.
COMPANY_FIELDS = ["company_name", "company_code", "industry", "address", "email", "phone", "website", "vat_number"]


def _document_storage_path(session_id: str, document_id: str, filename: str) -> str:
    return f"{session_id}/{document_id}/{filename}"


def _session_out(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "status": row["status"],
        "companyId": str(row["company_id"]) if row["company_id"] else None,
        "createdAt": row["created_at"].isoformat(),
        "publishedAt": row["published_at"].isoformat() if row["published_at"] else None,
    }


def _document_out(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "filename": row["filename"],
        "documentType": row["document_type"],
        "extractionStatus": row["extraction_status"],
        "extractionError": row["extraction_error"],
        "uploadedAt": row["uploaded_at"].isoformat(),
    }


def _field_out(row: dict) -> dict:
    return {
        "fieldName": row["field_name"],
        "extractedValue": row["extracted_value"],
        "confidence": row["confidence"],
        "reviewedValue": row["reviewed_value"],
        "sourceDocumentId": str(row["source_document_id"]) if row["source_document_id"] else None,
    }


def _product_out(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "productName": row["product_name"],
        "code": row["code"],
        "description": row["description"],
        "brand": row["brand"],
        "model": row["model"],
        "origin": row["origin"],
        "category": row["category"],
        "warranty": row["warranty"],
        "price": float(row["price"]),
        "mrp": float(row["mrp"]),
        "confidence": row["confidence"],
        "duplicateOfProductId": str(row["duplicate_of_product_id"]) if row["duplicate_of_product_id"] else None,
        "included": row["included"],
        "sourceDocumentId": str(row["source_document_id"]) if row["source_document_id"] else None,
    }


@router.post("/sessions")
@handle_app_errors
def create_session(request: Request, current_user: CurrentUser = Depends(require_super_admin)):
    with get_connection(user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "insert into onboarding_sessions (created_by) values (%s) "
                "returning id, status, company_id, created_at, published_at",
                (current_user.id,),
            )
            row = cur.fetchone()
    log_action(current_user, None, "start_onboarding", "onboarding_session", str(row["id"]), request)
    return _session_out(row)


@router.get("/sessions/{session_id}")
@handle_app_errors
def get_session(session_id: str, current_user: CurrentUser = Depends(require_super_admin)):
    with get_connection(user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select id, status, company_id, created_at, published_at from onboarding_sessions where id = %s",
                (session_id,),
            )
            session = cur.fetchone()
            if session is None:
                raise HTTPException(status_code=404, detail={"message": "Onboarding session not found."})
            cur.execute(
                "select id, filename, document_type, extraction_status, extraction_error, uploaded_at "
                "from onboarding_documents where session_id = %s order by uploaded_at",
                (session_id,),
            )
            documents = cur.fetchall()
            cur.execute(
                "select field_name, extracted_value, confidence, reviewed_value, source_document_id "
                "from onboarding_company_fields where session_id = %s",
                (session_id,),
            )
            fields = cur.fetchall()
            cur.execute(
                "select id, product_name, code, description, brand, model, origin, category, warranty, "
                "price, mrp, confidence, duplicate_of_product_id, included, source_document_id "
                "from onboarding_products where session_id = %s order by product_name",
                (session_id,),
            )
            products = cur.fetchall()

    # Cross-document duplicate detection is computed on read, not stored -
    # it's cheap over a session's product count and always reflects the
    # current set (e.g. after a reviewer excludes one of a pair). Only
    # still-included products are grouped, so a duplicate the reviewer
    # already resolved (excluded) stops being flagged.
    included_products = [p for p in products if p["included"]]
    groups = find_duplicate_product_groups(
        [{"product_name": p["product_name"], "code": p["code"]} for p in included_products]
    )
    duplicate_groups = [[str(included_products[i]["id"]) for i in group] for group in groups]

    return {
        "session": _session_out(session),
        "documents": [_document_out(row) for row in documents],
        "companyFields": [_field_out(row) for row in fields],
        "products": [_product_out(row) for row in products],
        "duplicateGroups": duplicate_groups,
    }


def _run_extraction(current_user: CurrentUser, session_id: str, document_id: str, pdf_bytes: bytes, filename: str) -> None:
    """Runs synchronously inside the upload request - document counts per
    onboarding session are small (a handful of past quotations/catalogues),
    so there's no need for a background job queue, and the wizard needs
    results as soon as the upload finishes anyway. Every get_connection()
    call here must carry the caller's identity (not just company_id, which
    doesn't exist yet for these rows) - onboarding tables' RLS policy is a
    bare is_super_admin check (see 0012_company_onboarding.sql), and that
    flag is only set when role is passed through, same as everywhere else
    in this codebase."""
    with get_connection(user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "update onboarding_documents set extraction_status = 'processing' where id = %s", (document_id,)
            )

    try:
        extraction = extract_from_pdf(pdf_bytes, filename)
        images = extract_embedded_images(pdf_bytes)
        classifications = classify_images(images)
        logo_bytes = None
        signature_bytes = None
        for item in classifications:
            if item.role == "logo" and item.confidence >= 0.5 and logo_bytes is None:
                logo_bytes = images[item.image_index]
            elif item.role == "signature" and item.confidence >= 0.5 and signature_bytes is None:
                signature_bytes = images[item.image_index]
    except Exception as exc:  # noqa: BLE001 - surfaced to the wizard, not a 500
        with get_connection(user_id=current_user.id, role=current_user.role) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "update onboarding_documents set extraction_status = 'failed', extraction_error = %s where id = %s",
                    (str(exc), document_id),
                )
        return

    with get_connection(user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            for name in COMPANY_FIELDS:
                field_value = getattr(extraction.company, name)
                if field_value.value is None:
                    continue
                cur.execute(
                    "insert into onboarding_company_fields (session_id, field_name, extracted_value, confidence, source_document_id) "
                    "values (%s, %s, %s, %s, %s) "
                    "on conflict (session_id, field_name) do update set "
                    "extracted_value = excluded.extracted_value, confidence = excluded.confidence, "
                    "source_document_id = excluded.source_document_id "
                    "where excluded.confidence > onboarding_company_fields.confidence",
                    (session_id, name, field_value.value, field_value.confidence, document_id),
                )
            for product in extraction.products:
                if not product.product_name.value:
                    continue
                cur.execute(
                    "insert into onboarding_products "
                    "(session_id, product_name, code, description, brand, model, origin, category, warranty, "
                    "price, mrp, confidence, source_document_id) "
                    "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        session_id,
                        product.product_name.value,
                        product.code.value or "",
                        product.description.value or "",
                        product.brand.value or "",
                        product.model.value or "",
                        product.origin.value or "",
                        product.category.value or "",
                        product.warranty.value or "",
                        _to_number(product.price.value),
                        _to_number(product.mrp.value),
                        min(
                            product.product_name.confidence,
                            product.price.confidence if product.price.value else 1.0,
                        ),
                        document_id,
                    ),
                )
            if logo_bytes is not None:
                path = f"{session_id}/{document_id}/logo.png"
                storage_upload(DOCUMENTS_BUCKET, path, logo_bytes, "image/png")
                cur.execute(
                    "insert into onboarding_company_fields (session_id, field_name, extracted_value, confidence, source_document_id) "
                    "values (%s, 'logo_storage_path', %s, %s, %s) "
                    "on conflict (session_id, field_name) do nothing",
                    (session_id, path, 0.7, document_id),
                )
            if signature_bytes is not None:
                path = f"{session_id}/{document_id}/signature.png"
                storage_upload(DOCUMENTS_BUCKET, path, signature_bytes, "image/png")
                cur.execute(
                    "insert into onboarding_company_fields (session_id, field_name, extracted_value, confidence, source_document_id) "
                    "values (%s, 'signature_storage_path', %s, %s, %s) "
                    "on conflict (session_id, field_name) do nothing",
                    (session_id, path, 0.7, document_id),
                )
            cur.execute("update onboarding_documents set extraction_status = 'done' where id = %s", (document_id,))


def _to_number(value: Optional[str]) -> float:
    if not value:
        return 0.0
    cleaned = str(value).replace(",", "")
    for token in ("Rs.", "Rs", "NRs", "₹", "$"):
        cleaned = cleaned.replace(token, "")
    try:
        return float(cleaned.strip())
    except ValueError:
        return 0.0


@router.post("/sessions/{session_id}/documents")
@handle_app_errors
def upload_document(
    session_id: str, request: Request, file: UploadFile = File(...), current_user: CurrentUser = Depends(require_super_admin)
):
    content_type = file.content_type or ""
    if content_type == "application/pdf":
        document_type = "quotation"
    elif content_type.startswith("image/"):
        document_type = "image"
    else:
        raise HTTPException(
            status_code=400,
            detail={"message": "Only PDF documents and images are supported for AI onboarding right now."},
        )

    content = file.file.read()
    filename = file.filename or "document.pdf"

    with get_connection(user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute("select 1 from onboarding_sessions where id = %s", (session_id,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail={"message": "Onboarding session not found."})
            cur.execute(
                "insert into onboarding_documents (session_id, filename, storage_path, document_type) "
                "values (%s, %s, '', %s) returning id",
                (session_id, filename, document_type),
            )
            document_id = str(cur.fetchone()["id"])
            storage_path = _document_storage_path(session_id, document_id, filename)
            cur.execute("update onboarding_documents set storage_path = %s where id = %s", (storage_path, document_id))

    storage_upload(DOCUMENTS_BUCKET, storage_path, content, content_type)

    if content_type == "application/pdf":
        _run_extraction(current_user, session_id, document_id, content, filename)
    else:
        # A directly-uploaded image (not a PDF) skips text extraction and
        # goes straight through classification, same as an image pulled
        # out of a PDF.
        with get_connection(user_id=current_user.id, role=current_user.role) as conn:
            with conn.cursor() as cur:
                cur.execute("update onboarding_documents set extraction_status = 'processing' where id = %s", (document_id,))
        try:
            classifications = classify_images([content])
        except Exception as exc:  # noqa: BLE001
            with get_connection(user_id=current_user.id, role=current_user.role) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "update onboarding_documents set extraction_status = 'failed', extraction_error = %s where id = %s",
                        (str(exc), document_id),
                    )
        else:
            with get_connection(user_id=current_user.id, role=current_user.role) as conn:
                with conn.cursor() as cur:
                    if classifications and classifications[0].role in ("logo", "signature"):
                        field_name = f"{classifications[0].role}_storage_path"
                        cur.execute(
                            "insert into onboarding_company_fields (session_id, field_name, extracted_value, confidence, source_document_id) "
                            "values (%s, %s, %s, %s, %s) on conflict (session_id, field_name) do nothing",
                            (session_id, field_name, storage_path, classifications[0].confidence, document_id),
                        )
                    cur.execute("update onboarding_documents set extraction_status = 'done' where id = %s", (document_id,))

    log_action(current_user, None, "upload_onboarding_document", "onboarding_document", document_id, request, {"filename": filename})
    return get_session(session_id, current_user)


class UpdateFieldRequest(BaseModel):
    field_name: str
    reviewed_value: Optional[str] = None


@router.patch("/sessions/{session_id}/fields")
@handle_app_errors
def update_field(session_id: str, payload: UpdateFieldRequest, current_user: CurrentUser = Depends(require_super_admin)):
    with get_connection(user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "insert into onboarding_company_fields (session_id, field_name, reviewed_value, confidence) "
                "values (%s, %s, %s, 0) "
                "on conflict (session_id, field_name) do update set reviewed_value = excluded.reviewed_value",
                (session_id, payload.field_name, payload.reviewed_value),
            )
    return get_session(session_id, current_user)


class UpdateProductRequest(BaseModel):
    product_name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    origin: Optional[str] = None
    category: Optional[str] = None
    warranty: Optional[str] = None
    price: Optional[float] = None
    mrp: Optional[float] = None
    included: Optional[bool] = None


@router.patch("/sessions/{session_id}/products/{product_id}")
@handle_app_errors
def update_product(
    session_id: str, product_id: str, payload: UpdateProductRequest, current_user: CurrentUser = Depends(require_super_admin)
):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail={"message": "Nothing to update."})
    set_clause = ", ".join(f"{column} = %s" for column in updates)
    values = list(updates.values()) + [product_id, session_id]
    with get_connection(user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"update onboarding_products set {set_clause} where id = %s and session_id = %s returning id",
                values,
            )
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail={"message": "Product not found."})
    return get_session(session_id, current_user)


@router.post("/sessions/{session_id}/products/{product_id}/mark-duplicate")
@handle_app_errors
def mark_duplicate(
    session_id: str, product_id: str, duplicate_of_product_id: str, current_user: CurrentUser = Depends(require_super_admin)
):
    with get_connection(user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "update onboarding_products set duplicate_of_product_id = %s, included = false "
                "where id = %s and session_id = %s returning id",
                (duplicate_of_product_id, product_id, session_id),
            )
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail={"message": "Product not found."})
    return get_session(session_id, current_user)


class PublishRequest(BaseModel):
    slug: str = Field(min_length=1, pattern=r"^[a-z0-9_]+$")
    admin_username: str = Field(min_length=1)
    admin_full_name: str = Field(min_length=1)
    admin_password: str = Field(min_length=8)


@router.post("/sessions/{session_id}/publish")
@handle_app_errors
def publish_session(
    session_id: str, payload: PublishRequest, request: Request, current_user: CurrentUser = Depends(require_super_admin)
):
    with get_connection(user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select id, status from onboarding_sessions where id = %s", (session_id,)
            )
            session = cur.fetchone()
            if session is None:
                raise HTTPException(status_code=404, detail={"message": "Onboarding session not found."})
            if session["status"] == "published":
                raise HTTPException(status_code=400, detail={"message": "This session has already been published."})

            cur.execute(
                "select field_name, extracted_value, reviewed_value from onboarding_company_fields where session_id = %s",
                (session_id,),
            )
            field_rows = cur.fetchall()
            field_values = {row["field_name"]: row["reviewed_value"] or row["extracted_value"] for row in field_rows}

            if not field_values.get("company_name"):
                raise HTTPException(
                    status_code=400,
                    detail={"message": "Company name has no value yet - fill it in before publishing."},
                )

            cur.execute("select 1 from companies where slug = %s", (payload.slug,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail={"message": "That company slug is already in use."})

            cur.execute(
                "insert into companies (slug, display_name, company_code, industry, address, email, phone, website, vat_number) "
                "values (%s, %s, %s, %s, %s, %s, %s, %s, %s) returning id",
                (
                    payload.slug,
                    field_values.get("company_name"),
                    field_values.get("company_code"),
                    field_values.get("industry"),
                    field_values.get("address"),
                    field_values.get("email"),
                    field_values.get("phone"),
                    field_values.get("website"),
                    field_values.get("vat_number"),
                ),
            )
            company_id = str(cur.fetchone()["id"])

            cur.execute(
                "select id, product_name, code, description, brand, model, origin, category, warranty, price, mrp "
                "from onboarding_products where session_id = %s and included order by product_name",
                (session_id,),
            )
            products = cur.fetchall()

    # Logo/signature: promote the onboarding-documents copy into the real
    # company-scoped buckets via the same paths _company_assets_routes.py /
    # _signatures_routes.py use, so a downloaded/re-uploaded asset later
    # behaves identically to one uploaded through those pages directly.
    from _storage import download as storage_download

    logo_path = field_values.get("logo_storage_path")
    if logo_path:
        try:
            logo_bytes = storage_download(DOCUMENTS_BUCKET, logo_path)
            with Image.open(io.BytesIO(logo_bytes)) as img:
                img.verify()
            dest_path = _company_asset_storage_path(company_id, "logo.png")
            storage_upload(LOGO_BUCKET, dest_path, logo_bytes, "image/png")
            with get_connection(company_id=company_id, user_id=current_user.id, role=current_user.role) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "update companies set logo_storage_path = %s, logo_uploaded_at = now(), logo_uploaded_by = %s where id = %s",
                        (dest_path, current_user.id, company_id),
                    )
        except (InvalidLogoError, Exception):  # noqa: BLE001 - a bad extracted logo shouldn't block publish
            pass

    signature_path = field_values.get("signature_storage_path")
    if signature_path:
        try:
            signature_bytes = storage_download(DOCUMENTS_BUCKET, signature_path)
            with Image.open(io.BytesIO(signature_bytes)) as img:
                img.verify()
            with get_connection(company_id=company_id, user_id=current_user.id, role=current_user.role) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "insert into signatures (company_id, name, designation, image_storage_path, created_by) "
                        "values (%s, %s, '', '', %s) returning id",
                        (company_id, field_values.get("company_name") or "Authorized Signatory", current_user.id),
                    )
                    signature_id = str(cur.fetchone()["id"])
                    dest_path = _signature_storage_path(company_id, signature_id, "signature.png")
                    storage_upload(SIGNATURES_BUCKET, dest_path, signature_bytes, "image/png")
                    cur.execute("update signatures set image_storage_path = %s where id = %s", (dest_path, signature_id))
        except Exception:  # noqa: BLE001 - same reasoning as the logo above
            pass

    # Master Excel - build it from the reviewed, deduped product list and
    # push it through the exact same insert upload_master_excel() uses.
    products_for_excel = [
        {
            "product_name": p["product_name"],
            "price": float(p["price"]),
            "code": p["code"],
            "description": p["description"],
            "brand": p["brand"],
            "model": p["model"],
            "origin": p["origin"],
            "category": p["category"],
            "warranty": p["warranty"],
            "mrp": float(p["mrp"]),
        }
        for p in products
    ]
    with temp_output_path(suffix=".xlsx") as out_path:
        build_master_excel(out_path, products_for_excel)
        excel_bytes = out_path.read_bytes()
    excel_filename = f"{payload.slug}_master.xlsx"
    excel_storage_path = _master_excel_storage_path(company_id, excel_filename)
    storage_upload(MASTER_EXCEL_BUCKET, excel_storage_path, excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with get_connection(company_id=company_id, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "insert into master_excel (company_id, storage_path, original_filename, uploaded_by, file_size) "
                "values (%s, %s, %s, %s, %s)",
                (company_id, excel_storage_path, excel_filename, current_user.id, len(excel_bytes)),
            )

    # First admin user, so the new company is actually usable immediately.
    with get_connection(company_id=company_id, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute("select 1 from users where company_id = %s and username = %s", (company_id, payload.admin_username))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail={"message": "That admin username is already in use."})
            cur.execute(
                "insert into users (company_id, full_name, username, password_hash, role) "
                "values (%s, %s, %s, %s, 'staff') returning id",
                (company_id, payload.admin_full_name, payload.admin_username, _hash_password(payload.admin_password)),
            )
            admin_user_id = str(cur.fetchone()["id"])

    with get_connection(user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "update onboarding_sessions set status = 'published', company_id = %s, published_at = now() where id = %s",
                (company_id, session_id),
            )

    quotation_companies.invalidate_cache()
    log_action(
        current_user, company_id, "publish_onboarding", "onboarding_session", session_id, request,
        {"slug": payload.slug, "product_count": len(products)},
    )

    return {
        "companyId": company_id,
        "slug": payload.slug,
        "productCount": len(products),
        "adminUsername": payload.admin_username,
        "adminUserId": admin_user_id,
    }
