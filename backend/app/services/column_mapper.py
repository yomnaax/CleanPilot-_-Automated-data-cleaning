"""
Column Mapping Service.

Maps dataset-specific columns to canonical financial concepts using:
1. Column name analysis
2. Sample value validation
3. LLM-based semantic understanding
4. Previously validated mappings (learning)
"""

import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from ..db import models
from ..utils.io_helpers import read_dataframe
from .canonical_schema import (
    CanonicalFinancialConcept,
    get_canonical_concepts,
    get_concept_metadata,
    find_matching_concepts,
    validate_concept_with_samples
)
from .llm.client import get_llm_client
from .llm.prompts import build_column_mapping_prompt
import json


class ColumnMapping:
    """Represents a mapping from dataset column to canonical concept."""
    
    def __init__(
        self,
        column_name: str,
        canonical_concept: Optional[str],
        confidence: float,
        explanation: str,
        evidence: Dict[str, Any],
        alternatives: List[Dict[str, Any]] = None
    ):
        self.column_name = column_name
        self.canonical_concept = canonical_concept
        self.confidence = confidence
        self.explanation = explanation
        self.evidence = evidence
        self.alternatives = alternatives or []


def analyze_column_semantics(
    column_name: str,
    column_data: pd.Series,
    data_type: str
) -> Dict[str, Any]:
    """
    Step 1: Understand column semantics using name, type, and values.
    """
    analysis = {
        "column_name": column_name,
        "data_type": data_type,
        "sample_values": column_data.dropna().head(10).tolist(),
        "unique_count": column_data.nunique(),
        "null_count": column_data.isna().sum(),
        "null_percentage": (column_data.isna().sum() / len(column_data)) * 100,
    }
    
    # Analyze value patterns
    if pd.api.types.is_numeric_dtype(column_data):
        analysis["min"] = float(column_data.min())
        analysis["max"] = float(column_data.max())
        analysis["mean"] = float(column_data.mean()) if len(column_data.dropna()) > 0 else None
        analysis["is_negative_allowed"] = (column_data < 0).any()
        analysis["is_positive_only"] = (column_data >= 0).all()
    
    # Analyze text patterns
    if pd.api.types.is_string_dtype(column_data) or column_data.dtype == 'object':
        sample_str = column_data.dropna().head(100).astype(str)
        analysis["avg_length"] = float(sample_str.str.len().mean()) if len(sample_str) > 0 else 0
        analysis["has_special_chars"] = sample_str.str.contains(r'[^\w\s]', regex=True).any()
        analysis["is_categorical"] = column_data.nunique() < 50
    
    return analysis


def map_to_canonical_heuristic(
    column_name: str,
    column_analysis: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Step 2: Map column to canonical concepts using heuristics.
    Returns list of potential matches with confidence scores.
    """
    sample_values = column_analysis.get("sample_values", [])
    
    # Use canonical schema pattern matching
    matches = find_matching_concepts(column_name, sample_values)
    
    # Additional validation based on data characteristics
    validated_matches = []
    for match in matches:
        concept = match["concept"]
        metadata = get_concept_metadata(concept)
        if not metadata:
            continue
        
        confidence = match["confidence"]
        
        # Validate data type matches
        expected_type = metadata.get("data_type", "")
        actual_type = column_analysis.get("data_type", "")
        
        if expected_type == "numeric" and pd.api.types.is_numeric_dtype(column_analysis.get("sample_values", [])):
            confidence += 0.1
        elif expected_type == "date" and "date" in actual_type.lower():
            confidence += 0.1
        elif expected_type == "categorical" and column_analysis.get("is_categorical", False):
            confidence += 0.1
        
        # Validate value ranges for amounts
        if concept == CanonicalFinancialConcept.TRANSACTION_AMOUNT.value:
            if "min" in column_analysis and "max" in column_analysis:
                min_val = column_analysis["min"]
                max_val = column_analysis["max"]
                if -100000000 <= min_val <= 100000000 and -100000000 <= max_val <= 100000000:
                    confidence += 0.1
        
        validated_matches.append({
            **match,
            "confidence": min(confidence, 0.95)
        })
    
    return validated_matches


def map_to_canonical_llm(
    column_name: str,
    column_analysis: Dict[str, Any],
    dataset_context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Step 2 (LLM): Use LLM to map column to canonical concept with semantic understanding.
    """
    llm_client = get_llm_client()
    
    prompt = f"""
You are a data schema mapping expert. Map the following column to a canonical financial concept.

Column Information:
- Name: {column_name}
- Data Type: {column_analysis.get('data_type', 'unknown')}
- Sample Values: {column_analysis.get('sample_values', [])[:5]}
- Unique Count: {column_analysis.get('unique_count', 0)}
- Null Percentage: {column_analysis.get('null_percentage', 0):.1f}%

Canonical Financial Concepts:
{json.dumps(get_canonical_concepts(), indent=2)}

For each concept, consider:
1. Column name similarity
2. Data type compatibility
3. Value patterns and examples
4. Semantic meaning

Return JSON with:
{{
    "primary_mapping": {{
        "concept": "canonical_concept_name or null",
        "confidence": 0.0-1.0,
        "explanation": "Why this mapping",
        "evidence": ["key evidence points"]
    }},
    "alternatives": [
        {{
            "concept": "alternative_concept",
            "confidence": 0.0-1.0,
            "explanation": "Why this alternative"
        }}
    ]
}}

If no good match exists, set primary_mapping.concept to null and confidence < 0.5.
Be conservative - prefer unmapped over low-confidence mappings.
"""
    
    try:
        response = llm_client.generate(prompt)
        # Try to extract JSON
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(0))
            return result
        else:
            return {"primary_mapping": {"concept": None, "confidence": 0.0, "explanation": "LLM response parsing failed"}}
    except Exception as e:
        return {"primary_mapping": {"concept": None, "confidence": 0.0, "explanation": f"LLM mapping failed: {str(e)}"}}


