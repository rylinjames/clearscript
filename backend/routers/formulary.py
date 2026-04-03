"""Feature 8: Formulary Manipulation Detector + PDF Upload & Comparison"""

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from services.data_service import generate_formulary_data
from services.formulary_service import (
    parse_formulary_pdf,
    score_formulary,
    compare_formularies,
)

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


@router.post("/upload")
async def upload_formulary(
    file: UploadFile = File(..., description="A PBM formulary PDF"),
    tier_model: int | None = Form(
        default=None,
        description="Force tier model (3, 4, 5, or 6). Auto-detected if omitted.",
    ),
):
    """
    Upload a single formulary PDF, parse it, score it, and return
    structured drug rows plus scoring.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if tier_model is not None and tier_model not in (3, 4, 5, 6):
        raise HTTPException(
            status_code=400,
            detail="tier_model must be 3, 4, 5, or 6.",
        )

    try:
        rows = parse_formulary_pdf(
            content,
            tier_model=tier_model,
            filename=file.filename,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if not rows:
        raise HTTPException(
            status_code=422,
            detail="No drug rows could be extracted from the PDF. "
            "Ensure this is a tabular formulary document.",
        )

    scores = score_formulary(rows)

    return {
        "status": "success",
        "filename": file.filename,
        "tier_model": scores["tier_model"],
        "total_drugs": scores["total_drugs"],
        "scores": scores,
        "drugs": rows,
    }


@router.post("/compare")
async def compare_formulary_pdfs(
    file_a: UploadFile = File(..., description="First formulary PDF"),
    file_b: UploadFile = File(..., description="Second formulary PDF"),
    tier_model_a: int | None = Form(
        default=None,
        description="Force tier model for first PDF (3/4/5/6). Auto-detected if omitted.",
    ),
    tier_model_b: int | None = Form(
        default=None,
        description="Force tier model for second PDF (3/4/5/6). Auto-detected if omitted.",
    ),
):
    """
    Upload two formulary PDFs, parse and score each, then return a
    side-by-side comparison with tier changes, UM burden diffs,
    drugs added/removed, and a human-readable interpretation.
    """
    # Validate inputs
    for label, f in [("file_a", file_a), ("file_b", file_b)]:
        if not f.filename or not f.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"{label}: Only PDF files are accepted.",
            )

    for label, tm in [("tier_model_a", tier_model_a), ("tier_model_b", tier_model_b)]:
        if tm is not None and tm not in (3, 4, 5, 6):
            raise HTTPException(
                status_code=400,
                detail=f"{label} must be 3, 4, 5, or 6.",
            )

    content_a = await file_a.read()
    content_b = await file_b.read()

    if not content_a or not content_b:
        raise HTTPException(status_code=400, detail="Both uploaded files must be non-empty.")

    try:
        rows_a = parse_formulary_pdf(content_a, tier_model=tier_model_a, filename=file_a.filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"file_a: {exc}")

    try:
        rows_b = parse_formulary_pdf(content_b, tier_model=tier_model_b, filename=file_b.filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"file_b: {exc}")

    if not rows_a:
        raise HTTPException(
            status_code=422,
            detail="No drug rows could be extracted from the first PDF.",
        )
    if not rows_b:
        raise HTTPException(
            status_code=422,
            detail="No drug rows could be extracted from the second PDF.",
        )

    label_a = file_a.filename.rsplit(".", 1)[0] if file_a.filename else "Formulary A"
    label_b = file_b.filename.rsplit(".", 1)[0] if file_b.filename else "Formulary B"

    comparison = compare_formularies(rows_a, rows_b, label_a=label_a, label_b=label_b)

    return {
        "status": "success",
        "comparison": comparison,
    }
