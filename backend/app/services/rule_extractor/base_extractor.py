"""
Base abstract class for all rule extractors.

This provides a standard interface and common utilities for all extractors.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import pandas as pd
from ...db import models
from ...utils.io_helpers import read_dataframe
import logging

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """
    Abstract base class for all rule extractors.
    
    All extractors should inherit from this class and implement the extract() method.
    """
    
    def __init__(self, name: str):
        """
        Initialize the extractor.
        
        Args:
            name: Human-readable name of the extractor (e.g., "Regex Pattern Extractor")
        """
        self.name = name
    
    @abstractmethod
    def extract(self, dataset: models.Dataset) -> List[Dict[str, Any]]:
        """
        Extract rules from a dataset.
        
        Args:
            dataset: The dataset model to extract rules from
            
        Returns:
            List of rule dictionaries, each containing:
            - source: RuleSource enum
            - modality: Modality enum
            - targets: Dict with columns/fields affected
            - predicate: Machine-readable condition
            - action: Cleaning action to take
            - confidence: Float between 0.0 and 1.0
            - explanation: Human-readable description
        """
        pass
    
    def validate_dataset(self, dataset: models.Dataset) -> bool:
        """
        Validate that the dataset is suitable for extraction.
        
        Args:
            dataset: The dataset to validate
            
        Returns:
            True if dataset is valid, False otherwise
        """
        if dataset.modality != models.Modality.TABULAR:
            logger.debug(f"{self.name}: Skipping non-tabular dataset")
            return False
        return True
    
    def get_valid_columns(self, df: pd.DataFrame) -> List[str]:
        """
        Filter out invalid columns (metadata, empty, etc.).
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            List of valid column names
        """
        valid_columns = []
        
        for col in df.columns:
            # Skip columns that look like metadata
            if col.strip().lower() in ['sheet', 'sheet1', 'sheet2', 'index', 'unnamed']:
                continue
            
            # Skip columns that are all NaN or empty
            if df[col].isna().sum() == len(df):
                continue
            
            # Skip columns with no actual data
            if len(df[col].dropna()) == 0:
                continue
            
            valid_columns.append(col)
        
        return valid_columns

    def _effective_min_samples(
        self,
        total_rows: int,
        configured_min: int,
        min_floor: int = 5,
        ratio: float = 0.2,
    ) -> int:
        """
        Compute a dataset-aware minimum sample size to avoid skipping small datasets.
        """
        if total_rows <= 0:
            return configured_min
        return min(configured_min, max(min_floor, int(total_rows * ratio)))
    
    def format_rule(
        self,
        dataset: models.Dataset,
        columns: List[str],
        predicate: str,
        action: str,
        confidence: float,
        explanation: str,
        **extra_targets
    ) -> Dict[str, Any]:
        """
        Format a rule dictionary with standard structure.
        
        Args:
            dataset: The dataset model
            columns: List of column names affected
            predicate: Machine-readable condition
            action: Cleaning action
            confidence: Confidence score (0.0-1.0)
            explanation: Human-readable description
            **extra_targets: Additional fields to add to targets dict
            
        Returns:
            Formatted rule dictionary
        """
        targets = {"columns": columns}
        targets.update(extra_targets)
        
        return {
            "source": models.RuleSource.EXTRACTED,
            "modality": dataset.modality,
            "targets": targets,
            "predicate": predicate,
            "action": action,
            "confidence": confidence,
            "explanation": explanation,
        }
    
    def load_dataframe(self, dataset: models.Dataset, sample_rows: int = 10000) -> pd.DataFrame:
        """
        Load dataset into a pandas DataFrame.
        
        Args:
            dataset: The dataset model
            sample_rows: Maximum number of rows to load (for performance)
            
        Returns:
            DataFrame containing the dataset
        """
        try:
            df = read_dataframe(dataset.storage_path, sample_rows=sample_rows)
            logger.debug(f"{self.name}: Loaded {len(df)} rows from dataset {dataset.id}")
            return df
        except Exception as e:
            logger.error(f"{self.name}: Failed to load dataset {dataset.id}: {e}")
            raise
    
    def log_extraction(self, rule_count: int, dataset_id: int):
        """
        Log extraction results.
        
        Args:
            rule_count: Number of rules extracted
            dataset_id: ID of the dataset
        """
        logger.info(f"{self.name}: Extracted {rule_count} rules from dataset {dataset_id}")


