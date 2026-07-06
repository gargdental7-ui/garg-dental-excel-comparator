#!/usr/bin/env bash
# Builds a local macOS app bundle for testing only.
# The production target is Windows - see build_windows.bat / README.md.
set -euo pipefail
cd "$(dirname "$0")"

echo "Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

echo "Running tests..."
pytest -q

echo "Building GargDentalExcelComparator.app..."
pyinstaller --noconfirm GargDentalExcelComparator.spec

echo
echo "Build complete."
echo "App bundle: dist/GargDentalExcelComparator/"
