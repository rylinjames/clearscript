"""Feedback collection endpoint — backs the contact form mounted at the
bottom of every authenticated page in the frontend."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from services.usage_service import save_feedback, log_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)
    name: Optional[str] = Field(default=None, max_length=200)
    email: Optional[str] = Field(default=None, max_length=320)
    page: Optional[str] = Field(default=None, max_length=500)
    user_id: Optional[str] = Field(default=None, max_length=200)
    session_id: Optional[str] = Field(default=None, max_length=200)


@router.post("")
async def submit_feedback(payload: FeedbackRequest, request: Request):
    """
    Persist a single feedback submission. Always returns success unless
    the message is missing — feedback should never feel rejected.
    """
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail="A message is required.")

    user_agent = request.headers.get("user-agent")

    row_id = save_feedback(
        message=payload.message.strip(),
        name=(payload.name or "").strip() or None,
        email=(payload.email or "").strip() or None,
        page=(payload.page or "").strip() or None,
        user_id=payload.user_id,
        session_id=payload.session_id,
        user_agent=user_agent,
    )

    if row_id is None:
        # Don't fail the user — log and return a soft success so the
        # form still feels responsive even if the DB write blew up.
        logger.error("Feedback save returned None — DB write failed")
        return {"status": "queued", "id": None}

    try:
        log_event(
            event_type="feedback_submitted",
            payload={"id": row_id, "page": payload.page, "has_email": bool(payload.email)},
            user_id=payload.user_id,
            session_id=payload.session_id,
            user_agent=user_agent,
        )
    except Exception as e:
        logger.debug(f"feedback_submitted event logging failed: {e}")

    return {"status": "success", "id": row_id}
