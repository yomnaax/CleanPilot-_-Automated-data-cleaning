"""
RAG indexer for storing semantic rules in vector database.
"""

# Lazy imports - ChromaDB and SentenceTransformer are heavy, only import when needed
from typing import List, Dict, Any
from ...config import settings


class RAGIndexer:
    """Indexes semantic rules in vector database."""
    
    def __init__(self):
        # Lazy initialization - only create client when actually needed
        self._client = None
        self._collection = None
        # Lazy load embedder (only when needed - can be slow)
        self._embedder = None
    
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
    
    @property
    def embedder(self):
        """Lazy load SentenceTransformer model (only when needed)."""
        if self._embedder is None:
            # Lazy import SentenceTransformer only when needed
            from sentence_transformers import SentenceTransformer
            print("Loading SentenceTransformer model (this may take a moment)...")
            self._embedder = SentenceTransformer(settings.embedding_model)
            print("SentenceTransformer model loaded.")
        return self._embedder
    
    def index_rule(
        self,
        rule_id: str,
        explanation: str,
        predicate: str,
        action: str,
        modality: str,
        targets: Dict[str, Any],
        confidence: float = 0.9
    ):
        """Index a semantic rule."""
        # Create document text for embedding
        document_text = f"{explanation}. Predicate: {predicate}. Action: {action}. Modality: {modality}."
        
        # Generate embedding
        embedding = self.embedder.encode(document_text).tolist()
        
        # Store in ChromaDB
        self.collection.add(
            ids=[rule_id],
            embeddings=[embedding],
            documents=[document_text],
            metadatas=[{
                "predicate": predicate,
                "action": action,
                "modality": modality,
                "targets": str(targets),
                "confidence": str(confidence),
                "explanation": explanation,
            }]
        )
    
    def index_rules_batch(self, rules: List[Dict[str, Any]]):
        """Index multiple rules at once."""
        ids = []
        documents = []
        embeddings = []
        metadatas = []
        
        for rule in rules:
            rule_id = rule.get("id", f"rule_{len(ids)}")
            explanation = rule.get("explanation", "")
            predicate = rule.get("predicate", "")
            action = rule.get("action", "")
            modality = rule.get("modality", "tabular")
            targets = rule.get("targets", {})
            confidence = rule.get("confidence", 0.9)
            
            document_text = f"{explanation}. Predicate: {predicate}. Action: {action}. Modality: {modality}."
            embedding = self.embedder.encode(document_text).tolist()
            
            ids.append(rule_id)
            documents.append(document_text)
            embeddings.append(embedding)
            metadatas.append({
                "predicate": predicate,
                "action": action,
                "modality": str(modality),
                "targets": str(targets),
                "confidence": str(confidence),
                "explanation": explanation,
            })
        
        if ids:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
    
    def delete_rule(self, rule_id: str):
        """Delete a rule from index."""
        self.collection.delete(ids=[rule_id])


# Global instance
_indexer: RAGIndexer | None = None


def get_indexer() -> RAGIndexer:
    """Get singleton indexer instance."""
    global _indexer
    if _indexer is None:
        _indexer = RAGIndexer()
    return _indexer
