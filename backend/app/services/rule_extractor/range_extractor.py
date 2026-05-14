"""
Range Constraint Extractor.

Extracts numeric range constraints (min/max bounds) from columns.
Detects valid value ranges for numeric columns based on data distribution.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from .base_extractor import BaseExtractor
from ...db import models
import logging

logger = logging.getLogger(__name__)


class RangeExtractor(BaseExtractor):
    """
    Extracts range constraint rules for numeric columns.
    
    Detects:
    - Minimum and maximum bounds
    - Non-negative constraints (>= 0)
    - Bounded ranges (min <= value <= max)
    """
    
    def __init__(
        self,
        min_coverage: float = 0.95,
        outlier_threshold: float = 3.0,
        min_samples: int = 10
    ):
        """
        Initialize the range extractor.

        The range extractor adjusts its minimum coverage requirement based on
        reinforcement learning feedback.  Positive strictness increases
        ``min_coverage`` (requiring more values to fall within the
        inferred range), while negative values relax the requirement.
        Outlier threshold and minimum samples remain at sensible
        defaults.

        Args:
            min_coverage: Baseline minimum percentage of values that must be
                within range (default: 0.95 = 95%).
            outlier_threshold: Z-score threshold for outlier detection
                (default: 3.0).
            min_samples: Minimum number of non-null values required
                (default: 10).
        """
        # Apply reinforcement learning adjustments
        try:
            from ..reinforcement_learning import get_strictness  # type: ignore
            strictness = get_strictness("range")
        except Exception:
            strictness = 0.0
        delta = strictness * 0.02
        adj_cov = min_coverage + delta
        # Clamp to [0.80, 0.995]
        if adj_cov < 0.80:
            adj_cov = 0.80
        if adj_cov > 0.995:
            adj_cov = 0.995
        super().__init__("Range Constraint Extractor")
        self.min_coverage = adj_cov
        self.outlier_threshold = outlier_threshold
        self.min_samples = min_samples
    
    def extract(self, dataset: models.Dataset) -> List[Dict[str, Any]]:
        """
        Extract range constraint rules from dataset.
        
        Args:
            dataset: The dataset to extract rules from
            
        Returns:
            List of rule dictionaries
        """
        rules = []
        
        # Validate dataset
        if not self.validate_dataset(dataset):
            return rules
        
        try:
            # Load dataframe
            df = self.load_dataframe(dataset, sample_rows=5000)
            
            # Get valid columns
            valid_columns = self.get_valid_columns(df)
            
            if not valid_columns:
                logger.warning(f"{self.name}: No valid columns found in dataset {dataset.id}")
                return rules

            effective_min_samples = self._effective_min_samples(len(df), self.min_samples)
            
            # Extract ranges from each numeric column
            processed_columns = []
            skipped_columns = []
            
            for col in valid_columns:
                col_data = df[col]
                
                # Skip if mostly null
                null_ratio = col_data.isna().sum() / len(col_data)
                if null_ratio > 0.5:
                    skipped_columns.append((col, "mostly_null"))
                    continue
                
                # Try to convert to numeric
                numeric_data = pd.to_numeric(col_data, errors='coerce')
                non_null_numeric = numeric_data.dropna()

                # Check if column is numeric enough
                if len(non_null_numeric) < effective_min_samples:
                    skipped_columns.append((col, f"insufficient_data({len(non_null_numeric)})"))
                    continue
                numeric_ratio = len(non_null_numeric) / len(col_data.dropna())
                if numeric_ratio < 0.8:  # Less than 80% numeric
                    skipped_columns.append((col, "not_numeric"))
                    continue

                # Heuristic: skip likely identifier columns
                # Compute uniqueness ratio on numeric data
                unique_vals = non_null_numeric.nunique()
                unique_ratio = unique_vals / len(non_null_numeric) if len(non_null_numeric) > 0 else 1.0
                col_lower = col.strip().lower()
                id_keywords = ['id', 'identifier', 'code', 'number', 'serial', 'index']
                if (
                    unique_ratio >= 0.9 and len(non_null_numeric) >= 20 and
                    any(kw in col_lower for kw in id_keywords)
                ):
                    skipped_columns.append((col, f"likely_identifier(unique_ratio={unique_ratio:.2f})"))
                    continue

                logger.info(f"{self.name}: Processing column '{col}' for range extraction")
                processed_columns.append(col)
                
                # Extract range constraints
                range_rules = self._extract_range_from_column(non_null_numeric, col)
                
                # Create rules
                for range_info in range_rules:
                    rule = self.format_rule(
                        dataset=dataset,
                        columns=[col],
                        predicate=range_info['predicate'],
                        action=range_info['action'],
                        confidence=range_info['confidence'],
                        explanation=range_info['explanation'],
                        rule_type="Range Constraint",
                    )
                    # Add range metadata
                    rule["targets"]["min_value"] = range_info.get('min_value')
                    rule["targets"]["max_value"] = range_info.get('max_value')
                    rule["targets"]["coverage"] = range_info.get('coverage', 1.0)
                    
                    rules.append(rule)
            
            # Log results
            logger.info(f"{self.name}: Processed {len(processed_columns)} columns, skipped {len(skipped_columns)} columns")
            logger.info(f"{self.name}: Processed columns: {processed_columns}")
            if skipped_columns:
                logger.info(f"{self.name}: Skipped columns: {[f'{col} ({reason})' for col, reason in skipped_columns[:10]]}")
            self.log_extraction(len(rules), dataset.id)
            
        except Exception as e:
            logger.error(f"{self.name}: Error extracting rules from dataset {dataset.id}: {e}", exc_info=True)
            raise
        
        return rules
    
    def _extract_range_from_column(
        self,
        numeric_series: pd.Series,
        column_name: str
    ) -> List[Dict[str, Any]]:
        """
        Extract range constraints from a numeric column.
        
        Args:
            numeric_series: Series of numeric values
            column_name: Name of the column
            
        Returns:
            List of range constraint dictionaries
        """
        rules = []
        
        if len(numeric_series) == 0:
            return rules
        
        # Calculate statistics
        min_val = float(numeric_series.min())
        max_val = float(numeric_series.max())
        mean_val = float(numeric_series.mean())
        std_val = float(numeric_series.std())
        median_val = float(numeric_series.median())
        
        # Calculate coverage (percentage of values within range)
        total_values = len(numeric_series)
        
        # Strategy 1: Simple min/max range
        if min_val != max_val:
            # Check if range is meaningful (not too wide relative to mean)
            range_width = max_val - min_val
            if mean_val != 0:
                relative_width = range_width / abs(mean_val)
            else:
                relative_width = range_width
            
            # Only extract if range is not too wide (avoid extracting ranges like 0 to 1e10)
            if relative_width < 1000 or range_width < 1e6:
                coverage = 1.0  # All values are within min/max
                
                if coverage >= self.min_coverage:
                    # Determine if we should extract min, max, or both
                    extract_min = self._should_extract_min(min_val, numeric_series, column_name)
                    extract_max = self._should_extract_max(max_val, numeric_series, column_name)
                    
                    if extract_min and extract_max:
                        # Full range constraint
                        predicate = f"{column_name} >= {min_val} AND {column_name} <= {max_val}"
                        action = f"enforce_range({column_name}, {min_val}, {max_val})"
                        explanation = (
                            f"Column '{column_name}' values range from {min_val:.2f} to {max_val:.2f}. "
                            f"All values ({coverage:.1%}) fall within this range."
                        )
                        confidence = 0.9 if coverage >= 0.99 else 0.85
                        
                        rules.append({
                            "predicate": predicate,
                            "action": action,
                            "confidence": confidence,
                            "explanation": explanation,
                            "min_value": min_val,
                            "max_value": max_val,
                            "coverage": coverage,
                        })
                    elif extract_min:
                        # Only minimum constraint
                        predicate = f"{column_name} >= {min_val}"
                        action = f"enforce_min({column_name}, {min_val})"
                        explanation = (
                            f"Column '{column_name}' has a minimum value of {min_val:.2f}. "
                            f"All values ({coverage:.1%}) satisfy this constraint."
                        )
                        confidence = 0.9 if coverage >= 0.99 else 0.85
                        
                        rules.append({
                            "predicate": predicate,
                            "action": action,
                            "confidence": confidence,
                            "explanation": explanation,
                            "min_value": min_val,
                            "coverage": coverage,
                        })
                    elif extract_max:
                        # Only maximum constraint
                        predicate = f"{column_name} <= {max_val}"
                        action = f"enforce_max({column_name}, {max_val})"
                        explanation = (
                            f"Column '{column_name}' has a maximum value of {max_val:.2f}. "
                            f"All values ({coverage:.1%}) satisfy this constraint."
                        )
                        confidence = 0.9 if coverage >= 0.99 else 0.85
                        
                        rules.append({
                            "predicate": predicate,
                            "action": action,
                            "confidence": confidence,
                            "explanation": explanation,
                            "max_value": max_val,
                            "coverage": coverage,
                        })
        
        # Strategy 2: Non-negative constraint (common pattern)
        if min_val >= 0 and len(numeric_series[numeric_series >= 0]) / total_values >= self.min_coverage:
            # Check if this is meaningful (not just because all values happen to be >= 0)
            if min_val == 0 or (min_val > 0 and min_val < 0.1 * mean_val):
                # This is a meaningful non-negative constraint
                predicate = f"{column_name} >= 0"
                action = f"enforce_non_negative({column_name})"
                explanation = (
                    f"Column '{column_name}' contains only non-negative values. "
                    f"This is a common constraint for quantities, prices, scores, etc."
                )
                confidence = 0.85
                
                # Only add if we didn't already add a min constraint
                if not any(r.get('min_value') == 0 for r in rules):
                    rules.append({
                        "predicate": predicate,
                        "action": action,
                        "confidence": confidence,
                        "explanation": explanation,
                        "min_value": 0,
                        "coverage": len(numeric_series[numeric_series >= 0]) / total_values,
                    })
        
        # Strategy 3: Statistical range (using IQR to exclude outliers)
        if std_val > 0 and len(numeric_series) >= 20:
            q1 = float(numeric_series.quantile(0.25))
            q3 = float(numeric_series.quantile(0.75))
            iqr = q3 - q1
            
            # Calculate bounds excluding outliers
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            # Count values within IQR bounds
            within_bounds = ((numeric_series >= lower_bound) & (numeric_series <= upper_bound)).sum()
            coverage = within_bounds / total_values
            
            # Only use statistical range if it's more restrictive than simple min/max
            # and has good coverage
            if (coverage >= self.min_coverage and 
                (lower_bound > min_val or upper_bound < max_val) and
                not any(r.get('min_value') == lower_bound and r.get('max_value') == upper_bound for r in rules)):
                
                predicate = f"{column_name} >= {lower_bound:.2f} AND {column_name} <= {upper_bound:.2f}"
                action = f"enforce_range({column_name}, {lower_bound:.2f}, {upper_bound:.2f})"
                explanation = (
                    f"Column '{column_name}' values typically range from {lower_bound:.2f} to {upper_bound:.2f} "
                    f"(based on IQR method, excluding outliers). {coverage:.1%} of values fall within this range."
                )
                confidence = 0.8 if coverage >= 0.95 else 0.7
                
                rules.append({
                    "predicate": predicate,
                    "action": action,
                    "confidence": confidence,
                    "explanation": explanation,
                    "min_value": lower_bound,
                    "max_value": upper_bound,
                    "coverage": coverage,
                })
        
        return rules
    
    def _should_extract_min(self, min_val: float, series: pd.Series, column_name: str) -> bool:
        """
        Determine if minimum constraint should be extracted.
        
        Args:
            min_val: Minimum value
            series: Numeric series
            column_name: Column name
            
        Returns:
            True if min constraint should be extracted
        """
        # Always extract if min is 0 (non-negative constraint)
        if min_val == 0:
            return True
        
        # Extract if min is significantly above 0 (meaningful lower bound)
        mean_val = series.mean()
        if mean_val > 0:
            if min_val > 0.1 * mean_val:  # Min is at least 10% of mean
                return True
        
        # Extract if column name suggests it should have a minimum
        col_lower = column_name.lower()
        min_keywords = ['age', 'price', 'cost', 'amount', 'quantity', 'count', 'score', 'rating']
        if any(kw in col_lower for kw in min_keywords):
            return True
        
        return False
    
    def _should_extract_max(self, max_val: float, series: pd.Series, column_name: str) -> bool:
        """
        Determine if maximum constraint should be extracted.
        
        Args:
            max_val: Maximum value
            series: Numeric series
            column_name: Column name
            
        Returns:
            True if max constraint should be extracted
        """
        # Extract if max is not too large (avoid extracting max for unbounded columns)
        mean_val = series.mean()
        if mean_val > 0:
            if max_val < 100 * mean_val:  # Max is not more than 100x mean
                return True
        
        # Extract if column name suggests it should have a maximum
        col_lower = column_name.lower()
        max_keywords = ['age', 'score', 'rating', 'percentage', 'percent', 'ratio']
        if any(kw in col_lower for kw in max_keywords):
            return True
        
        return False


# Factory function for backward compatibility
def extract(dataset: models.Dataset) -> List[Dict[str, Any]]:
    """
    Extract range constraint rules from dataset.
    
    Args:
        dataset: The dataset to extract rules from
        
    Returns:
        List of rule dictionaries
    """
    extractor = RangeExtractor()
    return extractor.extract(dataset)

