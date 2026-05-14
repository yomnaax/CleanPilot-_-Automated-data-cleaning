"""
Rule application engine that evaluates and applies rules to datasets.
"""

import pandas as pd
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from ..db import models
from ..utils.io_helpers import read_dataframe, write_dataframe, detect_format
from ..services import rule_store
from ..services.column_alignment import align_columns


@dataclass
class ApplyResult:
    preview_path: str | None
    output_path: str | None
    summary: Dict[str, Any]
    changes: List[Dict[str, Any]]
    before_sample: Dict[str, Any] | None = None
    after_sample: Dict[str, Any] | None = None


class RuleEvaluator:
    """Evaluates rules against data."""
    
    @staticmethod
    def evaluate_predicate(df: pd.DataFrame, predicate: str, targets: Dict[str, Any]) -> pd.Series:
        """Evaluate rule predicate and return boolean mask."""
        columns = targets.get("columns", [])
        
        if "unique(" in predicate:
            col = columns[0] if columns else None
            if col:
                return ~df[col].duplicated(keep=False)
        
        elif "is_null(" in predicate or "missing_rate(" in predicate:
            col = columns[0] if columns else None
            if col:
                return df[col].isna()
        
        elif "regex_match(" in predicate:
            # Extract pattern from predicate
            match = re.search(r"regex_match\(([^,]+),\s*'([^']+)'\)", predicate)
            if match:
                col = match.group(1).strip()
                pattern = match.group(2)
                return df[col].astype(str).str.match(pattern, na=False)
        
        elif "IN" in predicate:
            # Categorical constraint
            match = re.search(r"(\w+)\s+IN\s+(\[.+\])", predicate)
            if match:
                col = match.group(1)
                categories = eval(match.group(2))
                return df[col].isin(categories)
        
        elif ">=" in predicate and "<=" in predicate:
            # Range constraint
            match = re.search(r"(\w+)\s*>=\s*([\d.]+)\s+AND\s+\1\s*<=\s*([\d.]+)", predicate)
            if match:
                col = match.group(1)
                min_val = float(match.group(2))
                max_val = float(match.group(3))
                return (df[col] >= min_val) & (df[col] <= max_val)

        elif "range(" in predicate:
            # Canonical range predicate: range(col, min=..., max=...)
            match = re.search(r"range\(([^,]+),\s*min\s*=\s*([\d.\-]+),\s*max\s*=\s*([\d.\-]+)\)", predicate)
            if match:
                col = match.group(1).strip()
                min_val = float(match.group(2))
                max_val = float(match.group(3))
                return (df[col] >= min_val) & (df[col] <= max_val)
        
        # Default: return all True (no filtering)
        return pd.Series([True] * len(df))


class RuleApplier:
    """Applies rule actions to data."""
    
    @staticmethod
    def apply_action(df: pd.DataFrame, action: str, targets: Dict[str, Any]) -> pd.DataFrame:
        """Apply rule action and return modified DataFrame."""
        columns = targets.get("columns", [])
        df = df.copy()
        
        if "enforce_uniqueness(" in action:
            # Remove duplicates, keep first
            col = columns[0] if columns else None
            if col:
                df = df.drop_duplicates(subset=[col], keep='first')
        
        elif "impute(" in action:
            col = columns[0] if columns else None
            if col:
                if pd.api.types.is_numeric_dtype(df[col]):
                    df[col] = df[col].fillna(df[col].median())
                else:
                    df[col] = df[col].fillna(df[col].mode()[0] if len(df[col].mode()) > 0 else "")
        
        elif "trim_whitespace(" in action:
            col = columns[0] if columns else None
            if col:
                df[col] = df[col].astype(str).str.strip()
        
        elif "standardize_case(" in action:
            col = columns[0] if columns else None
            if col:
                match = re.search(r"case='(\w+)'", action)
                case = match.group(1) if match else "lower"
                if case == "lower":
                    df[col] = df[col].astype(str).str.lower()
                elif case == "upper":
                    df[col] = df[col].astype(str).str.upper()
        
        elif "enforce_format(" in action:
            # Validate format, mark invalid as null
            col = columns[0] if columns else None
            if col:
                match = re.search(r"enforce_format\([^,]+,\s*'([^']+)'\)", action)
                if match:
                    pattern_name = match.group(1)
                    # For now, just log - full implementation would validate
                    pass
        
        elif "enforce_range(" in action:
            col = columns[0] if columns else None
            if col:
                match = re.search(r"enforce_range\([^,]+,\s*([\d.]+),\s*([\d.]+)\)", action)
                if match:
                    min_val = float(match.group(1))
                    max_val = float(match.group(2))
                    df.loc[df[col] < min_val, col] = min_val
                    df.loc[df[col] > max_val, col] = max_val
        
        elif "enforce_categories(" in action:
            col = columns[0] if columns else None
            if col:
                match = re.search(r"enforce_categories\([^,]+,\s*(\[.+\])\)", action)
                if match:
                    categories = eval(match.group(1))
                    df.loc[~df[col].isin(categories), col] = None
        
        elif "consider_drop(" in action:
            col = columns[0] if columns else None
            if col:
                # Don't drop automatically, just flag
                pass
        
        return df


