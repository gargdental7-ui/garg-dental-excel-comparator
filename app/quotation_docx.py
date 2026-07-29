"""Renders a Quotation into the company's Word proposal template via
docxtpl. Originally the template was always the reference Garg Dental
proposal document read from a static file in app/quotation_templates/
(see scripts/build_quotation_template.py for how that one was built);
Phase C of the multi-tenant redesign moved templates to a per-company
Storage upload instead, so render_quotation_docx now takes the template
as bytes - the caller (server/_quotation_routes.py) is responsible for
fetching those bytes from Storage, this module stays storage-agnostic and
only ever fills in data. It never constructs document layout from
scratch, so formatting stays byte-identical to whatever template was
uploaded outside of the fields that are actually meant to change.
"""
import base64
import binascii
import io
import logging
import re
from datetime import datetime
from typing import Optional

from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage
from PIL import Image, UnidentifiedImageError

from .quotation import ItemTotal, compute_item_total
from .quotation_companies import CompanyProfile

logger = logging.getLogger("gargdental.quotation_docx")

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


def _normalize_image_to_png(raw_bytes):
    """Word's native image support for WEBP is inconsistent across
    versions (older Word can show a broken-image icon), while PNG is
    universally safe - so every uploaded image, regardless of source
    format (PNG/JPEG/WEBP/...), gets normalized to PNG before embedding.
    Returns None (rather than raising) for anything Pillow can't decode,
    so a corrupt/unsupported image degrades to "no image" instead of
    failing the whole generation."""
    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
            output = io.BytesIO()
            img.save(output, format="PNG")
            return output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError):
        logger.warning("Could not decode product image - omitting it from the document.")
        return None


def _build_item_context(tpl, item):
    image = None
    raw_image = _decode_image(item.image)
    if raw_image:
        png_bytes = _normalize_image_to_png(raw_image)
        if png_bytes:
            image = InlineImage(tpl, io.BytesIO(png_bytes), width=PRODUCT_IMAGE_WIDTH)

    item_total: ItemTotal = compute_item_total(item)
    return {
        "product_name": item.product_name,
        "model": item.model,
        "brand": item.brand,
        "origin": item.origin,
        "image": image,
        "features": [f for f in item.features if f],
        "warranty": item.warranty,
        "mrp_formatted": _fmt_currency(item.mrp) if item.mrp else "",
        "specifications": [s for s in item.specifications if s],
        "accessories": [a for a in item.accessories if a],
        "installation_notes": item.installation_notes,
        "additional_notes": item.additional_notes,
        "rate_formatted": _fmt_currency(item_total.line_total),
    }


LOGO_IMAGE_WIDTH = Mm(35)
SIGNATURE_IMAGE_WIDTH = Mm(35)


def render_quotation_docx(
    company: CompanyProfile,
    customer,
    proposal,
    items,
    totals,
    template_bytes: bytes,
    logo_bytes: Optional[bytes] = None,
    signature: Optional[dict] = None,
) -> bytes:
    """template_bytes/logo_bytes come from Supabase Storage (fetched by the
    caller, not this module) via server/_company_assets_routes.py.
    `signature`, when provided, is {"image_bytes": bytes, "name": str,
    "designation": str} from server/_signatures_routes.py (Phase D) -
    optional because not every quotation has one selected. Both logo and
    signature are only visible in the output if the uploaded template
    actually references the corresponding tag ({{ company_logo }},
    {{ signature.image }} etc.) - see docs/quotation-template-tags.md."""
    tpl = DocxTemplate(io.BytesIO(template_bytes))

    logo_image = None
    if logo_bytes:
        png_bytes = _normalize_image_to_png(logo_bytes)
        if png_bytes:
            logo_image = InlineImage(tpl, io.BytesIO(png_bytes), width=LOGO_IMAGE_WIDTH)

    signature_context = None
    if signature:
        signature_image = None
        raw_signature_image = signature.get("image_bytes")
        if raw_signature_image:
            png_bytes = _normalize_image_to_png(raw_signature_image)
            if png_bytes:
                signature_image = InlineImage(tpl, io.BytesIO(png_bytes), width=SIGNATURE_IMAGE_WIDTH)
        signature_context = {
            "image": signature_image,
            "name": signature.get("name", ""),
            "designation": signature.get("designation", ""),
        }

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
        "company_logo": logo_image,
        "signature": signature_context,
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


def default_output_filename(company: CompanyProfile, customer, proposal) -> str:
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_company = re.sub(r"[^A-Za-z0-9]+", "_", company.display_name).strip("_")
    safe_name = re.sub(r"[^A-Za-z0-9]+", "_", customer.customer_name or "Quotation").strip("_")
    return f"{safe_company}_Quotation_{safe_name}_{date_str}.docx"
