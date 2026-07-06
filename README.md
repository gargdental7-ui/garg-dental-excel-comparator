# Garg Dental Operations Toolkit

A small, offline desktop application for Garg Dental office staff. One
window, one executable, three focused tools - each opens on its own page
via the sidebar:

- **Excel Comparator** - compare two stock reports by product Code.
- **Collection Priority Analyzer** - find out which customers to follow up
  with first from an outstanding/receivables report.
- **Inventory Movement Analyzer** - classify fast/slow/dead stock from a
  stock movement report.

Every tool follows the same principle: **upload Excel → process locally →
show results → export an actionable Excel file.** No database, no AI/ML, no
cloud, no accounts. Nothing you upload is stored anywhere - it's read into
memory, analyzed, and the original file is never modified.

## Excel Comparator

1. Select the Current File and the Latest OMS File (`.xlsx` / `.xlsm`).
2. Click **Compare Files**. Rows are matched by `Code`; every column shared
   by both files (besides `Code` itself) is compared automatically -
   nothing to select.
3. Any column that differs for a matched Code is reported individually,
   with its Current File (old) and OMS File (new) value.
4. Save the result as a new Excel file.

The result workbook has up to four sheets:

- **FIELD_CHANGES** - one row per changed value: `Code | Column | Old Value
  | New Value` (the main output - exactly what changed and to what).
- **DIFFERENCES** - the **complete** OMS row for every matched Code with at
  least one changed column, in the original OMS column order (for context).
- **NEW_CODES** - Codes present in the OMS file but not in the Current File.
- **MISSING_FROM_OMS** - Codes present in the Current File but not in the
  OMS file (only created when this actually happens).

Duplicate Codes within a file are detected, reported in a scrollable warning
dialog, and excluded from matching rather than silently guessed at.

## Collection Priority Analyzer

1. Select an outstanding/receivables Excel export. The sheet's columns are
   detected automatically (if the file has more than one sheet, pick which
   one to read).
2. Map the detected columns to logical fields: **Customer/Party Name** and
   **Outstanding Amount** are required; Days Overdue, Due Date, Last Payment
   Date, Salesperson, and Invoice Number are optional but improve the
   analysis. Column names are never hardcoded, since every OMS export is
   different.
3. Review (and edit if needed) the priority rule thresholds shown directly
   on the page - Critical/High/Medium overdue-day cutoffs and Critical/High
   amount cutoffs.
4. Click **Analyze**. Invoices are aggregated per customer; each customer is
   ranked **CRITICAL / HIGH / MEDIUM / NORMAL** by a transparent, rule-based
   score (no AI): overdue days, outstanding amount, and number of open
   invoices. Accounts with nothing owed are always NORMAL.
5. Click **Export Collection Report**.

The result workbook has three sheets:

- **COLLECTION_PRIORITY** - customers ranked highest priority first, with
  total outstanding, invoice count, max/average days overdue, oldest due
  date, and salesperson.
- **INVOICE_DETAILS** - the original invoice-level rows, preserved as-is.
- **SUMMARY** - total outstanding, account counts, amounts over 30/60/90
  days, and the exact threshold values the rule used (so the numbers are
  always explainable).

## Inventory Movement Analyzer

1. Select a stock movement Excel export - including the known Garg Dental
   two-row header layout (`Code, Description, Unit, Opening, Received,
   Delivered, Balance` with a `Qty` sub-header row).
2. Map columns to **Product Code, Opening, Received, Delivered, Balance**
   (all required), plus optional Description, Unit, Unit Cost, Stock Value,
   Brand, and Category.
3. Review (and edit if needed) the Fast/Normal moving ratio thresholds.
4. Click **Analyze**. Each product is classified for the **uploaded period
   only** - a single snapshot can't prove permanent dead stock, so results
   are always period-scoped:
   - **NEGATIVE STOCK** - Balance < 0.
   - **OUT OF STOCK** - Balance = 0.
   - **NO MOVEMENT** - Delivered = 0 and Balance > 0.
   - **FAST / NORMAL / SLOW MOVING** - by Movement Ratio = Delivered ÷
     (Opening + Received), against the configured thresholds.

   If Unit Cost or Stock Value is mapped, high-value products with no or
   slow movement are also flagged - this analysis is hidden entirely when
   no value data is available, rather than guessing.
