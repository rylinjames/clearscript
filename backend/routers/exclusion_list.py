"""
Feature 17: Express Scripts / Evernorth Formulary Exclusion List Parser & Comparator.

Upload ESI exclusion list PDFs, parse them into structured data,
compare year-over-year changes, and estimate claims impact.
"""

import logging
from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from services.exclusion_list_service import (
    parse_exclusion_pdf,
    compare_exclusion_lists,
    estimate_exclusion_impact,
)
from services.data_service import get_claims

logger = logging.getLogger("clearscript.exclusion_list")

router = APIRouter(prefix="/api/exclusion-list", tags=["Exclusion List"])


@router.post("/parse")
async def parse_exclusion_list(
    file: UploadFile = File(..., description="An ESI/Evernorth exclusion list PDF"),
):
    """
    Upload a single Express Scripts or Evernorth formulary exclusion list PDF.
    Returns the parsed exclusion data as structured rows with drug class,
    subclass, excluded medications, and preferred alternatives.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        rows = parse_exclusion_pdf(content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if not rows:
        raise HTTPException(
            status_code=422,
            detail="No exclusion data could be extracted from the PDF. "
            "Ensure this is a valid ESI/Evernorth exclusion list document.",
        )

    # Compute summary stats
    all_excluded = set()
    classes = set()
    for row in rows:
        all_excluded.update(row["excluded_medications"])
        if row["drug_class"]:
            classes.add(row["drug_class"])

    return {
        "status": "success",
        "filename": file.filename,
        "total_rows": len(rows),
        "total_excluded_drugs": len(all_excluded),
        "drug_classes": sorted(classes),
        "drug_classes_count": len(classes),
        "exclusions": rows,
    }


@router.post("/compare")
async def compare_exclusion_lists_endpoint(
    file_a: UploadFile = File(..., description="First exclusion list PDF (earlier year)"),
    file_b: UploadFile = File(..., description="Second exclusion list PDF (later year)"),
    year_a: str = Form(default="Year A", description="Label for the first year (e.g. '2022')"),
    year_b: str = Form(default="Year B", description="Label for the second year (e.g. '2026')"),
):
    """
    Upload two ESI/Evernorth exclusion list PDFs with year labels.
    Returns a year-over-year comparison including newly excluded drugs,
    drugs returned to formulary, alternative changes, and per-class summaries.
    """
    for label, f in [("file_a", file_a), ("file_b", file_b)]:
        if not f.filename or not f.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"{label}: Only PDF files are accepted.",
            )

    content_a = await file_a.read()
    content_b = await file_b.read()

    if not content_a or not content_b:
        raise HTTPException(status_code=400, detail="Both uploaded files must be non-empty.")

    try:
        rows_a = parse_exclusion_pdf(content_a)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"file_a: {exc}")

    try:
        rows_b = parse_exclusion_pdf(content_b)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"file_b: {exc}")

    if not rows_a:
        raise HTTPException(
            status_code=422,
            detail="No exclusion data could be extracted from the first PDF.",
        )
    if not rows_b:
        raise HTTPException(
            status_code=422,
            detail="No exclusion data could be extracted from the second PDF.",
        )

    comparison = compare_exclusion_lists(rows_a, rows_b, year_a=year_a, year_b=year_b)

    return {
        "status": "success",
        "comparison": comparison,
    }


@router.get("/impact")
async def exclusion_impact():
    """
    Estimate the impact of exclusions on current claims data.

    Uses the most recently parsed exclusion list (or a default empty list)
    and the current claims dataset to calculate how many claims would be
    affected and the estimated dollar savings from switching to preferred
    alternatives.

    Note: For a full analysis, first upload an exclusion list via POST /parse,
    then call this endpoint. Without a prior upload, the endpoint uses the
    current claims data against an empty exclusion list (returning zero impact).
    To run impact analysis with a specific PDF, use the POST /impact endpoint.
    """
    claims = get_claims()
    if not claims:
        raise HTTPException(
            status_code=404,
            detail="No claims data available. Upload claims first.",
        )

    # Use the cached exclusion list if available, otherwise return empty impact
    exclusions = _cached_exclusions if _cached_exclusions else []

    impact = estimate_exclusion_impact(exclusions, claims)

    return {
        "status": "success",
        "impact": impact,
        "note": (
            "Impact calculated against current claims data."
            if exclusions
            else "No exclusion list loaded. Upload one via POST /parse first, "
            "then re-run this endpoint, or use POST /impact with a PDF."
        ),
    }


@router.post("/impact")
async def exclusion_impact_with_upload(
    file: UploadFile = File(..., description="An ESI/Evernorth exclusion list PDF"),
):
    """
    Upload an exclusion list PDF and immediately estimate its impact on
    current claims data.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        exclusions = parse_exclusion_pdf(content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    claims = get_claims()
    if not claims:
        raise HTTPException(
            status_code=404,
            detail="No claims data available. Upload claims first.",
        )

    # Cache for the GET endpoint
    global _cached_exclusions
    _cached_exclusions = exclusions

    impact = estimate_exclusion_impact(exclusions, claims)

    return {
        "status": "success",
        "filename": file.filename,
        "exclusions_parsed": len(exclusions),
        "impact": impact,
    }


# Simple in-memory cache for the most recently parsed exclusion list
_cached_exclusions: list[dict] = []
