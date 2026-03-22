"""Feature 10: Compliance Deadline Tracker"""

from fastapi import APIRouter
from services.data_service import generate_compliance_deadlines

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


@router.get("/deadlines")
async def compliance_deadlines():
    """
    Returns all regulatory deadlines with status (upcoming, imminent, overdue).
    Includes DOL rule, HR 7148 delinking (2028), state-level bills.
    Shows days until each deadline.
    """
    deadlines = generate_compliance_deadlines()

    overdue = [d for d in deadlines if d["status"] == "overdue"]
    imminent = [d for d in deadlines if d["status"] == "imminent"]
    upcoming = [d for d in deadlines if d["status"] == "upcoming"]
    scheduled = [d for d in deadlines if d["status"] == "scheduled"]

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
