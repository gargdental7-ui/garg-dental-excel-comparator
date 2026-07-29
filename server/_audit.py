"""Audit logging helper, called from every mutating endpoint added in
Phases 2-4 (login, master Excel changes, quotation created, password
reset, user created/updated/disabled/deleted). One narrow function so
every call site looks the same and nothing forgets to capture IP/user
agent - "nothing should happen without a log" per the platform spec.
"""
import logging
from typing import TYPE_CHECKING

from fastapi import Request
from psycopg.types.json import Json

from _db import get_connection

if TYPE_CHECKING:
    # Deferred to avoid a circular import - _auth.py's login() calls
    # log_action(), so _audit.py can't import _auth at module load time.
    from _auth import CurrentUser

logger = logging.getLogger("gargdental.audit")


def log_action(
    current_user: "CurrentUser",
    action: str,
    entity_type: str,
    entity_id: str | None,
    request: Request,
    metadata: dict | None = None,
) -> None:
    """Best-effort - a logging failure must never break the action it's
    logging (same resilience principle as _quotation_routes.py's
    _persist_quotation: the primary action already succeeded by the time
    this is called, so a broken audit write shouldn't turn that into a
    500)."""
    try:
        ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
            request.client.host if request.client else None
        )
        user_agent = request.headers.get("user-agent")
        with get_connection(
            company_id=current_user.company_id, user_id=current_user.id, role=current_user.role
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "insert into audit_logs "
                    "(company_id, user_id, action, entity_type, entity_id, ip_address, user_agent, metadata) "
                    "values (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        current_user.company_id,
                        current_user.id,
                        action,
                        entity_type,
                        entity_id,
                        ip,
                        user_agent,
                        Json(metadata) if metadata is not None else None,
                    ),
                )
    except Exception:
        logger.exception("Failed to write audit log for action=%s entity_type=%s", action, entity_type)
