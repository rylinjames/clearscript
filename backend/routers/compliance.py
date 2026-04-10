"""Feature 10: Compliance Deadline Tracker"""

from typing import Optional
from fastapi import APIRouter
from services.data_service import generate_compliance_deadlines

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


@router.get("/deadlines")
async def compliance_deadlines(contract_id: Optional[int] = None):
    """
    Returns regulatory deadlines. If contract_id is provided, includes
    that contract's actual critical dates (notice deadline, RFP start,
    term end) from the persisted analysis. Otherwise returns only the
    federal statutory items.
    """
    deadlines = generate_compliance_deadlines(contract_id=contract_id)

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
