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


class InvalidHeaderRowError(AppError):
    def __init__(self, requested_row, max_row):
        super().__init__(f"Row {requested_row} is not a valid row in this sheet (it has {max_row} row(s)).")


class MissingColumnMappingError(AppError):
    def __init__(self, missing_fields):
        fields = ", ".join(missing_fields)
        super().__init__(f"Please map the following required column(s): {fields}.")


class NoDataRowsError(AppError):
    def __init__(self):
        super().__init__("No usable data rows were found in the uploaded file.")


class MissingCustomerNameError(AppError):
    def __init__(self):
        super().__init__("Please enter a Customer Name before generating the quotation.")


class NoQuotationProductsError(AppError):
    def __init__(self):
        super().__init__("Please add at least one product before generating the quotation.")


class InvalidQuotationItemError(AppError):
    def __init__(self, problems):
        joined = "; ".join(problems)
        super().__init__(f"Please fix the following product(s): {joined}.")


class UnknownCompanyError(AppError):
    def __init__(self, company_id):
        super().__init__(f"'{company_id}' is not a recognized company profile.")


class NoColumnMappingError(AppError):
    def __init__(self):
        super().__init__("Please map at least one column between the two files before comparing.")


class DuplicateQuotationItemError(AppError):
    def __init__(self, duplicate_names):
        joined = ", ".join(duplicate_names)
        super().__init__(f"The following product(s) were added more than once: {joined}.")


class NoMasterExcelError(AppError):
    def __init__(self):
        super().__init__("No Company Master Excel has been uploaded.")


class MissingUploadedFileError(AppError):
    def __init__(self):
        super().__init__("Please choose an Excel file to upload.")


class CompanyDataUnavailableError(AppError):
    def __init__(self):
        super().__init__("Company data is temporarily unavailable. Please try again shortly.")


class NoQuotationTemplateError(AppError):
    def __init__(self, company_display_name: str):
        super().__init__(f"{company_display_name} has no quotation template uploaded yet.")


class InvalidTemplateError(AppError):
    def __init__(self):
        super().__init__("The selected file could not be opened as a Word document (.docx).")


class InvalidLogoError(AppError):
    def __init__(self):
        super().__init__("The selected file could not be opened as an image.")
