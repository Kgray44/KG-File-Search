# Integrations

KGFS is local-first. Most integrations are local libraries or local OS features. The only cloud integration at this commit is optional OpenAI AI Assist.

## SQLite and FTS5

Purpose:

- Store indexed file metadata, extracted text, latest results, schema version, and semantic chunks.
- Provide keyword search through SQLite FTS5.

Source:

- `kgfs/db/connection.py`
- `kgfs/db/schema.py`
- `kgfs/search/keyword.py`

Diagnostics:

```bash
kgfs doctor
```

`doctor` reports whether SQLite FTS5 is available.

## platformdirs

Purpose:

- Resolve user config/data/cache/log directories by OS.

Source:

- `kgfs/core/app_dirs.py`
- `pyproject.toml`

Overrides:

- `KGFS_CONFIG_DIR`
- `KGFS_DATA_DIR`
- `KGFS_CACHE_DIR`
- `KGFS_LOG_DIR`
- `--project-local`

## OS Open and Reveal

Purpose:

- Open or reveal indexed files from search results.

Source:

- `kgfs/core/platform_utils.py`
- `kgfs/cli/commands/open_reveal.py`
- `kgfs/web/app.py`

Behavior:

| Platform | Open | Reveal |
|---|---|---|
| Windows | `os.startfile` | `explorer /select,<path>` with folder fallback |
| macOS | `open <path>` | `open -R <path>` with folder fallback |
| Other | `xdg-open <path>` | `xdg-open <containing folder>` |

Tests: `tests/test_platform_utils.py`, `tests/test_platform_boundary.py`.

## Typer and Rich

Purpose:

- Typer defines the `kgfs` CLI app and command parameters.
- Rich renders console tables, status messages, and highlighted snippets.

Source:

- `kgfs/cli/app.py`
- `kgfs/cli/shared.py`
- `kgfs/cli/commands/*.py`
- `pyproject.toml`

Notes:

- The console script is declared as `kgfs = "kgfs.cli:app"`.
- Search highlighting uses Rich `[bold]...[/bold]` markup when `search.highlight_matches` is true.

Tests: `tests/test_cli.py`, `tests/test_snippets.py`.

## Pydantic and PyYAML

Purpose:

- Pydantic validates the YAML config into `KGFSConfig` and nested settings models.
- PyYAML reads config files and writes folder-command edits.

Source:

- `kgfs/core/config.py`
- `kgfs/core/config_commands.py`
- `pyproject.toml`

Notes:

- Extension config values are normalized to lowercase and dot-prefixed.
- Folder commands use `yaml.safe_dump`, so generated YAML comments are not preserved after add/remove operations.

Tests: `tests/test_config.py`, `tests/test_config_commands.py`.

## pypdf

Purpose:

- Extract text from PDF files.

Source:

- `kgfs/extractors/pdf.py`
- `pyproject.toml`

Settings:

- `extraction.pdf_max_pages`

Failure behavior:

- Missing dependency returns extraction status `error` with message `pypdf is not installed`.
- Parser errors are caught and stored as extraction errors.

## python-docx

Purpose:

- Extract paragraph and table text from DOCX files.

Source:

- `kgfs/extractors/docx.py`
- `pyproject.toml`

Failure behavior:

- Missing dependency returns extraction status `error` with message `python-docx is not installed`.

## sentence-transformers

Purpose:

- Optional local embedding model for semantic and hybrid search.

Source:

- `kgfs/search/semantic.py`
- `pyproject.toml`

Install:

```bash
python -m pip install -e ".[semantic]"
```

Settings:

- `semantic.enabled`
- `semantic.model_name`
- `semantic.chunk_size_chars`
- `semantic.chunk_overlap_chars`
- `semantic.local_files_only`
- `semantic.batch_size`

Important behavior:

- `local_files_only` defaults to true.
- If the model is not already available locally, semantic availability can fail.
- The base PyInstaller package excludes sentence-transformers and model caches.

Tests: `tests/test_semantic.py`, `tests/test_search_kernel.py`.

## Vector Backend Registry

Purpose:

- Route semantic and hybrid chunk search through a configured local vector backend.
- Report vector readiness and clear/rebuild vector data.

Source:

