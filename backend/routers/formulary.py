"""Feature 8: Formulary Manipulation Detector"""

from fastapi import APIRouter
from services.data_service import generate_formulary_data

router = APIRouter(prefix="/api/formulary", tags=["formulary"])


@router.get("/analysis")
async def formulary_analysis():
    """
    Compare two formulary snapshots (current vs 6 months ago).
    Flags mid-year changes correlated with rebate incentives.
    Returns swap list with cost impact.
    """
    result = generate_formulary_data()

    return {
        "status": "success",
        "formulary_analysis": result,
    }
