from __future__ import annotations

"""Embedding provider abstractions.

This module defines a generic `EmbeddingProvider` protocol to decouple vector
store logic from the concrete embedding back-end.  The initial implementation
includes a cheap `DummyEmbeddingProvider` for unit tests and a skeleton
`OpenAIEmbeddingProvider` that will call the official OpenAI embeddings API
when an `OPENAI_API_KEY` environment variable is available.  The actual HTTP
call is placed behind a try/except import guard so that the test suite keeps
running even when the extra dependency (`openai`) is missing.
"""

from abc import ABC, abstractmethod
from typing import List, Sequence
import os

import numpy as np

__all__ = [
    "EmbeddingProvider",
    "DummyEmbeddingProvider",
    "OpenAIEmbeddingProvider",
]


class EmbeddingProvider(ABC):
    """Abstract base class for all embedding providers."""

    @abstractmethod
    def embed(self, texts: Sequence[str]) -> np.ndarray:  # noqa: D401
        """Return a 2-D numpy array of shape (len(texts), dim)."""


class DummyEmbeddingProvider(EmbeddingProvider):
    """A deterministic embedding provider for tests.

    It turns each text into a fixed-dimensional vector by hashing.  While the
    resulting vectors are **not** semantically meaningful, they are stable and
    allow us to test vector-store logic without external network calls.
    """

    def __init__(self, dim: int = 128) -> None:  # noqa: D401
        self._dim = dim

    def _hash(self, text: str) -> int:  # noqa: D401
        return abs(hash(text))

    def embed(self, texts: Sequence[str]) -> np.ndarray:  # noqa: D401
        vecs = np.zeros((len(texts), self._dim), dtype=np.float32)
        for i, t in enumerate(texts):
            h = self._hash(t)
            # Simple pseudo-random but deterministic vector
            rng = np.random.default_rng(h & 0xFFFF_FFFF)
            vecs[i] = rng.random(self._dim)
        return vecs


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embedding provider that proxies to the OpenAI Embeddings API."""

    def __init__(self, model: str = "text-embedding-3-small", batch_size: int = 96):
        self.model = model
        self.batch_size = batch_size
        try:
            import openai  # pylint: disable=import-error

            self._openai = openai
        except ModuleNotFoundError as exc:
            raise ImportError(
                "openai package is required for OpenAIEmbeddingProvider."
            ) from exc

        if not os.getenv("OPENAI_API_KEY"):
            raise EnvironmentError("OPENAI_API_KEY environment variable not set.")

    def embed(self, texts: Sequence[str]) -> np.ndarray:  # noqa: D401
        vectors: List[np.ndarray] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            resp = self._openai.embeddings.create(model=self.model, input=list(batch))
            batch_vecs = np.array([d["embedding"] for d in resp.data], dtype=np.float32)
            vectors.append(batch_vecs)
        return np.concatenate(vectors, axis=0) 