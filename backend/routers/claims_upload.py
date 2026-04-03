import logging
logger = logging.getLogger(__name__)
"""
Claims CSV Upload Router — allows employers to upload real pharmacy claims data.
Uploaded claims replace synthetic data for all analysis endpoints.
"""

import csv
import io
from datetime import datetime
from typing import List, Dict, Any

from fastapi import APIRouter, UploadFile, File, HTTPException

from services.data_service import set_claims_data, reset_claims_data, get_claims_status, get_claims
from services.db_service import save_claims, clear_claims as db_clear_claims, load_latest_claims

router = APIRouter(prefix="/api/claims", tags=["Claims Upload"])

REQUIRED_COLUMNS = [
    "claim_id", "drug_name", "ndc", "quantity", "days_supply",
    "date_filled", "channel", "pharmacy_name", "pharmacy_npi",
    "pharmacy_zip", "plan_paid", "pharmacy_reimbursed", "awp",
    "nadac_price", "rebate_amount", "formulary_tier",
]

NUMERIC_FIELDS = {
    "quantity": int,
    "days_supply": int,
    "plan_paid": float,
    "pharmacy_reimbursed": float,
    "awp": float,
    "nadac_price": float,
    "rebate_amount": float,
    "formulary_tier": int,
}


def _parse_numeric(value: str, field: str):
    """Parse a numeric field, returning 0 on failure."""
    if not value or value.strip() == "":
        return 0
    try:
        return NUMERIC_FIELDS[field](value.strip())
    except (ValueError, KeyError):
        return 0


def _csv_row_to_claim(row: Dict[str, str], index: int) -> Dict[str, Any]:
    """Map a CSV row to the internal claims format used by data_service."""
    qty = _parse_numeric(row.get("quantity", "30"), "quantity") or 30
    nadac_price = _parse_numeric(row.get("nadac_price", "0"), "nadac_price")
    plan_paid = _parse_numeric(row.get("plan_paid", "0"), "plan_paid")
    pharmacy_reimbursed = _parse_numeric(row.get("pharmacy_reimbursed", "0"), "pharmacy_reimbursed")
    awp = _parse_numeric(row.get("awp", "0"), "awp")
    rebate_amount = _parse_numeric(row.get("rebate_amount", "0"), "rebate_amount")
    tier = _parse_numeric(row.get("formulary_tier", "1"), "formulary_tier") or 1

    spread = round(plan_paid - pharmacy_reimbursed, 2)
    is_generic = tier <= 1
    channel = (row.get("channel", "retail") or "retail").strip().lower()
    nadac_unit = round(nadac_price / qty, 4) if qty else nadac_price
    awp_unit = round(awp / qty, 4) if qty else awp

    return {
        "claim_id": row.get("claim_id", f"UPL-{str(index).zfill(6)}").strip(),
        "fill_date": row.get("date_filled", "2025-01-01").strip(),
        "member_id": f"MEM-{10000 + index}",
        "drug_name": row.get("drug_name", "Unknown").strip(),
        "ndc": row.get("ndc", "00000000000").strip(),
        "generic": is_generic,
        "drug_class": "Uploaded",
        "quantity": qty,
        "days_supply": _parse_numeric(row.get("days_supply", "30"), "days_supply") or 30,
        "pharmacy_id": f"PH-UPL-{index % 20}",
        "pharmacy_name": row.get("pharmacy_name", "Unknown Pharmacy").strip(),
        "pharmacy_npi": row.get("pharmacy_npi", "0000000000").strip(),
        "channel": channel if channel in ("retail", "mail", "specialty") else "retail",
        "nadac_unit_cost": nadac_unit,
        "nadac_total": nadac_price,
        "awp_unit_cost": awp_unit,
        "plan_paid": plan_paid,
        "pharmacy_reimbursed": pharmacy_reimbursed,
        "spread": spread,
        "copay": 0.0,
        "rebate_amount": rebate_amount,
        "rebate_passed_to_plan": round(rebate_amount * 0.7, 2),
        "rebate_retained_by_pbm": round(rebate_amount * 0.3, 2),
        "is_specialty": channel == "specialty",
    }


