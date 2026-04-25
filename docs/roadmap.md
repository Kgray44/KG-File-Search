# Roadmap

This roadmap separates behavior implemented in the repository state at this commit from work that is planned, intentionally absent, or only represented as extension points.

## Implemented At This Commit

- Explicit-folder local indexing with risky-root protection.
- File discovery and filtering for ignored folders, ignored extensions, include extensions, globs, file size, and symlink policy.
- Text extraction for text-like files, Markdown, code, CSV, PDF, and DOCX.
- Optional local Tesseract OCR for configured image files, plus safe scanned-PDF candidate reporting.
- Local SQLite storage for file records, FTS5 rows, latest search results, semantic chunks, and schema version.
- Incremental indexing, forced reindexing, hash verification, prune, reset, and rebuild.
- Keyword, semantic, hybrid, and auto search modes with score breakdowns and `kgfs why`.
- Local vector backend interface, registry, default `sqlite_scan` backend, and optional accelerated `sqlite_vec`, `hnsw`, and `faiss` backends.
- `kgfs vector status`, `kgfs vector rebuild`, `kgfs vector clear --yes`, `kgfs vector benchmark`, and `kgfs vector recommend`.
- Local semantic embeddings through optional sentence-transformers.
- Optional OpenAI AI Assist for snippet-bounded answer synthesis and reranking.
- Typer CLI, local FastAPI dashboard, and PyInstaller packaging scripts.
- GitHub Actions CI and package artifact workflow.

Source anchors:

- CLI: `kgfs/cli/app.py`, `kgfs/cli/commands/*.py`
- Config: `kgfs/core/config.py`
- Indexing: `kgfs/indexing/*.py`
- Search: `kgfs/search/*.py`, `kgfs/search/modes/*.py`, `kgfs/search/backends/*.py`
- Vectors: `kgfs/vectors/*.py`
- Explanations: `kgfs/cli/commands/why.py`, `kgfs/search/explain.py`
- Web: `kgfs/web/app.py`
- Packaging/CI: `scripts/*.py`, `.github/workflows/*.yml`

## Planned Or Not Implemented

The following are not implemented as user-facing KGFS features at this commit:

- More advanced vector tuning beyond the current optional sqlite-vec/HNSW/FAISS implementations.
- Full scanned-PDF OCR rasterization, OCR backend expansion, or multimodal file search.
- Similar-file search.
- Deep search or remote retrieval.
- Background daemon/index scheduler.
- Web dashboard authentication.
- Structured file logging or telemetry backend.
- Encrypted index storage.
- Docker, Kubernetes, or cloud deployment manifests.
- Release publishing workflow that creates GitHub Releases from package artifacts.
- Query expansion, despite the `ai.allow_query_expansion` config key.
- Search-time backend selection in CLI/web, despite the `SearchOptions.backend` runtime field. Vector management commands expose `--backend`.
- Generic `--explain` search flag, despite the `SearchOptions.explain` runtime field. Use `kgfs why` for implemented result explanations.

When adding planned work, update [features](features.md), [settings](settings.md), [cli](cli.md), [architecture](architecture.md), [data model](data-model.md), [security](security.md), and this roadmap in the same change.
