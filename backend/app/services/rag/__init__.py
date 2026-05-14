# Lazy imports - only import when actually used
# This prevents ChromaDB and SentenceTransformer from loading at startup
def retrieve_semantic_rules(*args, **kwargs):
    """Lazy import wrapper for retrieve_semantic_rules."""
    from .retriever import retrieve_semantic_rules as _func
    return _func(*args, **kwargs)

def get_retriever():
    """Lazy import wrapper for get_retriever."""
    from .retriever import get_retriever as _func
    return _func()

def get_indexer():
    """Lazy import wrapper for get_indexer."""
    from .indexer import get_indexer as _func
    return _func()

# For type hints and direct access (will still lazy load)
def RAGRetriever():
    from .retriever import RAGRetriever as _class
    return _class

def RAGIndexer():
    from .indexer import RAGIndexer as _class
    return _class

