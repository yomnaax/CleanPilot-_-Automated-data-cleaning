from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os

from ..db.base import get_db
from ..db import models
from ..services import apply_engine, rule_store


class ApplyRequest(BaseModel):
    rule_ids: list[int]
    preview: bool = True
    reference_dataset_id: int | None = None
    apply_general_preprocessing: bool = False


class ApplyResponse(BaseModel):
    run_id: int
    preview_path: str | None
    output_path: str | None
    summary: dict
    changes: list[dict] = []
    before_sample: dict | None = None
    after_sample: dict | None = None


router = APIRouter()


@router.post("/{dataset_id}", response_model=ApplyResponse)
def apply_rules(
    dataset_id: int,
    body: ApplyRequest,
    db: Session = Depends(get_db)
):
    dataset = db.get(models.Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    rules = []
    if body.rule_ids:
        rules = rule_store.list_rules(db, rule_ids=body.rule_ids)
        if not rules and not body.apply_general_preprocessing:
            raise HTTPException(status_code=400, detail="No rules found")

    run, result = apply_engine.apply_rules(
        db,
        dataset,
        rules,
        preview=body.preview,
        reference_dataset_id=body.reference_dataset_id,
        apply_general_preprocessing=body.apply_general_preprocessing,
    )
    return ApplyResponse(
        run_id=run.id,
        preview_path=result.preview_path,
        output_path=result.output_path,
        summary=result.summary,
        changes=result.changes,
        before_sample=result.before_sample,
        after_sample=result.after_sample,
    )


@router.get("/{dataset_id}/download")
def download_cleaned_dataset(
    dataset_id: int,
    run_id: int,
    db: Session = Depends(get_db)
):
    """Download the cleaned dataset file for a specific run."""
    # Find the run
    run = db.query(models.Run).filter(
        models.Run.id == run_id,
        models.Run.dataset_id == dataset_id
    ).first()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Get output path from run summary
    output_path = run.summary.get("output_path") if run.summary else None

    if not output_path or not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Cleaned file not found. Please apply rules first.")

    filename = os.path.basename(output_path)
    return FileResponse(
        path=output_path,
        filename=filename,
        media_type="text/csv"
    )