5. Click **Export Inventory Analysis**.

The result workbook has up to six sheets: **INVENTORY_ANALYSIS** (every
classified product), **NO_MOVEMENT**, **SLOW_MOVING**, **FAST_MOVING**,
**STOCK_EXCEPTIONS** (negative/invalid/missing/duplicate Codes), and
**HIGH_VALUE_RISK** (only created when cost/value data is available).

## Mac developer setup

```bash
cd gargdentalmodel
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Running tests

```bash
source .venv/bin/activate
pytest -q
```

## Running locally

```bash
source .venv/bin/activate
python3 main.py
```

Manual end-to-end check on Mac:

1. **Excel Comparator**: select a Current File and an OMS File, confirm
   Compare Files enables once both load, compare, save, and confirm
   `FIELD_CHANGES` lists exact old/new values and `DIFFERENCES` preserves
   complete OMS rows.
2. **Collection Analyzer**: upload an outstanding report, confirm columns
   auto-map where names are recognizable, run Analyze, export, and confirm
   `COLLECTION_PRIORITY` is sorted highest-priority first and
   `INVOICE_DETAILS` preserves the original rows.
3. **Inventory Analyzer**: upload a stock movement report (including a
   two-row-header file), confirm required fields are enforced, run
   Analyze, export, and confirm classifications and sheet counts match
   expectations.

## Mac build (local testing only)

The production target is Windows - this just produces a local `.app` bundle
for testing on your own Mac:

```bash
./build_mac.sh
```

Output: `dist/GargDentalOperationsToolkit.app`

## Windows build

On a Windows machine, with Python 3.11+ installed:

```bat
build_windows.bat
```

This creates a virtual environment, installs dependencies, runs the test
suite (aborting the build if tests fail), and produces:

```
dist\GargDentalOperationsToolkit\GargDentalOperationsToolkit.exe
```

Copy the whole `GargDentalOperationsToolkit` folder to a staff computer -
nothing else (no Python, no dependencies) needs to be installed there.

## GitHub Actions Windows build (free, no local Windows machine needed)

1. Push this repository to GitHub.
2. Open the **Actions** tab.
3. Select the **Build Windows Executable** workflow.
4. Click **Run workflow** (or push a tag like `v1.0` to trigger it
   automatically).
5. Once it finishes, download the `GargDentalOperationsToolkit-windows`
   artifact - it contains the ready-to-run Windows app folder.

## Error logging

Technical error details are written to a local `logs/` folder next to
`main.py` (or next to the `.exe` when packaged) rather than shown to staff as
a raw error. Staff only ever see plain-English dialog messages.

## Project layout

```
main.py                        Entry point (python3 main.py)
app/
  app_shell.py                 Main window: sidebar navigation between the 3 tools
  pages/
    comparator_page.py         Excel Comparator page
    collection_page.py         Collection Priority Analyzer page
    inventory_page.py          Inventory Movement Analyzer page
    common.py                  Shared background-task runner, dialogs, mapping widget
  comparator.py                Comparator matching/diff logic (no GUI dependency)
  workbook_reader.py            Comparator Excel loading + header detection glue
  header_detector.py            Comparator's single-row / two-row header detection
  workbook_writer.py            Comparator result workbook writer
  generic_excel.py              Generic sheet/header detection for Collection & Inventory
  collection_analyzer.py        Collection Analyzer aggregation + priority rules
  collection_writer.py          Collection Analyzer result workbook writer
  inventory_analyzer.py         Inventory Analyzer movement classification rules
  inventory_writer.py           Inventory Analyzer result workbook writer
  report_style.py               Shared openpyxl formatting helpers
  normalizers.py                 Code / value normalization rules
  exceptions.py                  Human-readable error types
  logging_setup.py               Cross-platform log file location
tests/                           pytest suite (all analysis logic is testable headlessly)
GargDentalOperationsToolkit.spec  PyInstaller build config
build_windows.bat / build_mac.sh
.github/workflows/build-windows.yml
```
