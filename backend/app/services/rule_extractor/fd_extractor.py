"""
Functional Dependency (FD) Extractor.

Extracts pairwise functional dependencies of the form A -> B
based on compliance ratio across groups.
"""

from typing import List, Dict, Any, Tuple
import pandas as pd
from .base_extractor import BaseExtractor
from ...db import models
import logging

logger = logging.getLogger(__name__)


class FDExtractor(BaseExtractor):
    """
    Extracts functional dependency rules for column pairs.

    This extractor identifies column pairs where the value of one column
    (the determinant) uniquely determines the value of another column (the
    dependent). To avoid spurious or trivial dependencies, additional
    heuristics are applied:

    * **unique_threshold** controls when a determinant is considered near‑unique
      and therefore uninformative (e.g. Transaction_ID or dates). When the
      ratio of unique values to total rows exceeds this threshold, no FDs
      are emitted for that determinant.
    * **min_avg_group_size** sets the minimum average number of rows per
      determinant value. If too few rows repeat (e.g. every value is
      distinct), the FD is ignored even if compliance is 100%.

    These heuristics reduce noisy FD rules that are mathematically correct
    but add no cleaning value.
    """

    def __init__(
        self,
        min_compliance: float = 0.98,
        min_samples: int = 50,
        max_columns: int = 25,
        unique_threshold: float = 0.90,
        min_avg_group_size: float = 3.0,
    ):
        """
        Initialize FD extractor.

        Reinforcement learning adjusts the unique threshold, minimum
        average group size, and minimum compliance required to accept a
        functional dependency.  Positive strictness increases these
        values (making the extractor stricter), while negative strictness
        decreases them.

        Args:
            min_compliance: Baseline minimum compliance ratio to accept FD (default: 0.98).
            min_samples: Minimum non-null pairs required (default: 50).
            max_columns: Max number of columns to consider (default: 25).
            unique_threshold: Baseline ratio above which a determinant is considered
                near‑unique and will not be used to form FDs (default: 0.90).
            min_avg_group_size: Baseline minimum average group size (rows per unique
                determinant) required to accept an FD (default: 3.0).
        """
        try:
            from ..reinforcement_learning import get_strictness  # type: ignore
            strictness = get_strictness("fd")
        except Exception:
            strictness = 0.0
        # Adjust unique threshold within [0.70, 0.99]
        adj_unique = unique_threshold + strictness * 0.02
        if adj_unique < 0.70:
            adj_unique = 0.70
        if adj_unique > 0.99:
            adj_unique = 0.99
        # Adjust minimum average group size; positive strictness increases by up to 1.0
        adj_group = min_avg_group_size + strictness * 0.5
        if adj_group < 1.0:
            adj_group = 1.0
        # Adjust minimum compliance within [0.90, 0.995]
        adj_comp = min_compliance + strictness * 0.01
        if adj_comp < 0.90:
            adj_comp = 0.90
        if adj_comp > 0.995:
            adj_comp = 0.995
        super().__init__("FD Extractor")
        self.min_compliance = adj_comp
        self.min_samples = min_samples
        self.max_columns = max_columns
        self.unique_threshold = adj_unique
        self.min_avg_group_size = adj_group

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

            # Limit columns to avoid O(n^2) blow-up
            candidate_columns = valid_columns[: self.max_columns]
            effective_min_samples = self._effective_min_samples(len(df), self.min_samples)
            processed_pairs = []
            skipped_pairs = []

            for i, determinant in enumerate(candidate_columns):
                for dependent in candidate_columns:
                    if determinant == dependent:
                        continue

                    # Prepare the pairwise subset, dropping rows with missing values
                    pair_df = df[[determinant, dependent]].dropna()
                    n = len(pair_df)
                    if n < effective_min_samples:
                        skipped_pairs.append((f"{determinant}->{dependent}", "insufficient_data"))
                        continue

                    # Heuristic 1: Skip determinants that are nearly unique
                    # Compute unique ratio for determinant and dependent
                    unique_det = pair_df[determinant].nunique(dropna=False)
                    dependent_unique = pair_df[dependent].nunique(dropna=False)
                    if unique_det > 0:
                        unique_ratio = unique_det / n
                        avg_group_size = n / unique_det
                        dep_unique_ratio = dependent_unique / n if n > 0 else 0.0
                        # Skip if determinant is too unique or groups are too small (e.g. IDs or timestamps)
                        if unique_ratio >= self.unique_threshold or avg_group_size < self.min_avg_group_size:
                            skipped_pairs.append(
                                (
                                    f"{determinant}->{dependent}",
                                    f"near_unique_determinant(unique_ratio={unique_ratio:.2f},avg_group_size={avg_group_size:.2f})",
                                )
                            )
                            continue
                        # Additional heuristic: if determinant is moderately unique (>0.5) and dependent has very few unique values (<10% of rows), skip to avoid spurious mappings like address->gender
                        if unique_ratio > 0.5 and dep_unique_ratio <= 0.1:
                            skipped_pairs.append(
                                (
                                    f"{determinant}->{dependent}",
                                    f"spurious_fd(unique_det_ratio={unique_ratio:.2f},dep_unique_ratio={dep_unique_ratio:.2f})",
                                )
                            )
                            continue
                        # New heuristic: skip FDs where the dependent itself is near-unique (trivial mapping) or both columns are highly unique
                        if dep_unique_ratio >= self.unique_threshold:
                            skipped_pairs.append(
                                (
                                    f"{determinant}->{dependent}",
                                    f"near_unique_dependent(dep_unique_ratio={dep_unique_ratio:.2f})",
                                )
                            )
                            continue

                    # Compute FD compliance
                    compliance = self._compute_compliance(pair_df, determinant, dependent)
                    if compliance < self.min_compliance:
                        skipped_pairs.append(
                            (f"{determinant}->{dependent}", f"low_compliance({compliance:.3f})")
                        )
                        continue

                    # Build and record rule
                    rule = self._build_rule(dataset, determinant, dependent, compliance)
                    rules.append(rule)
                    processed_pairs.append((determinant, dependent))

            self.log_extraction(len(rules), dataset.id)
            if processed_pairs:
                logger.info(f"{self.name}: Processed pairs: {processed_pairs[:10]}")
            if skipped_pairs:
                logger.info(f"{self.name}: Skipped pairs: {skipped_pairs[:10]}")

        except Exception as e:
            logger.error(f"{self.name}: Error extracting FDs for dataset {dataset.id}: {e}", exc_info=True)
            raise

        return rules

    def _compute_compliance(self, df: pd.DataFrame, determinant: str, dependent: str) -> float:
        """
        Compute compliance ratio for FD determinant -> dependent.
        """
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
        predicate = f"fd({determinant} -> {dependent})"
        action = f"enforce_dependency({determinant}, {dependent})"
        explanation = (
            f"Column '{dependent}' appears to be functionally dependent on '{determinant}' "
            f"({compliance:.1%} compliance)."
        )

        rule = self.format_rule(
            dataset=dataset,
            columns=[determinant, dependent],
            predicate=predicate,
            action=action,
            confidence=min(0.95, compliance),
            explanation=explanation,
            rule_type="Functional Dependency (FD)",
            determinant_column=determinant,
            dependent_column=dependent,
            compliance=compliance * 100,
        )
        return rule


def extract(dataset: models.Dataset) -> List[Dict[str, Any]]:
    extractor = FDExtractor()
    return extractor.extract(dataset)

