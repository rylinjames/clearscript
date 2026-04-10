"""Feature 3: Semiannual Report Auditor"""

from fastapi import APIRouter
from services.data_service import get_claims, audit_report
from services.nadac_service import get_nadac_prices

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/audit")
async def run_audit():
    """
    Audit semiannual PBM report using uploaded claims data.
    Cross-references against NADAC pricing to find discrepancies.
    """
    claims = get_claims()
    if not claims:
        return {
            "status": "no_data",
            "message": "No claims data uploaded. Upload your pharmacy claims CSV on the Upload Claims page to run the report audit.",
            "audit": None,
        }

    # Try to get real NADAC prices for top drugs
    top_ndcs = list(set(c["ndc"] for c in claims))[:10]
    try:
        nadac_data = await get_nadac_prices(top_ndcs)
    except Exception:
        nadac_data = []

    # Build NADAC lookup
    nadac_lookup = {r["ndc"]: r.get("nadac_per_unit") for r in nadac_data if r.get("nadac_per_unit")}

    # Add NADAC comparison where available
    nadac_comparisons = []
    for ndc, price in nadac_lookup.items():
        matching_claims = [c for c in claims if c["ndc"] == ndc]
        if matching_claims:
            sample = matching_claims[0]
            nadac_comparisons.append({
                "ndc": ndc,
                "drug_name": sample["drug_name"],
                "our_nadac_unit": sample["nadac_unit_cost"],
                "cms_nadac_unit": price,
                "difference_pct": round((sample["nadac_unit_cost"] - price) / price * 100, 1) if price else None,
            })

    audit_result = audit_report(claims)

    return {
        "status": "success",
        "audit": audit_result,
        "nadac_cross_reference": nadac_comparisons if nadac_comparisons else "NADAC API data unavailable — using synthetic NADAC baseline",
        "claims_summary": {
            "total_claims": len(claims),
            "total_plan_paid": round(sum(c["plan_paid"] for c in claims), 2),
            "total_nadac_cost": round(sum(c["nadac_total"] for c in claims), 2),
            "unique_drugs": len(set(c["drug_name"] for c in claims)),
            "unique_pharmacies": len(set(c["pharmacy_id"] for c in claims)),
            "date_range": {
                "start": min(c["fill_date"] for c in claims),
                "end": max(c["fill_date"] for c in claims),
            }
        }
    }
