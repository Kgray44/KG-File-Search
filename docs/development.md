# Development Guide

This guide describes how to work on KGFS from the repository state at this commit.

## Requirements

- Python 3.11 or newer.
- Package manager: `pip`.
- Test runner: `pytest`.

Runtime and optional dependencies are declared in `pyproject.toml`.

## Local Setup

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Windows PowerShell activation example:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install optional extras only when needed:

```bash
python -m pip install -e ".[semantic]"
python -m pip install -e ".[openai]"
python -m pip install -e ".[package]"
python -m pip install -e ".[hnsw]"
python -m pip install -e ".[sqlite-vec]"
python -m pip install -e ".[faiss]"
```

Sources: `pyproject.toml`, `README.md`.

## Run Tests

```bash
python -m pytest
```

The configured pytest settings are:

- `testpaths = ["tests"]`
- `addopts = "-ra"`

Sources: `pyproject.toml`.

## Lint, Typecheck, and Build

No dedicated lint or typecheck tool configuration is present at this commit. There is no `ruff`, `black`, `mypy`, `Makefile`, Dockerfile, Kubernetes config, or cloud deployment manifest found in the repo.

Packaging build:

```bash
python -m pip install -e ".[package]"
python scripts/build_package.py --clean
python scripts/smoke_test_packaged.py --package dist-packages/KGFS
```

Sources: `scripts/build_package.py`, `scripts/smoke_test_packaged.py`, `packaging/README-packaging.md`.

## Repository Conventions

- Use `pathlib.Path` for paths.
- Keep platform-specific open/reveal logic in `kgfs/core/platform_utils.py`.
- Keep platform app data in platformdirs paths unless project-local mode is explicit.
- Do not index a whole drive by default.
- Do not follow symlinks unless config says to.
- Do not delete, move, rename, or overwrite indexed source files.
- Treat protected/system/app/dependency/cache/game install folders as ignored by default.

Sources: `AGENTS.md`, `kgfs/core/config.py`, `kgfs/core/platform_utils.py`, `tests/test_platform_boundary.py`.

## Add a New CLI Command

1. Add a module under `kgfs/cli/commands/`.
2. Define `register(app: typer.Typer) -> None`.
3. Register command functions with `app.command(...)`.
4. Add the module to the import list and registration tuple in `kgfs/cli/app.py`.
5. Use shared runtime helpers from `kgfs/cli/shared.py` when the command needs config or DB.
6. Add tests in `tests/test_cli.py` or a focused command test file.
7. Update [CLI](cli.md), [Usage](usage.md), and [Features](features.md).

Existing examples:

- `kgfs/cli/commands/index.py`
- `kgfs/cli/commands/search.py`
- `kgfs/cli/commands/semantic.py`

## Add a New Config Setting

1. Add a field to the appropriate Pydantic model in `kgfs/core/config.py`.
2. Add the default to `DEFAULT_CONFIG_YAML`.
3. Add the key to `config.example.yaml`.
4. Thread the setting into the feature code.
5. Add or update tests in `tests/test_config.py` and feature-specific tests.
6. Update [Settings](settings.md) and any affected usage docs.

Important: If the setting changes indexing or privacy behavior, add focused tests that show the intended behavior.

## Add a New File Extractor

1. Add a module under `kgfs/extractors/`.
2. Return `ExtractionResult` using helpers from `kgfs/extractors/base.py`.
3. Register the suffix in `kgfs/extractors/__init__.py`.
4. Add the suffix to `DEFAULT_INCLUDE_EXTENSIONS` and `config.example.yaml` only if it should be enabled by default.
5. Add tests in `tests/test_extractors.py`.
6. If indexing/search behavior changes, add indexing/search tests too.

Current extractor dispatch:

- Text: `.txt`, `.html`, `.css`, `.json`
- Markdown: `.md`
- Code: `.py`, `.js`, `.ts`
- CSV: `.csv`
- PDF: `.pdf`
- DOCX: `.docx`

Sources: `kgfs/extractors/__init__.py`.

## Add or Change Database Schema

1. Update table creation in `kgfs/db/schema.py`.
2. Add idempotent migration behavior in `kgfs/db/migrations.py`.
3. Update repository helpers in `kgfs/db/repositories.py` if needed.
4. Update stats/latest-results helpers if affected.
5. Add migration tests in `tests/test_migrations.py`.
6. Update [Data Model](data-model.md).

Current schema version is `CURRENT_SCHEMA_VERSION = 1`.

## Add a New Search Mode

1. Add an enum value to `SearchMode` in `kgfs/search/options.py` if the mode is user-facing.
2. Add an engine wrapper under `kgfs/search/modes/`.
3. Implement `available()` and `search()`.
4. Register it in `build_default_search_registry()` in `kgfs/search/registry.py`.
5. Decide how `auto` should resolve or fall back.
6. Add tests in `tests/test_search_kernel.py`.
7. Expose the mode in CLI/web only if it is ready for users.
8. Update [CLI](cli.md), [Features](features.md), and [Architecture](architecture.md).

Current concrete engines:

