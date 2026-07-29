"""Smart Quotation Generator endpoints. Two Excel routes (mirroring
Collection/Inventory's inspect pattern) plus one JSON-body /generate route
- the first non-multipart endpoint in this API, since generating a
quotation never involves a file upload."""
import json
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List, Optional

from app import generic_excel, quotation
from app.exceptions import GenericHeaderDetectionError, InvalidHeaderRowError, MissingUploadedFileError
from app.quotation import ProductColumnMapping, QuotationCustomer, QuotationItem, QuotationProposal
from app.quotation_companies import get_company
from app.quotation_docx import default_output_filename, render_quotation_docx
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from _audit import log_action
from _auth import CurrentUser, require_auth
from _db import get_connection
from _errors import handle_app_errors
from _excel_loading import open_workbook
from _master_excel_routes import fetch_master_excel_bytes
from _mapping_heuristics import PRODUCT_CANDIDATES, suggest_mapping
from _pdf_conversion import convert_docx_to_pdf
from _serialization import mapping_kwargs
from _storage import upload as storage_upload
from _tempfiles import temp_download_path, temp_upload_path

logger = logging.getLogger("gargdental.quotation_persistence")

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MEDIA_TYPE = "application/pdf"

router = APIRouter(prefix="/api/quotation", dependencies=[Depends(require_auth)])

# Matches the "AUTOMATIC HEADER DETECTION" spec: check row 1 first, then
# scan up to the first 20 rows before giving up and asking the user to pick
# the header row manually - detection failing here is never fatal (see
# _resolve_header_row), unlike Collection/Inventory's hard-fail behavior.
PRODUCT_HEADER_SCAN_ROWS = 20
PRODUCT_PREVIEW_ROWS = 20


def _resolve_header_row(worksheet, header_row: Optional[int]):
    """Returns (effective_row, detected_row): the row to actually read
    headers from, and the row auto-detection would have picked (for
    display, even when the caller overrides it). effective_row is the
    caller's explicit choice when given (validated against the sheet's
    actual row count), otherwise the auto-detected row, or None if neither
    is available. Only an out-of-range manual row raises - a failed
    auto-detection alone never does, so the caller can fall back to
    showing the preview and asking the user to pick a row by hand."""
    detected = generic_excel.detect_header_row_index(worksheet, max_scan_rows=PRODUCT_HEADER_SCAN_ROWS)
    detected_row = detected[0] if detected else None

    if header_row is not None:
        if header_row < 1 or header_row > worksheet.max_row:
            raise InvalidHeaderRowError(header_row, worksheet.max_row)
        return header_row, detected_row

    return detected_row, detected_row


@contextmanager
def _resolve_excel_path(file: Optional[UploadFile], excel_source: str, current_user: CurrentUser):
    """Feeds either a fresh upload or the company's stored Master Excel into
    the same temp-file-backed path every open_workbook() caller already
    expects - open_workbook/generic_excel/_mapping_heuristics need no
    changes at all for the Master Excel source, they never know which one
    they got. current_user.company_id (not a client-supplied value) scopes
    the master-excel lookup, so a request can't read another company's
    file by passing a different company_id."""
    if excel_source == "company_master":
        content = fetch_master_excel_bytes(current_user)
        with temp_download_path(content) as path:
            yield path
    else:
        if file is None:
            raise MissingUploadedFileError()
        with temp_upload_path(file) as path:
            yield path


@router.post("/products/inspect")
@handle_app_errors
def inspect_products(
    file: Optional[UploadFile] = File(None),
    excel_source: str = Form("upload"),
    sheet: Optional[str] = Form(None),
    header_row: Optional[int] = Form(None),
    current_user: CurrentUser = Depends(require_auth),
):
    with _resolve_excel_path(file, excel_source, current_user) as path:
        workbook = open_workbook(path)
        sheet_names = workbook.sheetnames
        selected_sheet = sheet or sheet_names[0]
        worksheet = workbook[selected_sheet]

        preview_rows = generic_excel.read_preview_rows(worksheet, max_rows=PRODUCT_PREVIEW_ROWS)
        effective_row, detected_row = _resolve_header_row(worksheet, header_row)

        if effective_row is None:
            headers, row_count = [], 0
        else:
            data = generic_excel.load_generic_sheet_at_row(workbook, selected_sheet, effective_row)
            headers, row_count = data.headers, len(data.rows)

    return {
        "sheet_names": sheet_names,
        "selected_sheet": selected_sheet,
        "preview_rows": preview_rows,
        "detected_header_row": detected_row,
        "header_row": effective_row,
        "header_detected": detected_row is not None,
        "headers": headers,
        "row_count": row_count,
        "suggested_mapping": suggest_mapping(headers, PRODUCT_CANDIDATES),
    }


@router.post("/products/import")
@handle_app_errors
def import_products(
    sheet: str = Form(...),
    mapping: str = Form(...),
    file: Optional[UploadFile] = File(None),
    excel_source: str = Form("upload"),
    header_row: Optional[int] = Form(None),
    current_user: CurrentUser = Depends(require_auth),
):
    with _resolve_excel_path(file, excel_source, current_user) as path:
        workbook = open_workbook(path)
        worksheet = workbook[sheet]
        # header_row is omitted only by callers that never fetched a
        # preview (e.g. older clients) - fall back to auto-detect so those
        # imports keep working exactly as before; GenericHeaderDetectionError
        # still surfaces if that fails, same as the old behavior.
        effective_row, _detected_row = _resolve_header_row(worksheet, header_row)
        if effective_row is None:
            raise GenericHeaderDetectionError("uploaded file")
        data = generic_excel.load_generic_sheet_at_row(workbook, sheet, effective_row)

    mapping_obj = ProductColumnMapping(**mapping_kwargs(ProductColumnMapping, json.loads(mapping)))
    products = quotation.map_product_rows(data.headers, data.rows, mapping_obj)
    # Not capped by a preview limit like the diff/comparison routes -
    # this *is* the catalog the user browses/selects from, and nothing is
    # persisted server-side, so the whole mapped set has to reach the
    # client in one shot.
    return {"products": products, "products_total_count": len(products)}


