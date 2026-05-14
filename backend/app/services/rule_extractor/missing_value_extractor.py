"""
Missing Value Pattern Extractor.

Detects columns with significant missingness and recommends handling.
"""

from typing import List, Dict, Any
import pandas as pd
from .base_extractor import BaseExtractor
from ...db import models
import logging

logger = logging.getLogger(__name__)


class MissingValueExtractor(BaseExtractor):
    """
    Extracts missing value pattern rules for columns with nulls.
    """

    def __init__(
        self,
        min_missing_ratio: float = 0.05,
        high_missing_ratio: float = 0.3,
        min_samples: int = 30
    ):
        """
        Initialize missing value extractor.

        Reinforcement learning adjusts the thresholds for flagging missing
        values.  Positive strictness raises both the minimum missing
        ratio and the high missing ratio, making the extractor less
        sensitive.  Negative strictness lowers these thresholds,
        detecting missingness at lower levels.

        Args:
            min_missing_ratio: Baseline minimum missing ratio to flag (default: 5%).
            high_missing_ratio: Baseline high missing ratio to emphasize (default: 30%).
            min_samples: Minimum rows required (default: 30).
        """
        try:
            from ..reinforcement_learning import get_strictness  # type: ignore
            strictness = get_strictness("missing")
        except Exception:
            strictness = 0.0
        # Adjust min_missing_ratio within [0.01, 0.5]
        adj_min = min_missing_ratio + strictness * 0.02
        if adj_min < 0.01:
            adj_min = 0.01
        if adj_min > 0.5:
            adj_min = 0.5
        # Adjust high_missing_ratio within [0.1, 0.9]
        adj_high = high_missing_ratio + strictness * 0.05
        if adj_high < 0.1:
            adj_high = 0.1
        if adj_high > 0.9:
            adj_high = 0.9
        super().__init__("Missing Value Extractor")
        self.min_missing_ratio = adj_min
        self.high_missing_ratio = adj_high
        self.min_samples = min_samples

    def extract(self, dataset: models.Dataset) -> List[Dict[str, Any]]:
        rules: List[Dict[str, Any]] = []

        if not self.validate_dataset(dataset):
            return rules

        try:
            df = self.load_dataframe(dataset, sample_rows=5000)
            valid_columns = self.get_valid_columns(df)
            if not valid_columns:
                logger.warning(f"{self.name}: No valid columns found in dataset {dataset.id}")
                return rules

            effective_min_samples = self._effective_min_samples(len(df), self.min_samples)
            processed = []
            skipped = []

            for col in valid_columns:
                series = df[col]
                total = len(series)
                if total < effective_min_samples:
                    skipped.append((col, f"insufficient_data({total})"))
                    continue

                missing_count = series.isna().sum()
                missing_ratio = missing_count / total
                if missing_ratio < self.min_missing_ratio:
                    skipped.append((col, f"low_missing({missing_ratio:.3f})"))
                    continue

                processed.append(col)
                rule = self._build_rule(dataset, col, missing_ratio, missing_count, total)
                rules.append(rule)

            self.log_extraction(len(rules), dataset.id)
            if processed:
                logger.info(f"{self.name}: Processed columns: {processed[:10]}")
            if skipped:
                logger.info(f"{self.name}: Skipped columns: {skipped[:10]}")

        except Exception as e:
            logger.error(f"{self.name}: Error extracting missing value rules for dataset {dataset.id}: {e}", exc_info=True)
            raise

        return rules

    def _build_rule(
        self,
        dataset: models.Dataset,
        column: str,
        missing_ratio: float,
        missing_count: int,
        total: int
    ) -> Dict[str, Any]:
        predicate = f"is_null({column})"
        action = "impute" if missing_ratio < self.high_missing_ratio else "review_missingness"

        explanation = (
            f"Column '{column}' has {missing_ratio:.1%} missing values "
            f"({missing_count} of {total}). "
        )
        if missing_ratio >= self.high_missing_ratio:
            explanation += "High missingness—consider reviewing or dropping."
        else:
            explanation += "Consider imputation or filling missing values."

        rule = self.format_rule(
            dataset=dataset,
            columns=[column],
            predicate=predicate,
            action=action,
            confidence=0.7 if missing_ratio < self.high_missing_ratio else 0.6,
            explanation=explanation,
            rule_type="Missing Value Rule",
            missing_ratio=missing_ratio,
            missing_count=missing_count,
            total_count=total,
        )
        return rule


def extract(dataset: models.Dataset) -> List[Dict[str, Any]]:
    extractor = MissingValueExtractor()
    return extractor.extract(dataset)


