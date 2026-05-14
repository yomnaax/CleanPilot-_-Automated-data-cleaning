"""
ML/Statistical Anomaly Extractor.

Detects:
- Numeric outliers via IQR
- Rare categorical values
"""

from typing import List, Dict, Any, Tuple
import pandas as pd
from .base_extractor import BaseExtractor
from ...db import models
import logging

logger = logging.getLogger(__name__)


class AnomalyExtractor(BaseExtractor):
    """
    Extracts anomaly detection rules (outliers, rare values).
    """

    def __init__(
        self,
        min_samples: int = 30,
        outlier_iqr_multiplier: float = 1.5,
        rare_value_threshold: float = 0.01,
        max_columns: int = 30
    ):
        """
        Initialize anomaly extractor.

        Reinforcement learning adjusts the IQR multiplier and rare value
        threshold.  Positive strictness reduces the IQR multiplier (more
        potential outliers) and increases the rare value threshold
        (labels more values as rare).  Negative strictness does the
        opposite, making the extractor more conservative.

        Args:
            min_samples: Minimum non-null values required (default: 30)
            outlier_iqr_multiplier: Baseline IQR multiplier for outlier bounds (default: 1.5).
            rare_value_threshold: Baseline max frequency for rare values (default: 1%).
            max_columns: Max number of columns to consider (default: 30).
        """
        try:
            from ..reinforcement_learning import get_strictness  # type: ignore
            strictness = get_strictness("anomaly")
        except Exception:
            strictness = 0.0
        # Adjust IQR multiplier: positive strictness decreases multiplier
        adj_iqr = outlier_iqr_multiplier * (1 - 0.1 * strictness)
        if adj_iqr < 0.5:
            adj_iqr = 0.5
        if adj_iqr > 5.0:
            adj_iqr = 5.0
        # Adjust rare value threshold: positive strictness increases threshold
        adj_rare = rare_value_threshold * (1 + 0.5 * strictness)
        if adj_rare < 0.001:
            adj_rare = 0.001
        if adj_rare > 0.05:
            adj_rare = 0.05
        super().__init__("Anomaly Extractor")
        self.min_samples = min_samples
        self.outlier_iqr_multiplier = adj_iqr
        self.rare_value_threshold = adj_rare
        self.max_columns = max_columns

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

            candidate_columns = valid_columns[: self.max_columns]
            effective_min_samples = self._effective_min_samples(len(df), self.min_samples)
            processed = []
            skipped = []

            for col in candidate_columns:
                series = df[col]
                non_null = series.dropna()
                if len(non_null) < effective_min_samples:
                    skipped.append((col, f"insufficient_data({len(non_null)})"))
                    continue

                # Try numeric outlier detection
                numeric_series = pd.to_numeric(series, errors="coerce").dropna()
                numeric_ratio = len(numeric_series) / len(non_null)
                if numeric_ratio >= 0.8 and len(numeric_series) >= effective_min_samples:
                    outlier_rule = self._build_numeric_outlier_rule(dataset, col, numeric_series)
                    if outlier_rule:
                        rules.append(outlier_rule)
                        processed.append((col, "numeric_outlier"))
                    continue

                # Otherwise, try rare categorical values
                cat_rule = self._build_rare_value_rule(dataset, col, non_null)
                if cat_rule:
                    rules.append(cat_rule)
                    processed.append((col, "rare_values"))

            self.log_extraction(len(rules), dataset.id)
            if processed:
                logger.info(f"{self.name}: Processed columns: {processed[:10]}")
            if skipped:
                logger.info(f"{self.name}: Skipped columns: {skipped[:10]}")

        except Exception as e:
            logger.error(f"{self.name}: Error extracting anomalies for dataset {dataset.id}: {e}", exc_info=True)
            raise

        return rules

    def _build_numeric_outlier_rule(
        self,
        dataset: models.Dataset,
        column: str,
        series: pd.Series
    ) -> Dict[str, Any] | None:
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            return None

        lower = q1 - self.outlier_iqr_multiplier * iqr
        upper = q3 + self.outlier_iqr_multiplier * iqr

        # Estimate outlier ratio
        outliers = ((series < lower) | (series > upper)).mean()
        if outliers < 0.01:
            return None

        predicate = f"outlier_iqr({column}, {lower:.2f}, {upper:.2f})"
        action = f"flag_outliers({column}, {lower:.2f}, {upper:.2f})"
        explanation = (
            f"Column '{column}' has potential outliers outside "
            f"[{lower:.2f}, {upper:.2f}] based on IQR (outliers: {outliers:.1%})."
        )

        return self.format_rule(
            dataset=dataset,
            columns=[column],
            predicate=predicate,
            action=action,
            confidence=0.75,
            explanation=explanation,
            rule_type="Anomaly Rule",
            outlier_lower=lower,
            outlier_upper=upper,
            outlier_ratio=outliers,
        )

    def _build_rare_value_rule(
        self,
        dataset: models.Dataset,
        column: str,
        series: pd.Series
    ) -> Dict[str, Any] | None:
        value_counts = series.value_counts(normalize=True)
        rare_values = value_counts[value_counts < self.rare_value_threshold]

        if rare_values.empty:
            return None

        rare_list = rare_values.index.astype(str).tolist()[:20]
        rare_ratio = rare_values.sum()

        predicate = f"rare_values({column})"
        action = f"flag_rare_values({column})"
        explanation = (
            f"Column '{column}' contains rare values (total rare frequency {rare_ratio:.1%}). "
            f"Examples: {', '.join(rare_list[:5])}."
        )

        return self.format_rule(
            dataset=dataset,
            columns=[column],
            predicate=predicate,
            action=action,
            confidence=0.7,
            explanation=explanation,
            rule_type="Anomaly Rule",
            rare_values=rare_list,
            rare_ratio=rare_ratio,
        )


def extract(dataset: models.Dataset) -> List[Dict[str, Any]]:
    extractor = AnomalyExtractor()
    return extractor.extract(dataset)


