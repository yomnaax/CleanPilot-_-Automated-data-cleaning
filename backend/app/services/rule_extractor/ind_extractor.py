"""
Inclusion Dependency (IND) Extractor.

Extracts inclusion dependencies of the form A ⊆ B
based on set containment across columns within a dataset.
"""

from typing import List, Dict, Any
import pandas as pd
from .base_extractor import BaseExtractor
from ...db import models
import logging

logger = logging.getLogger(__name__)


class INDExtractor(BaseExtractor):
    """
    Extracts inclusion dependency rules for column pairs.
    """

    def __init__(
        self,
        min_coverage: float = 0.95,
        min_samples: int = 50,
        max_columns: int = 25,
        max_unique_values: int = 5000,
    ):
        """
        Initialize IND extractor.

        Args:
            min_coverage: Minimum coverage ratio to accept IND (default: 0.95)
            min_samples: Minimum non-null values required (default: 50)
            max_columns: Max number of columns to consider (default: 25)
            max_unique_values: Skip columns with too many unique values (default: 5000)
        """
        super().__init__("IND Extractor")
        self.min_coverage = min_coverage
        self.min_samples = min_samples
        self.max_columns = max_columns
        self.max_unique_values = max_unique_values

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
            processed_pairs = []
            skipped_pairs = []

            # Precompute value sets for each column
            value_sets: dict[str, set] = {}
            value_counts: dict[str, int] = {}
            for col in candidate_columns:
                series = df[col].dropna()
                if len(series) < effective_min_samples:
                    skipped_pairs.append((col, "insufficient_data"))
                    continue
                unique_values = set(series.astype(str).unique())
                if len(unique_values) > self.max_unique_values:
                    skipped_pairs.append((col, f"too_many_unique({len(unique_values)})"))
                    continue
                value_sets[col] = unique_values
                value_counts[col] = len(series)

            columns_with_sets = list(value_sets.keys())
            for referencing in columns_with_sets:
                for referenced in columns_with_sets:
                    if referencing == referenced:
                        continue

                    referencing_set = value_sets[referencing]
                    referenced_set = value_sets[referenced]

                    if not referencing_set or not referenced_set:
                        skipped_pairs.append((f"{referencing}->{referenced}", "empty_set"))
                        continue

                    # Coverage: fraction of referencing values contained in referenced values
                    overlap = referencing_set.intersection(referenced_set)
                    coverage = len(overlap) / len(referencing_set)

                    if coverage < self.min_coverage:
                        skipped_pairs.append((f"{referencing}->{referenced}", f"low_coverage({coverage:.3f})"))
                        continue

                    rule = self._build_rule(dataset, referencing, referenced, coverage)
                    rules.append(rule)
                    processed_pairs.append((referencing, referenced))

            self.log_extraction(len(rules), dataset.id)
            if processed_pairs:
                logger.info(f"{self.name}: Processed pairs: {processed_pairs[:10]}")
            if skipped_pairs:
                logger.info(f"{self.name}: Skipped pairs: {skipped_pairs[:10]}")

        except Exception as e:
            logger.error(f"{self.name}: Error extracting INDs for dataset {dataset.id}: {e}", exc_info=True)
            raise

        return rules

    def _build_rule(
        self,
        dataset: models.Dataset,
        referencing: str,
        referenced: str,
        coverage: float
    ) -> Dict[str, Any]:
        predicate = f"ind({referencing} subset_of {referenced})"
        action = f"enforce_inclusion({referencing}, {referenced})"
        explanation = (
            f"Column '{referencing}' values are mostly included in '{referenced}' "
            f"({coverage:.1%} coverage)."
        )

        rule = self.format_rule(
            dataset=dataset,
            columns=[referencing, referenced],
            predicate=predicate,
            action=action,
            confidence=min(0.95, coverage),
            explanation=explanation,
            rule_type="Inclusion Dependency (IND)",
            referencing_column=referencing,
            referenced_column=referenced,
            compliance=coverage * 100,
        )
        return rule


def extract(dataset: models.Dataset) -> List[Dict[str, Any]]:
    extractor = INDExtractor()
    return extractor.extract(dataset)

