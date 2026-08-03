# Quotation Template Tag Contract

Each company's quotation template is a free-form `.docx` upload (Company Assets → Quotation Template). The system only validates that the uploaded file is a real, openable Word document — it does **not** check that the file contains the right placeholder tags. If a template is missing a tag, that field will simply render blank in the generated quotation; there is no error.

Templates are built with [docxtpl](https://docxtpl.readthedocs.io/), which uses Jinja2 syntax inside the Word document. Below is the full set of variables available in the render context, sourced from `app/quotation_docx.py::render_quotation_docx`.

## Scalar / text tags

| Tag | Description |
|---|---|
| `{{ proposal.title }}` | Quotation title |
| `{{ proposal.subject }}` | Quotation subject line |
| `{{ proposal.quotation_date }}` | Quotation date |
| `{{ proposal.prepared_by }}` | Name of the staff member preparing the quotation |
| `{{ customer.designation }}` | Customer contact's designation |
| `{{ customer.company_name }}` | Customer's company name (falls back to customer name if blank) |
| `{{ customer.address }}` | Customer address |
| `{{ customer.notes }}` | Free-text customer notes |
| `{{ customer.reference_number }}` | Customer reference number |
| `{{ company.terms }}` | List of `(label, text)` pairs — the company's terms & conditions. Iterate with a `{%tr for %}`/`{%p for %}` loop, e.g. `{%p for label, text in company.terms %}{{ label }}: {{ text }}{%p endfor %}` |
| `{{ totals.subtotal_formatted }}` | Formatted subtotal |
| `{{ totals.discount_formatted }}` | Formatted discount |
| `{{ totals.vat_formatted }}` | Formatted VAT |
| `{{ totals.grand_total_formatted }}` | Formatted grand total |

## Images

| Tag | Description |
|---|---|
| `{{ company_logo }}` | Company's uploaded logo (Company Assets → Logo), inline image, 35mm wide. Renders nothing if no logo is uploaded — leave the tag in place, it degrades gracefully. |
| `{{ signature.image }}` | Selected signature's image, inline image, 35mm wide. `None` if no signature was selected when the quotation was generated. |
| `{{ signature.name }}` | Selected signature's name |
| `{{ signature.designation }}` | Selected signature's designation |

## Items (line items) — loop over `items`

Each entry in `items` has:

| Tag (inside the loop) | Description |
|---|---|
| `{{ product_name }}` | Product name |
| `{{ description }}` | Product description |
| `{{ model }}` | Model number |
| `{{ brand }}` | Brand |
| `{{ origin }}` | Country of origin |
| `{{ image }}` | Product photo, inline image, ~55mm wide. `None` if no photo was attached to that item. |
| `{{ features }}` | List of feature strings — iterate with a loop |
| `{{ warranty }}` | Warranty text |
| `{{ mrp_formatted }}` | Formatted MRP (empty string if not set) |
| `{{ specifications }}` | List of specification strings — iterate with a loop |
| `{{ accessories }}` | List of accessory strings — iterate with a loop |
| `{{ installation_notes }}` | Installation notes |
| `{{ additional_notes }}` | Additional notes |
| `{{ rate_formatted }}` | Formatted line total |

Example item loop inside a table row (docxtpl row-repeat syntax):

```
{%tr for item in items %}
{{ item.product_name }} | {{ item.model }} | {{ item.rate_formatted }}
{%tr endfor %}
```

## Watermark

Watermarks are **not** a dynamic tag or a separate upload. They must be authored directly inside the template's `.docx` file using Word's native watermark feature (Design → Watermark). Since the watermark becomes part of the template file itself, it will appear on every quotation generated from that template automatically — no special tag needed.

## Notes

- `autoescape=True` is enabled, so text containing `&`, `<`, `>` (e.g. "Smith & Sons Clinic") renders safely.
- Any tag not present in a template is simply not rendered — this cannot corrupt the document, but it does mean typos in a tag name (e.g. `{{ compnay_logo }}`) will silently produce a blank instead of an error. Double-check a new template's output after the first upload.
- The reference Garg Dental template (`app/quotation_templates/equipment_proposal_garg_dental.docx`) predates the `company_logo` and `signature.*` tags, so it doesn't include them — it's still a good starting point for the customer/proposal/items/totals structure, but a new template should add `{{ company_logo }}` and `{{ signature.image }}`/`{{ signature.name }}`/`{{ signature.designation }}` explicitly if those features are wanted.