def create_column_mapping(
    column_name: str,
    column_data: pd.Series,
    use_llm: bool = True,
    dataset_context: Dict[str, Any] = None
) -> ColumnMapping:
    """
    Complete mapping process: analyze column and map to canonical concept.
    """
    # Step 1: Understand column semantics
    data_type = str(column_data.dtype)
    column_analysis = analyze_column_semantics(column_name, column_data, data_type)
    
    # Step 2: Map to canonical concepts
    if use_llm:
        # Try LLM first for semantic understanding
        llm_result = map_to_canonical_llm(column_name, column_analysis, dataset_context)
        primary = llm_result.get("primary_mapping", {})
        alternatives = llm_result.get("alternatives", [])
        
        canonical_concept = primary.get("concept")
        confidence = float(primary.get("confidence", 0.0))
        explanation = primary.get("explanation", "")
        evidence = primary.get("evidence", [])
        
        # If LLM confidence is low, fall back to heuristics
        if confidence < 0.6:
            heuristic_matches = map_to_canonical_heuristic(column_name, column_analysis)
            if heuristic_matches and heuristic_matches[0]["confidence"] > confidence:
                best_match = heuristic_matches[0]
                canonical_concept = best_match["concept"]
                confidence = best_match["confidence"]
                explanation = best_match["reason"]
                evidence = [f"Pattern match: {best_match['reason']}"]
                alternatives = [{"concept": m["concept"], "confidence": m["confidence"]} 
                               for m in heuristic_matches[1:3]]
    else:
        # Use heuristics only
        heuristic_matches = map_to_canonical_heuristic(column_name, column_analysis)
        if heuristic_matches:
            best_match = heuristic_matches[0]
            canonical_concept = best_match["concept"]
            confidence = best_match["confidence"]
            explanation = best_match["reason"]
            evidence = [f"Pattern match: {best_match['reason']}"]
            alternatives = [{"concept": m["concept"], "confidence": m["confidence"]} 
                           for m in heuristic_matches[1:3]]
        else:
            canonical_concept = None
            confidence = 0.0
            explanation = "No matching canonical concept found"
            evidence = []
            alternatives = []
    
    # Step 3 & 4: Respect uncertainty - don't map if confidence too low
    if confidence < 0.5:
        canonical_concept = None
        explanation = f"Low confidence ({confidence:.2f}) - leaving unmapped to avoid incorrect assumptions"
    
    return ColumnMapping(
        column_name=column_name,
        canonical_concept=canonical_concept,
        confidence=confidence,
        explanation=explanation,
        evidence=evidence,
        alternatives=alternatives
    )


def map_dataset_columns(
    dataset: models.Dataset,
    use_llm: bool = True
) -> Dict[str, ColumnMapping]:
    """
    Map all columns in a dataset to canonical concepts.
    Returns dictionary: {column_name: ColumnMapping}
    """
    df = read_dataframe(dataset.storage_path, sample_rows=1000)
    
    dataset_context = {
        "dataset_name": dataset.name,
        "modality": dataset.modality.value,
        "domain": dataset.domain.value if dataset.domain else "general",
        "total_columns": len(df.columns),
        "total_rows": len(df)
    }
    
    mappings = {}
    
    for col in df.columns:
        # Skip metadata columns
        if col.strip().lower() in ['sheet', 'sheet1', 'sheet2', 'index', 'unnamed']:
            continue
        
        column_data = df[col]
        
        # Skip if all null
        if column_data.isna().sum() == len(column_data):
            continue
        
        mapping = create_column_mapping(col, column_data, use_llm=use_llm, dataset_context=dataset_context)
        mappings[col] = mapping
    
    return mappings








