# Usage Guide

KGFS can be used through its CLI, local web dashboard, and Python modules. This guide covers supported entry points found in the repository state at this commit.

## Install

Development install:

```bash
python -m pip install -e ".[dev]"
```

Optional semantic search:

```bash
python -m pip install -e ".[semantic]"
```

Optional OpenAI AI Assist:

```bash
python -m pip install -e ".[openai]"
```

Optional OCR helper dependencies:

```bash
python -m pip install -e ".[ocr]"
```

Tesseract itself is an external local executable and is installed separately on Windows/macOS.

Sources: `pyproject.toml`, `README.md`.

## First Run

Create a config:

```bash
kgfs init
kgfs doctor
```

Add a folder deliberately:

```bash
kgfs add-folder "~/Documents/Your Notes"
kgfs list-folders
```

Index and search:

```bash
kgfs index
kgfs search "motor torque"
kgfs why 1 "motor torque"
kgfs open 1
kgfs reveal 1
```

Important behavior:

- `kgfs init` creates a config but does not index files.
- The generated config starts with `indexed_folders: []`.
- `kgfs index` with no folders prints a setup message and exits without creating a database.
- `kgfs open` and `kgfs reveal` use the latest saved search result IDs.
- `kgfs why` also uses latest saved search result IDs and explains a result against a query.

Sources: `kgfs/cli/commands/init.py`, `kgfs/cli/commands/index.py`, `kgfs/cli/commands/open_reveal.py`, `tests/test_cli.py`.

## Project-Local Mode

Project-local mode stores config and data under `.kgfs/` in the current directory:

```bash
kgfs init --project-local
kgfs add-folder "./sample-files" --project-local
kgfs index --project-local
kgfs search "sample query" --project-local
kgfs stats --project-local
```

Sources: `kgfs/core/app_dirs.py`, `tests/test_app_dirs.py`.

## Config Workflow

Inspect active config:

```bash
kgfs config
```

Use explicit paths:

```bash
kgfs init --config ./config.yaml
kgfs index --config ./config.yaml --database ./kgfs.sqlite3
kgfs search "op amps" --config ./config.yaml --database ./kgfs.sqlite3
```

Path values can use `~`, `~/...`, `~\...`, POSIX env vars, and Windows `%VAR%` style variables.

Sources: `kgfs/core/path_utils.py`, `kgfs/core/app_dirs.py`, `kgfs/cli/shared.py`.

## Indexing Workflows

Normal incremental index:

```bash
kgfs index
```

Discover without writing to the database:

```bash
kgfs index --dry-run
```

Re-extract all discovered files:

```bash
kgfs index --force
```

Verify hashes even when size and modified time match:

```bash
kgfs index --verify-hashes
```

Index and then prune stale database records:

```bash
kgfs index --prune
```

Override risky-root protection only when intentional:

```bash
kgfs index --allow-risky-root
```

Sources: `kgfs/cli/commands/index.py`, `kgfs/indexing/indexer.py`, `kgfs/core/safety.py`.

## Search Workflows

Keyword search:

```bash
kgfs search "pid control" --mode keyword
```

Auto mode, the default:

```bash
kgfs search "motor torque"
kgfs search "motor torque" --mode auto
```

Auto mode uses hybrid search only when semantic search is enabled, dependencies
are available, vector backend is available, and chunks exist. If semantic is
disabled, it quietly uses keyword search. If semantic is enabled but not ready,
it prints one warning and uses keyword search.

Filtered search:

```bash
kgfs search "pid" --ext .pdf
kgfs search "pid" --type pdf
kgfs search "pid" --folder "Controls"
kgfs search "pid" --after 2025-01-01
kgfs search "pid" --before 2026-01-01
kgfs search "bad extraction" --failed-only
kgfs search "speaker crossover" --limit 25
```

Explain a latest result:

```bash
kgfs why 1 "motor torque"
kgfs why 1 "motor torque" --mode keyword
```

