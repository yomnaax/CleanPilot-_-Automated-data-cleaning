from fastapi import APIRouter
from ..db.base import SessionLocal
from ..db import models
from ..config import settings

router = APIRouter()


@router.get("/live")
def live():
    return {"status": "ok"}


@router.get("/ready")
def ready():
    db = SessionLocal()
    try:
        dataset_count = db.query(models.Dataset).count()
        rule_count = db.query(models.Rule).count()
        run_count = db.query(models.Run).count()
    finally:
        db.close()

    return {
        "status": "ready",
        "database_url": settings.database_url,
        "datasets": dataset_count,
        "rules": rule_count,
        "runs": run_count,
    }

