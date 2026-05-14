"""
I/O utilities for reading/writing various data formats.
"""

import json
import csv
from pathlib import Path
from typing import Any
import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa


def detect_format(file_path: str) -> str:
    """Detect file format from extension."""
    ext = Path(file_path).suffix.lower()
    if ext == '.csv':
        return 'csv'
    elif ext in ['.json', '.jsonl']:
        return 'json'
    elif ext == '.parquet':
        return 'parquet'
    elif ext in ['.xlsx', '.xls']:
        return 'excel'
    elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
        return 'image'
    elif ext in ['.mp3', '.wav', '.flac', '.ogg']:
        return 'audio'
    else:
        return 'unknown'


def read_dataframe(file_path: str, sample_rows: int | None = None) -> pd.DataFrame:
    """Read tabular data into pandas DataFrame."""
    format_type = detect_format(file_path)
    
    if format_type == 'csv':
        try:
            df = pd.read_csv(file_path, low_memory=False)
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, low_memory=False, encoding='latin-1')
        # Fix semicolon-separated files detected as single column
        if len(df.columns) == 1 and ';' in str(df.columns[0]):
            try:
                df = pd.read_csv(file_path, sep=';', low_memory=False)
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, sep=';', low_memory=False, encoding='latin-1')
    elif format_type == 'json':
        try:
            df = pd.read_json(file_path, orient='records')
        except:
            # Try JSONL
            df = pd.read_json(file_path, lines=True)
    elif format_type == 'parquet':
        df = pd.read_parquet(file_path)
    elif format_type == 'excel':
        # For Excel files, read only the first sheet and skip metadata columns
        df = pd.read_excel(file_path, sheet_name=0)  # Read first sheet only
    else:
        raise ValueError(f"Unsupported format: {format_type}")
    
    # Clean up: Remove common metadata columns that shouldn't be treated as data
    metadata_columns = ['Sheet', 'Sheet1', 'Sheet2', 'Sheet3', 'Index', 'Unnamed: 0']
    for col in metadata_columns:
        if col in df.columns:
            # Only remove if it looks like metadata (all values are sheet names or indices)
            if col == 'Sheet' or col.startswith('Sheet'):
                # Check if values look like sheet names
                unique_vals = df[col].dropna().unique()
                if len(unique_vals) <= 10:  # Likely metadata if few unique values
                    df = df.drop(columns=[col])
            else:
                df = df.drop(columns=[col])
    
    if sample_rows and len(df) > sample_rows:
        return df.sample(n=sample_rows, random_state=42).reset_index(drop=True)
    return df


def write_dataframe(df: pd.DataFrame, file_path: str, format_type: str | None = None):
    """Write DataFrame to file."""
    if format_type is None:
        format_type = detect_format(file_path)
    
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    if format_type == 'csv':
        df.to_csv(file_path, index=False)
    elif format_type == 'json':
        df.to_json(file_path, orient='records', indent=2)
    elif format_type == 'parquet':
        df.to_parquet(file_path, index=False)
    elif format_type == 'excel':
        df.to_excel(file_path, index=False)
    else:
        raise ValueError(f"Unsupported format: {format_type}")


def read_json(path: str) -> Any:
    """Read JSON file."""
    return json.loads(Path(path).read_text())


def write_json(path: str, data: Any):
    """Write JSON file."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2))


def get_file_size(file_path: str) -> int:
    """Get file size in bytes."""
    return Path(file_path).stat().st_size


def get_row_count(file_path: str) -> int:
    """Get approximate row count for tabular data."""
    try:
        df = read_dataframe(file_path, sample_rows=1000)
        return len(df)
    except:
        return 0
