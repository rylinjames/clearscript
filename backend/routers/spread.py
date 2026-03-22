"""Feature 5: Spread Pricing Detection"""

from fastapi import APIRouter
from services.data_service import get_claims, analyze_spread

router = APIRouter(prefix="/api/spread", tags=["spread"])


@router.get("/analysis")
async def spread_analysis():
    """
    Compare plan-paid vs pharmacy-reimbursed per prescription.
    Breaks down by retail, mail-order, specialty.
    Returns total spread captured by PBM and worst offender drugs.
    """
    claims = get_claims()
    result = analyze_spread(claims)

    return {
        "status": "success",
        "spread_analysis": result,
    }
