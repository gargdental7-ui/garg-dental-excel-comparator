"""AI Company Onboarding - extraction engine. Turns an uploaded PDF (a past
quotation, a product catalogue, a brochure) into a structured company
profile + product list via the Claude API, with a per-field confidence
score so the review wizard can flag anything below 85% instead of quietly
trusting it. Fully generic - nothing here should ever reference a specific
company; the same code onboards any company from any documents.

The Messages API is text-out only, so it can't itself return the bytes of
an embedded logo/signature/product photo - extract_embedded_images() pulls
those out of the PDF separately (via pypdf) and classify_images() asks
Claude to label what each one is."""
import base64
import io
import os
from typing import Literal, Optional

import anthropic
from pydantic import BaseModel, Field
from pypdf import PdfReader
from PIL import Image

from .exceptions import AppError

MODEL = "claude-opus-5"

# Below this pixel area an "image" extracted from a PDF is almost always a
# bullet icon, a rule line, or a tracking pixel - not worth a classification
# call.
MIN_IMAGE_PIXELS = 2500  # e.g. 50x50

SYSTEM_PROMPT = """You are an enterprise data-extraction assistant helping onboard a new \
company onto a quotation-management platform. You will be shown a real business document \
(a past quotation, a product catalogue, or a brochure) belonging to a company that is new \
to this platform - you know nothing about this company beyond what is in the document.

Extract two things:
1. The company's own profile (the company that ISSUED this document, not the customer it \
was addressed to): name, a short internal code if one is visible, industry, address, email, \
phone, website, VAT/tax number.
2. Every distinct product or service line item shown, with whatever fields are present: \
name, code/SKU, description, brand, model, country of origin, category, warranty, unit \
price, and MRP/list price if shown.

Rules - these matter more than completeness:
- Extract only what is literally written in the document. Never infer, guess, or fill in a \
plausible-sounding value.
- If a field is not present or not legible, set its value to null and its confidence to 0. \
Do not invent a value to avoid leaving a field empty.
- confidence is your own calibrated estimate (0.0-1.0) that the extracted value is both \
correct and unambiguous in the source document. A clearly printed, unambiguous value should \
score above 0.9. A value you had to infer from context, that appears in inconsistent form \
across the document, or that you are guessing at from poor image quality should score below \
0.85.
- Never invent a product that is not shown in the document, and never invent a price.
- The company profile is about the ISSUER of the document (look at the letterhead, footer, \
or "from" details), not the customer it was quoted to.
"""


class FieldValue(BaseModel):
    value: Optional[str] = None
    confidence: float = Field(ge=0, le=1)


class CompanyProfileExtraction(BaseModel):
    company_name: FieldValue
    company_code: FieldValue
    industry: FieldValue
    address: FieldValue
    email: FieldValue
    phone: FieldValue
    website: FieldValue
    vat_number: FieldValue


class ProductExtractionItem(BaseModel):
    product_name: FieldValue
    code: FieldValue
    description: FieldValue
    brand: FieldValue
    model: FieldValue
    origin: FieldValue
    category: FieldValue
    warranty: FieldValue
    price: FieldValue
    mrp: FieldValue


class DocumentExtraction(BaseModel):
    company: CompanyProfileExtraction
    products: list[ProductExtractionItem]


class ExtractionUnavailableError(AppError):
    def __init__(self):
        super().__init__("AI extraction is not configured on this server (missing ANTHROPIC_API_KEY).")


class ExtractionRefusedError(AppError):
    def __init__(self, filename: str):
        super().__init__(f"The AI declined to process '{filename}'. Try a different document or extract it manually.")


def _client() -> anthropic.Anthropic:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise ExtractionUnavailableError()
    return anthropic.Anthropic()


def extract_from_pdf(pdf_bytes: bytes, filename: str) -> DocumentExtraction:
    """Sends the whole PDF to Claude as a document content block (native
    layout/table reading, no OCR library needed) and returns a validated
    DocumentExtraction. Raises ExtractionRefusedError if Claude's safety
    classifiers decline the request (stop_reason == 'refusal') rather than
    letting a None parsed_output propagate as a confusing crash."""
    client = _client()
    encoded = base64.standard_b64encode(pdf_bytes).decode("ascii")
    response = client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {"type": "base64", "media_type": "application/pdf", "data": encoded},
                    },
                    {
                        "type": "text",
                        "text": f"Extract the issuing company's profile and every product/service line item from '{filename}'.",
                    },
                ],
            }
        ],
        output_format=DocumentExtraction,
    )
    if getattr(response, "stop_reason", None) == "refusal":
        raise ExtractionRefusedError(filename)
    return response.parsed_output


def extract_embedded_images(pdf_bytes: bytes) -> list[bytes]:
    """Pulls embedded image byte streams out of a PDF via pypdf, re-encoding
    each to PNG for a consistent media_type on the classification call.
    Filters out anything too small to plausibly be a logo/signature/product
    photo (bullet icons, rule lines, tracking pixels)."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    png_images: list[bytes] = []
    for page in reader.pages:
        for image_file in page.images:
            try:
                with Image.open(io.BytesIO(image_file.data)) as img:
                    if img.width * img.height < MIN_IMAGE_PIXELS:
                        continue
                    buffer = io.BytesIO()
                    img.convert("RGB").save(buffer, format="PNG")
                    png_images.append(buffer.getvalue())
            except Exception:
                # Not every embedded stream pypdf finds is a decodable
                # raster image (some are masks/separations) - skip rather
                # than fail the whole document's extraction over one.
                continue
    return png_images


ImageRole = Literal["logo", "signature", "product_photo", "irrelevant"]


class ImageClassificationItem(BaseModel):
    image_index: int
    role: ImageRole
    confidence: float = Field(ge=0, le=1)


class ImageClassificationResult(BaseModel):
    items: list[ImageClassificationItem]


def classify_images(png_images: list[bytes]) -> list[ImageClassificationItem]:
    """One call classifies every image extracted from a document at once
    (cheaper and gives Claude cross-image context, e.g. telling a logo
    apart from a product photo of similar size). Returns an empty list for
    an empty input without spending an API call."""
    if not png_images:
        return []
    client = _client()
    content = [
        {
            "type": "text",
            "text": (
                f"These are {len(png_images)} images extracted from a company's business document, "
                "indexed 0 to " + str(len(png_images) - 1) + " in the order shown below. "
                "Classify each one as exactly one of: logo (the issuing company's own logo/letterhead mark), "
                "signature (a handwritten or scanned signature), product_photo (a photo of a product being sold), "
                "or irrelevant (decorative elements, borders, unrelated icons)."
            ),
        }
    ]
    for image_bytes in png_images:
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64.standard_b64encode(image_bytes).decode("ascii"),
                },
            }
        )
    response = client.messages.parse(
        model=MODEL,
        max_tokens=4096,
        system="You are classifying images extracted from a business document for a company-onboarding tool.",
        messages=[{"role": "user", "content": content}],
        output_format=ImageClassificationResult,
    )
    if getattr(response, "stop_reason", None) == "refusal":
        return []
    return response.parsed_output.items
