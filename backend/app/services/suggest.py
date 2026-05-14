"""
Suggestion engine for next actions based on current state.
"""

from sqlalchemy.orm import Session
from ..db import models
from typing import List


def suggest_next_actions(db: Session, dataset_id: int) -> List[str]:
    """Suggest next actions based on dataset state."""
    dataset = db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()
    
    if not dataset:
        return []
    
    suggestions = []
    
    # Check if dataset has been profiled
    profile_run = (
        db.query(models.Run)
        .filter(
            models.Run.dataset_id == dataset_id,
            models.Run.run_type == models.RunType.PROFILING,
            models.Run.status == models.RunStatus.COMPLETED
        )
        .first()
    )
    
    if not profile_run:
        suggestions.append("profile_dataset")
        return suggestions
    
    # Check if rules have been extracted
    rules = db.query(models.Rule).filter(models.Rule.dataset_id == dataset_id).all()
    
    if not rules:
        suggestions.append("extract_rules")
        return suggestions
    
    # Check if rules have been reviewed/approved
    approved_rules = [r for r in rules if r.approved]
    
    if len(approved_rules) == 0:
        suggestions.append("review_rules")
        return suggestions
    
    # Check if rules have been applied
    apply_run = (
        db.query(models.Run)
        .filter(
            models.Run.dataset_id == dataset_id,
            models.Run.run_type == models.RunType.CLEANING,
            models.Run.status == models.RunStatus.COMPLETED
        )
        .first()
    )
    
    if not apply_run:
        suggestions.append("apply_rules")
    else:
        suggestions.append("review_results")
        suggestions.append("provide_feedback")
    
    return suggestions
