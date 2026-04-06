"""Feature 2: Initial Disclosure Analyzer"""

import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from services.ai_service import analyze_disclosure

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

    return {
        "status": "success",
        "filename": file.filename,
        "file_size": len(content),
        "analysis": result,
    }
