"""
Statistical profiling and schema detection for datasets.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
from ..utils.io_helpers import read_dataframe, detect_format
from ..db import models


def profile_dataset(dataset, sample_rows: int | None = 1000) -> Dict[str, Any]:
    """Profile dataset and return statistical summary."""
    file_path = dataset.storage_path
    
    # For non-tabular data, return basic info
    if dataset.modality != models.Modality.TABULAR:
        return {
            "dataset": dataset.name,
            "modality": dataset.modality.value,
            "file_path": file_path,
            "format": detect_format(file_path),
            "summary": {"note": "Non-tabular profiling not yet implemented"},
        }
    
    # Read data
    df = read_dataframe(file_path, sample_rows=sample_rows)
    
    # Basic stats
    total_rows = len(df)
    total_cols = len(df.columns)
    
    # Column-level profiling
    columns = {}
    missing_counts = {}
    type_distribution = {}
    outliers = []
    
    for col in df.columns:
        col_data = df[col]
        
        # Missing values
        missing_count = col_data.isna().sum()
        missing_pct = (missing_count / total_rows) * 100 if total_rows > 0 else 0
        missing_counts[col] = {"count": int(missing_count), "percentage": round(missing_pct, 2)}
        
        # Data type
        dtype = str(col_data.dtype)
        type_distribution[col] = dtype
        
        # Column statistics
        col_info = {
            "dtype": dtype,
            "missing_count": int(missing_count),
            "missing_percentage": round(missing_pct, 2),
            "unique_count": int(col_data.nunique()),
            "null_count": int(col_data.isnull().sum()),
        }
        
        # Numeric statistics
        if pd.api.types.is_numeric_dtype(col_data):
            col_info.update({
                "mean": float(col_data.mean()) if not col_data.isna().all() else None,
                "std": float(col_data.std()) if not col_data.isna().all() else None,
                "min": float(col_data.min()) if not col_data.isna().all() else None,
                "max": float(col_data.max()) if not col_data.isna().all() else None,
                "median": float(col_data.median()) if not col_data.isna().all() else None,
                "q25": float(col_data.quantile(0.25)) if not col_data.isna().all() else None,
                "q75": float(col_data.quantile(0.75)) if not col_data.isna().all() else None,
            })
            
            # Detect outliers using IQR method
            Q1 = col_data.quantile(0.25)
            Q3 = col_data.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            outlier_mask = (col_data < lower_bound) | (col_data > upper_bound)
            outlier_count = outlier_mask.sum()
            
            if outlier_count > 0:
                outliers.append({
                    "column": col,
                    "count": int(outlier_count),
                    "method": "IQR",
                    "bounds": {"lower": float(lower_bound), "upper": float(upper_bound)},
                })
        
        # String statistics
        elif pd.api.types.is_string_dtype(col_data) or col_data.dtype == 'object':
            col_info.update({
                "min_length": int(col_data.astype(str).str.len().min()) if not col_data.isna().all() else None,
                "max_length": int(col_data.astype(str).str.len().max()) if not col_data.isna().all() else None,
                "avg_length": float(col_data.astype(str).str.len().mean()) if not col_data.isna().all() else None,
            })
            
            # Most frequent values
            value_counts = col_data.value_counts().head(5)
            col_info["top_values"] = {str(k): int(v) for k, v in value_counts.items()}
        
        columns[col] = col_info
    
    # Detect potential primary keys
    potential_keys = []
    for col in df.columns:
        if df[col].nunique() == len(df) and df[col].notna().all():
            potential_keys.append(col)
    
    # Detect potential duplicates
    duplicate_count = df.duplicated().sum()
    
    return {
        "dataset": dataset.name,
        "modality": dataset.modality.value,
        "file_path": file_path,
        "format": detect_format(file_path),
        "summary": {
            "total_rows": total_rows,
            "total_columns": total_cols,
            "missing_counts": missing_counts,
            "type_distribution": type_distribution,
            "outliers": outliers,
            "potential_keys": potential_keys,
            "duplicate_rows": int(duplicate_count),
        },
        "columns": columns,
        "sample_rows": sample_rows if sample_rows else total_rows,
    }
