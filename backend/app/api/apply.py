from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.base import get_db
from ..db import models
from ..services import apply_engine, rule_store


class ApplyRequest(BaseModel):
    rule_ids: list[int]
    preview: bool = True
    # ID of a reference dataset whose rules are being applied.  Optional.
    reference_dataset_id: int | None = None
    # Whether to run general preprocessing (null imputation, whitespace trimming,
    # duplicate removal, case standardization, outlier clipping) before applying rules.
    apply_general_preprocessing: bool = False


class ApplyResponse(BaseModel):
    run_id: int
    preview_path: str | None
    output_path: str | None
    summary: dict
    changes: list[dict] = []
    # Optional samples of data before and after cleaning for UI display
    before_sample: dict | None = None
    after_sample: dict | None = None


router = APIRouter()


@router.post("/{dataset_id}", response_model=ApplyResponse)
def apply_rules(
    dataset_id: int,
    body: ApplyRequest,
    db: Session = Depends(get_db)
):
    """
    Apply rules to a dataset.

    This endpoint now supports optional general preprocessing and rule application
    from a reference dataset.  If `apply_general_preprocessing` is true,
    common data cleaning steps (null imputation, whitespace trimming, duplicate
    removal, case standardization, outlier clipping) are performed before
    applying the selected rules.  If a `reference_dataset_id` is provided,
    accuracy metrics are computed relative to that dataset (when
    implemented).  Unknown rule IDs produce a 400 error.
    """
    dataset = db.get(models.Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Fetch rules by IDs; allow empty list when only general preprocessing is requested
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
