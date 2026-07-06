"""Local error logging that works from source (Mac/Windows) and from a
packaged PyInstaller .exe, where sys.frozen points at the bundled executable."""
import logging
import sys
from pathlib import Path


def _log_directory() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parent.parent
    log_dir = base / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def configure_logging() -> Path:
    log_file = _log_directory() / "garg_dental_excel_comparator.log"
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logging.getLogger(__name__).info("Application started")
    return log_file