@router.post("/upload")
async def upload_claims(file: UploadFile = File(...)):
    """Upload a pharmacy claims CSV file. Replaces synthetic data for all analysis endpoints."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV (.csv)")

    try:
        contents = await file.read()
        text = contents.decode("utf-8-sig")  # Handle BOM
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read file. Ensure it is a valid UTF-8 CSV.")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise HTTPException(status_code=400, detail="CSV file appears empty or has no header row.")

    # Normalize column names
    cleaned_fields = [f.strip().lower().replace(" ", "_") for f in reader.fieldnames]
    missing = [col for col in REQUIRED_COLUMNS if col not in cleaned_fields]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV is missing required columns: {', '.join(missing)}. "
                   f"Expected columns: {', '.join(REQUIRED_COLUMNS)}",
        )

    # Re-read with normalized headers
    reader = csv.DictReader(io.StringIO(text))
    claims: List[Dict[str, Any]] = []
    for i, row in enumerate(reader, start=1):
        # Normalize keys
        normalized_row = {k.strip().lower().replace(" ", "_"): v for k, v in row.items()}
        try:
            claims.append(_csv_row_to_claim(normalized_row, i))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error parsing row {i}: {str(e)}")

    if not claims:
        raise HTTPException(status_code=400, detail="CSV contained no data rows.")

    # Compute summary stats
    dates = [c["fill_date"] for c in claims if c["fill_date"]]
    unique_drugs = set(c["drug_name"] for c in claims)
    unique_pharmacies = set(c["pharmacy_name"] for c in claims)

    try:
        parsed_dates = sorted([datetime.strptime(d, "%Y-%m-%d") for d in dates if d])
        date_range_start = parsed_dates[0].strftime("%Y-%m-%d") if parsed_dates else "N/A"
        date_range_end = parsed_dates[-1].strftime("%Y-%m-%d") if parsed_dates else "N/A"
    except ValueError:
        date_range_start = min(dates) if dates else "N/A"
        date_range_end = max(dates) if dates else "N/A"

    info = {
        "date_range_start": date_range_start,
        "date_range_end": date_range_end,
        "unique_drugs": len(unique_drugs),
        "unique_pharmacies": len(unique_pharmacies),
        "uploaded_at": datetime.now().isoformat(),
        "filename": file.filename,
    }

    set_claims_data(claims, info)

    # Persist to SQLite so data survives server restarts
    try:
        save_claims(file.filename, claims)
    except Exception as e:
        logger.warning(f"Failed to persist claims to SQLite: {e}")

    return {
        "status": "success",
        "message": f"Successfully uploaded {len(claims)} claims from {file.filename}",
        "summary": {
            "total_claims": len(claims),
            "date_range": f"{date_range_start} to {date_range_end}",
            "unique_drugs": len(unique_drugs),
            "unique_pharmacies": len(unique_pharmacies),
            "total_plan_paid": round(sum(c["plan_paid"] for c in claims), 2),
            "total_rebates": round(sum(c["rebate_amount"] for c in claims), 2),
        },
    }


@router.get("/status")
async def claims_status():
    """Check whether custom claims data is loaded or using synthetic data."""
    return get_claims_status()


@router.delete("/reset")
async def reset_claims():
    """Reset back to synthetic/sample data."""
    reset_claims_data()
    try:
        db_clear_claims()
    except Exception:
        pass
    return {
        "status": "success",
        "message": "Claims data reset to synthetic sample data.",
        "claims_count": len(get_claims()),
    }


async def restore_persisted_claims():
    """Restore last uploaded claims from SQLite if available. Call from app startup."""
    try:
        saved = load_latest_claims()
        if saved and saved["claims"]:
            set_claims_data(saved["claims"], {
                "filename": saved["filename"],
                "uploaded_at": saved["upload_date"],
                "restored_from_db": True,
            })
            logger.info(f"Restored {saved['claims_count']} claims from SQLite ({saved['filename']})")
    except Exception as e:
        logger.debug(f"No persisted claims to restore: {e}")
