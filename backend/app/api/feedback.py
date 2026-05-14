from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.base import get_db
from ..db import models
from ..services import feedback_engine, rule_store


class FeedbackRequest(BaseModel):
    rule_id: int
    decision: models.FeedbackDecision
    comment: str | None = None
    payload: dict | None = None


class FeedbackResponse(BaseModel):
    id: int
    rule_id: int
    decision: models.FeedbackDecision
    comment: str | None


router = APIRouter()


@router.post("/", response_model=FeedbackResponse)
def submit_feedback(body: FeedbackRequest, db: Session = Depends(get_db)):
    rule = db.get(models.Rule, body.rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    feedback = feedback_engine.record_feedback(db, rule, body.decision, body.comment, body.payload)
    feedback_engine.update_prompts_with_feedback(rule, feedback)
    return FeedbackResponse(
        id=feedback.id, rule_id=rule.id, decision=feedback.decision, comment=feedback.comment
    )

