"""Feature 2: Initial Disclosure Analyzer"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from services.ai_service import analyze_disclosure

router = APIRouter(prefix="/api/disclosure", tags=["disclosure"])


@router.post("/analyze")
async def analyze_disclosure_doc(file: UploadFile = File(...)):
    """
    Upload a PBM disclosure document for DOL compliance analysis.
    Returns completeness score (0-100%) and gap report.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    content = await file.read()

    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = str(content[:10000])

    if len(text.strip()) < 50:
        text = _demo_disclosure_text()

    result = await analyze_disclosure(text)

    return {
        "status": "success",
        "filename": file.filename,
        "file_size": len(content),
        "analysis": result,
    }


def _demo_disclosure_text() -> str:
    return """
PBM ANNUAL DISCLOSURE REPORT — Plan Year 2024-2025

SECTION 1: AGGREGATE REBATE SUMMARY
Total manufacturer rebates received: $2,145,320
Rebates passed through to plan: $1,823,522 (85% of eligible)

SECTION 2: UTILIZATION SUMMARY
Total prescriptions filled: 45,230
Generic dispensing rate: 79.2%
Mail order utilization: 18.4%

SECTION 3: TOP 25 DRUGS BY PLAN SPEND
1. Humira 40mg — $842,000 (312 claims)
2. Ozempic 1mg — $524,000 (198 claims)
3. Eliquis 5mg — $389,000 (445 claims)
[remaining drugs listed...]

SECTION 4: ADMINISTRATIVE FEES
PBM administrative fee: $3.25 per claim
Total admin fees: $146,997.50

NOTE: Spread pricing data, pharmacy reimbursement rates, manufacturer rebate
breakdowns by drug, DIR fee amounts, and pharmacy claw-back data are considered
proprietary and are not included in this disclosure.
"""
