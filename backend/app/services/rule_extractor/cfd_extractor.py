"""
Conditional Functional Dependency (CFD) Extractor.

Extracts rules of the form:
IF condition_column = value THEN dependent_column = constant
"""

from typing import List, Dict, Any
import pandas as pd
from .base_extractor import BaseExtractor
from ...db import models
import logging

logger = logging.getLogger(__name__)


class CFDExtractor(BaseExtractor):
    """
    Extracts conditional functional dependency rules.
    """

    def __init__(
        self,
        min_support: int = 30,
        min_compliance: float = 0.95,
        max_columns: int = 20,
        max_categories: int = 20
    ):
        """
        Initialize CFD extractor.

        Args:
            min_support: Minimum rows for a condition value (default: 30)
            min_compliance: Minimum compliance ratio (default: 0.95)
            max_columns: Max number of columns to consider (default: 20)
            max_categories: Max unique values in condition column (default: 20)
        """
        super().__init__("CFD Extractor")
        self.min_support = min_support
        self.min_compliance = min_compliance
        self.max_columns = max_columns
        self.max_categories = max_categories

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
            effective_min_support = self._effective_min_samples(len(df), self.min_support)
            processed = []
            skipped = []

            # Identify candidate condition columns (categorical-like)
            condition_columns = []
            for col in candidate_columns:
                unique_count = df[col].dropna().nunique()
                if 1 < unique_count <= self.max_categories:
                    condition_columns.append(col)
                else:
                    skipped.append((col, f"not_categorical({unique_count})"))

            for condition_col in condition_columns:
                value_counts = df[condition_col].dropna().value_counts()
                for condition_value, support in value_counts.items():
                    if support < effective_min_support:
                        continue

                    subset = df[df[condition_col] == condition_value]
                    if subset.empty:
                        continue

                    for dependent_col in candidate_columns:
                        if dependent_col == condition_col:
                            continue

                        dep_series = subset[dependent_col].dropna()
                        if len(dep_series) < effective_min_support:
                            continue

                        top_value = dep_series.value_counts().index[0]
                        compliance = (dep_series == top_value).mean()

                        if compliance < self.min_compliance:
                            continue

                        rule = self._build_rule(
                            dataset,
                            condition_col,
                            condition_value,
                            dependent_col,
                            top_value,
                            compliance,
                            support=len(subset)
                        )
                        rules.append(rule)
                        processed.append((condition_col, condition_value, dependent_col))

            self.log_extraction(len(rules), dataset.id)
            if processed:
                logger.info(f"{self.name}: Processed CFDs: {processed[:10]}")
            if skipped:
                logger.info(f"{self.name}: Skipped columns: {skipped[:10]}")

        except Exception as e:
            logger.error(f"{self.name}: Error extracting CFDs for dataset {dataset.id}: {e}", exc_info=True)
            raise

        return rules

    def _format_value(self, value: Any) -> str:
        if isinstance(value, str):
            safe = value.replace("'", "\\'")
            return f"'{safe}'"
        return str(value)

    def _build_rule(
        self,
        dataset: models.Dataset,
        condition_col: str,
        condition_value: Any,
        dependent_col: str,
        dependent_value: Any,
        compliance: float,
        support: int
    ) -> Dict[str, Any]:
        condition_val_str = self._format_value(condition_value)
        dependent_val_str = self._format_value(dependent_value)

        predicate = f"if {condition_col} == {condition_val_str} then {dependent_col} == {dependent_val_str}"
        action = f"enforce_implication({condition_col}, {condition_val_str}, {dependent_col}, {dependent_val_str})"
        explanation = (
            f"When '{condition_col}' is {condition_val_str}, '{dependent_col}' is usually "
            f"{dependent_val_str} ({compliance:.1%} compliance, {support} rows)."
        )

        rule = self.format_rule(
            dataset=dataset,
            columns=[condition_col, dependent_col],
            predicate=predicate,
            action=action,
            confidence=min(0.95, compliance),
            explanation=explanation,
            rule_type="Conditional FD (CFD)",
            determinant_column=condition_col,
            dependent_column=dependent_col,
            compliance=compliance * 100,
            condition_column=condition_col,
            condition_value=condition_value,
        )
        return rule


def extract(dataset: models.Dataset) -> List[Dict[str, Any]]:
    extractor = CFDExtractor()
    return extractor.extract(dataset)


