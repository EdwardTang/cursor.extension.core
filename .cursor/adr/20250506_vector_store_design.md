# 20250506 - Adopt EmbeddingProvider Abstraction & FAISS-based Vector Store

## Status
Accepted

## Context
The Oppie Remote Cursor Control Mesh requires fast, local semantic search of code chunks to feed both the mobile UI and the internal Planner.  A Vector Store component is needed to map text → embedding → index → nearest-neighbour search.

Key questions:
- Which **embedding model** should we start with?
- Which **indexing library** balances performance with minimal dependencies?
- How do we design the **abstraction** to allow future swapping (e.g., offline mode)?
- How should the Vector Store integrate with the VS Code extension?
- How do we handle environments where FAISS isn't available?

## Decision
1. Define an `EmbeddingProvider` ABC with a production `OpenAIEmbeddingProvider` and a deterministic `DummyEmbeddingProvider` for tests.
2. Use **FAISS** (`IndexFlatIP`) as the default in-memory index when the library is present; automatically fall back to a brute-force cosine similarity implementation otherwise to keep CI lightweight.
3. Introduce `VectorStore` interface and `InMemoryVectorStore` concrete class that stores `(VectorRecord, embedding)` pairs.  Only cosine similarity (inner-product) is required for MVP.
4. Expose a **FastAPI** service (`oppie_vector.server`) with `/upsert` and `/search` endpoints so that:
   - The VS Code extension can spawn the server as a child process and talk over HTTP.
   - Plan-Execute loops can call the same local API.
5. Persist nothing for now; the server is expected to be short-lived.  A follow-up ADR will address persistence & sharding.
6. VS Code Extension Integration:
   - During extension activation, check for `oppie.vector.endpoint` setting.
   - If set to `auto` (default), spawn a Python child process running `oppie_vector.server`.
   - Parse the "READY <port>" message from stdout to determine the endpoint.
   - Expose `oppie.vectorSearch` command that shows QuickPick UI to search and navigate to results.
   - On extension deactivation, cleanly terminate the child process.
7. CI Strategy:
   - Stage 1: Run tests marked with `not faiss` on all platforms.
   - Stage 2: Run all tests including FAISS-dependent ones only on Linux with `faiss-cpu` installed.

## Consequences
- New Python package `oppie_vector` added (≈300 LOC) with minimal external deps (`numpy`, `faiss-cpu`, `fastapi`, `uvicorn[standard]`, `pydantic`).
- Unit tests can run entirely offline using `DummyEmbeddingProvider` and brute-force search, so CI remains fast (<5s).
- Switching to a local embedding model only requires implementing a new `EmbeddingProvider` – no changes to VectorStore.
- FAISS is optional; developers without the dependency still get correct (albeit slower) behaviour.
- VS Code extension can now provide semantic code search through a local REST API.
- The REST API pattern allows separating the embedding/indexing logic from UI concerns.
- Cross-platform support achieved via the `FAISS_AVAILABLE` guard and Python launcher selection.
- Future work: persistence layer, multi-index support, async batching, advanced IVFPQ quantisation for large corpora.

## Alternatives Considered

### Alternative 1: Direct Python Binding
Directly binding to Python from the VS Code extension was considered, but rejected due to:
- Complexity of Node.js <-> Python FFI
- Cross-platform compatibility issues
- Difficulty in cleanly handling the dependency on FAISS

### Alternative 2: Langchain VectorStore
Using Langchain's VectorStore directly was evaluated but not chosen because:
- We need finer control over the embedding process
- A small, targeted implementation better meets our performance requirements
- Avoiding the large dependency footprint of Langchain

### Alternative 3: In-Process JavaScript Vector Store
Building the vector store directly in JavaScript/TypeScript was considered but rejected due to:
- Limited high-performance vector indexing libraries in JS ecosystem
- Higher memory usage for large codebases
- Loss of ability to use FAISS's optimized similarity search

## Related Work
- LangChain VectorStore interface.
- OpenAI Cookbook: `text-embedding-3-small` best practices. 
- VS Code extension API for spawning child processes.
- FastAPI for lightweight REST services.

## Implementation Notes
- The `FAISS_AVAILABLE` flag is used throughout the codebase to conditionally use FAISS when available.
- VS Code extension uses `cross-spawn` to handle path differences across platforms.
- Test fixtures are designed to run with or without FAISS, marked with pytest markers.
- The CI pipeline is split into two stages to avoid requiring FAISS for basic tests. 