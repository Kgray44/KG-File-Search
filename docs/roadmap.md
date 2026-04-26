# Roadmap

This roadmap separates behavior implemented in the repository state at this commit from work that is planned, intentionally absent, or only represented as extension points.

## Implemented At This Commit

- Explicit-folder local indexing with risky-root protection.
- File discovery and filtering for ignored folders, ignored extensions, include extensions, globs, file size, and symlink policy.
- Text extraction for text-like files, Markdown, code, CSV, PDF, and DOCX.
- Optional local Tesseract OCR for configured image files, plus safe scanned-PDF candidate reporting.
- Optional local model backend readiness for EasyOCR, PaddleOCR, metadata/Transformers captions, faster-whisper transcription, bytehash visual embeddings, and CLIP-style visual embeddings.
- Optional local photo/EXIF metadata, media-derived search text, media embeddings, local model path validation, and no-download model setup helpers.
- Local SQLite storage for file records, FTS5 rows, latest search results, semantic chunks, and schema version.
- Incremental indexing, forced reindexing, hash verification, prune, reset, and rebuild.
- Keyword, semantic, hybrid, and auto search modes with score breakdowns and `kgfs why`.
- Local vector backend interface, registry, default `sqlite_scan` backend, and optional accelerated `sqlite_vec`, `hnsw`, and `faiss` backends.
- `kgfs vector status`, `kgfs vector rebuild`, `kgfs vector clear --yes`, `kgfs vector benchmark`, and `kgfs vector recommend`.
- Local semantic embeddings through optional sentence-transformers.
- Local investigation commands: `kgfs deep`, `kgfs similar`, `kgfs similar-file`, `kgfs compare`, `kgfs timeline`, and `kgfs research`.
- Local workflow metadata: profiles, saved searches, collections, tags, notes, assignment mode, and manual projects.
- Local file intelligence: exact/semantic duplicates, likely versions, project candidates, bounded graphs, health reports, and metadata export/import/backup/restore.
- Optional OpenAI AI Assist for snippet-bounded answer synthesis and reranking.
- Typer CLI, enhanced local FastAPI dashboard, token-gated local JSON API, optional Textual TUI launcher, local integration scaffolds, and PyInstaller packaging scripts.
- Release-readiness commands and scripts: `kgfs version`, `kgfs quickstart`, `kgfs capabilities`, `kgfs db check`, docs consistency checks, checksum generation, and release checks.
- GitHub Actions CI, package artifact workflow, and draft `v*` GitHub Release workflow support.

Source anchors:

- CLI: `kgfs/cli/app.py`, `kgfs/cli/commands/*.py`
- Config: `kgfs/core/config.py`
- Indexing: `kgfs/indexing/*.py`
- Search: `kgfs/search/*.py`, `kgfs/search/modes/*.py`, `kgfs/search/backends/*.py`
- Vectors: `kgfs/vectors/*.py`
- Local models/media: `kgfs/models/*.py`, `kgfs/media/*.py`, `kgfs/ocr/*.py`
- Workflows: `kgfs/workflows/*.py`
- Intelligence: `kgfs/intelligence/*.py`
- Explanations: `kgfs/cli/commands/why.py`, `kgfs/search/explain.py`
- Web: `kgfs/web/app.py`
- Release/packaging/CI: `scripts/*.py`, `.github/workflows/*.yml`, `kgfs/version.py`, `kgfs/capabilities.py`, `kgfs/db/checks.py`

## Planned Or Not Implemented

The following are not implemented as user-facing KGFS features at this commit:

- More advanced vector tuning beyond the current optional sqlite-vec/HNSW/FAISS implementations.
- Full scanned-PDF OCR rasterization.
- Automatic model downloads by default.
- Cloud OCR providers or any automatic upload path.
- Production-grade visual understanding beyond the current optional local adapters and deterministic `bytehash` plumbing backend.
- Background daemon/index scheduler.
- Web dashboard authentication.
- Richer web/TUI workflow editing surfaces beyond the current read/search/list views.
- Automatic installation for Raycast, Alfred, PowerToys, Finder, Explorer, tray/menu-bar, and VS Code integrations.
- Structured file logging or telemetry backend.
- Encrypted index storage.
- Docker, Kubernetes, or cloud deployment manifests.
- Signing/notarization for release artifacts; the current `v*` workflow creates draft GitHub Releases without requiring signing secrets.
- AI-driven query expansion, despite the `ai.allow_query_expansion` config key. Local deep-search query variants are implemented.
- Search-time backend selection in CLI/web, despite the `SearchOptions.backend` runtime field. Vector management commands expose `--backend`.
- Generic `--explain` search flag, despite the `SearchOptions.explain` runtime field. Use `kgfs why` for implemented result explanations.
- Background tray/menu-bar daemon behavior; current tray support is a scaffold writer only.

When adding planned work, update [features](features.md), [settings](settings.md), [cli](cli.md), [architecture](architecture.md), [data model](data-model.md), [security](security.md), and this roadmap in the same change.
