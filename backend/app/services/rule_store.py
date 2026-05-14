"""
Simple CRUD helpers for rules.
"""

from sqlalchemy.orm import Session
from ..db import models


def _json_sanitize(obj):
    """Recursively convert common non-JSON-serializable types to native Python.

    This mainly targets numpy scalar types (int64/float64/bool_) and pandas
    types (Timestamp/NA). SQLAlchemy's JSON column ultimately relies on the
    stdlib json encoder, which can't handle these.
    """
    try:
        import numpy as np
    except Exception:  # pragma: no cover
        np = None
    try:
        import pandas as pd
    except Exception:  # pragma: no cover
        pd = None

    # Primitive JSON types
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    # Numpy scalars
    if np is not None:
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)

    # Pandas scalars
    if pd is not None:
        if isinstance(obj, getattr(pd, "Timestamp", ())):
            return obj.isoformat()
        if obj is getattr(pd, "NA", None):
            return None

    # Dict
    if isinstance(obj, dict):
        return {str(k): _json_sanitize(v) for k, v in obj.items()}

    # List / Tuple / Set
    if isinstance(obj, (list, tuple, set)):
        return [_json_sanitize(v) for v in obj]

    # Fallback: try string conversion
    return str(obj)


def to_dict(rule: models.Rule) -> dict:
    """Convert rule to dictionary with structured metadata."""
    targets = rule.targets or {}
    
    # Extract structured metadata from targets
    rule_type = targets.get("rule_type") or _infer_rule_type(rule)
    determinant_column = targets.get("determinant_column") or _extract_determinant(rule)
    dependent_column = targets.get("dependent_column") or _extract_dependent(rule)
    compliance = targets.get("compliance")
    extraction_algorithm = targets.get("extraction_algorithm") or _infer_algorithm(rule.source.value)
    
    # Format compliance
    compliance_display = None
    if compliance is not None:
        compliance_display = f"{compliance:.1f}%"
        if compliance >= 99:
            compliance_display += " (Very High)"
        elif compliance >= 95:
            compliance_display += " (High)"
        elif compliance >= 90:
            compliance_display += " (Medium)"
        else:
            compliance_display += " (Low)"
    
    # Suggested action based on confidence and approval status
    suggested_action = "Review before auto-application"
    if rule.approved is True:
        suggested_action = "Ready for application"
    elif rule.approved is False:
        suggested_action = "Rejected - needs revision"
    elif rule.confidence and rule.confidence >= 0.9:
        suggested_action = "High confidence - consider auto-approval"
    
    # Extract user-friendly explanation from targets
    user_explanation = targets.get("user_explanation")
    
    # Extract LLM opinion from targets
    llm_opinion = targets.get("llm_opinion", {})
    
    return {
        "id": rule.id,
        "source": rule.source.value,
        "modality": rule.modality.value,
        "targets": targets,
        "predicate": rule.predicate,
        "action": rule.action,
        "confidence": rule.confidence,
        "explanation": rule.explanation,
        "is_active": rule.is_active,
        "approved": rule.approved,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        # Structured metadata
        "rule_type": rule_type,
        "determinant_column": determinant_column,
        "dependent_column": dependent_column,
        "compliance": compliance,
        "compliance_display": compliance_display,
        "extraction_algorithm": extraction_algorithm,
        "suggested_action": suggested_action,
        "user_explanation": user_explanation,  # LLM-generated user-friendly explanation
        # LLM opinion on rule correctness
        "llm_opinion": llm_opinion.get("opinion") if llm_opinion else None,
        "llm_confidence": llm_opinion.get("confidence") if llm_opinion else None,
        "llm_reasoning": llm_opinion.get("reasoning") if llm_opinion else None,
        "llm_concerns": llm_opinion.get("concerns", []) if llm_opinion else [],
        "llm_suggestions": llm_opinion.get("suggestions", []) if llm_opinion else [],
    }


