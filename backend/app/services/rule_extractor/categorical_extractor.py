"""
Categorical Constraint Extractor.

Extracts IN-set constraints (categorical value constraints) from columns.
Detects columns with a small set of distinct values and creates constraints
that enumerate all valid values.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Set, Tuple
from collections import Counter
from .base_extractor import BaseExtractor
from ...db import models
import logging

logger = logging.getLogger(__name__)


class CategoricalExtractor(BaseExtractor):
    """
    Extracts categorical/IN-set constraint rules from columns.
    
    Detects columns with a small set of distinct values and creates
    constraints that enumerate all valid values.
    """
    
    def __init__(
        self,
        max_unique_values: int = 50,
        min_coverage: float = 0.95,
        min_samples: int = 10,
        stability_threshold: float = 0.9
    ):
        """
        Initialize the categorical extractor.

        Reinforcement learning adjusts the maximum number of unique
        values considered "categorical" and the stability threshold.
        Positive strictness reduces ``max_unique_values`` (making the
        extractor stricter) and increases ``stability_threshold``.

        Args:
            max_unique_values: Baseline maximum unique values to consider categorical (default: 50).
            min_coverage: Minimum percentage of values that must be in the set (default: 0.95).
            min_samples: Minimum number of non-null values required (default: 10).
            stability_threshold: Baseline minimum stability ratio (default: 0.9).
        """
        try:
            from ..reinforcement_learning import get_strictness  # type: ignore
            strictness = get_strictness("categorical")
        except Exception:
            strictness = 0.0
        # Adjust maximum unique values; positive strictness lowers the cap
        # by up to 40%, negative strictness increases it by up to 40%.
        # Ensure at least 5 unique values are allowed.
        factor = 1.0 - 0.2 * strictness
        adj_max = int(max_unique_values * factor)
        if adj_max < 5:
            adj_max = 5
        # Adjust stability_threshold; positive strictness increases the
        # threshold (requiring fewer rare values), negative decreases it.
        adj_stability = stability_threshold + strictness * 0.05
        if adj_stability < 0.5:
            adj_stability = 0.5
        if adj_stability > 0.99:
            adj_stability = 0.99
        super().__init__("Categorical Constraint Extractor")
        self.max_unique_values = adj_max
        self.min_coverage = min_coverage
        self.min_samples = min_samples
        self.stability_threshold = adj_stability
    
    def extract(self, dataset: models.Dataset) -> List[Dict[str, Any]]:
        """
        Extract categorical constraint rules from dataset.
        
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
            
            # Extract categorical constraints from each column
            processed_columns = []
            skipped_columns = []
            
            for col in valid_columns:
                col_data = df[col]
                
                # Skip if mostly null
                null_ratio = col_data.isna().sum() / len(col_data)
                if null_ratio > 0.5:
                    skipped_columns.append((col, "mostly_null"))
                    continue
                
                # Get non-null values
                non_null = col_data.dropna()
                
                if len(non_null) < effective_min_samples:
                    skipped_columns.append((col, f"insufficient_data({len(non_null)})"))
                    continue
                
                # Check if column is categorical
                unique_count = non_null.nunique()
                
                if unique_count > self.max_unique_values:
                    skipped_columns.append((col, f"too_many_unique({unique_count})"))
                    continue
                
                # Skip if only 1 unique value (constant column)
                if unique_count == 1:
                    skipped_columns.append((col, "constant_value"))
                    continue
                
                logger.info(f"{self.name}: Processing column '{col}' for categorical extraction (unique values: {unique_count})")
                processed_columns.append(col)
                
                # Extract categorical constraints
                categorical_rules = self._extract_categorical_from_column(non_null, col)
                
                # Create rules
                for cat_info in categorical_rules:
                    rule = self.format_rule(
                        dataset=dataset,
                        columns=[col],
                        predicate=cat_info['predicate'],
                        action=cat_info['action'],
                        confidence=cat_info['confidence'],
                        explanation=cat_info['explanation'],
                        rule_type="Categorical Constraint",
                    )
                    # Add categorical metadata
                    rule["targets"]["valid_values"] = cat_info['valid_values']
                    rule["targets"]["value_count"] = len(cat_info['valid_values'])
                    rule["targets"]["coverage"] = cat_info.get('coverage', 1.0)
                    
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
    
    def _extract_categorical_from_column(
        self,
        series: pd.Series,
        column_name: str
    ) -> List[Dict[str, Any]]:
        """
        Extract categorical constraints from a column.
        
        Args:
            series: Series of non-null values
            column_name: Name of the column
            
        Returns:
            List of categorical constraint dictionaries
        """
        rules = []
        
        if len(series) == 0:
            return rules
        
        # Get unique values and their counts
        value_counts = series.value_counts()
        unique_values = value_counts.index.tolist()
        total_count = len(series)
        
        # Calculate coverage (percentage of values that are in the top N values)
        # For categorical columns, we want high coverage (most values should be in the set)
        coverage = 1.0  # All values are in the unique set
        
        # Check if values are stable (not too many rare values)
        # A categorical column should have most values concentrated in the valid set
        rare_threshold = max(1, int(total_count * 0.01))  # Values appearing < 1% are rare
        rare_values = value_counts[value_counts < rare_threshold]
        rare_ratio = rare_values.sum() / total_count if len(rare_values) > 0 else 0
        
        # If too many rare values, the column might not be truly categorical
        if rare_ratio > (1 - self.stability_threshold):
            logger.debug(f"Column '{column_name}' has too many rare values ({rare_ratio:.1%}), skipping")
            return rules
        
        # Convert values to strings for consistency (handles mixed types)
        valid_values_str = [str(v) for v in unique_values]
        
        # Sort values for consistent output
        valid_values_str.sort()
        
        # Build predicate and action
        # Format: column IN ['value1', 'value2', ...]
        values_list_str = "', '".join(valid_values_str)
        predicate = f"{column_name} IN ['{values_list_str}']"
        action = f"enforce_categories({column_name}, ['{values_list_str}'])"
        
        # Calculate confidence based on:
        # 1. Coverage (how many values are in the set)
        # 2. Stability (how concentrated the values are)
        # 3. Number of values (fewer values = higher confidence for categorical)
        
        # Base confidence from coverage
        base_confidence = min(coverage, 0.95)
        
        # Adjust based on stability
        stability_score = 1.0 - rare_ratio
        stability_adjusted = base_confidence * stability_score
        
        # Adjust based on number of values (fewer = more categorical)
        num_values = len(valid_values_str)
        if num_values <= 5:
            size_bonus = 0.1
        elif num_values <= 10:
            size_bonus = 0.05
        elif num_values <= 20:
            size_bonus = 0.0
        else:
            size_bonus = -0.05
        
        confidence = min(stability_adjusted + size_bonus, 0.95)
        confidence = max(confidence, 0.7)  # Minimum confidence
        
        # Build explanation
        if num_values <= 10:
            values_display = ", ".join(valid_values_str)
            explanation = (
                f"Column '{column_name}' is categorical with {num_values} valid values: {values_display}. "
                f"All values ({coverage:.1%}) fall within this set."
            )
        else:
            top_values = valid_values_str[:5]
            explanation = (
                f"Column '{column_name}' is categorical with {num_values} valid values "
                f"(e.g., {', '.join(top_values)}, ...). "
                f"All values ({coverage:.1%}) fall within this set."
            )
        
        # Add warning if there are rare values
        if rare_ratio > 0.05:
            explanation += f" ⚠️ Note: {rare_ratio:.1%} of values are rare - review carefully."
        
        rules.append({
            "predicate": predicate,
            "action": action,
            "confidence": confidence,
            "explanation": explanation,
            "valid_values": valid_values_str,
            "coverage": coverage,
            "rare_ratio": rare_ratio,
        })
        
        return rules
    
    def _should_extract_categorical(
        self,
        series: pd.Series,
        column_name: str
    ) -> bool:
        """
        Determine if a column should be treated as categorical.
        
        Args:
            series: Series of values
            column_name: Column name
            
        Returns:
            True if column should be treated as categorical
        """
        # Check column name for categorical indicators
        col_lower = column_name.lower()
        categorical_keywords = [
            'status', 'type', 'category', 'class', 'kind', 'state',
            'priority', 'level', 'grade', 'rank', 'role', 'group',
            'code', 'flag', 'indicator', 'mode', 'option'
        ]
        
        if any(kw in col_lower for kw in categorical_keywords):
            return True
        
        # Check data characteristics
        unique_count = series.nunique()
        total_count = len(series)
        
        # High ratio of unique values suggests not categorical
        if unique_count / total_count > 0.5:
            return False
        
        # Low number of unique values suggests categorical
        if unique_count <= self.max_unique_values:
            return True
        
        return False


# Factory function for backward compatibility
def extract(dataset: models.Dataset) -> List[Dict[str, Any]]:
    """
    Extract categorical constraint rules from dataset.
    
    Args:
        dataset: The dataset to extract rules from
        
    Returns:
        List of rule dictionaries
    """
    extractor = CategoricalExtractor()
    return extractor.extract(dataset)

