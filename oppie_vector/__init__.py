from typing import List, Tuple, Optional, Dict, Any

from .embedding import EmbeddingProvider, OpenAIEmbeddingProvider, DummyEmbeddingProvider
from .vector_store import VectorStore, InMemoryVectorStore

# Optional FAISS dependency guard. Some CI stages run without native faiss.
try:
    import faiss  # type: ignore

    FAISS_AVAILABLE: bool = True
except ModuleNotFoundError:
    FAISS_AVAILABLE = False  # pragma: no cover

__all__: List[str] = [
    "EmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "DummyEmbeddingProvider",
    "VectorStore",
    "InMemoryVectorStore",
    "FAISS_AVAILABLE",
] 