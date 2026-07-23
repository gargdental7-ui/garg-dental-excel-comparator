"""Renders a Quotation into the company's Word proposal template via
docxtpl. The template IS the reference Garg Dental proposal document
(app/quotation_templates/), minimally edited in place with Jinja
placeholders - see scripts/build_quotation_template.py for how it was
built. This module only ever fills in data; it never constructs document
layout from scratch, so formatting stays byte-identical to the reference
outside of the fields that are actually meant to change.
"""
import base64
import binascii
import io
import re
from datetime import datetime

from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage

from .quotation import ItemTotal, compute_item_total
from .quotation_companies import CompanyProfile

# Roughly matches the reference document's own embedded product image width
# (~65mm) so a real photo doesn't dominate or shrink oddly inside the cell.
PRODUCT_IMAGE_WIDTH = Mm(55)


def _fmt_currency(value: float) -> str:
    return f"{value:,.2f}"


def _decode_image(data_url):
    """`data_url` is a "data:image/png;base64,...." string from the
    browser's FileReader - nothing is ever stored server-side, it's
    decoded straight into the render and discarded."""
    if not data_url:
        return None
    match = re.match(r"^data:image/[^;]+;base64,(.+)$", data_url, re.DOTALL)
    encoded = match.group(1) if match else data_url
    try:
        return base64.b64decode(encoded)
    except (ValueError, binascii.Error):
        return None


def _build_item_context(tpl, item):
    image = None
    raw_image = _decode_image(item.image)
    if raw_image:
        image = InlineImage(tpl, io.BytesIO(raw_image), width=PRODUCT_IMAGE_WIDTH)

    item_total: ItemTotal = compute_item_total(item)
    return {
        "product_name": item.product_name,
        "model": item.model,
        "brand": item.brand,
        "origin": item.origin,
        "image": image,
        "features": [f for f in item.features if f],
        "warranty": item.warranty,
        "specifications": [s for s in item.specifications if s],
        "accessories": [a for a in item.accessories if a],
        "installation_notes": item.installation_notes,
        "additional_notes": item.additional_notes,
        "rate_formatted": _fmt_currency(item_total.line_total),
    }


def render_quotation_docx(company: CompanyProfile, customer, proposal, items, totals) -> bytes:
    tpl = DocxTemplate(str(company.template_path))

    context = {
        "proposal": {
            "title": proposal.title,
            "subject": proposal.subject,
            "quotation_date": proposal.quotation_date,
        },
        "customer": {
            "designation": customer.designation,
            "company_name": customer.company_name or customer.customer_name,
            "address": customer.address,
            "notes": customer.notes,
            "reference_number": customer.reference_number,
        },
        "company": {"terms": company.terms_and_conditions},
        "items": [_build_item_context(tpl, item) for item in items],
        "totals": {
            "subtotal_formatted": _fmt_currency(totals.subtotal),
            "discount_formatted": _fmt_currency(totals.discount),
            "vat_formatted": _fmt_currency(totals.vat),
            "grand_total_formatted": _fmt_currency(totals.grand_total),
        },
    }

    # autoescape=True is mandatory here, not cosmetic - customer/product
    # text routinely contains "&" (e.g. "Smith & Sons Clinic"). Without
    # it, docxtpl substitutes a raw "&" into the XML, which is invalid
    # there and corrupts unrelated static text elsewhere in the document
    # once lxml's recovery parser has to step in.
    tpl.render(context, autoescape=True)

    buffer = io.BytesIO()
    tpl.save(buffer)
    return buffer.getvalue()


def default_output_filename(customer, proposal) -> str:
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_name = re.sub(r"[^A-Za-z0-9]+", "_", customer.customer_name or "Quotation").strip("_")
    return f"Garg_Dental_Quotation_{safe_name}_{date_str}.docx"
