import numpy as np
import pytest

from oppie_vector import FAISS_AVAILABLE
from oppie_vector.embedding import DummyEmbeddingProvider
from oppie_vector.vector_store import InMemoryVectorStore, VectorRecord

# Skip entire module if faiss is not available and environment does not allow
pytest.importorskip("faiss", reason="faiss library not installed", allow_module_level=True)

def test_upsert_and_search_with_dummy() -> None:
    provider = DummyEmbeddingProvider(dim=64)
    store = InMemoryVectorStore(dim=64, use_faiss=False)

    texts = ["def foo():\n    pass", "def bar():\n    pass", "baz qux"]
    embeddings = provider.embed(texts)
    records = [
        VectorRecord(file_path=f"f{i}.py", start_line=1, end_line=2, language="python")
        for i in range(len(texts))
    ]
    store.upsert(records, embeddings)

    q_emb = provider.embed(["foo function"])
    hits = store.search(q_emb, k=2)
    assert len(hits) == 2
    # Ensure scores are sorted descending
    scores = [score for _, score in hits]
    assert scores == sorted(scores, reverse=True)
    # The top result should correspond to the first record ideally
    assert hits[0][0].file_path in {"f0.py", "f1.py"} 