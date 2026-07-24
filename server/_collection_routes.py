import json
from typing import Optional

from app.collection_analyzer import CollectionColumnMapping, CollectionThresholds, analyze_collections
from app import collection_writer
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response

from _auth import require_auth
from _errors import handle_app_errors
from _excel_loading import load_sheet, open_workbook
from _mapping_heuristics import COLLECTION_CANDIDATES, suggest_mapping
from _serialization import dataclass_kwargs, json_safe, mapping_kwargs
from _tempfiles import temp_upload_path, write_and_read_bytes

router = APIRouter(prefix="/api/collection", tags=["collection"], dependencies=[Depends(require_auth)])

PREVIEW_LIMIT = 200


def _load(file: UploadFile, sheet: Optional[str]):
    with temp_upload_path(file) as path:
        workbook = open_workbook(path)
        sheet_names = workbook.sheetnames
        selected_sheet = sheet or sheet_names[0]
        data = load_sheet(workbook, selected_sheet)
    return sheet_names, selected_sheet, data


@router.post("/inspect")
@handle_app_errors
def inspect(file: UploadFile = File(...), sheet: Optional[str] = Form(None)):
    sheet_names, selected_sheet, data = _load(file, sheet)
    return {
        "sheet_names": sheet_names,
        "selected_sheet": selected_sheet,
        "headers": data.headers,
        "row_count": len(data.rows),
        "suggested_mapping": suggest_mapping(data.headers, COLLECTION_CANDIDATES),
    }


@router.post("/analyze")
@handle_app_errors
def analyze(
    file: UploadFile = File(...),
    sheet: str = Form(...),
    mapping: str = Form(...),
    thresholds: Optional[str] = Form(None),
):
    _, _, data = _load(file, sheet)
    mapping_obj = CollectionColumnMapping(**mapping_kwargs(CollectionColumnMapping, json.loads(mapping)))
    thresholds_data = json.loads(thresholds) if thresholds else {}
    thresholds_obj = CollectionThresholds(**dataclass_kwargs(CollectionThresholds, thresholds_data))

    result = analyze_collections(data.headers, data.rows, mapping_obj, thresholds_obj)
    return {
        "stats": {
            "total_outstanding": result.total_outstanding,
            "total_customers": result.total_customers,
            "critical_count": result.critical_count,
            "high_count": result.high_count,
            "critical_amount": result.critical_amount,
            "high_priority_amount": result.high_priority_amount,
            "amount_over_30": result.amount_over_30,
            "amount_over_60": result.amount_over_60,
            "amount_over_90": result.amount_over_90,
        },
        "customers_preview": [json_safe(c) for c in result.customers[:PREVIEW_LIMIT]],
        "customers_total_count": len(result.customers),
    }


@router.post("/export")
@handle_app_errors
def export(
    file: UploadFile = File(...),
    sheet: str = Form(...),
    mapping: str = Form(...),
    thresholds: Optional[str] = Form(None),
):
    _, _, data = _load(file, sheet)
    mapping_obj = CollectionColumnMapping(**mapping_kwargs(CollectionColumnMapping, json.loads(mapping)))
    thresholds_data = json.loads(thresholds) if thresholds else {}
    thresholds_obj = CollectionThresholds(**dataclass_kwargs(CollectionThresholds, thresholds_data))

    result = analyze_collections(data.headers, data.rows, mapping_obj, thresholds_obj)
    content = write_and_read_bytes(collection_writer.write_collection_report, result)
    filename = collection_writer.default_output_filename()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
