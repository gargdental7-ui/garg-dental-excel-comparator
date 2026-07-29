"""DOCX -> PDF conversion via CloudConvert's REST API.

Originally planned as a Vercel Sandbox + LibreOffice conversion (self-hosted,
no third-party dependency), but Sandbox access proved unavailable on this
account's plan in practice (403s persisted even after the pricing docs
suggested Hobby should include a free allotment). CloudConvert is the
fallback: a third-party API, but simple and guaranteed to work regardless
of Vercel plan. Kept isolated behind convert_docx_to_pdf() so swapping back
to a Sandbox-based implementation later only means replacing this file's
internals, not any call site.
"""
import os
import time

import httpx

from app.exceptions import AppError

API_BASE = "https://api.cloudconvert.com/v2"
POLL_INTERVAL_SECONDS = 1.5
MAX_WAIT_SECONDS = 60
DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class PdfConversionError(AppError):
    def __init__(self, detail: str):
        super().__init__(f"Could not create a PDF version of this quotation: {detail}")


def _api_key() -> str:
    key = os.environ.get("CLOUDCONVERT_API_KEY")
    if not key:
        raise RuntimeError("CLOUDCONVERT_API_KEY environment variable is not set.")
    return key


def _headers() -> dict:
    return {"Authorization": f"Bearer {_api_key()}"}


def convert_docx_to_pdf(docx_bytes: bytes, filename: str) -> bytes:
    """Uploads docx_bytes to CloudConvert, waits for conversion, and
    returns the resulting PDF bytes. Raises PdfConversionError (an
    AppError, so handle_app_errors turns it into a normal 400 the frontend
    can display) on any failure - never raises a raw httpx/JSON error up to
    the route."""
    with httpx.Client(timeout=30.0) as client:
        job_resp = client.post(
            f"{API_BASE}/jobs",
            headers=_headers(),
            json={
                "tasks": {
                    "import-file": {"operation": "import/upload"},
                    "convert-file": {
                        "operation": "convert",
                        "input": "import-file",
                        "output_format": "pdf",
                    },
                    "export-file": {"operation": "export/url", "input": "convert-file"},
                }
            },
        )
        if job_resp.status_code >= 400:
            raise PdfConversionError(f"job creation failed ({job_resp.status_code})")
        job = job_resp.json()["data"]

        import_task = next(t for t in job["tasks"] if t["name"] == "import-file")
        form = import_task["result"]["form"]

        upload_resp = client.post(
            form["url"],
            data=form["parameters"],
            files={"file": (filename, docx_bytes, DOCX_MEDIA_TYPE)},
        )
        if upload_resp.status_code >= 400:
            raise PdfConversionError(f"upload failed ({upload_resp.status_code})")

        job_id = job["id"]
        deadline = time.monotonic() + MAX_WAIT_SECONDS
        while True:
            status_resp = client.get(f"{API_BASE}/jobs/{job_id}", headers=_headers())
            if status_resp.status_code >= 400:
                raise PdfConversionError(f"status check failed ({status_resp.status_code})")
            job = status_resp.json()["data"]
            if job["status"] == "finished":
                break
            if job["status"] == "error":
                raise PdfConversionError("the conversion job reported an error")
            if time.monotonic() > deadline:
                raise PdfConversionError("timed out waiting for conversion")
            time.sleep(POLL_INTERVAL_SECONDS)

        export_task = next(t for t in job["tasks"] if t["name"] == "export-file")
        files = export_task["result"]["files"]
        if not files:
            raise PdfConversionError("no output file was produced")
        pdf_url = files[0]["url"]

        pdf_resp = client.get(pdf_url)
        if pdf_resp.status_code >= 400:
            raise PdfConversionError(f"download of converted file failed ({pdf_resp.status_code})")
        return pdf_resp.content
