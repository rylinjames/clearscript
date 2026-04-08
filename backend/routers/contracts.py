import logging
logger = logging.getLogger(__name__)
"""Feature 1: Plan Intelligence — Contract Analysis + Plan Document (SBC/SPD/EOC) Parsing + Cross-Reference"""

import os
import io
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from services.pipeline_service import run_contract_pipeline, get_pipeline_status
from services.audit_rights_service import score_audit_rights
from services.db_service import save_contract_analysis, list_contract_analyses, load_contract_analysis_by_id
from services.usage_service import log_file_upload, log_event
from services.spc_service import parse_spc
from services.plan_crossref_service import cross_reference_contract_and_plan
from services.pdf_report_service import generate_contract_report
from services.training_data_service import save_training_example, get_training_stats

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
        raise HTTPException(
            status_code=422,
            detail=(
                "Could not extract meaningful text from the uploaded file. "
                "If this is a scanned PDF, OCR is not yet supported — please "
                "upload a text-based PDF or a .txt / .docx copy of the contract."
            ),
        )

    try:
        result = await run_contract_pipeline(text)
    except Exception as e:
        logger.error(f"Contract analysis pipeline failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"AI contract analysis is currently unavailable: {e}",
        )

    # Run audit rights benchmark scoring against gold-standard template
    audit_benchmark = score_audit_rights(result)

    # Persist to SQLite
    risk_score = result.get("overall_risk_score", 0) if isinstance(result, dict) else 0
    contract_row_id: int | None = None
    try:
        contract_row_id = save_contract_analysis(file.filename, result, risk_score, audit_benchmark.get("score", 0))
    except Exception as e:
        logger.warning(f"Failed to persist contract analysis: {e}")

    # Persist the original upload (raw bytes + extracted text) for the
    # data collection layer. Linked to the contract_analyses row via
    # related_id so usage queries can join the two.
    try:
        log_file_upload(
            upload_kind="pbm_contract",
            filename=file.filename,
            content_type=file.content_type,
            file_bytes=content,
            extracted_text=text,
            related_id=contract_row_id,
        )
    except Exception as e:
        logger.debug(f"file_upload logging failed: {e}")

    return {
        "status": "success",
        "filename": file.filename,
        "file_size": len(content),
        "extracted_text_length": len(text),
        "pdf_parsed": filename.endswith(".pdf"),
        "analysis": result,
        "audit_rights_benchmark": audit_benchmark,
        "generated_by": result.get("_generated_by", "ai") if isinstance(result, dict) else "ai",
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

    try:
        log_event(
            event_type="pdf_exported",
            payload={
                "filename": filename,
                "byte_size": len(pdf_bytes),
                "has_plan_benefits": bool(request.get("plan_benefits")),
                "has_cross_reference": bool(request.get("cross_reference")),
                "has_audit_letter": bool(request.get("audit_letter")),
            },
        )
    except Exception as e:
        logger.debug(f"pdf_exported event logging failed: {e}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="ClearScript_Report_{safe_name}.pdf"',
        },
    )


@router.post("/feedback")
async def submit_feedback(request: dict):
    """
    Submit corrected analysis for fine-tuning data collection.
    Call this when a user corrects the AI's output.

    Expects JSON body with:
    - contract_text: original contract text
    - original_analysis: the AI's output
    - corrected_analysis: the human-corrected version
    - feedback_notes: optional string describing what was wrong
    - contract_filename: optional filename
    """
    contract_text = request.get("contract_text", "")
    original = request.get("original_analysis", {})
    corrected = request.get("corrected_analysis", {})
    notes = request.get("feedback_notes", "")
    filename = request.get("contract_filename", "")

    if not corrected:
        raise HTTPException(status_code=400, detail="'corrected_analysis' is required.")

    result = save_training_example(
        contract_text=contract_text,
        original_analysis=original,
        corrected_analysis=corrected,
        feedback_notes=notes,
        contract_filename=filename,
    )
    return result


@router.get("/training-stats")
async def training_stats():
    """Check how many training examples have been collected."""
    return get_training_stats()


@router.get("/pipeline-status")
async def pipeline_status():
    """Check if RocketRide pipeline engine is available."""
    return await get_pipeline_status()


@router.get("/list")
async def list_contracts():
    """
    Return every persisted contract analysis as a lightweight summary,
    most recent first. Used by the audit-letter contract picker so the
    user can choose which uploaded contract to draft an audit letter for.

    Each item carries:
      - id, filename, analysis_date (UTC ISO timestamp)
      - deal_score (0-100, derived from the persisted analysis)
      - risk_level ("low" | "moderate" | "high")
      - risk_score, audit_rights_score
    """
    items = list_contract_analyses(limit=100)
    return {"status": "success", "count": len(items), "contracts": items}


@router.get("/{contract_id}")
async def get_contract(contract_id: int):
    """Fetch one persisted contract analysis by id."""
    item = load_contract_analysis_by_id(contract_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"No contract analysis with id={contract_id}")
    return {"status": "success", "contract": item}

