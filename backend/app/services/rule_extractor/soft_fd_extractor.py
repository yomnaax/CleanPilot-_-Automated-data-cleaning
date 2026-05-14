"""
Approximate / Soft Functional Dependency (Soft FD) Extractor.

Extracts pairwise dependencies A -> B that hold with high (but not perfect)
compliance. These are useful for messy, real-world data.
"""

from typing import List, Dict, Any
import pandas as pd
from .base_extractor import BaseExtractor
from ...db import models
import logging

logger = logging.getLogger(__name__)


class SoftFDExtractor(BaseExtractor):
    """
    Extracts approximate functional dependencies for column pairs.
    """

    def __init__(
        self,
        min_compliance: float = 0.85,
        max_compliance: float = 0.95,
        min_samples: int = 50,
        max_columns: int = 25
    ):
        """
        Initialize Soft FD extractor.

        Args:
            min_compliance: Minimum compliance ratio (default: 0.85)
            max_compliance: Upper bound to avoid overlap with strict FDs (default: 0.95)
            min_samples: Minimum non-null pairs required (default: 50)
            max_columns: Max number of columns to consider (default: 25)
        """
        super().__init__("Soft FD Extractor")
        self.min_compliance = min_compliance
        self.max_compliance = max_compliance
        self.min_samples = min_samples
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
            processed_pairs = []
            skipped_pairs = []

            for determinant in candidate_columns:
                for dependent in candidate_columns:
                    if determinant == dependent:
                        continue

                    pair_df = df[[determinant, dependent]].dropna()
                    if len(pair_df) < effective_min_samples:
                        skipped_pairs.append((f"{determinant}->{dependent}", "insufficient_data"))
                        continue

                    compliance = self._compute_compliance(pair_df, determinant, dependent)
                    if compliance < self.min_compliance or compliance >= self.max_compliance:
                        skipped_pairs.append((f"{determinant}->{dependent}", f"compliance_out_of_range({compliance:.3f})"))
                        continue

                    rule = self._build_rule(dataset, determinant, dependent, compliance)
                    rules.append(rule)
                    processed_pairs.append((determinant, dependent))

            self.log_extraction(len(rules), dataset.id)
            if processed_pairs:
                logger.info(f"{self.name}: Processed pairs: {processed_pairs[:10]}")
            if skipped_pairs:
                logger.info(f"{self.name}: Skipped pairs: {skipped_pairs[:10]}")

        except Exception as e:
            logger.error(f"{self.name}: Error extracting soft FDs for dataset {dataset.id}: {e}", exc_info=True)
            raise

        return rules

    def _compute_compliance(self, df: pd.DataFrame, determinant: str, dependent: str) -> float:
        grouped = df.groupby(determinant, dropna=False)[dependent].nunique(dropna=False)
        if grouped.empty:
            return 0.0
        compliant_groups = (grouped <= 1).sum()
        return compliant_groups / len(grouped)

    def _build_rule(
        self,
        dataset: models.Dataset,
        determinant: str,
        dependent: str,
        compliance: float
    ) -> Dict[str, Any]:
        predicate = f"soft_fd({determinant} -> {dependent})"
        action = f"enforce_soft_dependency({determinant}, {dependent})"
        explanation = (
            f"Column '{dependent}' is usually determined by '{determinant}' "
            f"({compliance:.1%} compliance). This is an approximate dependency."
        )

        rule = self.format_rule(
            dataset=dataset,
            columns=[determinant, dependent],
            predicate=predicate,
            action=action,
            confidence=min(0.9, compliance),
            explanation=explanation,
            rule_type="Approximate/Soft FD",
            determinant_column=determinant,
            dependent_column=dependent,
            compliance=compliance * 100,
        )
        return rule


def extract(dataset: models.Dataset) -> List[Dict[str, Any]]:
    extractor = SoftFDExtractor()
    return extractor.extract(dataset)


