"""
Data collection / usage logging service.

ClearScript collects everything during the beta:
  - The full system prompt + user prompt + response for every AI call,
    along with token counts, latency, and cost estimate
  - The raw bytes and extracted text of every uploaded file
  - Generic usage events (PDF exports, feature use, etc.)
  - User feedback submissions

This is the raw material for prompt iteration, model A/B testing,
per-user usage metering, and product analytics.

All writes go through this module so the call sites in routers and
services stay clean. SQLite is used today; the same function signatures
will work against Postgres / Supabase if we migrate.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from services import database

logger = logging.getLogger(__name__)


# ─── Cost estimation ─────────────────────────────────────────────────────────

# Per-1M-token rates we use for the cost_usd column on ai_calls. These are
# coarse estimates — refine against the actual OpenAI billing dashboard.
# The whole point of logging cost_usd is so we can re-derive it later if
# the rates were wrong.
_MODEL_PRICING_PER_MTOK: dict[str, tuple[float, float]] = {
    # (input_per_mtok_usd, output_per_mtok_usd)
    "gpt-5.4-mini":  (0.25, 2.00),
    "gpt-5-mini":    (0.25, 2.00),
    "gpt-5":         (1.25, 10.00),
    "gpt-4o-mini":   (0.15, 0.60),
    "gpt-4o":        (2.50, 10.00),
    "gpt-4.1-mini":  (0.40, 1.60),
}


def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Estimate the dollar cost of a single AI call. Falls back to gpt-5.4-mini
    pricing for unknown models so the column is always populated.
    """
    inp, outp = _MODEL_PRICING_PER_MTOK.get(model, _MODEL_PRICING_PER_MTOK["gpt-5.4-mini"])
    return round(
        (prompt_tokens / 1_000_000.0) * inp
        + (completion_tokens / 1_000_000.0) * outp,
        6,
    )


# ─── AI call logging ─────────────────────────────────────────────────────────

def log_ai_call(
    *,
    operation: str,
    model: str,
    system_prompt: Optional[str],
    user_prompt: Optional[str],
    response_text: Optional[str],
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    latency_ms: int = 0,
    error: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Optional[int]:
    """
    Persist a single AI call with its full prompt, response, token counts,
    and cost estimate. Returns the new row id, or None on failure (logging
    must never break the request).
    """
    total_tokens = prompt_tokens + completion_tokens
    cost = estimate_cost_usd(model, prompt_tokens, completion_tokens)
    try:
        conn = database.get_conn()
        try:
            row_id = database.execute_insert(
                conn,
                """
                INSERT INTO ai_calls (
                    operation, model, system_prompt, user_prompt, response_text,
                    prompt_tokens, completion_tokens, total_tokens, latency_ms,
                    cost_usd, error, user_id, session_id, request_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    operation,
                    model,
                    system_prompt,
                    user_prompt,
                    response_text,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    latency_ms,
                    cost,
                    error,
                    user_id,
                    session_id,
                    request_id,
                ),
            )
            conn.commit()
            return row_id
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f"Failed to log AI call ({operation}): {e}")
        return None


# ─── File upload logging ─────────────────────────────────────────────────────

def log_file_upload(
    *,
    upload_kind: str,
    filename: Optional[str],
    content_type: Optional[str],
    file_bytes: Optional[bytes],
    extracted_text: Optional[str],
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    related_id: Optional[int] = None,
) -> Optional[int]:
    """
    Persist a file the user uploaded — original bytes plus extracted text.

    upload_kind values: "pbm_contract", "plan_document", "disclosure",
    "claims_csv", "exclusion_list", "formulary_csv".

    related_id is the foreign key into the analysis table the upload
    produced (e.g. contract_analyses.id for a pbm_contract upload), so
    we can join back later.
    """
    byte_size = len(file_bytes) if file_bytes else 0
    try:
        conn = database.get_conn()
        try:
            # Both sqlite3 and psycopg accept raw `bytes` for BLOB/BYTEA
            # columns; sqlite3.Binary() is no longer required.
            row_id = database.execute_insert(
                conn,
                """
                INSERT INTO file_uploads (
                    upload_kind, filename, content_type, byte_size,
                    file_bytes, extracted_text, user_id, session_id, related_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    upload_kind,
                    filename,
                    content_type,
                    byte_size,
                    file_bytes if file_bytes else None,
                    extracted_text,
                    user_id,
                    session_id,
                    related_id,
                ),
            )
            conn.commit()
            return row_id
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f"Failed to log file upload ({upload_kind}, {filename}): {e}")
        return None


# ─── Generic event logging ───────────────────────────────────────────────────

def log_event(
    *,
    event_type: str,
    payload: Optional[dict[str, Any]] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Optional[int]:
    """
    Catch-all event logger. Use for things that don't have their own table:
    pdf_exported, feedback_submitted, audit_letter_copied, etc.
    """
    try:
        payload_json = json.dumps(payload, default=str) if payload else None
        conn = database.get_conn()
        try:
            row_id = database.execute_insert(
                conn,
                """
                INSERT INTO usage_events (event_type, payload_json, user_id, session_id, ip, user_agent)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event_type, payload_json, user_id, session_id, ip, user_agent),
            )
            conn.commit()
            return row_id
        finally:
            conn.close()
    except (Exception,) as e:
        logger.warning(f"Failed to log event ({event_type}): {e}")
        return None


# ─── Feedback submission ─────────────────────────────────────────────────────

def save_feedback(
    *,
    message: str,
    name: Optional[str] = None,
    email: Optional[str] = None,
    page: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Optional[int]:
    """Persist a single feedback-form submission. Returns the new row id."""
    try:
        conn = database.get_conn()
        try:
            row_id = database.execute_insert(
                conn,
                """
                INSERT INTO feedback (name, email, page, message, user_id, session_id, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (name, email, page, message, user_id, session_id, user_agent),
            )
            conn.commit()
            return row_id
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Failed to save feedback: {e}")
        return None
