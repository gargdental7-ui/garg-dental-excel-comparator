"""The reused business logic (generic_excel.open_workbook, workbook_reader.load_sheet,
and every *_writer.write_* function) requires a real filesystem path - it does
`Path(path)` internally, so it isn't safe to pass a Vercel UploadFile/BytesIO
directly. These helpers bridge an upload (or a write) through a real temp file
and clean it up immediately after - nothing is ever retained server-side."""
import tempfile
from contextlib import contextmanager
from pathlib import Path

from fastapi import UploadFile


@contextmanager
def temp_upload_path(upload: UploadFile):
    suffix = Path(upload.filename or "").suffix or ".xlsx"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(upload.file.read())
        tmp_path = Path(tmp.name)
    try:
        yield tmp_path
    finally:
        tmp_path.unlink(missing_ok=True)


@contextmanager
def temp_output_path(suffix=".xlsx"):
    tmp_path = Path(tempfile.mktemp(suffix=suffix))
    try:
        yield tmp_path
    finally:
        tmp_path.unlink(missing_ok=True)


def write_and_read_bytes(write_fn, *args, **kwargs) -> bytes:
    """Call one of the app/*_writer.write_* functions (which require a real
    output path) into a temp file, then return its bytes for a download
    response - the temp file is deleted immediately after, before returning."""
    with temp_output_path() as out_path:
        write_fn(out_path, *args, **kwargs)
        return out_path.read_bytes()
