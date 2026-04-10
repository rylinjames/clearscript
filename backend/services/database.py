"""
Tiny database abstraction layer.

ClearScript needs to run against two databases:
  - **SQLite** for local development and the pytest suite (zero-setup,
    in-process, deleted between tests via the `_isolated_db` fixture)
  - **Postgres on Supabase** for production on Render so contract data,
    AI call logs, and uploaded files survive container restarts

This module hides the small differences between the two so the rest of
db_service / usage_service can call one set of helpers without caring.

Backend selection:
  - If the `SUPABASE_DB_URL` environment variable is set at process
    start, every connection is opened against Postgres.
  - Otherwise we fall back to SQLite at `backend/data/clearscript.db`.

The pytest fixture in tests/conftest.py monkeypatches `DB_PATH` and
explicitly clears `SUPABASE_DB_URL` before importing, so tests always
go through the SQLite path even if the developer has the env var set
locally for debugging.
"""
from __future__ import annotations

import os
import sqlite3
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ─── Backend selection ───────────────────────────────────────────────────────

def _supabase_url() -> Optional[str]:
    """
    Resolve the Supabase Postgres connection string at call time (not at
    import time) so tests can monkeypatch the env after the module loads.
    """
    url = os.getenv("SUPABASE_DB_URL", "").strip()
    return url if url else None


def using_postgres() -> bool:
    """Return True if we should target Postgres on this call."""
    return _supabase_url() is not None


# ─── Module-level config ─────────────────────────────────────────────────────

# SQLite path (used when SUPABASE_DB_URL is not set). Tests monkeypatch
# this attribute to point at a temp file per test.
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "clearscript.db"


# ─── Connection ──────────────────────────────────────────────────────────────

