"""FastAPI server that wraps the InMemoryVectorStore.

The server is meant for local usage inside VS Code or Plan-Execute loops, so it
keeps the implementation minimal: everything is stored in memory, and the
process is expected to be short-lived.  In production we may swap this
implementation with a persistent DB-backed store.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import List, Sequence

import uvicorn  # type: ignore
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .embedding import DummyEmbeddingProvider, EmbeddingProvider, OpenAIEmbeddingProvider
from .vector_store import InMemoryVectorStore, VectorRecord

logger = logging.getLogger(__name__)

app = FastAPI(title="Oppie Vector Store API", version="0.1.0")

# NOTE: For MVP we initialise a single global store.  A future version could
#       support multiple named indexes.
_embedding_provider: EmbeddingProvider | None = None
_store: InMemoryVectorStore | None = None


class UpsertChunk(BaseModel):
    file_path: str = Field(..., description="Relative path of the file")
    start_line: int = Field(..., ge=1)
    end_line: int = Field(..., ge=1)
    language: str = Field(...)
    text: str = Field(..., description="The original source text of the chunk")


class SearchRequest(BaseModel):
    query: str = Field(...)
    k: int = Field(5, ge=1, le=20)


class SearchHit(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    language: str
    score: float


@app.on_event("startup")
async def _startup() -> None:  # noqa: D401
    global _embedding_provider, _store  # pylint: disable=global-statement
    try:
        _embedding_provider = OpenAIEmbeddingProvider()  # pragma: no cover
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falling back to DummyEmbeddingProvider due to: %s", exc)
        _embedding_provider = DummyEmbeddingProvider()
    _store = InMemoryVectorStore(dim=128)


@app.post("/upsert", status_code=204)
async def upsert(chunks: List[UpsertChunk]) -> None:  # noqa: D401
    assert _embedding_provider and _store  # nosec B101
    texts = [c.text for c in chunks]
    embeddings = _embedding_provider.embed(texts)
    records = [
        VectorRecord(
            file_path=c.file_path,
            start_line=c.start_line,
            end_line=c.end_line,
            language=c.language,
        )
        for c in chunks
    ]
    _store.upsert(records, embeddings)


@app.post("/search", response_model=List[SearchHit])
async def search(req: SearchRequest) -> List[SearchHit]:  # noqa: D401
    assert _embedding_provider and _store  # nosec B101
    emb = _embedding_provider.embed([req.query])
    hits = _store.search(emb, k=req.k)
    return [
        SearchHit(
            file_path=r.file_path,
            start_line=r.start_line,
            end_line=r.end_line,
            language=r.language,
            score=score,
        )
        for r, score in hits
    ]


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:  # noqa: D401
    parser = argparse.ArgumentParser(description="Run Oppie Vector Store API server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:  # noqa: D401
    args = _parse_args(argv)
    uvicorn.run("oppie_vector.server:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":  # pragma: no cover
    main() 