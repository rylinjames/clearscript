"""Feature 14: Provider Billing Anomaly Detection"""

from fastapi import APIRouter
from services.provider_anomaly_service import analyze_provider_anomalies

router = APIRouter(prefix="/api/provider-anomalies", tags=["provider-anomalies"])


@router.get("/analysis")
async def provider_anomaly_analysis():
    """
    Detect provider billing anomalies using CMS-benchmarked utilization patterns.
    Flags providers billing significantly above peers for same procedures.
    """
    result = await analyze_provider_anomalies()
    return {"status": "success", "provider_analysis": result}
