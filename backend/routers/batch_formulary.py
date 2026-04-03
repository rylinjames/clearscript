"""Batch Cigna Formulary Processor — process multiple formulary PDFs, search across plans, compare states."""

import logging
from typing import Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, Query

from services.batch_formulary_service import (
    infer_metadata_from_filename,
    build_formulary_index,
    search_drug_across_plans,
    get_state_comparison,
    get_mock_index,
)
from services.formulary_service import parse_formulary_pdf

logger = logging.getLogger("clearscript.batch_formulary")

router = APIRouter(prefix="/api/batch-formulary", tags=["Batch Formulary"])

# ---------------------------------------------------------------------------
# In-memory index — populated via /process endpoint or demo mode
# ---------------------------------------------------------------------------
_current_index: dict = {}


def _get_index() -> dict:
    """Return current index, falling back to mock data if nothing uploaded."""
    global _current_index
    if not _current_index:
        logger.info("No formularies uploaded yet — returning mock demo index")
        return get_mock_index()
    return _current_index


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/process")
async def process_batch(
    files: list[UploadFile] = File(..., description="One or more Cigna formulary PDFs"),
):
    """
    Upload multiple formulary PDFs, parse each one, infer metadata from
    filenames, and build a searchable cross-plan index.

    The index is stored in memory and used by the /search, /states, and
    /stats endpoints.
    """
    global _current_index

    if not files:
        raise HTTPException(status_code=400, detail="At least one PDF file is required.")

    parsed_formularies: list[dict] = []
    errors: list[dict] = []

    for f in files:
        fname = f.filename or "unknown.pdf"
        if not fname.lower().endswith(".pdf"):
            errors.append({"filename": fname, "error": "Not a PDF file, skipped."})
            continue

        content = await f.read()
        if not content:
            errors.append({"filename": fname, "error": "Empty file, skipped."})
            continue

        meta = infer_metadata_from_filename(fname)

        try:
            rows = parse_formulary_pdf(
                content,
                tier_model=meta.get("tier_model"),
                filename=fname,
            )
        except (ValueError, Exception) as exc:
            logger.warning("Failed to parse %s: %s", fname, exc)
            errors.append({"filename": fname, "error": str(exc)})
            continue

        if not rows:
            errors.append({"filename": fname, "error": "No drug rows extracted."})
            continue

        parsed_formularies.append({"metadata": meta, "rows": rows})
        logger.info(
            "Parsed %s: %d drugs, state=%s, tier_model=%s",
            fname, len(rows), meta.get("state"), meta.get("tier_model"),
        )

    if not parsed_formularies:
        raise HTTPException(
            status_code=422,
            detail="No formularies could be parsed from the uploaded files.",
        )

    _current_index = build_formulary_index(parsed_formularies)

    return {
        "status": "success",
        "formularies_processed": len(parsed_formularies),
        "total_drugs_indexed": _current_index.get("total_drugs", 0),
        "plans": list(_current_index.get("plan_index", {}).keys()),
        "states": list(_current_index.get("state_index", {}).keys()),
        "errors": errors if errors else None,
    }


@router.get("/search")
async def search_drug(
    drug: str = Query(..., min_length=2, description="Drug name to search for"),
):
    """
    Search for a drug across all processed (or demo) formularies.
    Returns tier placement, PA requirements, and most/least favorable plans.
    """
    index = _get_index()
    result = search_drug_across_plans(drug, index)
    return {"status": "success", "result": result}


@router.get("/states")
async def state_comparison():
    """
    Compare formulary restrictiveness by state across all processed formularies.
    Returns per-state metrics ranked by restrictiveness.
    """
    index = _get_index()
    result = get_state_comparison(index)
    return {"status": "success", "comparison": result}


@router.get("/stats")
async def aggregate_stats():
    """
    Return aggregate statistics about the currently indexed formularies.
    """
    index = _get_index()
    plan_index = index.get("plan_index", {})
    state_index = index.get("state_index", {})
    drug_index = index.get("drug_index", {})

    # Tier model distribution
    tier_models: dict[int, int] = {}
    for pinfo in plan_index.values():
        tm = pinfo.get("metadata", {}).get("tier_model")
        if tm:
            tier_models[tm] = tier_models.get(tm, 0) + 1

    # Plan family distribution
    families: dict[str, int] = {}
    for pinfo in plan_index.values():
        fam = pinfo.get("metadata", {}).get("plan_family") or "Unknown"
        families[fam] = families.get(fam, 0) + 1

    # Average UM rates across all plans
    total_pa = 0.0
    total_ql = 0.0
    total_st = 0.0
    n_plans = max(len(plan_index), 1)
    for pinfo in plan_index.values():
        um = pinfo.get("um_rates", {})
        total_pa += um.get("pa_pct", 0)
        total_ql += um.get("ql_pct", 0)
        total_st += um.get("st_pct", 0)

    return {
        "status": "success",
        "stats": {
            "total_formularies": index.get("total_formularies", 0),
            "total_drugs_indexed": len(drug_index),
            "total_plans": len(plan_index),
            "states_covered": list(state_index.keys()),
            "tier_model_distribution": tier_models,
            "plan_family_distribution": families,
            "avg_um_rates": {
                "pa_pct": round(total_pa / n_plans, 2),
                "ql_pct": round(total_ql / n_plans, 2),
                "st_pct": round(total_st / n_plans, 2),
            },
            "is_demo_data": not bool(_current_index),
        },
    }