- `kgfs/search/backends/base.py`
- `kgfs/search/backends/__init__.py`
- `kgfs/search/backends/sqlite_scan.py`
- `kgfs/vectors/*.py`

Settings:

- `vectors.backend`
- `vectors.shard_strategy`

Current backend:

- `sqlite_scan` scans local SQLite `chunks`, unpacks float32 BLOBs, computes cosine similarity in Python, applies filters, and returns nearest chunk hits.

Limitations:

- No external vector database integration is implemented.
- `vectors.shard_strategy` is present in config but has no behavior beyond the default placeholder.

Tests: `tests/test_vector_backend.py`, `tests/test_vector_status.py`, `tests/test_vector_commands.py`.

## OpenAI

Purpose:

- Optional AI Assist for answer synthesis and reranking local KGFS results.

Source:

- `kgfs/ai.py`
- `kgfs/cli/commands/search.py`
- `pyproject.toml`

Install:

```bash
python -m pip install -e ".[openai]"
```

Settings:

- `ai.enabled`
- `ai.provider`
- `ai.model`
- `ai.api_key_env`
- `ai.require_confirmation`
- `ai.preview_context_before_send`
- `ai.send_file_paths`
- `ai.redact_home_path`
- `ai.send_full_file_text`
- `ai.max_results_sent`
- `ai.max_chars_per_result`
- `ai.max_total_chars_sent`
- `ai.allow_rerank`
- `ai.allow_answer_synthesis`

API key:

- Read from environment variable named by `ai.api_key_env`.
- Default: `OPENAI_API_KEY`.

Supported provider:

- `openai` only.

Privacy defaults:

- Disabled by default.
- Sends snippets, not full text.
- Omits paths.
- Redacts home path.
- Previews context and asks for confirmation.

Tests: `tests/test_ai.py`, `tests/test_cli.py`.

## FastAPI, Jinja2, Uvicorn

Purpose:

- Local web dashboard.

Source:

- `kgfs/web/app.py`
- `kgfs/web/templates/*.html`
- `kgfs/web/static/style.css`
- `kgfs/cli/commands/web.py`
- `pyproject.toml`

Run:

```bash
kgfs web
```

Default:

- Host `127.0.0.1`
- Port `8765`

Limitations:

- No authentication at this commit.
- Web search is keyword-only.

Tests: `tests/test_web.py`.

## PyInstaller

Purpose:

- Build packaged CLI artifacts for users without a Python environment.

Source:

- `scripts/build_package.py`
- `packaging/pyinstaller/kgfs.spec`
- `packaging/README-packaging.md`

Build:

```bash
python -m pip install -e ".[package]"
python scripts/build_package.py --clean
```

Included assets:

- Runtime modules and base dependencies
- Web templates/static files
- `README.md`
- `LICENSE`
- `config.example.yaml`
- Generated `QUICKSTART-KGFS.txt`

Excluded:

- tests
- pytest tooling
- semantic model stack
- OpenAI SDK

Smoke test:

```bash
python scripts/smoke_test_packaged.py --package dist-packages/KGFS
```

Tests: `tests/test_packaging_scripts.py`.

## GitHub Actions

Purpose:

- CI tests and package artifacts.

Source:

- `.github/workflows/ci.yml`
- `.github/workflows/package.yml`

CI:

- Runs on Windows, macOS, Ubuntu.
- Python 3.11 and 3.12.
- Installs `.[dev]`.
- Runs `python -m pytest`.

Packaging:

- Runs on Windows and macOS.
- Installs `.[dev,package]`.
- Runs tests.
- Builds onedir package.
- Runs packaged smoke test.
- Uploads zip artifacts.

Tests: `tests/test_ci_workflow.py`.

## Build Backend and Test Tooling

Purpose:

- Setuptools builds the Python package.
- Pytest and pytest-mock run the test suite.

Source:

- `pyproject.toml`
- `tests/*.py`

Configuration:

- Build system: `setuptools.build_meta`
- Python requirement: `>=3.11`
- Test path: `tests`
- Pytest options: `-ra`

## Not Present At This Commit

No implementation was found for:

- Docker image/runtime.
- Kubernetes/cloud deployment.
- Background job scheduler or daemon.
- Non-OpenAI AI providers.
- Remote index storage.
- Authentication provider.
- Telemetry backend.