def _infer_rule_type(rule: models.Rule) -> str:
    """Infer rule type from predicate and source."""
    predicate = rule.predicate or ""
    source = rule.source.value
    
    if "fd(" in predicate.lower():
        return "Functional Dependency (FD)"
    elif "regex" in predicate.lower() or "pattern" in predicate.lower():
        return "Pattern/Regex Rule"
    elif "range" in predicate.lower() or "min" in predicate.lower() or "max" in predicate.lower():
        return "Range Constraint"
    elif "unique" in predicate.lower():
        return "Uniqueness Constraint"
    elif "if" in predicate.lower() and "then" in predicate.lower():
        return "Conditional Rule (CFD)"
    elif source == "rag":
        return "Semantic Rule (RAG)"
    else:
        return "Data Quality Rule"


def _extract_determinant(rule: models.Rule) -> str:
    """Extract determinant column from predicate or targets."""
    targets = rule.targets or {}
    columns = targets.get("columns", [])
    
    if "fd(" in (rule.predicate or "").lower():
        # Extract from predicate like "fd(col1 -> col2)"
        import re
        match = re.search(r'fd\(([^->]+)', rule.predicate)
        if match:
            return match.group(1).strip()
    
    if len(columns) > 0:
        return columns[0]
    
    return "N/A"


def _extract_dependent(rule: models.Rule) -> str:
    """Extract dependent column from predicate or targets."""
    targets = rule.targets or {}
    columns = targets.get("columns", [])
    
    if "fd(" in (rule.predicate or "").lower():
        # Extract from predicate like "fd(col1 -> col2)"
        import re
        match = re.search(r'fd\([^->]+->\s*([^)]+)', rule.predicate)
        if match:
            return match.group(1).strip()
    
    if len(columns) > 1:
        return columns[-1]
    elif len(columns) == 1:
        return columns[0]
    
    return "N/A"


def _infer_algorithm(source: str) -> str:
    """Infer extraction algorithm from source."""
    algorithms = {
        "extracted": "Statistical/ML Mining Algorithm",
        "rag": "RAG Semantic Retrieval",
        "user": "User-Defined",
    }
    return algorithms.get(source, "Unknown Algorithm")


def add_rule(db: Session, dataset_id: int | None, **kwargs) -> models.Rule:
    """Add a rule to the database, filtering out invalid fields."""
    # Only pass fields that exist in the Rule model
    valid_fields = {
        'source', 'modality', 'targets', 'predicate', 'action', 
        'confidence', 'explanation', 'is_active', 'approved'
    }
    
    # Filter kwargs to only include valid fields
    filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_fields}

    # Sanitize JSON fields (targets often contains numpy int64, etc.)
    if "targets" in filtered_kwargs and filtered_kwargs["targets"] is not None:
        filtered_kwargs["targets"] = _json_sanitize(filtered_kwargs["targets"])

    # Also sanitize a few common scalar fields that sometimes come in as numpy types
    if "confidence" in filtered_kwargs and filtered_kwargs["confidence"] is not None:
        filtered_kwargs["confidence"] = _json_sanitize(filtered_kwargs["confidence"])
    
    rule = models.Rule(dataset_id=dataset_id, **filtered_kwargs)
    db.add(rule)
    try:
        db.commit()
    except Exception:
        # Ensure the session is usable after a failed flush/commit
        db.rollback()
        raise
    db.refresh(rule)
    return rule


def list_rules(
    db: Session,
    dataset_id: int | None = None,
    rule_ids: list[int] | None = None,
    active_only: bool = True,
):
    """List rules.

    By default returns only active rules. Pass active_only=False to include
    deactivated (dropped/noisy) rules.
    """
    query = db.query(models.Rule)
    if dataset_id:
        query = query.filter(models.Rule.dataset_id == dataset_id)
    if rule_ids:
        query = query.filter(models.Rule.id.in_(rule_ids))
    if active_only:
        query = query.filter(models.Rule.is_active == True)  # noqa: E712
    return query.all()