def get_conn():
    """
    Open a fresh connection. Caller is responsible for closing.

    Returns either a sqlite3.Connection or a psycopg.Connection depending
    on the backend in use. The two have different APIs in places, so the
    helpers below abstract over them.
    """
    if using_postgres():
        try:
            import psycopg
        except ImportError as e:
            raise RuntimeError(
                "SUPABASE_DB_URL is set but the psycopg package is not "
                "installed. Run: pip install 'psycopg[binary]>=3.1'"
            ) from e
        return psycopg.connect(_supabase_url(), autocommit=False)
    else:
        os.makedirs(DB_PATH.parent, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("PRAGMA journal_mode=WAL")
        return conn


# ─── Query helpers ───────────────────────────────────────────────────────────

def _adapt_query(query: str) -> str:
    """
    Convert SQLite-style `?` parameter placeholders to Postgres `%s`
    placeholders if we're targeting Postgres. The function bodies in
    db_service / usage_service all use `?` for consistency.
    """
    if using_postgres():
        return query.replace("?", "%s")
    return query


def execute(conn, query: str, params: tuple = ()) -> Any:
    """
    Run a query and return the cursor. Use this for SELECTs and for
    INSERTs/UPDATEs/DELETEs that don't need the new row id.
    """
    return conn.execute(_adapt_query(query), params)


def execute_insert(conn, query: str, params: tuple = ()) -> Optional[int]:
    """
    Run an INSERT and return the new row's primary key.

    SQLite uses `cursor.lastrowid`. Postgres needs `RETURNING id`
    appended to the query. This helper hides both behaviors so the
    function bodies don't need a backend check at every call site.
    """
    if using_postgres():
        adapted = _adapt_query(query)
        if "returning" not in adapted.lower():
            adapted = adapted.rstrip().rstrip(";") + " RETURNING id"
        cur = conn.execute(adapted, params)
        row = cur.fetchone()
        return int(row[0]) if row else None
    else:
        cur = conn.execute(query, params)
        return cur.lastrowid


# ─── Schema ──────────────────────────────────────────────────────────────────

# SQLite-flavored DDL — used for local dev and tests.
SQLITE_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS uploaded_claims (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        upload_date TEXT DEFAULT (datetime('now')),
        claims_json TEXT NOT NULL,
        claims_count INTEGER NOT NULL,
        contract_id INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS contract_analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        analysis_date TEXT DEFAULT (datetime('now')),
        analysis_json TEXT NOT NULL,
        risk_score INTEGER,
        audit_rights_score INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        analysis_type TEXT NOT NULL,
        analysis_date TEXT DEFAULT (datetime('now')),
        result_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_calls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT DEFAULT (datetime('now')),
        operation TEXT NOT NULL,
        model TEXT NOT NULL,
        system_prompt TEXT,
        user_prompt TEXT,
        response_text TEXT,
        prompt_tokens INTEGER,
        completion_tokens INTEGER,
        total_tokens INTEGER,
        latency_ms INTEGER,
        cost_usd REAL,
        error TEXT,
        user_id TEXT,
        session_id TEXT,
        request_id TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS file_uploads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT DEFAULT (datetime('now')),
        upload_kind TEXT NOT NULL,
        filename TEXT,
        content_type TEXT,
        byte_size INTEGER,
        file_bytes BLOB,
        extracted_text TEXT,
        user_id TEXT,
        session_id TEXT,
        related_id INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS usage_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT DEFAULT (datetime('now')),
        event_type TEXT NOT NULL,
        payload_json TEXT,
        user_id TEXT,
        session_id TEXT,
        ip TEXT,
        user_agent TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT DEFAULT (datetime('now')),
        name TEXT,
        email TEXT,
        page TEXT,
        message TEXT NOT NULL,
        user_id TEXT,
        session_id TEXT,
        user_agent TEXT
    )
    """,
]

# Postgres-flavored DDL — same schema, native types.
POSTGRES_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS uploaded_claims (
        id BIGSERIAL PRIMARY KEY,
        filename TEXT NOT NULL,
        upload_date TIMESTAMPTZ DEFAULT NOW(),
        claims_json TEXT NOT NULL,
        claims_count INTEGER NOT NULL,
        contract_id INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS contract_analyses (
        id BIGSERIAL PRIMARY KEY,
        filename TEXT NOT NULL,
        analysis_date TIMESTAMPTZ DEFAULT NOW(),
        analysis_json TEXT NOT NULL,
        risk_score INTEGER,
        audit_rights_score INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_results (
        id BIGSERIAL PRIMARY KEY,
        analysis_type TEXT NOT NULL,
        analysis_date TIMESTAMPTZ DEFAULT NOW(),
        result_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_calls (
        id BIGSERIAL PRIMARY KEY,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        operation TEXT NOT NULL,
        model TEXT NOT NULL,
        system_prompt TEXT,
        user_prompt TEXT,
        response_text TEXT,
        prompt_tokens INTEGER,
        completion_tokens INTEGER,
        total_tokens INTEGER,
        latency_ms INTEGER,
        cost_usd DOUBLE PRECISION,
        error TEXT,
        user_id TEXT,
        session_id TEXT,
        request_id TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS file_uploads (
        id BIGSERIAL PRIMARY KEY,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        upload_kind TEXT NOT NULL,
        filename TEXT,
        content_type TEXT,
        byte_size INTEGER,
        file_bytes BYTEA,
        extracted_text TEXT,
        user_id TEXT,
        session_id TEXT,
        related_id BIGINT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS usage_events (
        id BIGSERIAL PRIMARY KEY,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        event_type TEXT NOT NULL,
        payload_json TEXT,
        user_id TEXT,
        session_id TEXT,
        ip TEXT,
        user_agent TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS feedback (
        id BIGSERIAL PRIMARY KEY,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        name TEXT,
        email TEXT,
        page TEXT,
        message TEXT NOT NULL,
        user_id TEXT,
        session_id TEXT,
        user_agent TEXT
    )
    """,
]


def init_schema() -> None:
    """
    Create every table if it doesn't already exist. Idempotent — safe to
    run on every process start.
    """
    statements = POSTGRES_SCHEMA if using_postgres() else SQLITE_SCHEMA
    try:
        conn = get_conn()
        try:
            for stmt in statements:
                conn.execute(stmt)
            conn.commit()
        finally:
            conn.close()
        logger.info(
            f"Schema initialized on {'Postgres' if using_postgres() else 'SQLite'}"
        )
    except Exception as e:
        logger.error(f"Schema init failed: {e}")
        raise
