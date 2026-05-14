"""
RAG retriever for semantic rules using ChromaDB.
"""

# Lazy imports - ChromaDB is heavy, only import when needed
from typing import List, Dict, Any
from ...config import settings
from ...db import models


class RAGRetriever:
    """Retrieves semantic rules from vector database."""
    
    def __init__(self):
        # Lazy initialization - only create client when actually needed
        self._client = None
        self._collection = None
    
    @property
    def client(self):
        """Lazy load ChromaDB client."""
        if self._client is None:
            # Lazy import ChromaDB only when needed
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            self._client = chromadb.PersistentClient(
                path=settings.chroma_db_path,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
        return self._client
    
    @property
    def collection(self):
        """Lazy load ChromaDB collection."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name="semantic_rules",
                metadata={"description": "Domain-invariant semantic rules"}
            )
        return self._collection
    
    def retrieve_semantic_rules(
        self,
        modality: str,
        domain: str | None = None,
        dataset_columns: list = None,
        column_mappings: dict = None,
        top_k: int = 10,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Retrieve semantic rules relevant to modality and domain."""
        # Load domain-specific rules from JSON if domain is specified
        domain_rules = []
        if domain and domain != "general":
            domain_rules = self._load_domain_rules(domain, dataset_columns=dataset_columns, column_mappings=column_mappings)
        
        # Query vector DB by modality and domain
        query_text = f"data cleaning rules for {modality} data"
        if domain and domain != "general":
            query_text += f" in {domain} domain"
        
        results = self.collection.query(
            query_texts=[query_text],
            n_results=top_k,
        )
        
        rules = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i, rule_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if "distances" in results else 0.0
                similarity = 1 - distance  # Convert distance to similarity
                
                if similarity >= threshold:
                    metadata = results["metadatas"][0][i] if "metadatas" in results else {}
                    document = results["documents"][0][i] if "documents" in results else ""
                    
                    rule = {
                        "source": models.RuleSource.RAG,
                        "modality": models.Modality(modality.upper()) if hasattr(models.Modality, modality.upper()) else models.Modality.TABULAR,
                        "targets": metadata.get("targets", {}),
                        "predicate": metadata.get("predicate", ""),
                        "action": metadata.get("action", ""),
                        "confidence": float(metadata.get("confidence", similarity)),
                        "explanation": document or metadata.get("explanation", ""),
                    }
                    rules.append(rule)
        
        # Combine vector DB results with domain-specific JSON rules
        all_rules = rules + domain_rules
        return all_rules
    
    def get_feedback_context_for_extraction(
        self,
        domain: str = "general",
        column_names: list = None,
        top_k: int = 5,
    ) -> list:
        """
        Query ChromaDB for past approved/rejected rules relevant to
        the current dataset's domain and columns.
        Called by llm_multi_extractor before building the LLM prompt.
        """
        try:
            col_text = ", ".join(column_names[:10]) if column_names else "unknown columns"
            query = f"Domain: {domain}. Columns: {col_text}."

            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where={"type": "feedback"},
            )

            examples = []
            if results["ids"] and results["ids"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i]
                    decision = meta.get("decision", "")
                    if decision == "approved":
                        examples.append(
                            f"Previously APPROVED: {meta.get('explanation', doc)}"
                            f" (action: {meta.get('action', '?')})"
                        )
                    elif decision == "rejected":
                        examples.append(
                            f"Previously REJECTED: {meta.get('explanation', doc)}"
                            f" — avoid suggesting similar rules"
                        )
            return examples

        except Exception as e:
            print(f"[RAG] get_feedback_context_for_extraction failed: {e}")
            return []
    
    
    def _load_domain_rules(self, domain: str, dataset_columns: list = None, column_mappings: dict = None) -> List[Dict[str, Any]]:
        """
        Load domain-specific rules from JSON file.
        Rules use canonical concepts, which are then mapped to actual columns.
        """
        import json
        import os
        
        domain_rules = []
        domain_path = os.path.join(settings.rag_index_path, domain, "rules.json")
        
        if os.path.exists(domain_path):
            try:
                with open(domain_path, 'r') as f:
                    rules_data = json.load(f)
                    for rule_data in rules_data:
                        # RAG rules are defined using canonical concepts
                        # Extract canonical concept names from predicate/action
                        predicate = rule_data.get("predicate", "")
                        action = rule_data.get("action", "")
                        
                        # Find canonical concepts in predicate/action
                        from ...services.canonical_schema import get_canonical_concepts
                        canonical_concepts = get_canonical_concepts()
                        
                        # First, check if rule explicitly lists canonical_concepts
                        explicit_concepts = rule_data.get("canonical_concepts", [])
                        used_concepts = explicit_concepts.copy() if explicit_concepts else []
                        
                        # Also search for canonical concepts in predicate/action text
                        for concept in canonical_concepts:
                            if concept in predicate or concept in action:
                                if concept not in used_concepts:
                                    used_concepts.append(concept)
                        
                        # Map canonical concepts to actual columns if mappings available
                        matched_columns = []
                        if column_mappings:
                            # Create reverse mapping: canonical_concept -> column_name
                            concept_to_column = {}
                            for col_name, mapping in column_mappings.items():
                                canonical_concept = mapping.get("canonical_concept")
                                if canonical_concept and canonical_concept in used_concepts:
                                    if canonical_concept not in concept_to_column:
                                        concept_to_column[canonical_concept] = col_name
                            
                            # Get actual columns for used concepts
                            for concept in used_concepts:
                                actual_col = concept_to_column.get(concept)
                                if actual_col:
                                    matched_columns.append(actual_col)
                            
                            # Replace canonical concepts with actual column names
                            updated_predicate = predicate
                            updated_action = action
                            for concept in used_concepts:
                                actual_col = concept_to_column.get(concept)
                                if actual_col:
                                    updated_predicate = updated_predicate.replace(concept, actual_col)
                                    updated_action = updated_action.replace(concept, actual_col)
                        else:
                            # No mappings - use canonical concepts as-is (will need mapping later)
                            updated_predicate = predicate
                            updated_action = action
                            matched_columns = used_concepts  # Use concepts as placeholder
                        
                        # Only create rule if we found matching columns or concepts
                        if matched_columns or used_concepts:
                            rule = {
                                "source": models.RuleSource.RAG,
                                "modality": models.Modality.TABULAR,
                                "targets": {
                                    "columns": matched_columns,
                                    "canonical_concepts": used_concepts,
                                    "domain": domain
                                },
                                "predicate": updated_predicate,
                                "action": updated_action,
                                "confidence": float(rule_data.get("confidence", 0.9)),
                                "explanation": rule_data.get("explanation", rule_data.get("rule", "")),
                            }
                            domain_rules.append(rule)
            except Exception as e:
                print(f"Failed to load domain rules from {domain_path}: {e}")
        
        return domain_rules


# Global instance
_retriever: RAGRetriever | None = None


def get_retriever() -> RAGRetriever:
    """Get singleton retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever()
    return _retriever


def retrieve_semantic_rules(modality: str, domain: str | None = None, dataset_columns: list = None, column_mappings: dict = None, **kwargs) -> List[Dict[str, Any]]:
    """Convenience function for retrieving semantic rules."""
    return get_retriever().retrieve_semantic_rules(modality, domain=domain, dataset_columns=dataset_columns, column_mappings=column_mappings, **kwargs)