class QuotationCustomerIn(BaseModel):
    customer_name: str
    contact_person: str = ""
    designation: str = ""
    company_name: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
    reference_number: str = ""
    notes: str = ""


class QuotationProposalIn(BaseModel):
    title: str = ""
    subject: str = ""
    quotation_date: str = ""
    validity: str = ""
    prepared_by: str = ""
    currency: str = "NRs"


class QuotationItemIn(BaseModel):
    product_name: str
    price: float
    quantity: float = 1
    code: str = ""
    description: str = ""
    brand: str = ""
    model: str = ""
    origin: str = ""
    category: str = ""
    warranty: str = ""
    mrp: float = 0
    discount_percent: float = 0
    discount_amount: float = 0
    image: Optional[str] = None
    features: List[str] = []
    specifications: List[str] = []
    installation_notes: str = ""
    additional_notes: str = ""
    accessories: List[str] = []
    brochure_note: str = ""


class GenerateQuotationRequest(BaseModel):
    company_id: str = "garg_dental"
    customer: QuotationCustomerIn
    proposal: QuotationProposalIn
    items: List[QuotationItemIn]


def _persist_quotation(current_user: CurrentUser, customer: QuotationCustomer, docx_bytes: bytes, request: Request) -> None:
    """Best-effort save of the just-rendered quotation (DOCX always, PDF
    when conversion succeeds) to Storage + DB. Deliberately never raises -
    "existing functionality must keep working exactly as today" means a
    Storage/DB/CloudConvert outage must not stop a staff member from
    getting their DOCX to send to a customer right now, so any failure
    here is logged and swallowed rather than turned into a 500. A PDF
    conversion failure specifically still lets the DOCX save proceed
    (status="pdf_pending"), since those are independent failure modes."""
    try:
        pdf_bytes = None
        try:
            pdf_bytes = convert_docx_to_pdf(docx_bytes, "quotation.docx")
        except Exception:
            logger.exception("PDF conversion failed; the quotation will still be saved as DOCX-only")

        now = datetime.now(timezone.utc)
        with get_connection(
            company_id=current_user.company_id, user_id=current_user.id, role=current_user.role
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "insert into quote_number_counters (company_id, next_number) values (%s, 2) "
                    "on conflict (company_id) do update set next_number = quote_number_counters.next_number + 1 "
                    "returning (next_number - 1) as quote_number",
                    (current_user.company_id,),
                )
                quote_number = cur.fetchone()["quote_number"]

            folder = f"{current_user.company_id}/Quotations/{now.year}/{now.month:02d}"
            docx_path = f"{folder}/Quote-{quote_number:04d}.docx"
            pdf_path = f"{folder}/Quote-{quote_number:04d}.pdf" if pdf_bytes else None

            storage_upload("quotations-docx", docx_path, docx_bytes, DOCX_MEDIA_TYPE)
            if pdf_bytes:
                storage_upload("quotations-pdf", pdf_path, pdf_bytes, PDF_MEDIA_TYPE)

            with conn.cursor() as cur:
                cur.execute(
                    "insert into quotations "
                    "(company_id, quote_number, customer_name, created_by, status, docx_storage_path, pdf_storage_path) "
                    "values (%s, %s, %s, %s, %s, %s, %s) returning id",
                    (
                        current_user.company_id,
                        quote_number,
                        customer.customer_name,
                        current_user.id,
                        "final" if pdf_bytes else "pdf_pending",
                        docx_path,
                        pdf_path,
                    ),
                )
                quotation_id = cur.fetchone()["id"]

                cur.execute(
                    "insert into quotation_files (quotation_id, kind, storage_path, size_bytes) values (%s, 'docx', %s, %s)",
                    (quotation_id, docx_path, len(docx_bytes)),
                )
                if pdf_bytes:
                    cur.execute(
                        "insert into quotation_files (quotation_id, kind, storage_path, size_bytes) values (%s, 'pdf', %s, %s)",
                        (quotation_id, pdf_path, len(pdf_bytes)),
                    )
        log_action(
            current_user, "create_quotation", "quotation", str(quotation_id), request,
            {"quote_number": quote_number, "customer_name": customer.customer_name},
        )
    except Exception:
        logger.exception("Failed to persist quotation; the DOCX response to the user is unaffected")


@router.post("/generate")
@handle_app_errors
def generate(payload: GenerateQuotationRequest, request: Request, current_user: CurrentUser = Depends(require_auth)):
    company = get_company(payload.company_id)
    customer = QuotationCustomer(**payload.customer.model_dump())
    proposal = QuotationProposal(**payload.proposal.model_dump())
    items = [QuotationItem(**item.model_dump()) for item in payload.items]

    quotation.validate_quotation(customer, items)
    totals = quotation.compute_totals(items, vat_rate=company.default_vat_rate)
    content = render_quotation_docx(company, customer, proposal, items, totals)
    filename = default_output_filename(customer, proposal)

    _persist_quotation(current_user, customer, content, request)

    return Response(
        content=content,
        media_type=DOCX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
