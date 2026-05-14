from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.base import get_db
from ..db import models
from ..services import validator, rule_store


class ValidateRequest(BaseModel):
    dataset_id: int
    rule_ids: list[int] | None = None


class ValidateResponse(BaseModel):
    dataset_id: int
    violations: list[dict]


router = APIRouter()


@router.post("/", response_model=ValidateResponse)
def validate_dataset(body: ValidateRequest, db: Session = Depends(get_db)):
    dataset = db.get(models.Dataset, body.dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    rules = rule_store.list_rules(db, dataset_id=dataset.id, rule_ids=body.rule_ids)
    violations = validator.validate(dataset, rules)
    return ValidateResponse(dataset_id=dataset.id, violations=violations)

