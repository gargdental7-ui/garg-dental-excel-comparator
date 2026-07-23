"""One-off build script: turns the reference Garg Dental proposal .docx into
the docxtpl template used by app/quotation_docx.py. Run again only if the
reference document or the desired tag layout changes:

    source .venv/bin/activate
    python3 scripts/build_quotation_template.py <path-to-reference.docx>

Every edit below replaces run/cell TEXT with Jinja tags in place, reusing
the original run's XML (font, bold, color, size) so formatting is
untouched - this is the "docxtpl on the real reference file" approach: the
template is the reference file, minimally edited, not a reconstruction.
"""
import copy
import sys
from pathlib import Path

import docx
from docx.oxml.ns import qn

OUTPUT_PATH = Path(__file__).parent.parent / "app" / "quotation_templates" / "equipment_proposal_garg_dental.docx"


def set_run_text(run, text):
    run.text = text


def clear_other_runs(paragraph, keep_index=0, skip_indexes=()):
    keep_indexes = {keep_index, *skip_indexes}
    for i, run in enumerate(paragraph.runs):
        if i not in keep_indexes:
            set_run_text(run, "")


def strip_drawings(run):
    for drawing in run._r.findall(qn("w:drawing")):
        run._r.remove(drawing)


def clone_paragraph_after(paragraph):
    """Insert a copy of `paragraph`'s XML (same pPr/rPr styling) right
    after it, returning the new Paragraph wrapper. Used for optional
    product-detail lines that don't exist in the reference sample."""
    new_p_element = copy.deepcopy(paragraph._p)
    paragraph._p.addnext(new_p_element)
    return docx.text.paragraph.Paragraph(new_p_element, paragraph._parent)


def set_paragraph_single_run_text(paragraph, text):
    """Collapse a paragraph down to a single run holding `text`, reusing
    the paragraph's first run's formatting (font/bold/etc)."""
    if not paragraph.runs:
        paragraph.add_run(text)
        return
    set_run_text(paragraph.runs[0], text)
    clear_other_runs(paragraph, keep_index=0)


def edit_letterhead_and_title(doc):
    title_p = doc.paragraphs[6]
    set_paragraph_single_run_text(title_p, "{{ proposal.title }}")


def edit_submitted_to_block(doc):
    # Paragraph 14: "The Director\nSamaj Dental Hospital" - run[1] is a
    # real <w:br/> line-break run (verified against the source XML), not
    # literal text, so it's left untouched; only the two text runs around
    # it change.
    p14 = doc.paragraphs[14]
    set_run_text(p14.runs[0], "{{ customer.designation }}")
    set_run_text(p14.runs[2], "{{ customer.company_name }}")
    # keep run[1] (the real <w:br/> line-break run) completely untouched
    clear_other_runs(p14, keep_index=0, skip_indexes=(1, 2))

    p15 = doc.paragraphs[15]  # "Bibhuti Janak Marg, Kathmandu"
    set_paragraph_single_run_text(p15, "{{ customer.address }}")
    # paragraph 16 ("Nepal") stays static - Garg Dental serves Nepal only.


def edit_ref_and_date(doc):
    p33 = doc.paragraphs[33]  # "Ref No: GD/Q/SDH/2082/83-01"
    set_run_text(p33.runs[0], "Ref No: {{ customer.reference_number }}")
    clear_other_runs(p33, keep_index=0)

    p34 = doc.paragraphs[34]  # "Date: 28th June, 2026"
    set_run_text(p34.runs[0], "Date: {{ proposal.quotation_date }}")
    clear_other_runs(p34, keep_index=0)


def edit_to_address_block(doc):
    p37 = doc.paragraphs[37]  # "The Director"
    set_paragraph_single_run_text(p37, "{{ customer.designation }}")

    p38 = doc.paragraphs[38]  # "Samaj Dental Hospital"
    set_paragraph_single_run_text(p38, "{{ customer.company_name }}")

    p39 = doc.paragraphs[39]  # "Bibhuti Janak Marg, Kathmandu"
    set_paragraph_single_run_text(p39, "{{ customer.address }}")
    # paragraph 40 ("Nepal") stays static.


