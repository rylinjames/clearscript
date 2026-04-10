"""Feature 5: Spread Pricing Detection"""

from fastapi import APIRouter
from services.data_service import get_claims, get_claims_status, analyze_spread

router = APIRouter(prefix="/api/spread", tags=["spread"])


@router.get("/analysis")
async def spread_analysis():
    """
    Compare plan-paid vs pharmacy-reimbursed per prescription.
    Breaks down by retail, mail-order, specialty.
    Returns total spread captured by PBM and worst offender drugs.
    """
    claims = get_claims()
    if not claims:
        return {
            "status": "no_data",
            "message": "No claims data uploaded. Upload your pharmacy claims CSV on the Upload Claims page to see spread pricing analysis.",
            "spread_analysis": None,
        }
    result = analyze_spread(claims)

    return {
        "status": "success",
        "spread_analysis": result,
        "data_source": "uploaded_claims" if get_claims_status().get("custom_data_loaded") else "none",
    }
