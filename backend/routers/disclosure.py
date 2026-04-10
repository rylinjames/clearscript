"""Feature 2: Initial Disclosure Analyzer"""

import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException
from services.ai_service import analyze_disclosure, analyze_disclosure_with_contract
from services.db_service import load_contract_analysis_by_id
from services.usage_service import log_file_upload

logger = logging.getLogger(__name__)

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
        raise HTTPException(
            status_code=422,
            detail=(
                "Could not extract meaningful text from the uploaded disclosure. "
                "Please upload a text-based file (.txt or text-based PDF)."
            ),
        )

    try:
        result = await analyze_disclosure(text)
    except Exception as e:
        logger.error(f"Disclosure analysis failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"AI disclosure analysis is currently unavailable: {e}",
        )

    try:
        log_file_upload(
            upload_kind="disclosure",
            filename=file.filename,
            content_type=file.content_type,
            file_bytes=content,
            extracted_text=text,
        )
    except Exception as e:
        logger.debug(f"file_upload logging failed: {e}")

    return {
        "status": "success",
        "filename": file.filename,
        "file_size": len(content),
        "analysis": result,
    }


@router.post("/cross-reference")
async def disclosure_cross_ref(
    file: UploadFile = File(...),
    contract_id: Optional[int] = None,
):
    """
    Cross-reference a PBM disclosure document against a specific contract
    analysis. Finds discrepancies between what the contract promises and
    what the disclosure actually reports.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    if contract_id is None:
        raise HTTPException(status_code=400, detail="contract_id is required for cross-reference")

    # Load the contract analysis
    contract = load_contract_analysis_by_id(contract_id)
    if not contract or not isinstance(contract.get("analysis"), dict):
        raise HTTPException(status_code=404, detail=f"No contract analysis found with id={contract_id}")

    content = await file.read()
    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = str(content[:10000])

    if len(text.strip()) < 50:
        raise HTTPException(
            status_code=422,
            detail="Could not extract meaningful text from the uploaded disclosure.",
        )

    try:
        result = await analyze_disclosure_with_contract(text, contract["analysis"])
    except Exception as e:
        logger.error(f"Disclosure cross-reference failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"AI disclosure cross-reference is currently unavailable: {e}",
        )

    return {
        "status": "success",
        "contract_id": contract_id,
        "contract_filename": contract.get("filename"),
        "cross_reference": result,
    }
