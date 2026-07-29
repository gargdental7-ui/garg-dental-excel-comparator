"""Postgres connection layer for the Supabase-backed persistence added in
Phase 1. The FastAPI backend is the sole DB access path - no client ever
talks to Supabase directly - so the RLS policies in
server/migrations/0001_initial_schema.sql are defense-in-depth, not the
primary authorization boundary; the real checks live in route code. Those
policies only hold if every acquired connection sets the app.current_*
session vars below, which is why get_connection() is the single choke point
every other module must go through rather than opening psycopg connections
directly - a raw connection with no session vars set matches nothing in a
company_isolation policy (current_setting() reads back empty), so skipping
this helper fails closed rather than silently bypassing RLS.
"""
import os
from contextlib import contextmanager
from typing import Optional

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

_pool: Optional[ConnectionPool] = None


def is_configured() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")
    return url


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        # min_size=0 so a cold start (or a local dev process that never
        # touches the DB) doesn't pay for a connection nobody uses yet.
        # connect_timeout keeps an unreachable DB failing fast (a few
        # seconds) instead of hanging on the pool's default long wait -
        # callers like app/quotation_companies.py's fallback path depend on
        # failures surfacing quickly, not eventually.
        _pool = ConnectionPool(
            _database_url(),
            min_size=0,
            max_size=5,
            open=True,
            kwargs={"row_factory": dict_row, "connect_timeout": 5},
        )
    return _pool


@contextmanager
def get_connection(*, company_id: Optional[str] = None, user_id: Optional[str] = None, role: Optional[str] = None):
    """Yields a connection, inside a transaction, with app.current_company_id
    / app.current_user_id / app.current_role set for that transaction's
    duration (SET LOCAL semantics via set_config's is_local=true, so it
    automatically reverts when the transaction ends - never leaks across
    pooled connection reuse). Pass whichever of company_id/user_id/role the caller
    actually knows; routes that haven't resolved a user yet (e.g. login,
    which needs to read `users` before any identity exists) can omit all
    three and rely on route-level checks instead."""
    pool = _get_pool()
    with pool.connection(timeout=5) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("select set_config('app.current_company_id', %s, true)", (company_id or "",))
                cur.execute("select set_config('app.current_user_id', %s, true)", (user_id or "",))
                cur.execute("select set_config('app.current_role', %s, true)", (role or "",))
            yield conn


@contextmanager
def login_lookup_connection():
    """A narrow escape hatch for server/_auth.py's login() function only,
    which needs to read a users row before any company_id/user_id identity
    is known (the submitted username is all it has). Sets
    app.is_login_lookup='true' for the transaction's duration, matching the
    login_lookup RLS policy in server/migrations/0001_initial_schema.sql.
    Do not use this anywhere else - every other caller should go through
    get_connection(), which is what keeps this bypass auditable to one call
    site instead of becoming a general-purpose RLS escape hatch."""
    pool = _get_pool()
    with pool.connection(timeout=5) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("select set_config('app.is_login_lookup', 'true', true)")
            yield conn