The explanation command reruns local search, prints the score breakdown and
matched snippet, and notes when the saved result no longer appears in the fresh
rerun. It does not call AI.

Sources: `kgfs/cli/commands/search.py`, `kgfs/search/filters.py`, `kgfs/search/registry.py`, `tests/test_search_filters.py`, `tests/test_search_kernel.py`.

## Semantic Search

Install semantic dependencies:

```bash
python -m pip install -e ".[semantic]"
```

Enable semantic search:

```yaml
semantic:
  enabled: true
  model_name: "sentence-transformers/all-MiniLM-L6-v2"
  chunk_size_chars: 1200
  chunk_overlap_chars: 200
  local_files_only: true
  batch_size: 16
```

Build or rebuild chunks:

```bash
kgfs semantic-index --rebuild
```

Search semantic chunks:

```bash
kgfs semantic "rotational force"
kgfs search "rotational force" --mode semantic
kgfs search "rotational force" --hybrid
```

Check semantic status:

```bash
kgfs semantic-index
kgfs doctor
kgfs stats
```

Sources: `kgfs/cli/commands/semantic.py`, `kgfs/search/semantic.py`, `kgfs/search/modes/semantic.py`, `tests/test_semantic.py`.

## Vector Backend Lab

Semantic and hybrid search use the configured vector backend. `sqlite_scan` is
the default and remains part of the base install. Optional backend names are
registered for `sqlite_vec`, `hnsw`, and `faiss`, but they stay disabled and
lazy unless their optional dependency is installed and the backend is enabled.

Check vector readiness:

```bash
kgfs vector status
```

Rebuild vectors from already indexed extracted text:

```bash
kgfs vector rebuild
kgfs vector rebuild --no-force
kgfs vector rebuild --backend sqlite_scan
```

Benchmark local backends using existing stored vectors:

```bash
kgfs vector benchmark
kgfs vector benchmark --backend sqlite_scan
kgfs vector benchmark --query "motor torque" --query "op amp gain"
```

Ask KGFS for a conservative backend recommendation:

```bash
kgfs vector recommend
```

Clear only KGFS vector/chunk rows for the configured model, or clear optional
backend artifacts without deleting chunks:

```bash
kgfs vector clear --yes
kgfs vector clear --backend hnsw --yes
kgfs vector clear --all-backends --yes
```

Important behavior:

- `vector rebuild` requires `semantic.enabled: true`.
- `vector clear` requires `--yes`.
- Vector clear does not delete source files, `files` rows, or keyword FTS rows.
- Benchmarking does not call cloud APIs and can run against existing vectors without loading sentence-transformers.
- Unknown `vectors.backend` values make vector rebuild/clear fail and semantic/hybrid search unavailable with known-backend guidance.

Optional advanced backend extras:

```bash
python -m pip install -e ".[hnsw]"
python -m pip install -e ".[sqlite-vec]"
python -m pip install -e ".[faiss]"
```

The optional accelerated backends build/search from KGFS's existing local chunk
embeddings. They do not fake successful search when a dependency, enablement, or
backend artifact is missing.

Sources: `kgfs/cli/commands/vector.py`, `kgfs/search/backends/*.py`, `kgfs/vectors/*.py`, `tests/test_vector_commands.py`, `tests/test_vector_benchmark.py`, `tests/test_vector_recommend.py`.

## OCR Workflows

OCR is disabled by default. When enabled, supported image files are admitted by
the normal file filters, processed through local Tesseract, cached in the KGFS
database/cache, and searched through the same keyword/semantic/hybrid pipeline
as other extracted text.

Enable OCR:

```yaml
ocr:
  enabled: true
  backend: "tesseract"
  tesseract:
    command: "tesseract"
    language: "eng"
```

Check local availability:

```bash
kgfs ocr status
```

Preview OCR on one image without indexing:

```bash
kgfs ocr test ./screenshot.png
```

Index configured folders with OCR extraction:

