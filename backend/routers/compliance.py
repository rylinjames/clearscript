"""Feature 10: Compliance Deadline Tracker"""

from fastapi import APIRouter
from services.data_service import generate_compliance_deadlines

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


@router.get("/deadlines")
async def compliance_deadlines():
    """
    Returns all regulatory deadlines as rich, educational items.

    Each deadline includes the statutory basis, what-it-is / why-it-matters
    explanations, action items, and a `timing_phase` for grouping in the
    UI. Contract-derived deadlines (renegotiation windows, audit response
    windows) are pulled from contracts the user has actually uploaded.

    The legacy `summary` block is preserved for backward compatibility,
    using the new `timing_phase` values mapped to the older bucket names
    so old clients keep working while new clients render the rich format.
    """
    deadlines = generate_compliance_deadlines()

    # Legacy summary buckets — map the new neutral phase names to the
    # old labels so the existing summary block keeps the same shape.
    overdue = [d for d in deadlines if d.get("timing_phase") == "past"]
    imminent = [
        d for d in deadlines
        if d.get("timing_phase") in ("today", "this_week", "this_month")
    ]
    upcoming = [
        d for d in deadlines
        if d.get("timing_phase") == "next_quarter"
    ]
    scheduled = [
        d for d in deadlines
        if d.get("timing_phase") in ("this_year", "future")
    ]

    return {
        "status": "success",
        "summary": {
            "total_deadlines": len(deadlines),
            "overdue": len(overdue),
            "imminent": len(imminent),
            "upcoming": len(upcoming),
            "scheduled": len(scheduled),
        },
        "deadlines": deadlines,
    }
