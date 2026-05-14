from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db.base import get_db
from ..services.suggest import suggest_next_actions

router = APIRouter()


@router.get("/{dataset_id}")
def get_suggested_actions(dataset_id: int, db: Session = Depends(get_db)):
    """Get suggested next actions for a dataset."""
    actions = suggest_next_actions(db, dataset_id)
    return {"actions": actions}