```bash
kgfs ocr index
kgfs search "text from screenshot"
kgfs why 1 "text from screenshot"
```

Scanned/image-only PDFs are detected when normal PDF text extraction is nearly
empty. Full PDF page rasterization is not implemented yet, so KGFS records a
helpful extraction error rather than modifying the PDF or creating sidecars.

Sources: `kgfs/cli/commands/ocr.py`, `kgfs/ocr/*.py`, `kgfs/extractors/image_ocr.py`, `kgfs/extractors/pdf.py`.

## AI Assist

AI Assist is optional and disabled by default. It runs local search first, builds a bounded context from snippets, and calls OpenAI only after AI is enabled and the command path requests it.

Install optional dependency:

```bash
python -m pip install -e ".[openai]"
```

Set an API key in the environment:

```bash
export OPENAI_API_KEY="sk-..."
```

Enable AI in config:

```yaml
ai:
  enabled: true
  require_confirmation: true
  preview_context_before_send: true
  send_file_paths: false
  send_full_file_text: false
  redact_home_path: true
```

Preview without sending:

```bash
kgfs ask "What do my notes say about op-amps?" --preview-ai-context
kgfs search "motor torque" --ai-rerank --preview-ai-context
```

Ask or rerank:

```bash
kgfs ask "What do my notes say about op-amps?"
kgfs search "speaker crossover design" --ai-rerank
```

Sources: `kgfs/ai.py`, `kgfs/cli/commands/search.py`, `tests/test_ai.py`, `tests/test_cli.py`.

## Web Dashboard

Start the local FastAPI dashboard:

```bash
kgfs web
```

Default URL:

```text
http://127.0.0.1:8765
```

Override host or port:

```bash
kgfs web --host 127.0.0.1 --port 9000
```

Pages:

- `/`: home and summary metrics.
- `/search`: keyword search form with filters.
- `/stats`: database/index stats.
- `/config`: active config display.
- `/failures`: latest extraction failures.
- `/open/{result_id}` and `/reveal/{result_id}`: open or reveal latest search result paths.

Sources: `kgfs/cli/commands/web.py`, `kgfs/web/app.py`, `tests/test_web.py`.

## Maintenance

Prune stale records:

```bash
kgfs prune --dry-run
kgfs prune
```

Reset only KGFS database files:

```bash
kgfs reset-index --dry-run
kgfs reset-index --yes
```

Reset and index again:

```bash
kgfs rebuild --yes
```

Sources: `kgfs/cli/commands/maintenance.py`, `kgfs/indexing/prune.py`, `kgfs/reset.py`, `tests/test_prune.py`, `tests/test_reset_rebuild.py`.

## Packaged Builds

Install packaging dependencies:

```bash
python -m pip install -e ".[package]"
```

Build and smoke test:

```bash
python scripts/build_package.py --clean
python scripts/smoke_test_packaged.py --package dist-packages/KGFS
```

The zip name is generated as `KGFS-<os>-<arch>.zip`.

Sources: `scripts/build_package.py`, `scripts/smoke_test_packaged.py`, `packaging/README-packaging.md`.

## Python Module Usage

Minimal keyword search from Python:

```python
from pathlib import Path

from kgfs.config import KGFSConfig
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.search import search

root = Path("sample-files")
db_path = Path("kgfs.sqlite3")

conn = connect_database(db_path)
initialize_database(conn)
config = KGFSConfig(indexed_folders=[root])
index_configured_folders(config, conn)

results = search(conn, "motor torque")
for result in results:
    print(result.result_id, result.file_name, result.snippet)
```

Registry-based search:

```python
from kgfs.search import SearchContext, SearchOptions, build_default_search_registry

registry = build_default_search_registry()
context = SearchContext(conn=conn, config=config)
execution = registry.search("motor torque", SearchOptions(mode="auto"), context)
print(execution.mode_used, execution.warnings)
```

Sources: `kgfs/search/registry.py`, `tests/test_search_kernel.py`.
