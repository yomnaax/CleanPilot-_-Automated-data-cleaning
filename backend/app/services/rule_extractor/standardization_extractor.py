"""
Standardization Needs Extractor.

Detects columns that need standardization (case, whitespace, punctuation).
"""

from typing import List, Dict, Any
import pandas as pd
from .base_extractor import BaseExtractor
from ...db import models
import logging

logger = logging.getLogger(__name__)


class StandardizationExtractor(BaseExtractor):
    """
    Extracts standardization rules for string columns.
    """

    def __init__(
        self,
        min_samples: int = 30,
        min_change_ratio: float = 0.1
    ):
        """
        Initialize standardization extractor.

        Args:
            min_samples: Minimum non-null values required (default: 30)
            min_change_ratio: Minimum ratio of values that would change if standardized (default: 10%)
        """
        super().__init__("Standardization Extractor")
        self.min_samples = min_samples
        self.min_change_ratio = min_change_ratio

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
                series = df[col].dropna()
                if len(series) < effective_min_samples:
                    skipped.append((col, f"insufficient_data({len(series)})"))
                    continue

                # Only consider string-like columns
                if not self._is_string_like(series):
                    skipped.append((col, "not_string"))
                    continue

                changes = self._analyze_standardization(series.astype(str))
                if not changes:
                    skipped.append((col, "no_standardization_needed"))
                    continue

                change_ratio = changes["change_ratio"]
                if change_ratio < self.min_change_ratio:
                    skipped.append((col, f"low_change_ratio({change_ratio:.2f})"))
                    continue

                rule = self._build_rule(dataset, col, changes)
                rules.append(rule)
                processed.append(col)

            self.log_extraction(len(rules), dataset.id)
            if processed:
                logger.info(f"{self.name}: Processed columns: {processed[:10]}")
            if skipped:
                logger.info(f"{self.name}: Skipped columns: {skipped[:10]}")

        except Exception as e:
            logger.error(f"{self.name}: Error extracting standardization rules for dataset {dataset.id}: {e}", exc_info=True)
            raise

        return rules

    def _is_string_like(self, series: pd.Series) -> bool:
        sample = series.head(50).astype(str)
        # If most values contain letters or whitespace, treat as string-like
        letter_ratio = sample.str.contains(r"[A-Za-z]", regex=True).mean()
        return letter_ratio >= 0.3

    def _analyze_standardization(self, series: pd.Series) -> Dict[str, Any] | None:
        # Standardization operations
        trimmed = series.str.strip()
        lowercased = trimmed.str.lower()

        # Detect whitespace issues
        whitespace_changes = (series != trimmed).mean()
        # Detect case inconsistencies
        case_changes = (trimmed != lowercased).mean()

        # Detect punctuation normalization need (basic)
        punct_removed = lowercased.str.replace(r"[^\w\s]", "", regex=True)
        punct_changes = (lowercased != punct_removed).mean()

        # Overall ratio of values that change under standardization
        standardized = punct_removed
        change_ratio = (series != standardized).mean()

        if change_ratio == 0:
            return None

        return {
            "change_ratio": change_ratio,
            "whitespace_changes": whitespace_changes,
            "case_changes": case_changes,
            "punct_changes": punct_changes,
        }

    def _build_rule(self, dataset: models.Dataset, column: str, changes: Dict[str, Any]) -> Dict[str, Any]:
        predicate = f"needs_standardization({column})"
        action = f"standardize({column})"

        explanation = (
            f"Column '{column}' shows inconsistent formatting "
            f"({changes['change_ratio']:.1%} of values would change with standardization)."
        )

        rule = self.format_rule(
            dataset=dataset,
            columns=[column],
            predicate=predicate,
            action=action,
            confidence=0.7,
            explanation=explanation,
            rule_type="Standardization Rule",
            change_ratio=changes["change_ratio"],
            whitespace_changes=changes["whitespace_changes"],
            case_changes=changes["case_changes"],
            punct_changes=changes["punct_changes"],
        )
        return rule


def extract(dataset: models.Dataset) -> List[Dict[str, Any]]:
    extractor = StandardizationExtractor()
    return extractor.extract(dataset)


