"""
Persistent storage for ClearScript.

Stores uploaded claims, contract analyses, audit results, and analytics
on top of either SQLite (local dev + tests) or Postgres on Supabase
(production). Backend selection is handled by `services.database` —
this file just calls the helpers it exposes.

Every function uses `?` parameter placeholders; the abstraction layer
translates them to `%s` if we're targeting Postgres.
"""

import json
import logging
from typing import List, Dict, Any, Optional

from services import database
from services.database import (  # re-export so existing imports keep working
    DB_PATH,  # noqa: F401  — patched by the test fixture
)

logger = logging.getLogger(__name__)


def _get_conn():
    """Backwards-compatible alias for the abstraction's get_conn()."""
    return database.get_conn()


def _ensure_db() -> None:
    """Create database and tables if they don't exist."""
    database.init_schema()


# ─── Claims ──────────────────────────────────────────────────────────────────

def save_claims(filename: str, claims: List[Dict[str, Any]], contract_id: Optional[int] = None) -> int:
    """Save uploaded claims to the database, optionally associated with a specific contract."""
    conn = database.get_conn()
    try:
        claims_json = json.dumps(claims, default=str)
        # If uploading for a specific contract, remove any previous claims
        # for that contract first so there's only ever one active claims
        # file per contract.
        if contract_id is not None:
            database.execute(
                conn,
                "DELETE FROM uploaded_claims WHERE contract_id = ?",
                (contract_id,),
            )
        row_id = database.execute_insert(
            conn,
            "INSERT INTO uploaded_claims (filename, claims_json, claims_count, contract_id) VALUES (?, ?, ?, ?)",
            (filename, claims_json, len(claims), contract_id),
        )
        conn.commit()
        return row_id
    except Exception as e:
        logger.error(f"Failed to save claims: {e}")
        raise
    finally:
        conn.close()


def load_claims_for_contract(contract_id: int) -> Optional[Dict[str, Any]]:
    """Load the claims file associated with a specific contract."""
    conn = database.get_conn()
    try:
        row = database.execute(
            conn,
            "SELECT filename, upload_date, claims_json, claims_count FROM uploaded_claims WHERE contract_id = ? ORDER BY id DESC LIMIT 1",
            (contract_id,),
        ).fetchone()
        if not row:
            return None
        try:
            claims = json.loads(row[2])
        except json.JSONDecodeError:
            logger.error(f"Corrupted claims JSON for contract {contract_id}: {row[0]}")
            return None
        return {
            "filename": row[0],
            "upload_date": str(row[1]) if row[1] is not None else None,
            "claims": claims,
            "claims_count": row[3],
            "contract_id": contract_id,
        }
    except Exception as e:
        logger.error(f"Failed to load claims for contract {contract_id}: {e}")
        return None
    finally:
        conn.close()


def load_latest_claims() -> Optional[Dict[str, Any]]:
    """Load the most recent claims file regardless of contract association."""
    conn = database.get_conn()
    try:
        row = database.execute(
            conn,
            "SELECT filename, upload_date, claims_json, claims_count, contract_id FROM uploaded_claims ORDER BY id DESC LIMIT 1",
        ).fetchone()
        if not row:
            return None
        try:
            claims = json.loads(row[2])
        except json.JSONDecodeError:
            logger.error(f"Corrupted claims JSON for file: {row[0]}")
            return None
        return {
            "filename": row[0],
            "upload_date": str(row[1]) if row[1] is not None else None,
            "claims": claims,
            "claims_count": row[3],
            "contract_id": row[4] if len(row) > 4 else None,
        }
    except Exception as e:
        logger.error(f"Failed to load claims: {e}")
        return None
    finally:
        conn.close()


