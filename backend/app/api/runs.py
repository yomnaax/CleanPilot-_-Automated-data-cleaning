from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from ..db.base import get_db
from ..db import models

router = APIRouter()


@router.get("/latest")
def get_latest_run(
    dataset_id: int,
    run_type: str,
    db: Session = Depends(get_db)
) -> dict:
    """
    Retrieve the most recent run of a given type for a dataset.

    This endpoint returns the run metadata and summary for the latest run
    matching the provided dataset_id and run_type.  If no such run
    exists, a 404 is returned.  The run summary may include skip
    reasons recorded by extractors.  If skip reasons are not present,
    an empty dict is returned for skip_reasons.

    Args:
        dataset_id: ID of the dataset
        run_type: Type of run (profiling, rule_extraction, cleaning)
        db: Database session (injected)

    Returns:
        Dict with run information and summary
    """
    # Validate run_type
    try:
        run_type_enum = models.RunType(run_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid run_type: {run_type}")

    # Find the latest run for this dataset and type
    run: Optional[models.Run] = (
        db.query(models.Run)
        .filter(models.Run.dataset_id == dataset_id, models.Run.run_type == run_type_enum)
        .order_by(models.Run.created_at.desc())
        .first()
    )

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    summary = run.summary or {}
    # Ensure skip_reasons key exists so frontend can handle gracefully
    if 'skip_reasons' not in summary:
        summary['skip_reasons'] = {}

    return {
        'run_id': run.id,
        'dataset_id': run.dataset_id,
        'run_type': run.run_type.value,
        'status': run.status.value,
        'created_at': run.created_at.isoformat() if run.created_at else None,
        'completed_at': run.completed_at.isoformat() if run.completed_at else None,
        'summary': summary,
    }