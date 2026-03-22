"""Feature 4: Rebate Passthrough Tracker"""

from fastapi import APIRouter
from services.data_service import get_claims, analyze_rebates

router = APIRouter(prefix="/api/rebates", tags=["rebates"])


@router.get("/analysis")
async def rebate_analysis():
    """
    Track rebate flow from manufacturer to PBM to plan.
    Returns leakage percentage, formulary reconciliation, and
    drugs where high-rebate brands are favored over cheaper generics.
    """
    claims = get_claims()
    result = analyze_rebates(claims)

    return {
        "status": "success",
        "rebate_analysis": result,
    }
