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
    # Try to load real claims from the claims upload module
    claims: list[dict] = []
    try:
        from routers.claims_upload import _claims_store
        if _claims_store:
            claims = list(_claims_store)
            logger.info("Using %d uploaded claims for accumulator analysis", len(claims))
    except Exception:
        logger.debug("Could not load uploaded claims — using demo mode")

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
