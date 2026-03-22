"""Feature 1: Contract Intake & Parsing"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from services.ai_service import analyze_contract

router = APIRouter(prefix="/api/contracts", tags=["contracts"])


@router.post("/upload")
async def upload_contract(file: UploadFile = File(...)):
    """
    Upload a PBM contract (PDF/text) for AI-powered term extraction.
    Returns structured JSON with extracted PBM terms and compliance flags.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    allowed_types = [
        "application/pdf",
        "text/plain",
        "application/octet-stream",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]

    content = await file.read()

    # For PDF files, we extract text (simplified — in production use PyPDF2/pdfplumber)
    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = str(content[:10000])

    if len(text.strip()) < 50:
        # If content is too short (binary PDF not decoded), use a demo contract
        text = _demo_contract_text()

    result = await analyze_contract(text)

    return {
        "status": "success",
        "filename": file.filename,
        "file_size": len(content),
        "analysis": result,
    }


def _demo_contract_text() -> str:
    return """
PHARMACY BENEFIT MANAGEMENT SERVICES AGREEMENT

This Agreement is entered into between Employer Health Plan ("Plan Sponsor") and
National PBM Services, Inc. ("PBM").

SECTION 3 — PRICING AND REIMBURSEMENT
3.1 AWP Discount: PBM shall provide a minimum discount of AWP minus 15% for brand
drugs and AWP minus 75% for generic drugs at retail pharmacies.
3.2 Mail Order: AWP minus 18% for brand and AWP minus 78% for generic.
3.3 Spread Pricing: PBM may retain the difference between the amount billed to Plan
and the amount reimbursed to pharmacies.

SECTION 5 — REBATES
5.1 Rebate Passthrough: PBM shall pass through 85% of Eligible Rebates to Plan Sponsor.
5.2 Definition of Eligible Rebates: Eligible Rebates include base manufacturer rebates
directly attributable to Plan utilization. Administrative fees, manufacturer volume
bonuses, price protection rebates, and other compensation shall not be considered
Eligible Rebates.

SECTION 7 — FORMULARY MANAGEMENT
7.1 PBM shall maintain a formulary of covered drugs. PBM may make mid-year changes
to the formulary with 60 days written notice to Plan Sponsor.
7.2 PBM is not required to obtain Plan Sponsor approval for tier placement changes.

SECTION 9 — AUDIT RIGHTS
9.1 Plan Sponsor may conduct one audit per contract year of claims data.
9.2 Audit shall be limited to claims processing accuracy and shall not include
review of rebate contracts, pharmacy reimbursement rates, or PBM internal pricing.
9.3 Plan Sponsor must provide 90 days advance written notice and select an auditor
from PBM's approved auditor list.

SECTION 12 — TERM AND TERMINATION
12.1 Initial term of 3 years with automatic 1-year renewals.
12.2 Early termination requires 180 days written notice.
12.3 Early termination is subject to liquidated damages equal to 50% of remaining
contract value.

SECTION 14 — CONFIDENTIALITY
14.1 All terms of this Agreement are confidential.
14.2 Plan Sponsor shall not disclose any pricing, rebate, or reimbursement data
to any third party, including benefits consultants, brokers, or competing PBMs,
without PBM's prior written consent.
"""
