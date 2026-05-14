"""
Rule Converter: Converts rules from raw column names to canonical concepts and vice versa.
"""

from typing import Dict, List, Any, Optional
import re
from ..db import models


def convert_rule_to_canonical(
    rule: Dict[str, Any],
    column_mappings: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Convert a rule from raw column names to canonical concepts.
    
    Args:
        rule: Rule with raw column names in predicate/action
        column_mappings: Dict mapping column_name -> {canonical_concept, confidence, ...}
    
    Returns:
        Rule with canonical concepts, or None if mapping fails
    """
    if not column_mappings:
        return rule  # No mapping available, return as-is
    
    # Get columns from rule targets
    rule_columns = rule.get("targets", {}).get("columns", [])
    if not rule_columns:
        return rule  # No columns to map
    
    # Map columns to canonical concepts
    canonical_columns = []
    mapped_concepts = []
    
    for col in rule_columns:
        mapping = column_mappings.get(col)
        if mapping and mapping.get("canonical_concept"):
            canonical_concept = mapping["canonical_concept"]
            canonical_columns.append(canonical_concept)
            mapped_concepts.append(canonical_concept)
        else:
            # Column not mapped - keep original
            canonical_columns.append(col)
    
    # Convert predicate and action to use canonical concepts
    predicate = rule.get("predicate", "")
    action = rule.get("action", "")
    
    # Replace column names with canonical concepts in predicate/action
    for col in rule_columns:
        mapping = column_mappings.get(col)
        if mapping and mapping.get("canonical_concept"):
            canonical_concept = mapping["canonical_concept"]
            # Replace column name with canonical concept
            predicate = re.sub(r'\b' + re.escape(col) + r'\b', canonical_concept, predicate)
            action = re.sub(r'\b' + re.escape(col) + r'\b', canonical_concept, action)
    
    # Create new rule with canonical concepts
    canonical_rule = rule.copy()
    
    # Update targets with canonical mapping info
    updated_targets = rule.get("targets", {}).copy()
    updated_targets.update({
        "columns": canonical_columns,
        "canonical_concepts": mapped_concepts,
        "original_columns": rule_columns,  # Keep original for reference
        "uses_canonical_mapping": True,  # Store in targets, not as top-level field
        "mapping_confidence": min(
            [column_mappings.get(col, {}).get("confidence", 0.0) for col in rule_columns],
            default=1.0
        )
    })
    
    canonical_rule["targets"] = updated_targets
    canonical_rule["predicate"] = predicate
    canonical_rule["action"] = action
    
    return canonical_rule


def convert_rule_from_canonical(
    rule: Dict[str, Any],
    column_mappings: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Convert a rule from canonical concepts back to actual column names.
    Used when applying rules to a dataset.
    
    Args:
        rule: Rule with canonical concepts
        column_mappings: Dict mapping column_name -> {canonical_concept, ...}
    
    Returns:
        Rule with actual column names
    """
    if not column_mappings:
        return rule  # No mapping available
    
    # Create reverse mapping: canonical_concept -> column_name
    concept_to_column = {}
    for col_name, mapping in column_mappings.items():
        canonical_concept = mapping.get("canonical_concept")
        if canonical_concept:
            # If multiple columns map to same concept, use first one (or could use highest confidence)
            if canonical_concept not in concept_to_column:
                concept_to_column[canonical_concept] = col_name
    
    # Get canonical concepts from rule
    canonical_concepts = rule.get("targets", {}).get("canonical_concepts", [])
    original_columns = rule.get("targets", {}).get("original_columns", [])
    
    # Use original columns if available, otherwise map from concepts
    if original_columns:
        actual_columns = original_columns
    else:
        actual_columns = [concept_to_column.get(concept, concept) for concept in canonical_concepts]
    
    # Convert predicate and action back to actual column names
    predicate = rule.get("predicate", "")
    action = rule.get("action", "")
    
    for canonical_concept in canonical_concepts:
        actual_column = concept_to_column.get(canonical_concept)
        if actual_column:
            # Replace canonical concept with actual column name
            predicate = re.sub(r'\b' + re.escape(canonical_concept) + r'\b', actual_column, predicate)
            action = re.sub(r'\b' + re.escape(canonical_concept) + r'\b', actual_column, action)
    
    # Create rule with actual column names
    actual_rule = rule.copy()
    actual_rule["targets"] = {
        **rule.get("targets", {}),
        "columns": actual_columns
    }
    actual_rule["predicate"] = predicate
    actual_rule["action"] = action
    
    return actual_rule

