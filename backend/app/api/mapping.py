"""
API endpoints for column mapping to canonical concepts.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from ..db.base import get_db
from ..db import models
from ..services import column_mapper


class MappingResponse(BaseModel):
    column_name: str
    canonical_concept: Optional[str]
    confidence: float
    explanation: str
    evidence: list
    alternatives: list
    # Whether the mapping has been approved by a user.  None means pending, True approved, False rejected
    approved: Optional[bool] = None


class DatasetMappingsResponse(BaseModel):
    dataset_id: int
    mappings: Dict[str, MappingResponse]


router = APIRouter()


@router.post("/{dataset_id}", response_model=DatasetMappingsResponse)
def map_dataset_columns(
    dataset_id: int,
    use_llm: bool = True,
    db: Session = Depends(get_db)
):
    """
    Map all columns in a dataset to canonical financial concepts.
    """
    dataset = db.get(models.Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    try:
        # Perform mapping
        column_mappings = column_mapper.map_dataset_columns(dataset, use_llm=use_llm)
        
        # Convert to response format
        mappings_dict = {}
        mappings_json = {}
        for col_name, mapping in column_mappings.items():
            # Create response with approved set to None by default
            mappings_dict[col_name] = MappingResponse(
                column_name=mapping.column_name,
                canonical_concept=mapping.canonical_concept,
                confidence=mapping.confidence,
                explanation=mapping.explanation,
                evidence=mapping.evidence,
                alternatives=mapping.alternatives,
                approved=None
            )
            mappings_json[col_name] = {
                "canonical_concept": mapping.canonical_concept,
                "confidence": mapping.confidence,
                "explanation": mapping.explanation,
                "evidence": mapping.evidence,
                "alternatives": mapping.alternatives,
                "approved": None
            }
        
        # Store mappings in dataset
        dataset.column_mappings = mappings_json
        db.commit()

        return DatasetMappingsResponse(
            dataset_id=dataset.id,
            mappings=mappings_dict
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to map columns: {str(e)}")


@router.get("/{dataset_id}", response_model=DatasetMappingsResponse)
def get_dataset_mappings(
    dataset_id: int,
    db: Session = Depends(get_db)
):
    """Get stored column mappings for a dataset."""
    dataset = db.get(models.Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # If no mappings present, return empty result instead of 404
    if not dataset.column_mappings:
        return DatasetMappingsResponse(
            dataset_id=dataset.id,
            mappings={}
        )

    # Convert stored JSON to response format
    mappings_dict = {}
    for col_name, mapping_data in dataset.column_mappings.items():
        mappings_dict[col_name] = MappingResponse(
            column_name=col_name,
            canonical_concept=mapping_data.get("canonical_concept"),
            confidence=mapping_data.get("confidence", 0.0),
            explanation=mapping_data.get("explanation", ""),
            evidence=mapping_data.get("evidence", []),
            alternatives=mapping_data.get("alternatives", []),
            approved=mapping_data.get("approved")
        )

    return DatasetMappingsResponse(
        dataset_id=dataset.id,
        mappings=mappings_dict
    )


@router.patch("/{dataset_id}/{column_name}", response_model=MappingResponse)
def update_column_mapping(
    dataset_id: int,
    column_name: str,
    updates: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update a specific column's mapping. Accepts canonical_concept (str|None) and approved (bool|None)."""
    dataset = db.get(models.Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    # Ensure mappings exists
    column_mappings = dataset.column_mappings or {}
    if column_name not in column_mappings:
        # If unknown mapping, create new entry
        column_mappings[column_name] = {
            "canonical_concept": None,
            "confidence": 0.0,
            "explanation": "",
            "evidence": [],
            "alternatives": [],
            "approved": None
        }
    mapping_data = column_mappings[column_name]
    # Apply updates
    if 'canonical_concept' in updates:
        mapping_data['canonical_concept'] = updates['canonical_concept']
    if 'confidence' in updates:
        # Accept manual confidence update
        mapping_data['confidence'] = updates['confidence']
    if 'explanation' in updates:
        mapping_data['explanation'] = updates['explanation']
    if 'evidence' in updates:
        mapping_data['evidence'] = updates['evidence']
    if 'alternatives' in updates:
        mapping_data['alternatives'] = updates['alternatives']
    if 'approved' in updates:
        mapping_data['approved'] = updates['approved']
    # Save back
    column_mappings[column_name] = mapping_data
    dataset.column_mappings = column_mappings
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update mapping: {str(e)}")
    # Return updated mapping
    return MappingResponse(
        column_name=column_name,
        canonical_concept=mapping_data.get("canonical_concept"),
        confidence=mapping_data.get("confidence", 0.0),
        explanation=mapping_data.get("explanation", ""),
        evidence=mapping_data.get("evidence", []),
        alternatives=mapping_data.get("alternatives", []),
        approved=mapping_data.get("approved")
    )








