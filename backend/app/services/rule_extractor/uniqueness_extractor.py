"""
Uniqueness Constraint Extractor.

Extracts uniqueness constraints for columns that appear to be unique identifiers.
"""

import pandas as pd
from typing import List, Dict, Any, Tuple
from .base_extractor import BaseExtractor
from ...db import models
import logging

logger = logging.getLogger(__name__)


class UniquenessExtractor(BaseExtractor):
    """
    Extracts uniqueness constraints for columns that are likely identifiers.
    """

    def __init__(
        self,
        min_samples: int = 10,
        min_non_null_ratio: float = 0.9,
        unique_ratio_threshold: float = 0.95,
    ):
        """
        Initialize the uniqueness extractor.

        Reinforcement learning adjusts two key heuristics:

        * **min_non_null_ratio** – the minimum fraction of non‑null values
          required for a column to be considered.  A higher strictness
          score increases this value, making the extractor stricter.
        * **unique_ratio_threshold** – the minimum fraction of distinct
          values to total non‑null values required for a column to be
          considered unique.  By default a column must be at least
          95 % unique; reinforcement learning increases or decreases
          this threshold.  Columns exceeding the threshold but not
          strictly unique (100 %) are still treated as unique.

        Args:
            min_samples: Minimum number of non-null values required (default: 10)
            min_non_null_ratio: Baseline minimum ratio of non-null values (default: 0.9)
            unique_ratio_threshold: Baseline fraction of unique values required (default: 0.95)
        """
        try:
            from ..reinforcement_learning import get_strictness  # type: ignore
            strictness = get_strictness("uniqueness")
        except Exception:
            strictness = 0.0
        # Adjust non-null ratio by ±0.02 per strictness unit
        adj_non_null = min_non_null_ratio + strictness * 0.02
        if adj_non_null < 0.5:
            adj_non_null = 0.5
        if adj_non_null > 0.99:
            adj_non_null = 0.99
        # Adjust unique ratio threshold by ±0.01 per strictness unit
        adj_unique_ratio = unique_ratio_threshold + strictness * 0.01
        if adj_unique_ratio < 0.5:
            adj_unique_ratio = 0.5
        if adj_unique_ratio > 0.995:
            adj_unique_ratio = 0.995
        super().__init__("Uniqueness Constraint Extractor")
        self.min_samples = min_samples
        self.min_non_null_ratio = adj_non_null
        self.unique_ratio_threshold = adj_unique_ratio

    def extract(self, dataset: models.Dataset) -> List[Dict[str, Any]]:
        """
        Extract uniqueness constraints from dataset.

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

            processed_columns = []
            skipped_columns = []

            for col in valid_columns:
                col_data = df[col]

                # Skip if mostly null
                non_null_ratio = 1 - (col_data.isna().sum() / len(col_data))
                if non_null_ratio < self.min_non_null_ratio:
                    skipped_columns.append((col, "mostly_null"))
                    continue

                non_null = col_data.dropna()

                if len(non_null) < effective_min_samples:
                    skipped_columns.append((col, f"insufficient_data({len(non_null)})"))
                    continue

                # Check uniqueness ratio
                unique_count = non_null.nunique(dropna=True)
                total_count = len(non_null)
                if total_count == 0:
                    skipped_columns.append((col, "no_non_null"))
                    continue
                unique_ratio = unique_count / total_count

                # If the column does not meet the uniqueness ratio threshold, skip
                if unique_ratio < self.unique_ratio_threshold:
                    skipped_columns.append(
                        (col, f"unique_ratio_too_low({unique_ratio:.2f}<{self.unique_ratio_threshold:.2f})")
                    )
                    continue

                logger.info(f"{self.name}: Processing column '{col}' for uniqueness extraction")
                processed_columns.append(col)

                # Build rule; confidence proportional to unique_ratio
                predicate = f"unique({col})"
                action = f"enforce_uniqueness({col})"
                explanation = (
                    f"Column '{col}' appears to be a unique identifier "
                    f"({unique_count} unique values out of {total_count} non-null rows; uniqueness ratio = {unique_ratio:.1%})."
                )

                rule = self.format_rule(
                    dataset=dataset,
                    columns=[col],
                    predicate=predicate,
                    action=action,
                    confidence=min(0.99, max(0.5, unique_ratio)),
                    explanation=explanation,
                    rule_type="Uniqueness Constraint",
                )
                rule["targets"]["unique_count"] = unique_count
                rule["targets"]["non_null_count"] = total_count
                rule["targets"]["non_null_ratio"] = non_null_ratio
                rule["targets"]["unique_ratio"] = unique_ratio

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


# Factory function for backward compatibility
def extract(dataset: models.Dataset) -> List[Dict[str, Any]]:
    """
    Extract uniqueness constraint rules from dataset.
    """
    extractor = UniquenessExtractor()
    return extractor.extract(dataset)

