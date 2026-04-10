"""Feature 4: Rebate Passthrough Tracker"""

from fastapi import APIRouter
from services.data_service import get_claims, get_claims_status, analyze_rebates

router = APIRouter(prefix="/api/rebates", tags=["rebates"])


@router.get("/analysis")
async def rebate_analysis():
    """
    Track rebate flow from manufacturer to PBM to plan.
    Returns leakage percentage, formulary reconciliation, and
    drugs where high-rebate brands are favored over cheaper generics.
    """
    claims = get_claims()
    if not claims:
        return {
            "status": "no_data",
            "message": "No claims data uploaded. Upload your pharmacy claims CSV on the Upload Claims page to see rebate analysis.",
            "rebate_analysis": None,
        }
    result = analyze_rebates(claims)

    return {
        "status": "success",
        "rebate_analysis": result,
        "data_source": "uploaded_claims" if get_claims_status().get("custom_data_loaded") else "none",
    }
