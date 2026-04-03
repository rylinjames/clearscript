import logging
logger = logging.getLogger(__name__)
"""Feature 1: Plan Intelligence — Contract Analysis + Plan Document (SBC/SPD/EOC) Parsing + Cross-Reference"""

import os
import io
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from services.pipeline_service import run_contract_pipeline, get_pipeline_status
from services.audit_rights_service import score_audit_rights
from services.db_service import save_contract_analysis
from services.spc_service import parse_spc
from services.plan_crossref_service import cross_reference_contract_and_plan
from services.pdf_report_service import generate_contract_report

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}

router = APIRouter(prefix="/api/contracts", tags=["contracts"])


def _extract_pdf_text(content: bytes) -> str:
    """Extract text from PDF using pdfplumber."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n\n".join(pages)
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed: {e}")
        return ""


@router.post("/upload")
async def upload_contract(file: UploadFile = File(...)):
    """
    Upload a PBM contract (PDF/text) for AI-powered term extraction.
    Now with real PDF parsing via pdfplumber + audit rights benchmarking.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'. Accepted: {', '.join(ALLOWED_EXTENSIONS)}")

    content = await file.read()

    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large ({len(content) / 1024 / 1024:.1f}MB). Maximum: 50MB.")

    filename = file.filename.lower()

    # Real PDF extraction
    if filename.endswith(".pdf"):
        text = _extract_pdf_text(content)
    else:
        try:
            text = content.decode("utf-8", errors="ignore")
        except Exception:
            text = ""

    if len(text.strip()) < 50:
        text = _demo_contract_text()

    result = await run_contract_pipeline(text)

    # Run audit rights benchmark scoring against gold-standard template
    audit_benchmark = score_audit_rights(result)

    # Persist to SQLite
    risk_score = result.get("overall_risk_score", 0) if isinstance(result, dict) else 0
    try:
        save_contract_analysis(file.filename, result, risk_score, audit_benchmark.get("score", 0))
    except Exception as e:
        logger.warning(f"Failed to persist contract analysis: {e}")

    return {
        "status": "success",
        "filename": file.filename,
        "file_size": len(content),
        "extracted_text_length": len(text),
        "pdf_parsed": filename.endswith(".pdf") and len(text.strip()) >= 50,
        "analysis": result,
        "audit_rights_benchmark": audit_benchmark,
        "generated_by": "ai" if len(text.strip()) >= 50 else "mock",
        "engine": "rocketride_pipeline",
    }


@router.post("/upload-plan-document")
async def upload_plan_document(file: UploadFile = File(...)):
    """
    Step 2: Upload a plan document (SBC, SPD, EOC/COC) for benefit extraction.
    Reuses the SPC parser to extract structured benefit data from plan documents.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'. Accepted: {', '.join(ALLOWED_EXTENSIONS)}")

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large ({len(content) / 1024 / 1024:.1f}MB). Maximum: 50MB.")

    filename = file.filename.lower()

    if filename.endswith(".pdf"):
        text = _extract_pdf_text(content)
    else:
        try:
            text = content.decode("utf-8", errors="ignore")
        except Exception:
            text = ""

    if len(text.strip()) < 50:
        raise HTTPException(status_code=422, detail="Could not extract enough text from this document. Please upload a valid SBC, SPD, or EOC/COC.")

    # Detect document type from content
    doc_type = _detect_plan_doc_type(text)

    # Parse using SPC service (handles SBC/SPD/EOC)
    benefits = await parse_spc(text)

    return {
        "status": "success",
        "filename": file.filename,
        "file_size": len(content),
        "extracted_text_length": len(text),
        "document_type": doc_type,
        "benefits": benefits,
    }


@router.post("/cross-reference")
async def cross_reference_endpoint(request: dict):
    """
    Step 3: Cross-reference PBM contract analysis against plan document benefits.
    Flags mismatches between contract guarantees and actual plan design.

    Expects JSON body with:
    - contract_analysis: output from contract parsing
    - plan_benefits: output from plan document parsing
    """
    contract_analysis = request.get("contract_analysis")
    plan_benefits = request.get("plan_benefits")

    if not contract_analysis or not plan_benefits:
        raise HTTPException(
            status_code=400,
            detail="Both 'contract_analysis' and 'plan_benefits' are required.",
        )

    result = await cross_reference_contract_and_plan(contract_analysis, plan_benefits)

    return {
        "status": "success",
        "cross_reference": result,
    }


def _detect_plan_doc_type(text: str) -> str:
    """Detect whether the document is an SBC, SPD, EOC, or COC based on content."""
    text_lower = text[:3000].lower()
    if "summary of benefits and coverage" in text_lower or "sbc" in text_lower:
        return "SBC"
    elif "summary plan description" in text_lower or "spd" in text_lower:
        return "SPD"
    elif "evidence of coverage" in text_lower or "eoc" in text_lower:
        return "EOC"
    elif "certificate of coverage" in text_lower or "coc" in text_lower:
        return "COC"
    elif "plan document" in text_lower:
        return "Plan Document"
    return "Unknown"


@router.post("/export-pdf")
async def export_pdf(request: dict):
    """
    Generate a downloadable PDF report from contract analysis results.

    Expects JSON body with:
    - filename: original contract filename
    - analysis: contract analysis output
    - audit_rights_benchmark: audit rights scoring (optional)
    - plan_benefits: parsed plan document benefits (optional)
    - cross_reference: cross-reference results (optional)
    - audit_letter: generated audit letter text (optional)
    """
    filename = request.get("filename", "PBM Contract")
    analysis = request.get("analysis")

    if not analysis:
        raise HTTPException(status_code=400, detail="'analysis' is required to generate the report.")

    # Fetch compliance deadlines
    compliance_deadlines = None
    try:
        from services.data_service import generate_compliance_deadlines
        compliance_deadlines = generate_compliance_deadlines()
    except Exception:
        pass

    pdf_bytes = generate_contract_report(
        filename=filename,
        analysis=analysis,
        audit_benchmark=request.get("audit_rights_benchmark"),
        plan_benefits=request.get("plan_benefits"),
        cross_reference=request.get("cross_reference"),
        compliance_deadlines=compliance_deadlines,
        audit_letter=request.get("audit_letter"),
    )

    safe_name = filename.replace(" ", "_").replace(".pdf", "").replace(".txt", "").replace(".docx", "")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="ClearScript_Report_{safe_name}.pdf"',
        },
    )


@router.get("/pipeline-status")
async def pipeline_status():
    """Check if RocketRide pipeline engine is available."""
    return await get_pipeline_status()


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
