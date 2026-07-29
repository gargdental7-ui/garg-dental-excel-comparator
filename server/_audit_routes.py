"""Admin-only audit log viewing and staff activity dashboard. Read-only -
the actual log writes happen via _audit.py::log_action(), called from
every mutating endpoint elsewhere (auth, users, master excel, quotation
generation)."""
from fastapi import APIRouter, Depends

from _auth import CurrentUser, require_admin
from _db import get_connection
from _errors import handle_app_errors

router = APIRouter(prefix="/api/audit", tags=["audit"])

PAGE_SIZE = 50


def _log_out(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "user": row["user_full_name"],
        "action": row["action"],
        "entityType": row["entity_type"],
        "entityId": row["entity_id"],
        "ipAddress": row["ip_address"],
        "userAgent": row["user_agent"],
        "metadata": row["metadata"],
        "createdAt": row["created_at"].isoformat(),
    }


@router.get("/logs")
@handle_app_errors
def list_logs(page: int = 1, staff_id: str | None = None, current_user: CurrentUser = Depends(require_admin)):
    conditions = ["a.company_id = %s"]
    params: list = [current_user.company_id]
    if staff_id:
        conditions.append("a.user_id = %s")
        params.append(staff_id)
    where_clause = " and ".join(conditions)
    offset = max(page - 1, 0) * PAGE_SIZE

    with get_connection(
        company_id=current_user.company_id, user_id=current_user.id, role=current_user.role
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(f"select count(*) as total from audit_logs a where {where_clause}", params)
            total = cur.fetchone()["total"]

            cur.execute(
                f"select a.id, a.action, a.entity_type, a.entity_id, a.ip_address, a.user_agent, a.metadata, "
                f"a.created_at, u.full_name as user_full_name "
                f"from audit_logs a left join users u on u.id = a.user_id "
                f"where {where_clause} order by a.created_at desc limit %s offset %s",
                params + [PAGE_SIZE, offset],
            )
            rows = cur.fetchall()

    return {"logs": [_log_out(row) for row in rows], "total": total, "page": page, "pageSize": PAGE_SIZE}


@router.get("/staff-summary")
@handle_app_errors
def staff_summary(current_user: CurrentUser = Depends(require_admin)):
    """Per-staff cards for the activity dashboard: quotes created today and
    last-active timestamp (most recent audit log of any kind)."""
    with get_connection(
        company_id=current_user.company_id, user_id=current_user.id, role=current_user.role
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select u.id, u.full_name, u.role, u.active, "
                "(select count(*) from quotations q where q.created_by = u.id "
                " and q.created_at >= date_trunc('day', now())) as quotes_today, "
                "(select max(a.created_at) from audit_logs a where a.user_id = u.id) as last_active "
                "from users u where u.company_id = %s order by u.full_name",
                (current_user.company_id,),
            )
            rows = cur.fetchall()

    return {
        "staff": [
            {
                "id": str(row["id"]),
                "fullName": row["full_name"],
                "role": row["role"],
                "active": row["active"],
                "quotesToday": row["quotes_today"],
                "lastActive": row["last_active"].isoformat() if row["last_active"] else None,
            }
            for row in rows
        ]
    }
