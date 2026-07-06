# Garg Dental Excel Comparator

A small, offline desktop tool for Garg Dental office staff. It compares two
Excel stock reports - a **Current File** and the **Latest OMS File** - by
matching rows on the unique `Code` column and checking every column they
have in common. Rows where nothing changed are ignored; rows with at least
one changed value are reported, with the exact old and new value for each
changed column.

No internet connection, database, login, or paid software is required.

## What the app does

1. You pick the Current File and the Latest OMS File (`.xlsx` / `.xlsm`).
2. Click **Compare Files**.
3. Rows are matched by `Code`. Every column shared by both files (besides
   `Code` itself) is compared automatically - nothing to select.
4. Any column that differs for a matched Code is reported individually, with
   its Current File (old) and OMS File (new) value.
5. Save the result as a new Excel file and open it like any other report.

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

## Daily staff usage

1. Open the app (double-click `GargDentalExcelComparator.exe` on Windows,
   or `GargDentalExcelComparator.app` on Mac).
2. Click **Select Current File** and choose your current stock file.
3. Click **Select OMS File** and choose the latest OMS export.
4. Click **Compare Files** (enabled as soon as both files load).
5. Review the counts shown (products compared, rows with differences, field
   changes, new codes).
6. Click **Save Result Excel** and choose where to save it. Open the
   **FIELD_CHANGES** sheet to see exactly which column changed and its old
   and new value for every affected Code.
7. Click **New Comparison** to start again with different files.

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

1. Select a Current File and an OMS File.
2. Confirm Compare Files enables as soon as both files finish loading.
3. Click Compare Files and confirm the result counts look right.
4. Save the result and open it in Excel/Numbers.
5. Confirm the `FIELD_CHANGES` sheet lists the exact old/new value for each
   changed column, and the `DIFFERENCES` sheet contains complete OMS rows
   (all columns,
   original order, blanks and negative numbers intact) and that unchanged
   rows are absent.

## Mac build (local testing only)

The production target is Windows - this just produces a local `.app` bundle
for testing on your own Mac:

```bash
./build_mac.sh
```

Output: `dist/GargDentalExcelComparator/`

## Windows build

On a Windows machine, with Python 3.11+ installed:

```bat
build_windows.bat
```

This creates a virtual environment, installs dependencies, runs the test
suite (aborting the build if tests fail), and produces:

```
dist\GargDentalExcelComparator\GargDentalExcelComparator.exe
```

Copy the whole `GargDentalExcelComparator` folder to a staff computer -
nothing else (no Python, no dependencies) needs to be installed there.

## GitHub Actions Windows build (free, no local Windows machine needed)

1. Push this repository to GitHub.
2. Open the **Actions** tab.
3. Select the **Build Windows Executable** workflow.
4. Click **Run workflow** (or push a tag like `v1.0` to trigger it
   automatically).
5. Once it finishes, download the `GargDentalExcelComparator-windows`
   artifact - it contains the ready-to-run Windows app folder.

## Error logging

Technical error details are written to a local `logs/` folder next to
`main.py` (or next to the `.exe` when packaged) rather than shown to staff as
a raw error. Staff only ever see plain-English dialog messages.

## Project layout

```
main.py                    Entry point (python3 main.py)
app/
  gui.py                   Tkinter UI
  workbook_reader.py        Excel loading + header detection glue
  header_detector.py        Single-row / two-row header detection
  comparator.py              Matching + comparison logic (no GUI dependency)
  workbook_writer.py         Result workbook writer
  normalizers.py             Code / value normalization rules
  exceptions.py               Human-readable error types
  logging_setup.py            Cross-platform log file location
tests/                        pytest suite (comparator is testable headlessly)
GargDentalExcelComparator.spec  PyInstaller build config
build_windows.bat / build_mac.sh
.github/workflows/build-windows.yml
```
