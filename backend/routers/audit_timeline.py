"""Feature 14: Audit Timeline Tracker — milestone-based PBM audit timeline with delay tactic warnings."""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from services.audit_timeline_service import generate_audit_timeline, get_default_timeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit-timeline", tags=["Audit Timeline"])


class TimelineRequest(BaseModel):
    plan_year_end: str = "2025-12-31"
    notice_requirement_days: Optional[int] = 90
    data_delivery_deadline_days: Optional[int] = 30
    response_deadline_days: Optional[int] = 30
    audit_frequency: Optional[str] = "annual"
    run_out_period_days: Optional[int] = 90
    auditor_selection: Optional[str] = "plan_choice"
    extrapolation_allowed: Optional[bool] = False
    concurrent_audit_limit: Optional[int] = None
    recovery_cap: Optional[str] = None
    dispute_resolution: Optional[str] = "arbitration"
    survival_years: Optional[int] = 3


@router.post("/generate")
async def generate_timeline(request: TimelineRequest):
    """
    Generate an audit timeline from plan parameters and contract terms.
    Returns milestones with dates, PBM delay tactics to watch for, and recommended actions.
    """
    try:
        contract_terms = {
            "notice_requirement_days": request.notice_requirement_days,
            "data_delivery_deadline_days": request.data_delivery_deadline_days,
            "response_deadline_days": request.response_deadline_days,
            "audit_frequency": request.audit_frequency,
            "run_out_period_days": request.run_out_period_days,
            "auditor_selection": request.auditor_selection,
            "extrapolation_allowed": request.extrapolation_allowed,
            "concurrent_audit_limit": request.concurrent_audit_limit,
            "recovery_cap": request.recovery_cap,
            "dispute_resolution": request.dispute_resolution,
            "survival_years": request.survival_years,
        }

        result = generate_audit_timeline(request.plan_year_end, contract_terms)

        return {
            "status": "success",
            "timeline": result,
        }
    except Exception as e:
        logger.error(f"Failed to generate audit timeline: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate audit timeline: {str(e)}")


@router.get("/template")
async def get_template_timeline():
    """
    Return a default audit timeline for a standard Jan-Dec plan year.
    Uses the most recently completed plan year and default contract terms.
    """
    try:
        result = get_default_timeline()
        return {
            "status": "success",
            "timeline": result,
        }
    except Exception as e:
        logger.error(f"Failed to generate template timeline: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate template timeline: {str(e)}")
