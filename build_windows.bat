@echo off
setlocal

cd /d "%~dp0"

echo Creating virtual environment...
python -m venv .venv
call .venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

echo Running tests...
pytest -q
if errorlevel 1 (
    echo Tests failed. Aborting build.
    exit /b 1
)

echo Building GargDentalOperationsToolkit.exe...
pyinstaller --noconfirm GargDentalOperationsToolkit.spec

echo.
echo Build complete.
echo Executable: dist\GargDentalOperationsToolkit\GargDentalOperationsToolkit.exe

endlocal
