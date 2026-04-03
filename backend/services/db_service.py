"""
SQLite persistent storage for ClearScript.
Stores uploaded claims, contract analyses, and audit results so data survives server restarts.
"""

import sqlite3
import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "clearscript.db"


def _get_conn() -> sqlite3.Connection:
    """Get a database connection with proper settings."""
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ensure_db() -> None:
    """Create database and tables if they don't exist."""
    try:
        conn = _get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS uploaded_claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                upload_date TEXT DEFAULT (datetime('now')),
                claims_json TEXT NOT NULL,
                claims_count INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS contract_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                analysis_date TEXT DEFAULT (datetime('now')),
                analysis_json TEXT NOT NULL,
                risk_score INTEGER,
                audit_rights_score INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_type TEXT NOT NULL,
                analysis_date TEXT DEFAULT (datetime('now')),
                result_json TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def save_claims(filename: str, claims: List[Dict[str, Any]]) -> int:
    """Save uploaded claims to persistent storage. Returns row ID."""
    conn = _get_conn()
    try:
        claims_json = json.dumps(claims, default=str)
        cursor = conn.execute(
            "INSERT INTO uploaded_claims (filename, claims_json, claims_count) VALUES (?, ?, ?)",
            (filename, claims_json, len(claims))
        )
        row_id = cursor.lastrowid
        conn.commit()
        return row_id
    except (sqlite3.Error, json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to save claims: {e}")
        raise
    finally:
        conn.close()


def load_latest_claims() -> Optional[Dict[str, Any]]:
    """Load the most recently uploaded claims dataset."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT filename, upload_date, claims_json, claims_count FROM uploaded_claims ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row:
            try:
                claims = json.loads(row[2])
            except json.JSONDecodeError:
                logger.error(f"Corrupted claims JSON for file: {row[0]}")
                return None
            return {
                "filename": row[0],
                "upload_date": row[1],
                "claims": claims,
                "claims_count": row[3],
            }
        return None
    except sqlite3.Error as e:
        logger.error(f"Failed to load claims: {e}")
        return None
    finally:
        conn.close()


def save_contract_analysis(filename: str, analysis: dict, risk_score: int, audit_rights_score: int) -> int:
    """Save contract analysis to persistent storage."""
    conn = _get_conn()
    try:
        analysis_json = json.dumps(analysis, default=str)
        cursor = conn.execute(
            "INSERT INTO contract_analyses (filename, analysis_json, risk_score, audit_rights_score) VALUES (?, ?, ?, ?)",
            (filename, analysis_json, risk_score, audit_rights_score)
        )
        row_id = cursor.lastrowid
        conn.commit()
        return row_id
    except (sqlite3.Error, json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to save contract analysis: {e}")
        raise
    finally:
        conn.close()


def save_audit_result(analysis_type: str, result: dict) -> int:
    """Save any analysis result for historical tracking."""
    conn = _get_conn()
    try:
        result_json = json.dumps(result, default=str)
        cursor = conn.execute(
            "INSERT INTO audit_results (analysis_type, result_json) VALUES (?, ?)",
            (analysis_type, result_json)
        )
        row_id = cursor.lastrowid
        conn.commit()
        return row_id
    except (sqlite3.Error, json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to save audit result: {e}")
        raise
    finally:
        conn.close()


def get_analysis_history(analysis_type: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent analysis history."""
    conn = _get_conn()
    try:
        if analysis_type:
            rows = conn.execute(
                "SELECT analysis_type, analysis_date, result_json FROM audit_results WHERE analysis_type = ? ORDER BY id DESC LIMIT ?",
                (analysis_type, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT analysis_type, analysis_date, result_json FROM audit_results ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
        results = []
        for r in rows:
            try:
                parsed = json.loads(r[2])
            except json.JSONDecodeError:
                logger.warning(f"Skipping corrupted result for {r[0]} at {r[1]}")
                continue
            results.append({"type": r[0], "date": r[1], "result": parsed})
        return results
    except sqlite3.Error as e:
        logger.error(f"Failed to load analysis history: {e}")
        return []
    finally:
        conn.close()


def clear_claims() -> None:
    """Clear uploaded claims (reset to synthetic)."""
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM uploaded_claims")
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to clear claims: {e}")
        raise
    finally:
        conn.close()


# Initialize DB on import
_ensure_db()
