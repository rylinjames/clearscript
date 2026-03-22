"""Feature 7: Pharmacy Network Adequacy"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from services.data_service import generate_network_analysis, generate_network_data

router = APIRouter(prefix="/api/network", tags=["network"])


class NetworkRequest(BaseModel):
    zip_codes: Optional[List[str]] = None


@router.post("/analyze")
async def analyze_network(request: NetworkRequest = None):
    """
    Analyze pharmacy network adequacy.
    Accepts employee zip codes, checks pharmacy coverage.
    Identifies gaps and phantom networks.
    Returns coverage map data, adequacy score, and flagged areas.
    """
    if request and request.zip_codes:
        zip_codes = request.zip_codes
    else:
        # Default demo zip codes (Chicago metro area)
        zip_codes = [
            "60601", "60605", "60611", "60614", "60622",
            "60625", "60630", "60640", "60647", "60657",
            "60173", "60540", "60201", "60302", "60304",
            "60431", "60515", "60523", "60532", "60559",
        ]

    result = generate_network_analysis(zip_codes)
    all_pharmacies = generate_network_data()

    return {
        "status": "success",
        "network_analysis": result,
        "network_pharmacies": [
            {
                "id": p["id"],
                "name": p["name"],
                "npi": p["npi"],
                "type": p["type"],
                "chain": p["chain"],
                "city": p["city"],
                "state": p["state"],
                "zip": p["zip"],
                "active": p["active"],
                "phantom": p.get("phantom", False),
                "flag_reason": p.get("flag_reason"),
            }
            for p in all_pharmacies
        ],
    }
