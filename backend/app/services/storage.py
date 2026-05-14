"""
Storage abstraction for datasets. Supports local filesystem and can be extended to S3/GCS.
"""

import os
import shutil
from pathlib import Path
from typing import BinaryIO
import uuid


STORAGE_ROOT = os.getenv("STORAGE_ROOT", "./data/storage")


def ensure_storage_root():
    """Ensure storage root directory exists."""
    Path(STORAGE_ROOT).mkdir(parents=True, exist_ok=True)


def register_dataset(original_filename: str, file_content, dataset_id: str = None) -> str:
    """Store uploaded dataset and return storage path."""
    ensure_storage_root()
    
    # Generate unique filename
    ext = Path(original_filename).suffix
    if dataset_id is None:
        import uuid
        dataset_id = str(uuid.uuid4())
    storage_filename = f"{dataset_id}{ext}"
    storage_path = os.path.join(STORAGE_ROOT, storage_filename)
    
    # Write file
    with open(storage_path, "wb") as f:
        shutil.copyfileobj(file_content, f)
    
    return storage_path


def get_path(storage_path: str) -> str:
    """Get absolute path to stored file."""
    if os.path.isabs(storage_path):
        return storage_path
    return os.path.abspath(storage_path)


def delete_dataset(storage_path: str):
    """Delete stored dataset."""
    path = get_path(storage_path)
    if os.path.exists(path):
        os.remove(path)


def copy_dataset(source_path: str, target_path: str):
    """Copy dataset to new location."""
    Path(target_path).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)
