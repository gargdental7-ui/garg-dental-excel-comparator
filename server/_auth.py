"""Per-user auth gate for the whole web app, replacing the original single
shared-password design. The Collection tool surfaces customer names and
outstanding balances, and the Quotation tool now saves customer/pricing
history, so every /api/* tool endpoint requires this cookie - enforced
here, not just via the Next.js proxy (which never even sees /api/*
requests under Vercel Services routing).

The cookie payload changed from `{issued_at}.{signature}` (proof of "some
valid session exists") to `{issued_at}.{user_id}.{signature}` (proof of
"this specific user's session exists"), so require_auth can resolve a real
CurrentUser - id, role, company_id - that other routes depend on for
authorization (require_super_admin) and data scoping (e.g. staff only
seeing their own quotations, resolved via _tenancy.py::resolve_company_scope).
Existing callers that just did
`dependencies=[Depends(require_auth)]` to gate a router need no changes:
the guard-only contract (raises 401 if not logged in) is unchanged, only
its internals and return value are new.
"""
import hashlib
import hmac
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from _db import get_connection, login_lookup_connection

COOKIE_NAME = "gd_session"
COOKIE_MAX_AGE_SECONDS = 30 * 24 * 60 * 60  # 30 days

logger = logging.getLogger("gargdental.auth")


@dataclass
class CurrentUser:
    id: str
    company_id: Optional[str]  # None for super_admin, who belongs to no single company
    username: str
    full_name: str
    role: str
    active: bool


def _session_secret() -> str:
    secret = os.environ.get("SESSION_SECRET")
    if not secret:
        raise RuntimeError("SESSION_SECRET environment variable is not set.")
    return secret


def _sign(issued_at: str, user_id: str) -> str:
    message = f"{issued_at}.{user_id}".encode()
    return hmac.new(_session_secret().encode(), message, hashlib.sha256).hexdigest()


def _make_cookie_value(user_id: str) -> str:
    issued_at = str(int(time.time()))
    return f"{issued_at}.{user_id}.{_sign(issued_at, user_id)}"


def _parse_cookie(value: str) -> Optional[str]:
    """Returns the user_id if the cookie is validly signed and not expired,
    else None."""
    if not value:
        return None
    parts = value.split(".", 2)
    if len(parts) != 3:
        return None
    issued_at, user_id, signature = parts
    if not issued_at.isdigit() or not user_id:
        return None
    if not hmac.compare_digest(signature, _sign(issued_at, user_id)):
        return None
    age = time.time() - int(issued_at)
    if not (0 <= age <= COOKIE_MAX_AGE_SECONDS):
        return None
    return user_id


def _row_to_user(row: dict) -> CurrentUser:
    return CurrentUser(
        id=str(row["id"]),
        company_id=str(row["company_id"]) if row["company_id"] is not None else None,
        username=row["username"],
        full_name=row["full_name"],
        role=row["role"],
        active=row["active"],
    )


def _user_and_company_active(row: dict) -> bool:
    """A staff member's company can be disabled (Super Admin action)
    independently of the user's own `active` flag - either one blocks
    login. super_admin rows have no company (company_active is None from
    the left join), so only their own `active` flag matters."""
    if not row["active"]:
        return False
    if row["company_id"] is not None and not row["company_active"]:
        return False
    return True


def _load_user_by_id(user_id: str) -> Optional[CurrentUser]:
    try:
        with get_connection(user_id=user_id) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "select u.id, u.company_id, u.username, u.full_name, u.role, u.active, c.active as company_active "
                    "from users u left join companies c on c.id = u.company_id "
                    "where u.id = %s",
                    (user_id,),
                )
                row = cur.fetchone()
    except Exception:
        logger.exception("Failed to load user %s", user_id)
        return None
    if row is None or not _user_and_company_active(row):
        return None
    return _row_to_user(row)


def _load_user_for_login(username: str) -> Optional[dict]:
    """Returns the raw row (including password_hash) for the login check
    only - never exposed outside this module. Uses login_lookup_connection
    because at this point we don't have a user_id or company_id to scope
    the normal RLS-protected query by; see server/_db.py."""
    try:
        with login_lookup_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "select u.id, u.company_id, u.username, u.full_name, u.role, u.active, u.password_hash, "
                    "c.active as company_active "
                    "from users u left join companies c on c.id = u.company_id "
                    "where u.username = %s",
                    (username,),
                )
                return cur.fetchone()
    except Exception:
        logger.exception("Failed to look up user %r for login", username)
        return None


def require_auth(request: Request) -> CurrentUser:
    user_id = _parse_cookie(request.cookies.get(COOKIE_NAME, ""))
    if user_id is None:
        raise HTTPException(status_code=401, detail={"message": "Please sign in."})
    user = _load_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail={"message": "Please sign in."})
    return user


def require_super_admin(current_user: CurrentUser = Depends(require_auth)) -> CurrentUser:
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail={"message": "Super Admin access required."})
    return current_user


router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response):
    row = _load_user_for_login(payload.username)
    generic_error = HTTPException(status_code=401, detail={"message": "Incorrect username or password."})
    if row is None or not _user_and_company_active(row):
        raise generic_error
    if not bcrypt.checkpw(payload.password.encode(), row["password_hash"].encode()):
        raise generic_error

    from _audit import log_action  # local import: see _audit.py's note on the _auth<->_audit cycle

    company_id = str(row["company_id"]) if row["company_id"] is not None else None
    log_action(_row_to_user(row), company_id, "login", "user", str(row["id"]), request)

    response.set_cookie(
        key=COOKIE_NAME,
        value=_make_cookie_value(str(row["id"])),
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
    user_id = _parse_cookie(request.cookies.get(COOKIE_NAME, ""))
    if user_id is None:
        return {"authenticated": False}
    user = _load_user_by_id(user_id)
    if user is None:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "fullName": user.full_name,
            "role": user.role,
            "companyId": user.company_id,
        },
    }
