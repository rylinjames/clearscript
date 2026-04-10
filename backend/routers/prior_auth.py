"""Feature 13: Prior Authorization Value Detector"""

from fastapi import APIRouter
from services.data_service import get_claims_status

router = APIRouter(prefix="/api/prior-auth", tags=["prior-auth"])


@router.get("/analysis")
async def pa_value_analysis():
    """
    Analyze prior authorization rules and output Keep/Remove/Modify recommendations.
    Requires uploaded claims data.
    """
    status = get_claims_status()
    if not status.get("custom_data_loaded"):
        return {
            "status": "no_data",
            "message": "No claims data uploaded. Upload your pharmacy claims CSV on the Upload Claims page to analyze prior authorization value.",
            "pa_analysis": None,
        }
    from services.prior_auth_service import analyze_prior_auth_value
    result = analyze_prior_auth_value()
    return {"status": "success", "pa_analysis": result}
