"""Shared open_workbook + load_generic_sheet wrapper for Collection and
Inventory, sanitizing WorkbookOpenError's embedded temp-file path the same
way _comparator_routes.py does for workbook_reader.load_sheet - otherwise it
would leak this server's internal temp file path to the client."""
from app import generic_excel
from app.exceptions import WorkbookOpenError

FILE_LABEL = "uploaded file"


def open_workbook(path):
    try:
        return generic_excel.open_workbook(path, FILE_LABEL)
    except WorkbookOpenError:
        raise WorkbookOpenError(FILE_LABEL)


def load_sheet(workbook, sheet_name):
    return generic_excel.load_generic_sheet(workbook, sheet_name, FILE_LABEL)
