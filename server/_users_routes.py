"""Super-Admin-only user management, scoped to whichever company is
specified in each request (resolved via _tenancy.py::resolve_company_scope
- since only super_admin ever calls this router, that's always the
explicit-company-required branch, not the staff default-to-own-company
one). Mirrors the router-per-feature convention used elsewhere, except
each endpoint takes require_super_admin as a parameter dependency (not
just a router-level `dependencies=[...]` guard) since every handler here
needs the resolved CurrentUser."""
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from _audit import log_action
from _auth import CurrentUser, require_super_admin
from _db import get_connection
from _errors import handle_app_errors
from _tenancy import resolve_company_scope

router = APIRouter(prefix="/api/users", tags=["users"])


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _user_out(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "username": row["username"],
        "fullName": row["full_name"],
        "role": row["role"],
        "active": row["active"],
        "companyId": str(row["company_id"]) if row["company_id"] else None,
        "createdAt": row["created_at"].isoformat(),
    }


@router.get("")
@handle_app_errors
def list_users(company_id: str, current_user: CurrentUser = Depends(require_super_admin)):
    scope = resolve_company_scope(current_user, company_id)
    with get_connection(company_id=scope, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select id, username, full_name, role, active, company_id, created_at from users "
                "where company_id = %s order by created_at",
                (scope,),
            )
            rows = cur.fetchall()
    return {"users": [_user_out(row) for row in rows]}


class CreateUserRequest(BaseModel):
    company_id: str
    username: str = Field(min_length=1)
    full_name: str = Field(min_length=1)
    password: str = Field(min_length=8)


@router.post("")
@handle_app_errors
def create_user(payload: CreateUserRequest, request: Request, current_user: CurrentUser = Depends(require_super_admin)):
    scope = resolve_company_scope(current_user, payload.company_id)
    with get_connection(company_id=scope, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute("select 1 from users where company_id = %s and username = %s", (scope, payload.username))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail={"message": "That username is already in use."})
            cur.execute(
                "insert into users (company_id, full_name, username, password_hash, role) "
                "values (%s, %s, %s, %s, 'staff') "
                "returning id, username, full_name, role, active, company_id, created_at",
                (scope, payload.full_name, payload.username, _hash_password(payload.password)),
            )
            row = cur.fetchone()
    log_action(current_user, scope, "create_user", "user", str(row["id"]), request, {"username": row["username"]})
    return _user_out(row)


class UpdateUserRequest(BaseModel):
    company_id: str  # which company this user currently belongs to (scope for the WHERE clause)
    full_name: str | None = Field(default=None, min_length=1)
    active: bool | None = None
    new_company_id: str | None = None  # set to move the user to a different company


@router.patch("/{user_id}")
@handle_app_errors
def update_user(user_id: str, payload: UpdateUserRequest, request: Request, current_user: CurrentUser = Depends(require_super_admin)):
    scope = resolve_company_scope(current_user, payload.company_id)
    updates = payload.model_dump(exclude_unset=True, exclude={"company_id", "new_company_id"})
    if payload.new_company_id is not None:
        updates["company_id"] = resolve_company_scope(current_user, payload.new_company_id)
    if not updates:
        raise HTTPException(status_code=400, detail={"message": "Nothing to update."})
    if user_id == current_user.id and updates.get("active") is False:
        raise HTTPException(status_code=400, detail={"message": "You can't disable your own account."})

    set_clause = ", ".join(f"{column} = %s" for column in updates)
    values = list(updates.values()) + [scope, user_id]

    with get_connection(company_id=scope, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"update users set {set_clause} where company_id = %s and id = %s "
                "returning id, username, full_name, role, active, company_id, created_at",
                values,
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail={"message": "User not found."})
    if "company_id" in updates:
        action = "move_user"
    elif "active" in updates:
        action = "enable_user" if updates["active"] else "disable_user"
    else:
        action = "update_user"
    log_action(current_user, scope, action, "user", str(row["id"]), request, {k: str(v) for k, v in updates.items()})
    return _user_out(row)


class ResetPasswordRequest(BaseModel):
    company_id: str
    new_password: str = Field(min_length=8)


@router.post("/{user_id}/reset-password")
@handle_app_errors
def reset_password(user_id: str, payload: ResetPasswordRequest, request: Request, current_user: CurrentUser = Depends(require_super_admin)):
    scope = resolve_company_scope(current_user, payload.company_id)
    with get_connection(company_id=scope, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "update users set password_hash = %s where company_id = %s and id = %s returning id, username",
                (_hash_password(payload.new_password), scope, user_id),
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail={"message": "User not found."})
    log_action(current_user, scope, "reset_password", "user", str(row["id"]), request, {"username": row["username"]})
    return {"ok": True}


@router.delete("/{user_id}")
@handle_app_errors
def delete_user(user_id: str, company_id: str, request: Request, current_user: CurrentUser = Depends(require_super_admin)):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail={"message": "You can't delete your own account."})
    scope = resolve_company_scope(current_user, company_id)
    with get_connection(company_id=scope, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "delete from users where company_id = %s and id = %s returning id, username", (scope, user_id)
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail={"message": "User not found."})
    log_action(current_user, scope, "delete_user", "user", str(row["id"]), request, {"username": row["username"]})
    return {"ok": True}
