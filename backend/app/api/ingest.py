from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List

from ..db.base import get_db
from ..db import models
from ..services import storage
from ..api.deps import get_current_user
from datetime import datetime


class IngestResponse(BaseModel):
    id: int
    name: str
    purpose: str
    modality: str
    domain: str | None = None
    created_at: str


router = APIRouter()


@router.get("/", response_model=List[IngestResponse])
def list_datasets(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List datasets belonging to the current user."""
    datasets = db.query(models.Dataset).filter(
        models.Dataset.user_id == current_user.id
    ).all()
    return [
        IngestResponse(
            id=d.id,
            name=d.name,
            purpose=d.purpose.value,
            modality=d.modality.value,
            domain=d.domain.value if d.domain else None,
            created_at=d.created_at.isoformat() if d.created_at else "",
        )
        for d in datasets
    ]


@router.post("/", response_model=IngestResponse)
async def ingest_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    purpose: str = Form(...),
    modality: str = Form(...),
    domain: str = Form(default="general"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and register a dataset."""
    try:
        try:
            purpose_enum = models.DatasetPurpose(purpose)
            modality_enum = models.Modality(modality)
            domain_enum = models.Domain(domain) if domain else models.Domain.GENERAL
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid purpose, modality, or domain: {e}")

        storage_path = storage.register_dataset(
            file.filename,
            file.file,
            f"dataset_{datetime.utcnow().timestamp()}"
        )

        dataset = models.Dataset(
            name=name,
            purpose=purpose_enum,
            modality=modality_enum,
            domain=domain_enum,
            storage_path=storage_path,
            user_id=current_user.id,   # ← attach to current user
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)

        return IngestResponse(
            id=dataset.id,
            name=dataset.name,
            purpose=dataset.purpose.value,
            modality=dataset.modality.value,
            domain=dataset.domain.value if dataset.domain else None,
            created_at=dataset.created_at.isoformat() if dataset.created_at else "",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_id}", response_model=IngestResponse)
def get_dataset(
    dataset_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific dataset (must belong to current user)."""
    dataset = db.query(models.Dataset).filter(
        models.Dataset.id == dataset_id,
        models.Dataset.user_id == current_user.id
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return IngestResponse(
        id=dataset.id,
        name=dataset.name,
        purpose=dataset.purpose.value,
        modality=dataset.modality.value,
        domain=dataset.domain.value if dataset.domain else None,
        created_at=dataset.created_at.isoformat() if dataset.created_at else "",
    )


@router.delete("/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a dataset (must belong to current user)."""
    dataset = db.query(models.Dataset).filter(
        models.Dataset.id == dataset_id,
        models.Dataset.user_id == current_user.id
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    rule_ids = [r.id for r in dataset.rules]
    if rule_ids:
        db.query(models.Feedback).filter(
            models.Feedback.rule_id.in_(rule_ids)
        ).delete(synchronize_session='fetch')

    db.query(models.Rule).filter(
        models.Rule.dataset_id == dataset_id
    ).delete(synchronize_session='fetch')

    db.query(models.Run).filter(
        models.Run.dataset_id == dataset_id
    ).delete(synchronize_session='fetch')

    try:
        import os
        if dataset.storage_path and os.path.exists(dataset.storage_path):
            os.remove(dataset.storage_path)
    except Exception:
        pass

    db.delete(dataset)
    db.commit()
    return {"detail": "Dataset deleted"}