def apply_rules(
    db: Session,
    dataset: models.Dataset,
    rules: List[models.Rule],
    preview: bool = True,
    reference_dataset_id: int | None = None,
    apply_general_preprocessing: bool = False,
) -> tuple[models.Run, ApplyResult]:
    """
    Apply rules to dataset.

    The cleaning pipeline now optionally performs general preprocessing and
    computes accuracy metrics relative to a reference dataset.  When
    `apply_general_preprocessing` is true, a suite of basic cleaning
    operations (null imputation, whitespace trimming, duplicate removal,
    case standardization, outlier clipping) are applied before the rule
    transformations.  When `reference_dataset_id` is provided, accuracy
    metrics may be computed by comparing the cleaned data against the
    reference dataset.  The returned ApplyResult includes optional
    before/after samples for UI display.
    """
    run = models.Run(
        dataset_id=dataset.id,
        run_type=models.RunType.CLEANING,
        status=models.RunStatus.RUNNING,
        created_at=datetime.utcnow(),
    )
    db.add(run)
    db.commit()

    try:
        # Read original data
        df_original = read_dataframe(dataset.storage_path)
        df_cleaned = df_original.copy()

        # Capture a small before sample for UI (first 5 rows and up to 10 columns)
        def _make_sample(df: pd.DataFrame, max_rows: int = 5, max_cols: int = 10) -> Dict[str, Any]:
            cols = list(df.columns)[:max_cols]
            rows = df.head(max_rows).to_dict(orient="records")
            return {"columns": cols, "rows": rows}

        before_sample = _make_sample(df_cleaned)

        # If rules originate from a different (reference) dataset or a reference
        # dataset is explicitly specified, align column names.  The
        # reference_dataset_id parameter overrides any implicit reference
        # derived from the rule objects (for back‑compatibility).
        implicit_reference_id = None
        for _r in rules:
            if _r.approved and _r.dataset_id is not None and _r.dataset_id != dataset.id:
                implicit_reference_id = _r.dataset_id
                break
        ref_id = reference_dataset_id if reference_dataset_id is not None else implicit_reference_id

        column_align_map: Dict[str, str] = {}
        if ref_id is not None:
            ref_ds = db.get(models.Dataset, ref_id)
            if ref_ds:
                try:
                    # Collect reference columns used by selected rules
                    ref_cols = set()
                    for r in rules:
                        if not r.approved:
                            continue
                        if r.targets and isinstance(r.targets, dict):
                            for c in (r.targets.get("columns") or []):
                                if isinstance(c, str):
                                    ref_cols.add(c)
                    column_align_map = align_columns(
                        reference_path=ref_ds.storage_path,
                        target_path=dataset.storage_path,
                        reference_columns=sorted(ref_cols),
                        rules_context=[rule_store.to_dict(r) for r in rules if r.approved],
                        use_llm=True,
                    )
                except Exception:
                    column_align_map = {}

        # NOTE: column_align_map already captures reference->target mappings (LLM + heuristics).
        
        changes: List[Dict[str, Any]] = []
        evaluator = RuleEvaluator()
        applier = RuleApplier()

        # ------------------------------------------------------------------
        # General preprocessing
        # ------------------------------------------------------------------
        general_summary: Dict[str, Any] | None = None
        if apply_general_preprocessing:
            # Track counts
            nulls_imputed = 0
            whitespace_trimmed = 0
            duplicates_removed = 0
            case_standardized = 0
            outliers_clipped = 0
            rows_before = int(len(df_cleaned))
            # Duplicate removal at row level
            before_dups = len(df_cleaned)
            df_cleaned = df_cleaned.drop_duplicates(keep='first')
            duplicates_removed = before_dups - len(df_cleaned)
            # For each column perform preprocessing
            for col in df_cleaned.columns:
                series = df_cleaned[col]
                # Trim whitespace and count trimmed entries
                try:
                    if series.dtype == object or pd.api.types.is_string_dtype(series):
                        trimmed = series.astype(str)
                        trimmed_strip = trimmed.str.strip()
                        whitespace_trimmed += int((trimmed != trimmed_strip).sum())
                        series = trimmed_strip
                        # Standardize case to lower
                        standardized = series.str.lower()
                        case_standardized += int((series != standardized).sum())
                        series = standardized
                        df_cleaned[col] = series
                    # Null imputation
                    if series.isna().any():
                        if pd.api.types.is_numeric_dtype(series):
                            median_val = series.median()
                            df_cleaned[col] = series.fillna(median_val)
                            nulls_imputed += int(series.isna().sum())
                        else:
                            mode_vals = series.mode()
                            fill_val = mode_vals.iloc[0] if not mode_vals.empty else ""
                            df_cleaned[col] = series.fillna(fill_val)
                            nulls_imputed += int(series.isna().sum())
                except Exception:
                    # Ignore errors on this column
                    pass
                # Outlier clipping for numeric columns using IQR
                try:
                    if pd.api.types.is_numeric_dtype(df_cleaned[col]):
                        q1 = df_cleaned[col].quantile(0.25)
                        q3 = df_cleaned[col].quantile(0.75)
                        iqr = q3 - q1
                        lower = q1 - 1.5 * iqr
                        upper = q3 + 1.5 * iqr
                        before_clip = df_cleaned[col].copy()
                        df_cleaned.loc[df_cleaned[col] < lower, col] = lower
                        df_cleaned.loc[df_cleaned[col] > upper, col] = upper
                        outliers_clipped += int(((before_clip < lower) | (before_clip > upper)).sum())
                except Exception:
                    pass
            rows_after = int(len(df_cleaned))
            general_summary = {
                "nulls_imputed": nulls_imputed,
                "whitespace_trimmed": whitespace_trimmed,
                "duplicates_removed": duplicates_removed,
                "case_standardized": case_standardized,
                "outliers_clipped": outliers_clipped,
                "rows_before": rows_before,
                "rows_after": rows_after,
            }
        
        # Convert rules from canonical to actual columns if needed
        # Import from sibling module within services to avoid incorrect package resolution
        from .rule_converter import convert_rule_from_canonical
        column_mappings = dataset.column_mappings or {}
        
        def _remap_text(text: str, mapping: Dict[str, str]) -> str:
            """Replace occurrences of reference column tokens with target column tokens."""
            if not text or not mapping:
                return text
            out = text
            # Replace longer names first to avoid partial overlaps
            for src in sorted(mapping.keys(), key=len, reverse=True):
                dst = mapping[src]
                if not dst or src == dst:
                    continue
                # Replace as identifier token (word boundary) and also inside function calls.
                out = re.sub(rf"\b{re.escape(src)}\b", dst, out)
            return out

        # Apply each rule
        for rule in rules:
            if not rule.approved:
                continue

            # Apply semantic alignment if this rule references columns from the reference dataset.
            
            # Convert rule from canonical to actual columns if it uses canonical mapping
            rule_dict = rule_store.to_dict(rule)
            if rule_dict.get("targets", {}).get("canonical_concepts"):
                rule_dict = convert_rule_from_canonical(rule_dict, column_mappings)
                # Update rule object temporarily for evaluation
                rule.predicate = rule_dict["predicate"]
                rule.targets = rule_dict["targets"]

            # Remap reference columns -> target columns (semantic alignment)
            if column_align_map:
                if rule.targets and isinstance(rule.targets, dict) and rule.targets.get("columns"):
                    cols = []
                    for c in rule.targets.get("columns"):
                        if isinstance(c, str) and c in column_align_map:
                            cols.append(column_align_map[c])
                        else:
                            cols.append(c)
                    rule.targets = {**rule.targets, "columns": cols}
                rule.predicate = _remap_text(rule.predicate, column_align_map)
                if rule.action:
                    rule.action = _remap_text(rule.action, column_align_map)
            
            # Evaluate predicate
            violations = ~evaluator.evaluate_predicate(df_cleaned, rule.predicate, rule.targets)
            violation_count = violations.sum()
            
            if violation_count > 0:
                # Apply action
                df_before = df_cleaned.copy()
                df_cleaned = applier.apply_action(df_cleaned, rule.action, rule.targets)
                
                # Track changes
                change_info = {
                    "rule_id": rule.id,
                    "rule_explanation": rule.explanation,
                    "violations_found": int(violation_count),
                    "rows_affected": int(violation_count),
                }
                changes.append(change_info)
        
        # Save results
        format_type = detect_format(dataset.storage_path)
        # Choose a safe output format.  Writing Excel requires optional dependencies
        # such as openpyxl; fallback to CSV if unsupported or unknown.
        safe_format = format_type if format_type in ["csv", "json", "parquet"] else "csv"

        # Capture after sample after all cleaning operations
        after_sample = _make_sample(df_cleaned)

        # Write preview or final cleaned file.  Use safe_format to avoid missing
        # dependencies when writing Excel files.
        if preview:
            preview_ext = safe_format if safe_format != "csv" else "csv"
            preview_path = f"{dataset.storage_path}.preview.{preview_ext}"
            try:
                write_dataframe(df_cleaned, preview_path, safe_format)
            except Exception:
                # Fallback to CSV
                preview_path = f"{dataset.storage_path}.preview.csv"
                write_dataframe(df_cleaned, preview_path, "csv")
            output_path = None
        else:
            output_ext = safe_format if safe_format != "csv" else "csv"
            output_path = f"{dataset.storage_path}.cleaned.{output_ext}"
            try:
                write_dataframe(df_cleaned, output_path, safe_format)
            except Exception:
                output_path = f"{dataset.storage_path}.cleaned.csv"
                write_dataframe(df_cleaned, output_path, "csv")
            preview_path = None
        
        # Update run summary
        summary: Dict[str, Any] = {
            "rules_applied": len([r for r in rules if r.approved]),
            "total_changes": len(changes),
            "rows_affected": sum(c["rows_affected"] for c in changes),
        }
        # Include general preprocessing counts if performed
        if general_summary is not None:
            summary["general_preprocessing"] = general_summary
        # Accuracy metrics placeholder when reference dataset provided
        if reference_dataset_id is not None:
            summary["accuracy_metrics"] = {
                "note": "Accuracy metrics not implemented for this version",
            }

        run.status = models.RunStatus.COMPLETED
        run.completed_at = datetime.utcnow()
        run.summary = summary

        result = ApplyResult(
            preview_path=preview_path,
            output_path=output_path,
            summary=summary,
            changes=changes,
            before_sample=before_sample,
            after_sample=after_sample,
        )
        
        db.commit()
        db.refresh(run)
        
        return run, result
    
    except Exception as e:
        run.status = models.RunStatus.FAILED
        run.summary = {"error": str(e)}
        db.commit()
        raise