- `KeywordSearchEngine`
- `SemanticSearchEngine`
- `HybridSearchEngine`

Sources: `kgfs/search/engine.py`, `kgfs/search/registry.py`, `kgfs/search/modes/*.py`.

## Add a New Vector Backend

1. Implement the `VectorBackend` protocol from `kgfs/search/backends/base.py`.
2. Register the backend descriptor in `kgfs/search/backends/registry.py`.
3. Implement clear/status behavior that preserves source files and non-vector index rows.
4. Keep optional dependency imports lazy; registry import must not import heavy packages.
5. Store backend artifacts under KGFS data/cache/project-local paths, never indexed source folders.
6. Decide whether `vectors.backend` should document the backend as user-facing.
7. Add tests in `tests/test_vector_backend_registry.py`, backend-specific tests, `tests/test_vector_status.py`, and search-kernel tests if semantic/hybrid routing changes.
8. Update [Settings](settings.md), [Features](features.md), [Architecture](architecture.md), and [Integrations](integrations.md).

Current vector backend support:

- `sqlite_scan`
- `sqlite_vec` optional accelerated backend
- `hnsw` optional accelerated backend
- `faiss` optional accelerated backend

Sources: `kgfs/search/backends/*.py`, `kgfs/vectors/*.py`.

## Add a Provider or Integration

For local integrations:

1. Keep dependency optional unless it is required for the base tool.
2. Add a feature flag/config key if the integration changes privacy, network, or storage behavior.
3. Add availability diagnostics to `kgfs doctor` if useful.
4. Add tests that cover missing dependency behavior.

For AI providers:

1. Extend `AISettings` in `kgfs/core/config.py` if provider-specific settings are required.
2. Extend `ensure_ai_enabled()` and client creation in `kgfs/ai.py`.
3. Preserve preview, confirmation, redaction, and bounded context behavior.
4. Add tests in `tests/test_ai.py` and CLI tests for failure modes.
5. Update [Security](security.md), [Integrations](integrations.md), and [Settings](settings.md).

Current AI provider support is OpenAI only.

## Add a Web Route

1. Add route logic in `kgfs/web/app.py`.
2. Add templates under `kgfs/web/templates/` or static assets under `kgfs/web/static/`.
3. Use resource helpers from `kgfs/core/resources.py` so source and PyInstaller builds both work.
4. Add tests in `tests/test_web.py`.
5. If the route exposes file paths or actions, update [Security](security.md).

## Packaging Workflow

Local packaging:

```bash
python -m pip install -e ".[package]"
python scripts/build_package.py --clean --mode onedir --name KGFS --dist-dir dist-packages
python scripts/smoke_test_packaged.py --package dist-packages/KGFS
```

The spec includes:

- Web templates and CSS.
- `config.example.yaml`.
- `README.md`.
- `LICENSE`.

The spec excludes:

- tests
- pytest tooling
- sentence-transformers, transformers, torch, tensorflow
- openai
- sqlite_vec, hnswlib, faiss, numpy

Sources: `packaging/pyinstaller/kgfs.spec`.

## CI

The CI workflow runs tests on:

- `windows-latest`
- `macos-latest`
- `ubuntu-latest`
- Python `3.11` and `3.12`

The package workflow runs tests, builds onedir packages on Windows and macOS, smoke tests them, and uploads zip artifacts.

Sources: `.github/workflows/ci.yml`, `.github/workflows/package.yml`, `tests/test_ci_workflow.py`.

## Debugging Development Issues

Start with:

```bash
kgfs doctor --config path/to/config.yaml --database path/to/kgfs.sqlite3
python -m pytest -ra
```

Useful focused tests:

```bash
python -m pytest tests/test_config.py
python -m pytest tests/test_indexing.py
python -m pytest tests/test_search_kernel.py
python -m pytest tests/test_web.py
python -m pytest tests/test_ai.py
python -m pytest tests/test_packaging_scripts.py
```

Inspect the database manually when needed:

```bash
python - <<'PY'
from pathlib import Path
from kgfs.database import connect_database

conn = connect_database(Path("kgfs.sqlite3"))
for row in conn.execute("SELECT id, file_name, extraction_status FROM files LIMIT 20"):
    print(row["id"], row["file_name"], row["extraction_status"])
PY
```

On PowerShell, use a here-string:

```powershell
@'
from pathlib import Path
from kgfs.database import connect_database
conn = connect_database(Path("kgfs.sqlite3"))
for row in conn.execute("SELECT id, file_name, extraction_status FROM files LIMIT 20"):
    print(row["id"], row["file_name"], row["extraction_status"])
'@ | python -
```

## Documentation Updates

When behavior changes, update the docs nearest to the change:

- User command or workflow: `docs/usage.md`, `docs/cli.md`, `docs/features.md`.
- Config or env: `docs/settings.md`.
- Schema or stored data: `docs/data-model.md`.
- Search/indexing internals: `docs/architecture.md`.
- Optional integrations: `docs/integrations.md`.
- Privacy or safety: `docs/security.md`.
- Common failure mode: `docs/troubleshooting.md`.
