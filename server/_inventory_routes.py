import json
from typing import Optional

from app import inventory_writer
from app.inventory_analyzer import InventoryColumnMapping, MovementThresholds, analyze_inventory
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response

from _auth import require_auth
from _errors import handle_app_errors
from _excel_loading import load_sheet, open_workbook
from _mapping_heuristics import INVENTORY_CANDIDATES, suggest_mapping
from _serialization import dataclass_kwargs, json_safe, mapping_kwargs
from _tempfiles import temp_upload_path, write_and_read_bytes

router = APIRouter(prefix="/api/inventory", tags=["inventory"], dependencies=[Depends(require_auth)])

PRODUCTS_PREVIEW_LIMIT = 200
EXCEPTIONS_PREVIEW_LIMIT = 50


def _load(file: UploadFile, sheet: Optional[str]):
    with temp_upload_path(file) as path:
        workbook = open_workbook(path)
        sheet_names = workbook.sheetnames
        selected_sheet = sheet or sheet_names[0]
        data = load_sheet(workbook, selected_sheet)
    return sheet_names, selected_sheet, data


def _analyze(file: UploadFile, sheet: str, mapping: str, thresholds: Optional[str]):
    _, _, data = _load(file, sheet)
    mapping_obj = InventoryColumnMapping(**mapping_kwargs(InventoryColumnMapping, json.loads(mapping)))
    thresholds_data = json.loads(thresholds) if thresholds else {}
    thresholds_obj = MovementThresholds(**dataclass_kwargs(MovementThresholds, thresholds_data))
    return analyze_inventory(data.headers, data.rows, data.row_excel_indexes, mapping_obj, thresholds_obj)


@router.post("/inspect")
@handle_app_errors
def inspect(file: UploadFile = File(...), sheet: Optional[str] = Form(None)):
    sheet_names, selected_sheet, data = _load(file, sheet)
    return {
        "sheet_names": sheet_names,
        "selected_sheet": selected_sheet,
        "headers": data.headers,
        "row_count": len(data.rows),
        "suggested_mapping": suggest_mapping(data.headers, INVENTORY_CANDIDATES),
    }


@router.post("/analyze")
@handle_app_errors
def analyze(
    file: UploadFile = File(...),
    sheet: str = Form(...),
    mapping: str = Form(...),
    thresholds: Optional[str] = Form(None),
):
    result = _analyze(file, sheet, mapping, thresholds)
    return {
        "stats": {
            "total_products": len(result.products),
            "counts": result.counts,
            "exceptions_count": len(result.exceptions),
            "has_value_data": result.has_value_data,
            "total_inventory_value": result.total_inventory_value,
            "value_no_movement": result.value_no_movement,
            "value_slow_moving": result.value_slow_moving,
        },
        "products_preview": [json_safe(p) for p in result.products[:PRODUCTS_PREVIEW_LIMIT]],
        "products_total_count": len(result.products),
        "exceptions_preview": [json_safe(e) for e in result.exceptions[:EXCEPTIONS_PREVIEW_LIMIT]],
        "exceptions_total_count": len(result.exceptions),
    }


@router.post("/export")
@handle_app_errors
def export(
    file: UploadFile = File(...),
    sheet: str = Form(...),
    mapping: str = Form(...),
    thresholds: Optional[str] = Form(None),
):
    result = _analyze(file, sheet, mapping, thresholds)
    content = write_and_read_bytes(inventory_writer.write_inventory_report, result)
    filename = inventory_writer.default_output_filename()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
