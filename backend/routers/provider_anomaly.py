"""Feature 14: Provider Billing Anomaly Detection"""

from fastapi import APIRouter
from services.data_service import get_claims_status

router = APIRouter(prefix="/api/provider-anomalies", tags=["provider-anomalies"])


@router.get("/analysis")
async def provider_anomaly_analysis():
    """
    Detect provider billing anomalies using CMS-benchmarked utilization patterns.
    Requires uploaded claims data.
    """
    status = get_claims_status()
    if not status.get("custom_data_loaded"):
        return {
            "status": "no_data",
            "message": "No claims data uploaded. Upload your pharmacy claims CSV on the Upload Claims page to detect provider anomalies.",
            "provider_analysis": None,
        }
    from services.provider_anomaly_service import analyze_provider_anomalies
    result = await analyze_provider_anomalies()
    return {"status": "success", "provider_analysis": result}
