"""Smart Quotation Generator endpoints. Two Excel routes (mirroring
Collection/Inventory's inspect pattern) plus one JSON-body /generate route
- the first non-multipart endpoint in this API, since generating a
quotation never involves a file upload."""
import json
from typing import List, Optional

from app import generic_excel, quotation
from app.exceptions import GenericHeaderDetectionError, InvalidHeaderRowError
from app.quotation import ProductColumnMapping, QuotationCustomer, QuotationItem, QuotationProposal
from app.quotation_companies import get_company
from app.quotation_docx import default_output_filename, render_quotation_docx
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from _auth import require_auth
from _errors import handle_app_errors
from _excel_loading import open_workbook
from _mapping_heuristics import PRODUCT_CANDIDATES, suggest_mapping
from _serialization import mapping_kwargs
from _tempfiles import temp_upload_path

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


@router.post("/products/inspect")
@handle_app_errors
def inspect_products(
    file: UploadFile = File(...),
    sheet: Optional[str] = Form(None),
    header_row: Optional[int] = Form(None),
):
    with temp_upload_path(file) as path:
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
    file: UploadFile = File(...),
    sheet: str = Form(...),
    mapping: str = Form(...),
    header_row: Optional[int] = Form(None),
):
    with temp_upload_path(file) as path:
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


@router.post("/generate")
@handle_app_errors
def generate(payload: GenerateQuotationRequest):
    company = get_company(payload.company_id)
    customer = QuotationCustomer(**payload.customer.model_dump())
    proposal = QuotationProposal(**payload.proposal.model_dump())
    items = [QuotationItem(**item.model_dump()) for item in payload.items]

    quotation.validate_quotation(customer, items)
    totals = quotation.compute_totals(items, vat_rate=company.default_vat_rate)
    content = render_quotation_docx(company, customer, proposal, items, totals)
    filename = default_output_filename(customer, proposal)

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
