from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.base import get_db
from ..db import models
from ..services import profiler


class ProfileRequest(BaseModel):
    dataset_id: int
    sample_rows: int | None = 100


class ProfileResponse(BaseModel):
    dataset_id: int
    dataset: str
    modality: str
    file_path: str
    format: str
    summary: dict
    columns: dict
    sample_rows: int


router = APIRouter()


@router.post("/{dataset_id}", response_model=ProfileResponse)
def profile_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """Profile a dataset."""
    dataset = db.get(models.Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    try:
        profile_data = profiler.profile_dataset(dataset, sample_rows=1000)

        # Record a profiling run so the UI can determine that profiling was done.
        run = models.Run(
            dataset_id=dataset.id,
            run_type=models.RunType.PROFILING,
            status=models.RunStatus.COMPLETED,
            summary={
                "summary": profile_data.get("summary", {}),
                "sample_rows": profile_data.get("sample_rows", 0),
            },
        )
        db.add(run)
        db.commit()

        return ProfileResponse(
            dataset_id=dataset.id,
            dataset=profile_data.get("dataset", ""),
            modality=profile_data.get("modality", ""),
            file_path=profile_data.get("file_path", ""),
            format=profile_data.get("format", ""),
            summary=profile_data.get("summary", {}),
            columns=profile_data.get("columns", {}),
            sample_rows=profile_data.get("sample_rows", 0),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to profile dataset: {str(e)}")

