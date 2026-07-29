"""One-off script (Phase C of the multi-tenant redesign): uploads the
existing static app/quotation_templates/equipment_proposal_garg_dental.docx
into the new Storage-backed quotation_templates system for Garg Dental, so
the live company's rendering keeps working unchanged after
server/_quotation_routes.py::generate() switched to fetching templates
from Storage instead of the repo file. Run once, from repo root:

    python scripts/migrate_garg_dental_template_to_storage.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "server"))

from _db import get_connection
from _storage import upload as storage_upload

TEMPLATE_BUCKET = "quotation-templates"
DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
GARG_DENTAL_SLUG = "garg_dental"
SOURCE_FILE = REPO_ROOT / "app" / "quotation_templates" / "equipment_proposal_garg_dental.docx"


def main() -> None:
    content = SOURCE_FILE.read_bytes()

    with get_connection(role="super_admin") as conn:
        with conn.cursor() as cur:
            cur.execute("select id from companies where slug = %s", (GARG_DENTAL_SLUG,))
            company_row = cur.fetchone()
            if company_row is None:
                raise SystemExit(f"No company found with slug {GARG_DENTAL_SLUG!r}")
            company_id = str(company_row["id"])

            cur.execute("select id from users where role = 'super_admin' order by created_at limit 1")
            user_row = cur.fetchone()
            if user_row is None:
                raise SystemExit("No super_admin user found to attribute the upload to")
            uploaded_by = str(user_row["id"])

            cur.execute("select 1 from quotation_templates where company_id = %s", (company_id,))
            if cur.fetchone() is not None:
                print(f"quotation_templates row already exists for {company_id}; nothing to do.")
                return

            storage_path = f"{company_id}/{SOURCE_FILE.name}"
            storage_upload(TEMPLATE_BUCKET, storage_path, content, DOCX_MEDIA_TYPE)

            cur.execute(
                "insert into quotation_templates (company_id, storage_path, original_filename, uploaded_by, file_size) "
                "values (%s, %s, %s, %s, %s)",
                (company_id, storage_path, SOURCE_FILE.name, uploaded_by, len(content)),
            )
            print(f"Uploaded {SOURCE_FILE.name} ({len(content)} bytes) to {TEMPLATE_BUCKET}/{storage_path}")
            print(f"Inserted quotation_templates row for company {company_id}")


if __name__ == "__main__":
    main()