def edit_subject_and_intro(doc):
    p41 = doc.paragraphs[41]  # "Subject: Quotation for ..."
    set_run_text(p41.runs[0], "Subject: {{ proposal.subject }}")
    clear_other_runs(p41, keep_index=0)

    # Intro paragraph 43: keep Garg Dental's boilerplate wording, append an
    # optional customer-notes line to its last run rather than inserting a
    # whole new paragraph (lower risk of corrupting the XML tree).
    p43 = doc.paragraphs[43]
    last_run = p43.runs[-1]
    set_run_text(
        last_run,
        last_run.text + "{{ (' Notes: ' + customer.notes) if customer.notes else '' }}",
    )


def edit_terms_and_conditions(doc):
    # Paragraphs 48-56 are the 9 static "Label:\t\tText" lines. Collapse
    # them into one docxtpl paragraph-loop line driven by
    # company.terms_and_conditions, and delete the other 8 - the
    # sub-bullet warranty-invalidity list (57-63) stays untouched/static.
    p48 = doc.paragraphs[48]
    for p in doc.paragraphs[49:57]:
        p._p.getparent().remove(p._p)
    # {%p for %}/{%p endfor %} each collapse their OWN paragraph down to
    # the bare tag (verified empirically), so for/content/endfor need to
    # be three separate paragraphs, not one combined line.
    set_paragraph_single_run_text(p48, "{%p for term in company.terms %}")
    anchor = clone_paragraph_after(p48)
    set_paragraph_single_run_text(anchor, "{{ term.0 }}:\t\t{{ term.1 }}")
    anchor = clone_paragraph_after(anchor)
    set_paragraph_single_run_text(anchor, "{%p endfor %}")


