"""
Rule curator service.

This module defines a post‑processing step for extracted rules.  It is
responsible for summarising, filtering, ranking and grouping the raw
rules into a small set of human‑reviewable rules.  It can also apply
simple heuristics to drop trivial or noisy rules (for example,
functional dependencies that simply state that an identifier column
determines every other column, or categorical constraints on numeric
columns).

The curator can optionally call an LLM (e.g. via a local Ollama
instance) to further refine the rule set, but it will gracefully
fall back to heuristics if an LLM is not available or disabled.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy.orm import Session

from ..db import models
from ..utils.io_helpers import read_dataframe
from .llm.client import get_llm_client
from . import rule_store
from ..config import settings


def _get_column_types(df: pd.DataFrame) -> Dict[str, str]:
    """
    Classify each column in a DataFrame as one of 'numeric', 'string',
    'datetime' or 'other'.  This is a helper used to detect when
    categorical rules are incorrectly applied to numeric columns.

    Args:
        df: DataFrame loaded from the dataset.

    Returns:
        Mapping of column name to type.
    """
    col_types: Dict[str, str] = {}
    for col in df.columns:
        series = df[col].dropna()
        if len(series) == 0:
            col_types[col] = 'other'
            continue
        if pd.api.types.is_numeric_dtype(series):
            col_types[col] = 'numeric'
        elif pd.api.types.is_datetime64_any_dtype(series):
            col_types[col] = 'datetime'
        elif pd.api.types.is_string_dtype(series) or series.dtype == 'object':
            col_types[col] = 'string'
        else:
            col_types[col] = 'other'
    return col_types


def _categorize_rule(rule_dict: Dict[str, Any]) -> str:
    """
    Assign a simple category to a rule based on its predicate.  This
    helps group rules for human review.  Categories include
    Identifier, Dependency, Format, Range, Categorical, Missing,
    Outlier, Standardization and Other.

    Args:
        rule_dict: Rule dictionary returned by rule_store.to_dict().

    Returns:
        Category name.
    """
    pred = (rule_dict.get('predicate') or '').lower()
    if pred.startswith('unique('):
        return 'identifier'
    if pred.startswith('fd(') or pred.startswith('soft_fd(') or pred.startswith('cfd('):
        return 'dependency'
    if 'regex_match(' in pred:
        return 'format'
    if ' in [' in pred:
        return 'categorical'
    if '>=' in pred and '<=' in pred:
        return 'range'
    if 'is_null(' in pred or 'missing_rate(' in pred:
        return 'missing'
    if 'outlier' in pred or 'z_score' in pred or 'is_rare_value' in pred:
        return 'outlier'
    if 'case=' in pred or 'standardize_case(' in pred:
        return 'standardization'
    return 'other'


def _parse_fd_predicate(predicate: str) -> Optional[Tuple[str, str]]:
    """
    Parse a functional dependency predicate of the form 'fd(A -> B)'.
    Returns a tuple (determinant, dependent).  If the predicate does
    not match the expected format, returns None.
    """
    m = re.search(r'fd\(([^\)]+)\)', predicate, re.IGNORECASE)
    if not m:
        return None
    content = m.group(1)
    if '->' not in content:
        return None
    left, right = content.split('->', 1)
    return left.strip(), right.strip()


def _looks_like_identifier(column_name: str) -> bool:
    """
    Heuristic to determine if a column name looks like an identifier.
    True if it contains 'id', 'uuid' or 'guid'.
    """
    name = column_name.lower()
    return any(token in name for token in ['id', 'uuid', 'guid'])


def curate_rules(
    db: Session,
    dataset: models.Dataset,
    rules: List[models.Rule],
    use_llm: bool = True
) -> Dict[str, Any]:
    """
    Curate a list of extracted rules for a dataset.

    This function applies heuristics to filter out noisy rules, groups
    the remaining rules by category, assigns a simple rank (higher
    confidence first) and stores curation metadata in the rule's
    targets.  It also deactivates dropped rules in the database.

    If use_llm is True and a local LLM provider is configured, the
    curator will send the rules and dataset summary to the LLM for
    additional deduplication and summarisation.  If the LLM call
    fails, the curator falls back to heuristics only.

    Args:
        db: SQLAlchemy session.
        dataset: Dataset model.
        rules: List of Rule ORM objects associated with the dataset.
        use_llm: Whether to call LLM for summarisation (default True).

    Returns:
        A dict summarising curation results, including groups and
        decisions.  The structure is designed to be serialisable and
        consumable by the API response.
    """
    # Read a small sample of the dataset to infer column types and uniqueness metrics
    try:
        df = read_dataframe(dataset.storage_path, sample_rows=2000)
        col_types = _get_column_types(df)
        # Compute per‑column uniqueness ratio and average group size
        n_rows = len(df) if hasattr(df, '__len__') else 0
        unique_ratio_map: Dict[str, float] = {}
        avg_group_size_map: Dict[str, float] = {}
        if n_rows > 0:
            for col in df.columns:
                # drop NA counts
                uniq = df[col].nunique(dropna=False)
                # Unique ratio: fraction of unique values in column
                unique_ratio_map[col] = (uniq / n_rows) if n_rows else 0.0
                # Average group size: average number of rows per unique value
                avg_group_size_map[col] = (n_rows / uniq) if uniq > 0 else 0.0
        else:
            unique_ratio_map = {}
            avg_group_size_map = {}
    except Exception:
        col_types = {}
        unique_ratio_map = {}
        avg_group_size_map = {}

    total_in = len(rules)
    kept_rules: List[models.Rule] = []
    dropped_rules: List[models.Rule] = []
    decisions: List[Dict[str, Any]] = []
    grouped: Dict[str, List[Dict[str, Any]]] = {}

    # Iterate through rules and apply heuristics
    for rule in rules:
        rule_dict = rule_store.to_dict(rule)
        category = _categorize_rule(rule_dict)
        rule_id = rule.id
        drop_reason: Optional[str] = None

        # 1. Drop trivial functional dependencies of the form id -> *
        if category == 'dependency':
            parsed = _parse_fd_predicate(rule_dict['predicate'])
            if parsed:
                left, _right = parsed
                # If determinant column name contains id-like token, drop
                if _looks_like_identifier(left):
                    drop_reason = f"Trivial functional dependency: {left} determines everything"
                # If determinant has too many unique values, drop
                if drop_reason is None:
                    uniq_ratio = unique_ratio_map.get(left)
                    avg_group = avg_group_size_map.get(left)
                    # Consider near‑unique determinants (>=95% unique) or small group sizes (<2 rows per value)
                    if uniq_ratio is not None and avg_group is not None:
                        if uniq_ratio >= 0.95 or avg_group < 2.0:
                            drop_reason = (
                                f"Near‑unique determinant '{left}' (unique_ratio={uniq_ratio:.2f}, avg_group_size={avg_group:.2f})"
                            )

        # 2. Drop categorical constraints on numeric columns
        if category == 'categorical':
            cols = rule_dict.get('targets', {}).get('columns', [])
            if cols:
                col = cols[0]
                if col_types.get(col) == 'numeric':
                    drop_reason = f"Categorical rule applied to numeric column '{col}'"

        # 2b. Drop generic format rules that provide little value
        if category == 'format' and drop_reason is None:
            # Format rules are from regex_match(...)
            # If the action references 'custom_format', hide the rule
            action = rule_dict.get('action') or ""
            if 'custom_format' in action:
                drop_reason = "Generic custom format rule"
            else:
                # Drop format rules on numeric columns (range rules are better)
                cols = rule_dict.get('targets', {}).get('columns', [])
                if cols:
                    col = cols[0]
                    if col_types.get(col) == 'numeric':
                        drop_reason = f"Format rule applied to numeric column '{col}'"

        # 3. Drop rules with extremely low confidence (<0.1)
        if drop_reason is None and (rule_dict.get('confidence') is not None):
            conf = rule_dict['confidence']
            if conf < 0.1:
                drop_reason = f"Low confidence ({conf:.2f})"

        # If a drop reason was identified, deactivate rule and record decision
        if drop_reason:
            rule.is_active = False
            rule.approved = False
            decisions.append({
                'rule_id': rule_id,
                'decision': 'drop',
                'reason': drop_reason
            })
            dropped_rules.append(rule)
            continue

        # Otherwise, keep the rule
        kept_rules.append(rule)
        # Mark as pending approval if not previously set
        if rule.approved is None:
            rule.approved = None  # explicitly pending
        rule.is_active = True
        # Attach curation metadata
        targets = rule.targets or {}
        # Ensure we have curation sub-dict
        curation = targets.get('curation', {})
        curation['category'] = category
        targets['curation'] = curation
        rule.targets = targets
        # Add to group container for return
        grouped.setdefault(category, []).append(rule_store.to_dict(rule))

    # Sort each group by confidence descending
    for group_name, group_rules in grouped.items():
        group_rules.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        # assign rank
        for idx, r in enumerate(group_rules, start=1):
            r.setdefault('targets', {}).setdefault('curation', {})['rank'] = idx

    # Hard cap: keep a small, human-reviewable set.
    # Even with an LLM, this deterministic cap ensures the UI stays manageable.
    max_per_category = int(os.getenv('CURATION_MAX_PER_CATEGORY', '15'))
    max_total = int(os.getenv('CURATION_MAX_TOTAL', '80'))

    # Build a set of rule IDs to keep active based on caps
    keep_ids: set[int] = set()
    for cat, grp in grouped.items():
        for r in grp[:max_per_category]:
            rid = r.get('id')
            if isinstance(rid, int):
                keep_ids.add(rid)

    # If still too many overall, keep the highest-confidence across all categories
    if len(keep_ids) > max_total:
        flat = []
        for cat, grp in grouped.items():
            flat.extend(grp[:max_per_category])
        flat.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        keep_ids = set([r['id'] for r in flat[:max_total] if isinstance(r.get('id'), int)])

    # Deactivate anything not in keep_ids (but don't mark as rejected; it's just hidden/noisy)
    if keep_ids:
        for rule in kept_rules:
            if rule.id not in keep_ids:
                rule.is_active = False
                # leave approved as None (pending) so user can re-enable if needed
                decisions.append({
                    'rule_id': rule.id,
                    'decision': 'hide',
                    'reason': 'Hidden by curator caps (non-top-ranked)'
                })

        # Rebuild grouped output to only include kept active rules
        grouped = {}
        for rule in kept_rules:
            if rule.is_active:
                rd = rule_store.to_dict(rule)
                cat = (rd.get('targets') or {}).get('curation', {}).get('category') or _categorize_rule(rd)
                grouped.setdefault(cat, []).append(rd)

        for group_name, group_rules in grouped.items():
            group_rules.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            for idx, r in enumerate(group_rules, start=1):
                r.setdefault('targets', {}).setdefault('curation', {})['rank'] = idx

    # Commit DB updates for dropped/kept rules
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    active_kept = sum(1 for r in kept_rules if getattr(r, 'is_active', False))
    summary = {
        'total_in': total_in,
        # total_out == number of active rules returned to UI
        'total_out': active_kept,
        'dropped': len(dropped_rules),
        'hidden': max(0, len(kept_rules) - active_kept),
        'caps': {
            'max_per_category': max_per_category,
            'max_total': max_total,
        },
    }
    result = {
        'summary': summary,
        'groups': grouped,
        'decisions': decisions,
    }

    # Optionally call LLM for further summarisation
    if use_llm and settings.llm_provider == 'ollama':
        try:
            llm = get_llm_client()
            # Build a prompt with a truncated rule list (to avoid exceeding token limits)
            sample_rules = []
            # Take first 100 rule dicts for summarisation
            for group_name, group_rules in grouped.items():
                for rule_dict in group_rules[:100]:
                    sample_rules.append({
                        'id': rule_dict['id'],
                        'predicate': rule_dict['predicate'],
                        'action': rule_dict['action'],
                        'explanation': rule_dict['explanation'],
                        'confidence': rule_dict.get('confidence')
                    })
            profile_summary = {
                'columns': list(col_types.keys()),
                'column_types': col_types,
                'num_rules': len(sample_rules)
            }
            prompt = (
                "You are a data-cleaning rule assistant. Given a dataset profile and a list "
                "of extracted rules, summarise them into a concise set of human-reviewable "
                "groups. Remove duplicates, drop trivial or inconsistent rules, rank the remaining "
                "rules by their importance, and assign them to categories such as identifier, format, "
                "range, categorical, missing, outlier, dependency or standardization. Return JSON "
                "containing a list of groups with their rules and a list of dropped rule IDs with "
                "reasons. If the input rules are already curated, you may simply return them.\n\n"
                f"Dataset profile: {json.dumps(profile_summary)}\n\n"
                f"Rules: {json.dumps(sample_rules)}\n\n"
                "Return your answer strictly as JSON with keys: groups (list) and decisions (list)."
            )
            schema = {
                'groups': [
                    {
                        'category': 'string',
                        'rules': [
                            {
                                'id': 0,
                                'rank': 0,
                                'predicate': 'string',
                                'action': 'string',
                                'explanation': 'string'
                            }
                        ]
                    }
                ],
                'decisions': [
                    {
                        'rule_id': 0,
                        'decision': 'drop',
                        'reason': 'string'
                    }
                ]
            }
            # Invoke LLM for structured JSON output
            llm_output = llm.generate_structured(
                prompt=prompt,
                schema=schema,
                model=settings.OLLAMA_MODEL,
                provider='ollama'
            )
            # Merge LLM decisions into result if available
            if isinstance(llm_output, dict):
                # Append LLM decisions for drop/keep to the existing ones
                if 'decisions' in llm_output:
                    result['decisions'].extend(llm_output['decisions'])
                if 'groups' in llm_output:
                    # Overwrite or append groups from LLM
                    result['groups'] = {g['category']: g['rules'] for g in llm_output.get('groups', [])}
        except Exception:
            # If LLM call fails, continue without modifying result
            pass

    return result