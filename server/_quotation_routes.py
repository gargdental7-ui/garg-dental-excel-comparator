"""Smart Quotation Generator endpoints. Two Excel routes (mirroring
Collection/Inventory's inspect pattern) plus one JSON-body /generate route
- the first non-multipart endpoint in this API, since generating a
quotation never involves a file upload."""
import json
from typing import List, Optional

from app import quotation
from app.quotation import ProductColumnMapping, QuotationCustomer, QuotationItem, QuotationProposal
from app.quotation_companies import get_company
from app.quotation_docx import default_output_filename, render_quotation_docx
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from _auth import require_auth
from _errors import handle_app_errors
from _excel_loading import load_sheet, open_workbook
from _mapping_heuristics import PRODUCT_CANDIDATES, suggest_mapping
from _serialization import mapping_kwargs
from _tempfiles import temp_upload_path

router = APIRouter(prefix="/api/quotation", dependencies=[Depends(require_auth)])


def _load(file: UploadFile, sheet: Optional[str]):
    with temp_upload_path(file) as path:
        workbook = open_workbook(path)
        sheet_names = workbook.sheetnames
        selected_sheet = sheet or sheet_names[0]
        data = load_sheet(workbook, selected_sheet)
    return sheet_names, selected_sheet, data


@router.post("/products/inspect")
@handle_app_errors
def inspect_products(file: UploadFile = File(...), sheet: Optional[str] = Form(None)):
    sheet_names, selected_sheet, data = _load(file, sheet)
    return {
        "sheet_names": sheet_names,
        "selected_sheet": selected_sheet,
        "headers": data.headers,
        "row_count": len(data.rows),
        "suggested_mapping": suggest_mapping(data.headers, PRODUCT_CANDIDATES),
    }


@router.post("/products/import")
@handle_app_errors
def import_products(file: UploadFile = File(...), sheet: str = Form(...), mapping: str = Form(...)):
    _, _, data = _load(file, sheet)
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
