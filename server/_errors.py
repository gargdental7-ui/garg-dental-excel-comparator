"""Mirrors the exact try/except split BackgroundTaskRunner uses in the
Tkinter app's app/pages/common.py: an AppError's message is safe to show
verbatim (it was already written for non-technical staff); anything else is
logged in full and only a generic message reaches the client."""
import functools
import logging

from app.exceptions import AppError
from fastapi import HTTPException

logger = logging.getLogger("gargdental.api")


def handle_app_errors(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except AppError as exc:
            raise HTTPException(
                status_code=400,
                detail={"message": str(exc), "error_type": type(exc).__name__},
            ) from exc
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Unexpected error in %s", fn.__name__)
            raise HTTPException(
                status_code=500,
                detail={"message": "An unexpected error occurred."},
            ) from exc

    return wrapper
