"""Drug Lookup Router — consolidated drug search across all data sources."""

from fastapi import APIRouter, HTTPException, Query
from services.drug_lookup_service import search_drug, get_drug_profile

router = APIRouter(prefix="/api/drug-lookup", tags=["drug-lookup"])


@router.get("/search")
async def drug_search(
    q: str = Query(..., min_length=2, description="Drug name to search for"),
):
    """
    Search for drugs by name across all ClearScript data sources:
    synthetic drug list, NADAC pricing, NDC/J-code crosswalks, and
    IRA selected drugs.
    """
    result = await search_drug(q)
    return {
        "status": "success",
        **result,
    }


@router.get("/profile/{ndc}")
async def drug_profile(ndc: str):
    """
    Get a full drug profile by NDC including pricing, rebate estimates,
    J-code mapping, IRA negotiation status, therapeutic alternatives,
    and AWP-to-NADAC spread.
    """
    if not ndc or len(ndc.replace("-", "")) < 5:
        raise HTTPException(status_code=400, detail="Invalid NDC format.")

    result = await get_drug_profile(ndc)

    if not result.get("found"):
        # Still return what we have (NADAC may have found something)
        return {
            "status": "partial",
            "detail": "NDC not found in ClearScript drug database. NADAC and crosswalk data may still be available.",
            "profile": result,
        }

    return {
        "status": "success",
        "profile": result,
    }
