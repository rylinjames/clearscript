"""Feature 12: NDC vs J-Code Rebate Gap Analysis"""

from fastapi import APIRouter
from services.data_service import get_claims
from services.ndc_service import analyze_ndc_jcode_gap

router = APIRouter(prefix="/api/ndc-analysis", tags=["ndc-analysis"])


@router.get("/analysis")
async def ndc_jcode_analysis():
    """
    Analyze claims for NDC vs J-code billing gap.
    Flags claims where J-code billing may be masking rebate-eligible NDCs.
    Calculates rebate leakage from missing NDC billing.
    """
    claims = get_claims()
    if not claims:
        return {
            "status": "no_data",
            "message": "No claims data uploaded. Upload your pharmacy claims CSV on the Upload Claims page to see NDC vs J-code analysis.",
            "ndc_analysis": None,
        }
    result = analyze_ndc_jcode_gap(claims)
    return {"status": "success", "ndc_analysis": result}
