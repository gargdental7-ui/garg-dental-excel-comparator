"""Admin-only user management. Mirrors the router-per-feature convention
used by _collection_routes.py/_quotation_routes.py, except each endpoint
takes require_admin as a parameter dependency (not just a router-level
`dependencies=[...]` guard) since every handler here needs the resolved
CurrentUser - to scope queries by company_id and to self-protect against
an admin disabling/demoting/deleting their own account."""
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from _audit import log_action
from _auth import CurrentUser, require_admin
from _db import get_connection
from _errors import handle_app_errors

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
        "createdAt": row["created_at"].isoformat(),
    }


@router.get("")
@handle_app_errors
def list_users(current_user: CurrentUser = Depends(require_admin)):
    with get_connection(company_id=current_user.company_id, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select id, username, full_name, role, active, created_at from users "
                "where company_id = %s order by created_at",
                (current_user.company_id,),
            )
            rows = cur.fetchall()
    return {"users": [_user_out(row) for row in rows]}


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1)
    full_name: str = Field(min_length=1)
    password: str = Field(min_length=8)
    role: str = Field(pattern="^(admin|staff)$")


@router.post("")
@handle_app_errors
def create_user(payload: CreateUserRequest, request: Request, current_user: CurrentUser = Depends(require_admin)):
    with get_connection(company_id=current_user.company_id, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute("select 1 from users where company_id = %s and username = %s", (current_user.company_id, payload.username))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail={"message": "That username is already in use."})
            cur.execute(
                "insert into users (company_id, full_name, username, password_hash, role) "
                "values (%s, %s, %s, %s, %s) "
                "returning id, username, full_name, role, active, created_at",
                (current_user.company_id, payload.full_name, payload.username, _hash_password(payload.password), payload.role),
            )
            row = cur.fetchone()
    log_action(current_user, "create_user", "user", str(row["id"]), request, {"username": row["username"], "role": row["role"]})
    return _user_out(row)


class UpdateUserRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1)
    role: str | None = Field(default=None, pattern="^(admin|staff)$")
    active: bool | None = None


@router.patch("/{user_id}")
@handle_app_errors
def update_user(user_id: str, payload: UpdateUserRequest, request: Request, current_user: CurrentUser = Depends(require_admin)):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail={"message": "Nothing to update."})
    if user_id == current_user.id and updates.get("active") is False:
        raise HTTPException(status_code=400, detail={"message": "You can't disable your own account."})
    if user_id == current_user.id and updates.get("role") == "staff":
        raise HTTPException(status_code=400, detail={"message": "You can't demote your own account."})

    column_map = {"full_name": "full_name", "role": "role", "active": "active"}
    set_clause = ", ".join(f"{column_map[k]} = %s" for k in updates)
    values = list(updates.values()) + [current_user.company_id, user_id]

    with get_connection(company_id=current_user.company_id, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"update users set {set_clause} where company_id = %s and id = %s "
                "returning id, username, full_name, role, active, created_at",
                values,
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail={"message": "User not found."})
    # "disable_user"/"enable_user" specifically when that's what changed
    # (matches the spec's activity-log examples more precisely than a
    # generic "update_user" would), otherwise a generic edit.
    if "active" in updates:
        action = "enable_user" if updates["active"] else "disable_user"
    else:
        action = "update_user"
    log_action(current_user, action, "user", str(row["id"]), request, updates)
    return _user_out(row)


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8)


@router.post("/{user_id}/reset-password")
@handle_app_errors
def reset_password(user_id: str, payload: ResetPasswordRequest, request: Request, current_user: CurrentUser = Depends(require_admin)):
    with get_connection(company_id=current_user.company_id, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "update users set password_hash = %s where company_id = %s and id = %s returning id, username",
                (_hash_password(payload.new_password), current_user.company_id, user_id),
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail={"message": "User not found."})
    log_action(current_user, "reset_password", "user", str(row["id"]), request, {"username": row["username"]})
    return {"ok": True}


@router.delete("/{user_id}")
@handle_app_errors
def delete_user(user_id: str, request: Request, current_user: CurrentUser = Depends(require_admin)):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail={"message": "You can't delete your own account."})
    with get_connection(company_id=current_user.company_id, user_id=current_user.id, role=current_user.role) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "delete from users where company_id = %s and id = %s returning id, username", (current_user.company_id, user_id)
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail={"message": "User not found."})
    log_action(current_user, "delete_user", "user", str(row["id"]), request, {"username": row["username"]})
    return {"ok": True}
