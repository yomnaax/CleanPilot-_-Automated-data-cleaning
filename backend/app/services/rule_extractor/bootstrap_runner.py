"""
Coordinates rule extraction pipeline.

Currently supports:
- Regex Pattern Extractor (statistical/pattern-based)
"""

from sqlalchemy.orm import Session
from datetime import datetime
from ...db import models
from .. import rule_store
from .regex_extractor import RegexExtractor
from .range_extractor import RangeExtractor
from .categorical_extractor import CategoricalExtractor
from .uniqueness_extractor import UniquenessExtractor
from .fd_extractor import FDExtractor
# from .ind_extractor import INDExtractor  # disabled
# from .cfd_extractor import CFDExtractor  # disabled
# from .soft_fd_extractor import SoftFDExtractor  # disabled
from .anomaly_extractor import AnomalyExtractor
from .missing_value_extractor import MissingValueExtractor
# from .standardization_extractor import StandardizationExtractor  # disabled
from .high_level_extractor import HighLevelExtractor
from .llm_multi_extractor import LLMMultiExtractor
import logging

logger = logging.getLogger(__name__)


def schedule_extraction(
    db: Session,
    dataset: models.Dataset,
    include_rag: bool = False,
    include_llm: bool = False,
) -> models.Run:
    """
    Schedule and execute rule extraction.
    
    Args:
        db: Database session
        dataset: The dataset to extract rules from
        include_rag: Whether to include RAG-based rules (currently disabled)
        include_llm: Whether to include LLM-based rules (currently disabled)
        
    Returns:
        Run model with extraction results
    """
    run = models.Run(
        dataset_id=dataset.id,
        run_type=models.RunType.RULE_EXTRACTION,
        status=models.RunStatus.RUNNING,
        created_at=datetime.utcnow(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    
    try:
        # For RAG summary later
        rag_rules: list[dict] | None = None
        extracted_rules = []
        
        # 1. Regex Pattern Extraction (always run)
        logger.info(f"Starting regex pattern extraction for dataset {dataset.id}")
        regex_extractor = RegexExtractor()
        regex_rules = regex_extractor.extract(dataset)
        extracted_rules.extend(regex_rules)
        logger.info(f"Extracted {len(regex_rules)} regex pattern rules")
        
        # 2. Range Constraint Extraction (always run)
        logger.info(f"Starting range constraint extraction for dataset {dataset.id}")
        range_extractor = RangeExtractor()
        range_rules = range_extractor.extract(dataset)
        extracted_rules.extend(range_rules)
        logger.info(f"Extracted {len(range_rules)} range constraint rules")
        
        # 3. Categorical Constraint Extraction (always run)
        logger.info(f"Starting categorical constraint extraction for dataset {dataset.id}")
        categorical_extractor = CategoricalExtractor()
        categorical_rules = categorical_extractor.extract(dataset)
        extracted_rules.extend(categorical_rules)
        logger.info(f"Extracted {len(categorical_rules)} categorical constraint rules")

        # 4. Uniqueness Constraint Extraction (always run)
        logger.info(f"Starting uniqueness constraint extraction for dataset {dataset.id}")
        uniqueness_extractor = UniquenessExtractor()
        uniqueness_rules = uniqueness_extractor.extract(dataset)
        extracted_rules.extend(uniqueness_rules)
        logger.info(f"Extracted {len(uniqueness_rules)} uniqueness constraint rules")
        
        # 5. Functional Dependency Extraction (always run)
        logger.info(f"Starting functional dependency extraction for dataset {dataset.id}")
        fd_extractor = FDExtractor()
        fd_rules = fd_extractor.extract(dataset)
        extracted_rules.extend(fd_rules)
        logger.info(f"Extracted {len(fd_rules)} functional dependency rules")

        # 6. Inclusion Dependency Extraction has been disabled.
        logger.info("Inclusion dependency extraction skipped (disabled)")
        ind_rules = []

        # 7. Conditional FD Extraction has been disabled.
        logger.info("Conditional FD extraction skipped (disabled)")
        cfd_rules = []

        # 8. Soft FD Extraction has been disabled.
        logger.info("Soft FD extraction skipped (disabled)")
        soft_fd_rules = []

        # 9. Anomaly Extraction (always run)
        logger.info(f"Starting anomaly extraction for dataset {dataset.id}")
        anomaly_extractor = AnomalyExtractor()
        anomaly_rules = anomaly_extractor.extract(dataset)
        extracted_rules.extend(anomaly_rules)
        logger.info(f"Extracted {len(anomaly_rules)} anomaly rules")

        # 10. Missing Value Extraction (always run)
        logger.info(f"Starting missing value extraction for dataset {dataset.id}")
        missing_extractor = MissingValueExtractor()
        missing_rules = missing_extractor.extract(dataset)
        extracted_rules.extend(missing_rules)
        logger.info(f"Extracted {len(missing_rules)} missing value rules")

        # 11. Standardization Extraction has been disabled.
        logger.info("Standardization extraction skipped (disabled)")
        standardization_rules = []

        # 12. High-level LLM-based rule extraction
        # If include_llm is False, skip high-level and LLM multi extraction
        if include_llm:
            # Always run the high-level extractor to capture arithmetic relations, city/state mappings,
            # conditional fraud probabilities and other semantic patterns.  This step leverages
            # a local LLM via the HighLevelExtractor.  Exceptions are logged but do not break
            try:
                logger.info(f"Starting high-level LLM rule extraction for dataset {dataset.id}")
                hl_extractor = HighLevelExtractor()
                hl_rules = hl_extractor.extract(dataset)
                extracted_rules.extend(hl_rules)
                logger.info(f"Extracted {len(hl_rules)} high-level LLM rules")
            except Exception as e:
                logger.error(f"High-level LLM rule extraction failed: {e}")

            # 13. LLM multi-category extraction (augment categories)
            try:
                logger.info(f"Starting LLM multi-category rule extraction for dataset {dataset.id}")
                multi_extractor = LLMMultiExtractor()
                multi_rules = multi_extractor.extract(dataset)
                extracted_rules.extend(multi_rules)
                logger.info(f"Extracted {len(multi_rules)} multi-category LLM rules")
            except Exception as e:
                logger.error(f"LLM multi-category rule extraction failed: {e}")
        else:
            logger.info("LLM-based rule extraction skipped as include_llm is False")

        # 14. RAG-based semantic rules (optional)
        if include_rag:
            try:
                logger.info(f"Starting RAG semantic rule retrieval for dataset {dataset.id}")
                # Determine modality and domain
                modality = dataset.modality.value if hasattr(dataset.modality, 'value') else str(dataset.modality)
                domain = dataset.domain.value if dataset.domain else 'general'
                # Determine dataset columns (try mapping keys first, else read from file)
                column_names = []
                if dataset.column_mappings:
                    column_names = list(dataset.column_mappings.keys())
                if not column_names:
                    try:
                        from ..utils.io_helpers import read_dataframe
                        df = read_dataframe(dataset.storage_path, sample_rows=1000)
                        column_names = df.columns.tolist()
                    except Exception:
                        column_names = []
                # Retrieve RAG rules
                from ..rag import retrieve_semantic_rules
                rag_rules = retrieve_semantic_rules(
                    modality=modality,
                    domain=domain,
                    dataset_columns=column_names,
                    column_mappings=dataset.column_mappings or {},
                    top_k=15,
                    threshold=0.6,
                )
                extracted_rules.extend(rag_rules)
                logger.info(f"Retrieved {len(rag_rules)} RAG semantic rules")
            except Exception as e:
                logger.error(f"RAG retrieval failed: {e}")
        
        # 4. Store all extracted rules
        logger.info(f"Storing {len(extracted_rules)} total rules")
        for rule_data in extracted_rules:
            try:
                rule_store.add_rule(db, dataset_id=dataset.id, **rule_data)
            except Exception as e:
                logger.error(f"Failed to store rule: {e}")
                # Continue with other rules
        
        # 5. Update run status
        run.status = models.RunStatus.COMPLETED
        run.completed_at = datetime.utcnow()
        # Compose summary with RAG count if available
        summary_dict = {
            "total_rules": len(extracted_rules),
            "regex_rules": len(regex_rules),
            "range_rules": len(range_rules),
            "categorical_rules": len(categorical_rules),
            "uniqueness_rules": len(uniqueness_rules),
            "fd_rules": len(fd_rules),
            # Disabled extractors are omitted from the summary
            "anomaly_rules": len(anomaly_rules),
            "missing_value_rules": len(missing_rules),
        }
        if include_rag and rag_rules is not None:
            summary_dict["rag_rules"] = len(rag_rules)
        run.summary = summary_dict
        
        db.commit()
        db.refresh(run)
        
        logger.info(f"Rule extraction completed for dataset {dataset.id}: {len(extracted_rules)} rules extracted")
        
        return run
    
    except Exception as e:
        logger.error(f"Rule extraction failed for dataset {dataset.id}: {e}", exc_info=True)
        run.status = models.RunStatus.FAILED
        run.summary = {"error": str(e)}
        db.commit()
        raise
