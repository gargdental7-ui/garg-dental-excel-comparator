"""Single shared-password gate for the whole web app. The Collection tool
surfaces customer names and outstanding balances, which now briefly transit
a server instead of staying on an offline PC, so every /api/* tool endpoint
requires this cookie - enforced here, not just via the Next.js proxy (which
never even sees /api/* requests under Vercel Services routing)."""
import hashlib
import hmac
import os
import time

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

COOKIE_NAME = "gd_session"
COOKIE_MAX_AGE_SECONDS = 30 * 24 * 60 * 60  # 30 days


def _session_secret() -> str:
    secret = os.environ.get("SESSION_SECRET")
    if not secret:
        raise RuntimeError("SESSION_SECRET environment variable is not set.")
    return secret


def _site_password() -> str:
    password = os.environ.get("SITE_PASSWORD")
    if not password:
        raise RuntimeError("SITE_PASSWORD environment variable is not set.")
    return password


def _sign(issued_at: str) -> str:
    return hmac.new(_session_secret().encode(), issued_at.encode(), hashlib.sha256).hexdigest()


def _make_cookie_value() -> str:
    issued_at = str(int(time.time()))
    return f"{issued_at}.{_sign(issued_at)}"


def _cookie_is_valid(value: str) -> bool:
    if not value or "." not in value:
        return False
    issued_at, _, signature = value.partition(".")
    if not issued_at.isdigit():
        return False
    if not hmac.compare_digest(signature, _sign(issued_at)):
        return False
    age = time.time() - int(issued_at)
    return 0 <= age <= COOKIE_MAX_AGE_SECONDS


def require_auth(request: Request) -> None:
    cookie_value = request.cookies.get(COOKIE_NAME, "")
    if not _cookie_is_valid(cookie_value):
        raise HTTPException(status_code=401, detail={"message": "Please sign in."})


router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
def login(payload: LoginRequest, response: Response):
    if not hmac.compare_digest(payload.password, _site_password()):
        raise HTTPException(status_code=401, detail={"message": "Incorrect password."})
    response.set_cookie(
        key=COOKIE_NAME,
        value=_make_cookie_value(),
        max_age=COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/status")
def status(request: Request):
    cookie_value = request.cookies.get(COOKIE_NAME, "")
    return {"authenticated": _cookie_is_valid(cookie_value)}
