"""
Validates datasets against rules.
"""

import pandas as pd
from typing import List, Dict, Any
from ..db import models
from ..utils.io_helpers import read_dataframe


def validate(dataset: models.Dataset, rules: List[models.Rule]) -> List[Dict[str, Any]]:
    """Validate dataset against rules and return violations."""
    violations = []
    
    if dataset.modality != models.Modality.TABULAR:
        return violations
    
    df = read_dataframe(dataset.storage_path, sample_rows=10000)
    
    for rule in rules:
        if not rule.is_active:
            continue
        
        # Evaluate predicate
        violations_found = evaluate_rule(df, rule)
        
        if violations_found:
            violations.append({
                "rule_id": rule.id,
                "rule_explanation": rule.explanation,
                "violations": violations_found,
                "violation_count": len(violations_found),
            })
    
    return violations


def evaluate_rule(df: pd.DataFrame, rule: models.Rule) -> List[Dict[str, Any]]:
    """Evaluate a single rule and return violations."""
    violations = []
    columns = rule.targets.get("columns", []) if rule.targets else []
    
    predicate = rule.predicate
    
    # Simple predicate evaluation
    if "unique(" in predicate:
        col = columns[0] if columns else None
        if col and col in df.columns:
            duplicates = df[df[col].duplicated(keep=False)]
            for idx, row in duplicates.iterrows():
                violations.append({
                    "row_index": int(idx),
                    "column": col,
                    "value": str(row[col]),
                    "issue": "Duplicate value violates uniqueness constraint",
                })
    
    elif "is_null(" in predicate:
        col = columns[0] if columns else None
        if col and col in df.columns:
            nulls = df[df[col].isna()]
            for idx, row in nulls.iterrows():
                violations.append({
                    "row_index": int(idx),
                    "column": col,
                    "value": None,
                    "issue": "Null value violates non-null constraint",
                })
    
    elif "regex_match(" in predicate:
        import re
        match = re.search(r"regex_match\(([^,]+),\s*'([^']+)'\)", predicate)
        if match:
            col = match.group(1).strip()
            pattern = match.group(2)
            if col in df.columns:
                invalid = df[~df[col].astype(str).str.match(pattern, na=False)]
                for idx, row in invalid.iterrows():
                    violations.append({
                        "row_index": int(idx),
                        "column": col,
                        "value": str(row[col]),
                        "issue": f"Value does not match pattern: {pattern}",
                    })
    
    elif "IN" in predicate:
        import re
        match = re.search(r"(\w+)\s+IN\s+(\[.+\])", predicate)
        if match:
            col = match.group(1)
            categories = eval(match.group(2))
            if col in df.columns:
                invalid = df[~df[col].isin(categories)]
                for idx, row in invalid.iterrows():
                    violations.append({
                        "row_index": int(idx),
                        "column": col,
                        "value": str(row[col]),
                        "issue": f"Value not in allowed categories: {categories}",
                    })
    
    elif ">=" in predicate and "<=" in predicate:
        import re
        match = re.search(r"(\w+)\s*>=\s*([\d.]+)\s+AND\s+\1\s*<=\s*([\d.]+)", predicate)
        if match:
            col = match.group(1)
            min_val = float(match.group(2))
            max_val = float(match.group(3))
            if col in df.columns:
                invalid = df[(df[col] < min_val) | (df[col] > max_val)]
                for idx, row in invalid.iterrows():
                    violations.append({
                        "row_index": int(idx),
                        "column": col,
                        "value": float(row[col]),
                        "issue": f"Value outside range [{min_val}, {max_val}]",
                    })
    
    return violations