def clear_claims(contract_id: Optional[int] = None) -> None:
    """Clear claims data. If contract_id is specified, only clear that contract's claims."""
    conn = database.get_conn()
    try:
        if contract_id is not None:
            database.execute(conn, "DELETE FROM uploaded_claims WHERE contract_id = ?", (contract_id,))
        else:
            database.execute(conn, "DELETE FROM uploaded_claims")
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to clear claims: {e}")
        raise
    finally:
        conn.close()


# ─── Contract analyses ───────────────────────────────────────────────────────

def save_contract_analysis(filename: str, analysis: dict, risk_score: int = 0, audit_rights_score: int = 0) -> int:
    conn = database.get_conn()
    try:
        analysis_json = json.dumps(analysis, default=str)
        row_id = database.execute_insert(
            conn,
            "INSERT INTO contract_analyses (filename, analysis_json, risk_score, audit_rights_score) VALUES (?, ?, ?, ?)",
            (filename, analysis_json, risk_score, audit_rights_score),
        )
        conn.commit()
        return row_id
    except Exception as e:
        logger.error(f"Failed to save contract analysis: {e}")
        raise
    finally:
        conn.close()


def update_contract_analysis(contract_id: int, analysis: dict) -> None:
    """Update an existing contract analysis row in-place (e.g. after
    re-enrichment with newly uploaded claims data). Does NOT create a
    duplicate row."""
    conn = database.get_conn()
    try:
        analysis_json = json.dumps(analysis, default=str)
        # Recompute the derived score fields so the list view stays
        # consistent with the updated analysis.
        wa = analysis.get("weighted_assessment", {}) if isinstance(analysis, dict) else {}
        risk_score = int(analysis.get("overall_risk_score", 0) or 0)
        audit = analysis.get("audit_rights", {}) if isinstance(analysis, dict) else {}
        audit_score = int(audit.get("score", 0) or 0) if isinstance(audit, dict) else 0
        database.execute(
            conn,
            "UPDATE contract_analyses SET analysis_json = ?, risk_score = ?, audit_rights_score = ? WHERE id = ?",
            (analysis_json, risk_score, audit_score, contract_id),
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to update contract analysis id={contract_id}: {e}")
        raise
    finally:
        conn.close()


def _row_to_contract(row) -> Optional[Dict[str, Any]]:
    """Decode a contract_analyses row into the standard dict shape."""
    try:
        parsed = json.loads(row[3])
    except json.JSONDecodeError:
        logger.error(f"Corrupted contract analysis JSON for file: {row[1]}")
        return None
    return {
        "id": row[0],
        "filename": row[1],
        "analysis_date": str(row[2]) if row[2] is not None else None,
        "analysis": parsed,
        "risk_score": row[4],
        "audit_rights_score": row[5],
    }


def load_latest_contract_analysis() -> Optional[Dict[str, Any]]:
    conn = database.get_conn()
    try:
        row = database.execute(
            conn,
            "SELECT id, filename, analysis_date, analysis_json, risk_score, audit_rights_score "
            "FROM contract_analyses ORDER BY id DESC LIMIT 1",
        ).fetchone()
        if not row:
            return None
        return _row_to_contract(row)
    except Exception as e:
        logger.error(f"Failed to load latest contract analysis: {e}")
        return None
    finally:
        conn.close()


def load_contract_analysis_by_id(contract_id: int) -> Optional[Dict[str, Any]]:
    conn = database.get_conn()
    try:
        row = database.execute(
            conn,
            "SELECT id, filename, analysis_date, analysis_json, risk_score, audit_rights_score "
            "FROM contract_analyses WHERE id = ? LIMIT 1",
            (contract_id,),
        ).fetchone()
        if not row:
            return None
        return _row_to_contract(row)
    except Exception as e:
        logger.error(f"Failed to load contract analysis by id={contract_id}: {e}")
        return None
    finally:
        conn.close()


def list_contract_analyses(limit: int = 50) -> List[Dict[str, Any]]:
    conn = database.get_conn()
    try:
        rows = database.execute(
            conn,
            "SELECT id, filename, analysis_date, risk_score, audit_rights_score, analysis_json "
            "FROM contract_analyses ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            deal_score: Optional[int] = None
            risk_level: Optional[str] = None
            try:
                analysis = json.loads(r[5]) if r[5] else {}
                wa = analysis.get("weighted_assessment", {}) if isinstance(analysis, dict) else {}
                if isinstance(wa, dict):
                    if wa.get("deal_score") is not None:
                        deal_score = int(wa["deal_score"])
                    if wa.get("risk_level"):
                        risk_level = str(wa["risk_level"])
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
            out.append({
                "id": r[0],
                "filename": r[1],
                "analysis_date": str(r[2]) if r[2] is not None else None,
                "risk_score": r[3],
                "audit_rights_score": r[4],
                "deal_score": deal_score,
                "risk_level": risk_level,
            })
        return out
    except Exception as e:
        logger.error(f"Failed to list contract analyses: {e}")
        return []
    finally:
        conn.close()


# ─── Generic audit result history ────────────────────────────────────────────

def save_audit_result(analysis_type: str, result: dict) -> int:
    conn = database.get_conn()
    try:
        result_json = json.dumps(result, default=str)
        row_id = database.execute_insert(
            conn,
            "INSERT INTO audit_results (analysis_type, result_json) VALUES (?, ?)",
            (analysis_type, result_json),
        )
        conn.commit()
        return row_id
    except Exception as e:
        logger.error(f"Failed to save audit result: {e}")
        raise
    finally:
        conn.close()


def get_analysis_history(analysis_type: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    conn = database.get_conn()
    try:
        if analysis_type:
            rows = database.execute(
                conn,
                "SELECT analysis_type, analysis_date, result_json FROM audit_results WHERE analysis_type = ? ORDER BY id DESC LIMIT ?",
                (analysis_type, limit),
            ).fetchall()
        else:
            rows = database.execute(
                conn,
                "SELECT analysis_type, analysis_date, result_json FROM audit_results ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        results = []
        for r in rows:
            try:
                parsed = json.loads(r[2])
            except json.JSONDecodeError:
                logger.warning(f"Skipping corrupted result for {r[0]} at {r[1]}")
                continue
            results.append({
                "type": r[0],
                "date": str(r[1]) if r[1] is not None else None,
                "result": parsed,
            })
        return results
    except Exception as e:
        logger.error(f"Failed to load analysis history: {e}")
        return []
    finally:
        conn.close()


# ─── Plan Documents per Contract ─────────────────────────────────────────────


def save_plan_doc(contract_id: int, filename: str, benefits: dict, document_type: str | None = None) -> int:
    """Save parsed plan document benefits scoped to a contract. Replaces any previous plan doc for this contract."""
    conn = database.get_conn()
    try:
        database.execute(conn, "DELETE FROM uploaded_plan_docs WHERE contract_id = ?", (contract_id,))
        benefits_json = json.dumps(benefits, default=str)
        row_id = database.execute_insert(
            conn,
            "INSERT INTO uploaded_plan_docs (contract_id, filename, benefits_json, document_type) VALUES (?, ?, ?, ?)",
            (contract_id, filename, benefits_json, document_type),
        )
        conn.commit()
        return row_id
    except Exception as e:
        logger.error(f"Failed to save plan doc for contract {contract_id}: {e}")
        raise
    finally:
        conn.close()


def load_plan_doc(contract_id: int) -> Optional[Dict[str, Any]]:
    """Load the saved plan document for a contract."""
    conn = database.get_conn()
    try:
        row = database.execute(
            conn,
            "SELECT filename, upload_date, benefits_json, document_type FROM uploaded_plan_docs WHERE contract_id = ? ORDER BY id DESC LIMIT 1",
            (contract_id,),
        ).fetchone()
        if not row:
            return None
        try:
            benefits = json.loads(row[2])
        except json.JSONDecodeError:
            return None
        return {
            "filename": row[0],
            "upload_date": str(row[1]) if row[1] else None,
            "benefits": benefits,
            "document_type": row[3],
        }
    except Exception as e:
        logger.error(f"Failed to load plan doc for contract {contract_id}: {e}")
        return None
    finally:
        conn.close()


# ─── Cross-Reference Results per Contract ────────────────────────────────────


def save_cross_reference(contract_id: int, result: dict) -> int:
    """Save cross-reference results scoped to a contract. Replaces any previous result."""
    conn = database.get_conn()
    try:
        database.execute(conn, "DELETE FROM cross_reference_results WHERE contract_id = ?", (contract_id,))
        result_json = json.dumps(result, default=str)
        row_id = database.execute_insert(
            conn,
            "INSERT INTO cross_reference_results (contract_id, result_json) VALUES (?, ?)",
            (contract_id, result_json),
        )
        conn.commit()
        return row_id
    except Exception as e:
        logger.error(f"Failed to save cross-ref for contract {contract_id}: {e}")
        raise
    finally:
        conn.close()


def load_cross_reference(contract_id: int) -> Optional[Dict[str, Any]]:
    """Load saved cross-reference results for a contract."""
    conn = database.get_conn()
    try:
        row = database.execute(
            conn,
            "SELECT upload_date, result_json FROM cross_reference_results WHERE contract_id = ? ORDER BY id DESC LIMIT 1",
            (contract_id,),
        ).fetchone()
        if not row:
            return None
        try:
            result = json.loads(row[1])
        except json.JSONDecodeError:
            return None
        return {"upload_date": str(row[0]) if row[0] else None, "result": result}
    except Exception as e:
        logger.error(f"Failed to load cross-ref for contract {contract_id}: {e}")
        return None
    finally:
        conn.close()


# ─── Disclosure Analyses ─────────────────────────────────────────────────────


def save_disclosure_analysis(filename: str, analysis: dict, completeness_score: int = 0) -> int:
    conn = database.get_conn()
    try:
        analysis_json = json.dumps(analysis, default=str)
        row_id = database.execute_insert(
            conn,
            "INSERT INTO disclosure_analyses (filename, analysis_json, completeness_score) VALUES (?, ?, ?)",
            (filename, analysis_json, completeness_score),
        )
        conn.commit()
        return row_id
    except Exception as e:
        logger.error(f"Failed to save disclosure analysis: {e}")
        raise
    finally:
        conn.close()


def list_disclosure_analyses(limit: int = 50) -> List[Dict[str, Any]]:
    conn = database.get_conn()
    try:
        rows = database.execute(
            conn,
            "SELECT id, filename, analysis_date, completeness_score FROM disclosure_analyses ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "id": r[0],
                "filename": r[1],
                "analysis_date": str(r[2]) if r[2] else None,
                "completeness_score": r[3],
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"Failed to list disclosure analyses: {e}")
        return []
    finally:
        conn.close()


def load_disclosure_analysis_by_id(disclosure_id: int) -> Optional[Dict[str, Any]]:
    conn = database.get_conn()
    try:
        row = database.execute(
            conn,
            "SELECT id, filename, analysis_date, analysis_json, completeness_score FROM disclosure_analyses WHERE id = ?",
            (disclosure_id,),
        ).fetchone()
        if not row:
            return None
        try:
            analysis = json.loads(row[3])
        except json.JSONDecodeError:
            return None
        return {
            "id": row[0],
            "filename": row[1],
            "analysis_date": str(row[2]) if row[2] else None,
            "analysis": analysis,
            "completeness_score": row[4],
        }
    except Exception as e:
        logger.error(f"Failed to load disclosure analysis by id={disclosure_id}: {e}")
        return None
    finally:
        conn.close()


# Initialize schema on import. Safe to call repeatedly — every CREATE
# TABLE has IF NOT EXISTS.
_ensure_db()
