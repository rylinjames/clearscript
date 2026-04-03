"""Feature 13: Prior Authorization Value Detector"""

from fastapi import APIRouter
from services.prior_auth_service import analyze_prior_auth_value

router = APIRouter(prefix="/api/prior-auth", tags=["prior-auth"])


@router.get("/analysis")
async def pa_value_analysis():
    """
    Analyze prior authorization rules and output Keep/Remove/Modify recommendations.
    Evaluates PA effectiveness at population level using approval rate benchmarks.
    """
    result = analyze_prior_auth_value()
    return {"status": "success", "pa_analysis": result}
