"""Excel Comparator endpoints. No sheet selector anywhere - matches the
desktop app, since workbook_reader.load_sheet only ever reads worksheets[0]."""
import json
from typing import Optional

from app import comparator, workbook_reader, workbook_writer
from app.exceptions import WorkbookOpenError
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response

from _auth import require_auth
from _errors import handle_app_errors
from _serialization import json_safe
from _tempfiles import temp_upload_path, write_and_read_bytes

router = APIRouter(prefix="/api/comparator", tags=["comparator"], dependencies=[Depends(require_auth)])

PREVIEW_LIMIT = 200


def _load(path, file_label):
    # load_sheet's WorkbookOpenError embeds the raw path in its message,
    # which would otherwise leak this server's internal temp file path to
    # the client - substitute the friendly label instead.
    try:
        return workbook_reader.load_sheet(path, file_label)
    except WorkbookOpenError:
        raise WorkbookOpenError(file_label)


def _load_pair(current_file: UploadFile, oms_file: UploadFile):
    with temp_upload_path(current_file) as current_path, temp_upload_path(oms_file) as oms_path:
        current_sheet = _load(current_path, "Current File")
        oms_sheet = _load(oms_path, "OMS File")
    return current_sheet, oms_sheet


def _parse_selected_columns(selected_columns: Optional[str]):
    if not selected_columns:
        return None
    return json.loads(selected_columns)


def _parse_column_mappings(column_mappings: Optional[str]):
    if not column_mappings:
        return None
    data = json.loads(column_mappings)
    return [
        comparator.ColumnMapping(current_column=d["current_column"], latest_column=d["latest_column"]) for d in data
    ]


def _is_legacy_mapping(mappings):
    """True when this should route through the original compare()/
    write_result() path: no mapping supplied at all, or exactly one pair
    with identical column names on both sides - behaviorally identical to
    the pre-existing shared-column checklist, so it must produce the exact
    same output ("single column mode... continue behaving exactly as it
    does today")."""
    if mappings is None:
        return True
    return len(mappings) == 1 and mappings[0].current_column.strip().lower() == mappings[0].latest_column.strip().lower()


@router.post("/inspect")
@handle_app_errors
def inspect(current_file: UploadFile = File(...), oms_file: UploadFile = File(...)):
    current_sheet, oms_sheet = _load_pair(current_file, oms_file)
    shared = comparator.find_shared_columns(current_sheet.headers, oms_sheet.headers)
    comparable_columns = [c for c in shared if c.strip().lower() != "code"]
    return {
        "current_headers": current_sheet.headers,
        "oms_headers": oms_sheet.headers,
        "current_row_count": len(current_sheet.rows),
        "oms_row_count": len(oms_sheet.rows),
        "comparable_columns": comparable_columns,
    }


@router.post("/analyze")
@handle_app_errors
def analyze(
    current_file: UploadFile = File(...),
    oms_file: UploadFile = File(...),
    selected_columns: Optional[str] = Form(None),
    column_mappings: Optional[str] = Form(None),
):
    current_sheet, oms_sheet = _load_pair(current_file, oms_file)
    mappings = _parse_column_mappings(column_mappings)

    if _is_legacy_mapping(mappings):
        legacy_selected = [mappings[0].current_column] if mappings else _parse_selected_columns(selected_columns)
        result = comparator.compare(current_sheet, oms_sheet, selected_columns=legacy_selected)
        return {
            "mode": "legacy",
            "stats": {
                "total_compared": result.total_compared,
                "total_differences": result.total_differences,
                "total_field_differences": result.total_field_differences,
                "new_codes_count": len(result.new_codes),
                "missing_from_oms_count": len(result.missing_from_oms),
                "compared_columns": result.compared_columns,
                "duplicate_warnings": result.duplicate_warnings,
            },
            "cell_differences_preview": [json_safe(d) for d in result.cell_differences[:PREVIEW_LIMIT]],
            "cell_differences_total_count": len(result.cell_differences),
        }

    result = comparator.compare_mapped(current_sheet, oms_sheet, mappings)
    changed = [r for r in result.rows if r.changed_field_labels]
    return {
        "mode": "mapped",
        "stats": {
            "total_compared": result.total_compared,
            "total_changed": result.total_changed,
            "total_unchanged": result.total_unchanged,
            "total_added": result.total_added,
            "total_removed": result.total_removed,
            "duplicate_warnings": result.duplicate_warnings,
            "mappings": [json_safe(m) for m in mappings],
        },
        "changed_preview": [json_safe(r) for r in changed[:PREVIEW_LIMIT]],
        "changed_total_count": len(changed),
        "added_preview": [json_safe(r) for r in result.added[:PREVIEW_LIMIT]],
        "added_total_count": len(result.added),
        "removed_preview": [json_safe(r) for r in result.removed[:PREVIEW_LIMIT]],
        "removed_total_count": len(result.removed),
    }


@router.post("/export")
@handle_app_errors
def export(
    current_file: UploadFile = File(...),
    oms_file: UploadFile = File(...),
    selected_columns: Optional[str] = Form(None),
    column_mappings: Optional[str] = Form(None),
):
    current_sheet, oms_sheet = _load_pair(current_file, oms_file)
    mappings = _parse_column_mappings(column_mappings)

    if _is_legacy_mapping(mappings):
        legacy_selected = [mappings[0].current_column] if mappings else _parse_selected_columns(selected_columns)
        result = comparator.compare(current_sheet, oms_sheet, selected_columns=legacy_selected)
        content = write_and_read_bytes(workbook_writer.write_result, current_sheet, oms_sheet, result)
        filename = workbook_writer.default_output_filename()
    else:
        result = comparator.compare_mapped(current_sheet, oms_sheet, mappings)
        content = write_and_read_bytes(
            workbook_writer.write_mapped_result, result, current_file.filename, oms_file.filename
        )
        filename = workbook_writer.default_mapped_output_filename()

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