def edit_product_table(doc):
    table = doc.tables[0]
    row = table.rows[1]
    cells = row.cells

    # docxtpl's {%tr for %}/{%tr endfor %} tags each collapse their own
    # ENTIRE <w:tr> down to the bare tag (verified empirically - the tag
    # can't share a row with the content it's supposed to repeat, or the
    # content gets eaten along with it). So the loop needs three rows: a
    # dedicated "for" marker row, this untouched content row, and a
    # dedicated "endfor" marker row - both markers vanish on render,
    # leaving only the repeated content row(s).
    sn_p = cells[0].paragraphs[0]
    set_paragraph_single_run_text(sn_p, "{{ loop.index }}.")

    # --- DESCRIPTION column: rewrite each paragraph in place ---
    desc_paragraphs = cells[1].paragraphs
    set_paragraph_single_run_text(desc_paragraphs[0], "{{ item.product_name }}")
    set_paragraph_single_run_text(desc_paragraphs[1], "MODEL : {{ item.model }}")
    set_paragraph_single_run_text(desc_paragraphs[2], "BRAND: {{ item.brand }}")
    set_paragraph_single_run_text(desc_paragraphs[3], "ORIGIN: {{ item.origin }}")

    # paragraph 4 held the reference's static product image - strip the
    # drawing and replace with the per-item conditional image tag.
    image_p = desc_paragraphs[4]
    image_run = image_p.runs[0] if image_p.runs else image_p.add_run("")
    strip_drawings(image_run)
    set_run_text(image_run, "{% if item.image %}{{ item.image }}{% endif %}")
    clear_other_runs(image_p, keep_index=0)

    set_paragraph_single_run_text(desc_paragraphs[5], "Key Features :")

    # paragraph 6 is the first feature line - reuse its styling for the
    # {%p for %} tag paragraph. {%p for %}/{%p endfor %} each collapse
    # their OWN paragraph down to the bare tag (verified empirically), so
    # for/content/endfor must be three separate paragraphs, not one
    # combined line. Delete the remaining sample feature lines (7, 8, 9)
    # first so paragraph indexes below stay valid.
    for p in desc_paragraphs[7:10]:
        p._p.getparent().remove(p._p)
    set_paragraph_single_run_text(desc_paragraphs[6], "{%p for f in item.features %}")
    anchor = clone_paragraph_after(desc_paragraphs[6])
    set_paragraph_single_run_text(anchor, "{{ f }}")
    anchor = clone_paragraph_after(anchor)
    set_paragraph_single_run_text(anchor, "{%p endfor %}")

    def append_line(text):
        nonlocal anchor
        anchor = clone_paragraph_after(anchor)
        set_paragraph_single_run_text(anchor, text)

    def append_loop(list_expr, item_name, endfor_label):
        append_line(f"{{%p for {item_name} in {list_expr} %}}")
        append_line(f"{{{{ {item_name} }}}}")
        append_line("{%p endfor %}")

    # Optional extra product-detail lines, cloned from the feature-line
    # paragraph's styling, appended after the features loop. Plain {{ }}
    # expressions (no {%p %}/{%tr %} tag) are safe to combine in one
    # paragraph, so the conditional single-line fields stay as one-liners;
    # only the list fields need the three-paragraph loop structure.
    append_line("{{ ('Warranty: ' + item.warranty) if item.warranty else '' }}")
    append_line("{{ 'Technical Specifications :' if item.specifications else '' }}")
    append_loop("item.specifications", "s", "specifications")
    append_line("{{ 'Accessories :' if item.accessories else '' }}")
    append_loop("item.accessories", "a", "accessories")
    append_line("{{ ('Installation Notes: ' + item.installation_notes) if item.installation_notes else '' }}")
    append_line("{{ ('Additional Notes: ' + item.additional_notes) if item.additional_notes else '' }}")

    # --- RATE column ---
    rate_p = cells[2].paragraphs[0]
    set_paragraph_single_run_text(rate_p, "{{ item.rate_formatted }}")

    # Delete the reference's second sample product row entirely - the
    # content row above now generates one row per real item.
    table.rows[2]._tr.getparent().remove(table.rows[2]._tr)

    # Wrap the content row with dedicated for/endfor marker rows (cloned
    # from it, so column widths/grid stay consistent, then cleared).
    content_tr = row._tr

    for_tr = copy.deepcopy(content_tr)
    content_tr.addprevious(for_tr)

    endfor_tr = copy.deepcopy(content_tr)
    content_tr.addnext(endfor_tr)

    table = doc.tables[0]  # re-fetch: row list changed after XML inserts
    for_row = table.rows[1]
    endfor_row = table.rows[3]
    for_row.cells[0].text = "{%tr for item in items %}"
    for c in for_row.cells[1:]:
        c.text = ""
    endfor_row.cells[0].text = "{%tr endfor %}"
    for c in endfor_row.cells[1:]:
        c.text = ""

    return table


def append_totals_rows(table):
    def add_row(label, value_expr, bold=False):
        row = table.add_row()
        row.cells[1].text = label
        row.cells[2].text = value_expr
        if bold:
            for cell in (row.cells[1], row.cells[2]):
                for run in cell.paragraphs[0].runs:
                    run.bold = True

    add_row("Subtotal", "{{ totals.subtotal_formatted }}")
    add_row("Discount", "{{ totals.discount_formatted }}")
    add_row("VAT", "{{ totals.vat_formatted }}")
    add_row("Grand Total", "{{ totals.grand_total_formatted }}", bold=True)


def build(reference_path: str):
    doc = docx.Document(reference_path)
    edit_letterhead_and_title(doc)
    edit_submitted_to_block(doc)
    edit_ref_and_date(doc)
    edit_to_address_block(doc)
    edit_subject_and_intro(doc)
    edit_terms_and_conditions(doc)
    table = edit_product_table(doc)
    append_totals_rows(table)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT_PATH)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/build_quotation_template.py <reference.docx>")
        sys.exit(1)
    build(sys.argv[1])
