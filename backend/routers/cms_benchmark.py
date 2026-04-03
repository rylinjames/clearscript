"""CMS Part D Benchmarking Router"""

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from services.cms_partd_service import (
    generate_partd_benchmarks,
    benchmark_formulary_against_partd,
    get_ira_selected_drugs,
)
from services.formulary_service import parse_formulary_pdf

router = APIRouter(prefix="/api/cms-benchmark", tags=["cms-benchmark"])


@router.get("/partd-stats")
async def partd_stats():
    """
    Returns CMS Part D benchmark statistics including tier distribution,
    UM rates, formulary size averages, and IRA provision details.
    """
    return {
        "status": "success",
        "partd_benchmarks": generate_partd_benchmarks(),
    }


@router.get("/ira-drugs")
async def ira_drugs():
    """
    Returns the 10 drugs selected for Medicare Price Negotiation under
    the Inflation Reduction Act with negotiated Maximum Fair Prices.
    """
    drugs = get_ira_selected_drugs()
    total_enrollees = sum(d["part_d_enrollees_using"] for d in drugs)
    return {
        "status": "success",
        "ira_selected_drugs": drugs,
        "total_enrollees_affected": total_enrollees,
        "program_note": (
            "Under the Inflation Reduction Act, CMS negotiated Maximum Fair "
            "Prices for these 10 drugs. Prices take effect January 2026 for "
            "Medicare Part D. Employer plans can use these as leverage in "
            "PBM contract negotiations."
        ),
    }


@router.post("/compare")
async def compare_against_partd(
    file: UploadFile = File(..., description="Employer formulary PDF"),
    tier_model: int | None = Form(
        default=None,
        description="Force tier model (3, 4, 5, or 6). Auto-detected if omitted.",
    ),
):
    """
    Upload an employer formulary PDF and compare it against CMS Part D
    benchmark averages. Returns tier distribution comparison, UM rate
    comparison, coverage gaps, tier mismatches, and a competitiveness score.
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
            content, tier_model=tier_model, filename=file.filename,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if not rows:
        raise HTTPException(
            status_code=422,
            detail="No drug rows could be extracted from the PDF. "
            "Ensure this is a tabular formulary document.",
        )

    comparison = benchmark_formulary_against_partd(rows)

    return {
        "status": "success",
        "filename": file.filename,
        "comparison": comparison,
    }
