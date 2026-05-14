from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.base import get_db
from ..db import models
from ..services import rule_extractor, rule_store, rule_curator
# Lazy import rag to avoid slow startup


class ExtractRequest(BaseModel):
    dataset_id: int | str  # Accept both int and string (frontend sends string)
    include_rag: bool = True
    include_llm: bool = True


class ExtractResponse(BaseModel):
    run_id: int
    # Curated rules.  Either a flat list of rule dicts or a dict of groups.
    rules: list[dict] | dict[str, list[dict]]
    # Optional curation summary with counts
    summary: dict | None = None
    # Optional list of drop/keep decisions
    decisions: list[dict] | None = None


router = APIRouter()


@router.post("/", response_model=ExtractResponse)
def extract_rules(body: ExtractRequest, db: Session = Depends(get_db)):
    """Extract rules from a dataset."""
    # Handle both int and string dataset_id (frontend may send string)
    dataset_id = body.dataset_id
    if isinstance(dataset_id, str):
        try:
            dataset_id = int(dataset_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid dataset_id: {body.dataset_id}")
    
    dataset = db.get(models.Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    try:
        run = rule_extractor.schedule_extraction(db, dataset, include_rag=body.include_rag, include_llm=body.include_llm)
        # Load rules associated with this dataset
        rules = rule_store.list_rules(db, dataset_id=dataset.id)
        # Curate rules using heuristics and optional LLM summarisation
        curation_result = rule_curator.curate_rules(db, dataset, rules, use_llm=True)
        # Flatten groups for rules field: front‑end can group based on targets.curation.category
        flat_rules: list[dict] = []
        for group_rules in curation_result.get('groups', {}).values():
            flat_rules.extend(group_rules)
        return ExtractResponse(
            run_id=run.id,
            rules=flat_rules,
            summary=curation_result.get('summary'),
            decisions=curation_result.get('decisions')
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to extract rules: {str(e)}")

