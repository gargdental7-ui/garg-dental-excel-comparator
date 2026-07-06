"""Human-readable exceptions shown directly to office staff in dialog boxes."""


class AppError(Exception):
    """Base class for errors whose message is safe to display to non-technical staff."""


class WorkbookOpenError(AppError):
    def __init__(self, path):
        super().__init__(f"The selected Excel file could not be opened:\n{path}")


class CodeColumnNotFoundError(AppError):
    def __init__(self, file_label):
        super().__init__(f"Could not find the 'Code' column in the {file_label}.")


class NoComparableColumnsError(AppError):
    def __init__(self):
        super().__init__(
            "The two files have no columns in common besides Code, so there is nothing to compare."
        )


class HeaderDetectionError(AppError):
    def __init__(self, file_label):
        super().__init__(
            f"The workbook header structure could not be identified reliably in the {file_label}."
        )


class NoMatchingCodesError(AppError):
    def __init__(self):
        super().__init__("No matching product Codes were found between the two files.")


class EmptyWorkbookError(AppError):
    def __init__(self, file_label):
        super().__init__(f"The {file_label} has no worksheets with data.")


class GenericHeaderDetectionError(AppError):
    def __init__(self, file_label):
        super().__init__(
            f"Could not find a header row in the {file_label}. "
            "Make sure the sheet has column titles (e.g. Customer, Amount, Due Date)."
        )


class MissingColumnMappingError(AppError):
    def __init__(self, missing_fields):
        fields = ", ".join(missing_fields)
        super().__init__(f"Please map the following required column(s): {fields}.")


class NoDataRowsError(AppError):
    def __init__(self):
        super().__init__("No usable data rows were found in the uploaded file.")
