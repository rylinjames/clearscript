"""Copay Accumulator Impact Estimator — estimate financial impact of PBM accumulator programs on members."""

import logging
from fastapi import APIRouter

from services.copay_accumulator_service import (
    estimate_accumulator_impact,
    get_drug_list,
)

logger = logging.getLogger("clearscript.copay_accumulator")

router = APIRouter(prefix="/api/copay-accumulator", tags=["Copay Accumulator"])


@router.get("/analysis")
async def accumulator_analysis():
    """
    Estimate copay accumulator impact on current claims.

    Uses uploaded claims if available (from the claims_upload module),
    otherwise returns a demo estimate for a hypothetical 5,000-member plan.
    """
    # Use real uploaded claims only — no synthetic fallback
    claims: list[dict] = []
    try:
        from services.data_service import get_claims, get_claims_status
        status = get_claims_status()
        if status.get("custom_data_loaded"):
            claims = get_claims()
            logger.info("Using %d uploaded claims for accumulator analysis", len(claims))
    except Exception:
        logger.debug("Could not load claims data")

    if not claims:
        return {
            "status": "no_data",
            "message": "No claims data uploaded. Upload your pharmacy claims CSV on the Upload Claims page to estimate copay accumulator impact.",
            "accumulator_impact": None,
        }

    result = estimate_accumulator_impact(claims)
    return {"status": "success", "accumulator_impact": result}


@router.get("/drug-list")
async def drug_list():
    """
    Return the reference list of drugs with known manufacturer copay
    assistance programs, including typical annual card values and
    therapeutic classes.
    """
    drugs = get_drug_list()
    return {
        "status": "success",
        "total_drugs": len(drugs),
        "drugs": drugs,
    }
