# Usage Guide

KGFS can be used through its CLI, local web dashboard, and Python modules. This guide covers supported entry points found in the current worktree.

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
kgfs open 1
kgfs reveal 1
```

Important behavior:

- `kgfs init` creates a config but does not index files.
- The generated config starts with `indexed_folders: []`.
- `kgfs index` with no folders prints a setup message and exits without creating a database.
- `kgfs open` and `kgfs reveal` use the latest saved search result IDs.

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

Auto mode uses hybrid search only when semantic search is enabled, dependencies are available, and chunks exist. Otherwise it falls back to keyword search.

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
