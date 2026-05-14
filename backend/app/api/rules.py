from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.base import get_db
from ..db import models
from ..services import rule_store
from ..services.reinforcement_learning import feedback_on_rule


class RuleResponse(BaseModel):
    id: int
    source: str
    modality: str
    targets: dict | None
    predicate: str
    action: str | None
    confidence: float | None
    explanation: str | None
    is_active: bool
    approved: bool | None  # Can be None (pending), True (approved), or False (rejected)
    # Structured metadata
    rule_type: str | None = None
    determinant_column: str | None = None
    dependent_column: str | None = None
    compliance: float | None = None
    compliance_display: str | None = None
    extraction_algorithm: str | None = None
    suggested_action: str | None = None
    user_explanation: str | None = None  # LLM-generated user-friendly explanation
    # LLM opinion
    llm_opinion: str | None = None  # "agree", "disagree", "uncertain"
    llm_confidence: float | None = None
    llm_reasoning: str | None = None
    llm_concerns: list[str] = []
    llm_suggestions: list[str] = []


class RuleUpdate(BaseModel):
    approved: bool | None = None  # None=pending, True=approved, False=rejected
    is_active: bool | None = None
    explanation: str | None = None
    # Allow manual adjustment in UI
    predicate: str | None = None
    action: str | None = None
    targets: dict | None = None


router = APIRouter()


@router.get("/", response_model=list[RuleResponse])
def list_rules(
    dataset_id: str | int | None = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    """List rules, optionally filtered by dataset_id."""
    # Convert string to int if needed (frontend sends as string)
    original_dataset_id = dataset_id
    if dataset_id is not None:
        try:
            dataset_id = int(dataset_id)
        except (ValueError, TypeError):
            print(f"Warning: Could not convert dataset_id '{original_dataset_id}' to int, filtering disabled")
            dataset_id = None
    
    rules = rule_store.list_rules(db, dataset_id=dataset_id, active_only=not include_inactive)
    return [rule_store.to_dict(r) for r in rules]


@router.get("/{rule_id}", response_model=RuleResponse)
def get_rule(rule_id: int, db: Session = Depends(get_db)):
    """Get a specific rule by ID."""
    rule = db.query(models.Rule).filter(models.Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule_store.to_dict(rule)


@router.patch("/{rule_id}", response_model=RuleResponse)
def update_rule(rule_id: int, updates: RuleUpdate, db: Session = Depends(get_db)):
    """Update a rule (approve/reject or modify)."""
    rule = db.query(models.Rule).filter(models.Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Get only fields that were explicitly set
    update_dict = updates.model_dump(exclude_unset=True)
    
    # Update fields (allow None to reset to pending)
    if 'approved' in update_dict:
        rule.approved = updates.approved
    if 'is_active' in update_dict:
        rule.is_active = updates.is_active
    if 'explanation' in update_dict:
        rule.explanation = updates.explanation
    if 'predicate' in update_dict and updates.predicate is not None:
        rule.predicate = updates.predicate
    if 'action' in update_dict:
        rule.action = updates.action
    if 'targets' in update_dict:
        rule.targets = updates.targets
    # if 'targets' in update_dict:
    #     # Ensure JSON-serializable types
    #     rule.targets = rule_store.json_sanitize(updates.targets)
    
    db.commit()
    db.refresh(rule)
    # Trigger reinforcement learning feedback if approval has been changed
    try:
        if 'approved' in update_dict:
            feedback_on_rule(rule, rule.approved)
    except Exception:
        # Best effort: ignore failures in feedback loop
        pass
    return rule_store.to_dict(rule)

