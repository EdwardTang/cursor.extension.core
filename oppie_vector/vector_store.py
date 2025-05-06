from __future__ import annotations

"""Simple in-memory vector store backed by FAISS (if available).

The design mirrors popular Python libraries such as `langchain.vectorstores` but
keeps the surface minimal for our use-case (code chunk search inside the Oppie
repo).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple, Dict, Any, Optional

import numpy as np

try:
    import faiss  # type: ignore

    _FAISS_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover — CI w/o faiss
    _FAISS_AVAILABLE = False

from .embedding import EmbeddingProvider, DummyEmbeddingProvider

__all__ = [
    "VectorStore",
    "InMemoryVectorStore",
]


@dataclass
class VectorRecord:
    """Metadata associated with a vector."""

    file_path: str
    start_line: int
    end_line: int
    language: str


class VectorStore:  # noqa: D101
    def upsert(self, records: Sequence[VectorRecord], embeddings: np.ndarray) -> None:  # noqa: D401
        raise NotImplementedError

    def search(self, query_emb: np.ndarray, k: int = 5) -> List[Tuple[VectorRecord, float]]:  # noqa: D401,E501
        raise NotImplementedError


class InMemoryVectorStore(VectorStore):
    """A RAM-based vector store using FAISS if available, else brute-force."""

    def __init__(self, dim: int, use_faiss: Optional[bool] = None):
        self.dim = dim
        self.records: List[VectorRecord] = []
        self.embeddings: Optional[np.ndarray] = None
        if use_faiss is None:
            use_faiss = _FAISS_AVAILABLE
        self._use_faiss = use_faiss
        if self._use_faiss and not _FAISS_AVAILABLE:
            raise RuntimeError("FAISS requested but not installed.")
        if self._use_faiss:
            self.index = faiss.IndexFlatIP(dim)  # type: ignore[attr-defined]

    def _ensure_array(self, arr: np.ndarray) -> np.ndarray:  # noqa: D401
        if arr.dtype != np.float32:
            arr = arr.astype(np.float32)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        return arr

    def upsert(self, records: Sequence[VectorRecord], embeddings: np.ndarray) -> None:  # noqa: D401,E501
        embeddings = self._ensure_array(embeddings)
        if embeddings.shape[0] != len(records):
            raise ValueError("Embeddings count does not match number of records")
        self.records.extend(records)
        if self._use_faiss:
            self.index.add(embeddings)  # type: ignore[attr-defined]
        else:
            if self.embeddings is None:
                self.embeddings = embeddings
            else:
                self.embeddings = np.vstack([self.embeddings, embeddings])

    def search(self, query_emb: np.ndarray, k: int = 5) -> List[Tuple[VectorRecord, float]]:  # noqa: D401,E501
        query_emb = self._ensure_array(query_emb)
        if self._use_faiss:
            scores, idxs = self.index.search(query_emb, k)  # type: ignore[attr-defined]
            idx_list = idxs[0]
            score_list = scores[0]
        else:
            # Brute-force cosine similarity
            if self.embeddings is None:
                return []
            vecs = self.embeddings
            # Normalize
            vecs_n = vecs / (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-10)
            q_n = query_emb / (np.linalg.norm(query_emb, axis=1, keepdims=True) + 1e-10)
            sims = vecs_n.dot(q_n.T)[:, 0]
            idx_list = np.argsort(-sims)[:k]
            score_list = sims[idx_list]
        results: List[Tuple[VectorRecord, float]] = []
        for i, score in zip(idx_list, score_list):
            if i >= len(self.records):
                continue
            results.append((self.records[i], float(score)))
        return results 