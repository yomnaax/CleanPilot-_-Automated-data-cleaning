"""
API endpoints for LLM-based rule validation.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from ..db.base import get_db
from ..db import models
from ..services import rule_store, rule_validator
from ..services.feedback_engine import get_feedback_examples


class ValidationResponse(BaseModel):
    rule_id: int
    opinion: str  # "agree", "disagree", "uncertain"
    confidence: float
    reasoning: str
    concerns: List[str]
    suggestions: List[str]


router = APIRouter()


@router.post("/{rule_id}", response_model=ValidationResponse)
def validate_rule_with_llm(
    rule_id: int,
    db: Session = Depends(get_db)
):
    """
    Get LLM's opinion on a specific rule.
    """
    rule = db.query(models.Rule).filter(models.Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Get dataset
    dataset = db.query(models.Dataset).filter(models.Dataset.id == rule.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Get user feedback history for similar rules
    feedback_history = get_feedback_examples(rule.dataset_id, limit=10, rule_id=rule.id, db=db)
    
    # Convert rule to dict
    rule_dict = rule_store.to_dict(rule)
    
    # Get LLM opinion
    try:
        print(f"Validating rule {rule_id} with LLM...")
        print(f"Dataset path: {dataset.storage_path}")
        print(f"Rule dict keys: {rule_dict.keys()}")
        
        opinion_data = rule_validator.validate_rule_with_llm(
            rule_id=rule.id,
            dataset_path=dataset.storage_path,
            rule_dict=rule_dict,
            user_feedback_history=feedback_history
        )
        
        print(f"LLM opinion received: {opinion_data}")
        
        # Check if this is a quota/error response that should be returned as HTTP error
        if opinion_data.get("opinion") == "uncertain" and opinion_data.get("confidence") == 0.0:
            reasoning = opinion_data.get("reasoning", "")
            if "quota" in reasoning.lower() or "insufficient_quota" in reasoning.lower() or "quota exceeded" in reasoning.lower():
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "API quota exceeded",
                        "message": "You've exceeded your OpenAI API quota. Please check your billing or upgrade your plan.",
                        "suggestions": opinion_data.get("suggestions", [
                            "Check your OpenAI billing dashboard",
                            "Upgrade your API plan",
                            "Wait for quota reset (usually monthly)",
                            "You can still review rules without LLM validation"
                        ])
                    }
                )
            elif "invalid api key" in reasoning.lower() or "unauthorized" in reasoning.lower() or "api key" in reasoning.lower():
                raise HTTPException(
                    status_code=401,
                    detail={
                        "error": "Invalid API key",
                        "message": "Your OpenAI API key is invalid or missing. Please check your .env file.",
                        "suggestions": opinion_data.get("suggestions", [
                            "Check OPENAI_API_KEY in .env file",
                            "Verify the API key is correct",
                            "You can still review rules without LLM validation"
                        ])
                    }
                )
        
        # Store opinion in rule targets for future reference
        if not rule.targets:
            rule.targets = {}
        rule.targets["llm_opinion"] = opinion_data
        db.commit()
        
        return ValidationResponse(
            rule_id=rule.id,
            **opinion_data
        )
    except HTTPException:
        # Re-raise HTTP exceptions (like 429, 401) as-is
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        error_str = str(e)
        print(f"Error validating rule {rule_id}: {error_trace}")
        raise HTTPException(status_code=500, detail=f"Failed to validate rule: {error_str}")


@router.post("/batch", response_model=List[ValidationResponse])
def validate_rules_batch(
    rule_ids: List[int],
    db: Session = Depends(get_db)
):
    """
    Get LLM opinions on multiple rules (batch processing).
    """
    results = []
    
    for rule_id in rule_ids:
        try:
            rule = db.query(models.Rule).filter(models.Rule.id == rule_id).first()
            if not rule:
                continue
            
            dataset = db.query(models.Dataset).filter(models.Dataset.id == rule.dataset_id).first()
            if not dataset:
                continue
            
            feedback_history = get_feedback_examples(rule.dataset_id, limit=10)
            rule_dict = rule_store.to_dict(rule)
            
            opinion_data = rule_validator.validate_rule_with_llm(
                rule_id=rule.id,
                dataset_path=dataset.storage_path,
                rule_dict=rule_dict,
                user_feedback_history=feedback_history
            )
            
            # Store opinion
            if not rule.targets:
                rule.targets = {}
            rule.targets["llm_opinion"] = opinion_data
            db.commit()
            
            results.append(ValidationResponse(
                rule_id=rule.id,
                **opinion_data
            ))
        except Exception as e:
            print(f"Failed to validate rule {rule_id}: {e}")
            continue
    
    return results

