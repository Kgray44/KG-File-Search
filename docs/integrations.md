# Integrations

KGFS is local-first. Most integrations are local libraries, local UI surfaces, local OS helpers, or scaffold files that shell out to the KGFS CLI. The only cloud integration at this commit is optional OpenAI AI Assist.

## SQLite and FTS5

Purpose:

- Store indexed file metadata, extracted text, latest results, schema version, semantic chunks, OCR cache rows, workflow metadata, and file-intelligence metadata.
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

## Tesseract OCR

Purpose:

- Optional local OCR for supported image files.
- Safe scanned/image-only PDF detection when normal PDF text extraction finds very little text.

Source:

- `kgfs/ocr/tesseract.py`
- `kgfs/ocr/status.py`
- `kgfs/extractors/image_ocr.py`
- `kgfs/extractors/pdf.py`

Install:

Tesseract is an external executable and is not installed by KGFS. Install it
with your OS package manager or installer, then set:

```yaml
ocr:
  enabled: true
  tesseract:
    command: "tesseract"
    language: "eng"
```

Optional Python extra:

```bash
python -m pip install -e ".[ocr]"
```

Behavior:

- Missing Tesseract reports a helpful status/extraction error.
- OCR output is stored in KGFS database/cache rows.
- Source images and PDFs are never modified.
- No cloud OCR is used.

Tests: `tests/test_ocr_backend.py`, `tests/test_ocr_indexing.py`, `tests/test_ocr_pdf.py`.

## Optional Media and Advanced OCR Packages

Purpose:

- Read local photo/EXIF metadata.
- Provide lazy optional local adapters/contracts for EasyOCR, PaddleOCR, captions, audio transcription, and visual embeddings.

Source:

- `kgfs/media/*.py`
- `kgfs/ocr/easyocr.py`
- `kgfs/ocr/paddle.py`
- `kgfs/ocr/cloud.py`
- `kgfs/models/*.py`
- `pyproject.toml`

Install:

```bash
python -m pip install -e ".[media]"
python -m pip install -e ".[ocr-easyocr]"
python -m pip install -e ".[ocr-paddle]"
python -m pip install -e ".[captions]"
python -m pip install -e ".[audio]"
python -m pip install -e ".[visual]"
```

Behavior:

- Media features are disabled by default.
- Pillow is optional and used only when EXIF metadata is read.
- EasyOCR/PaddleOCR are imported only when their backends are selected/enabled.
- Caption/audio/visual backends default to `none`; generated text and embeddings stay in KGFS DB/cache paths when a backend is enabled.
- `kgfs models doctor`, `kgfs models validate`, and `kgfs models config-snippet BACKEND` help users configure optional local backends without editing config automatically or downloading model files.
- Cloud OCR fallback is disabled and scaffolded to refuse upload in this phase.
- Generated metadata/text lives in KGFS database/cache paths only.

Tests: `tests/test_phase10_media.py`, `tests/test_phase10_1_local_models.py`, `tests/test_phase10_2_local_model_setup.py`.

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
- Report vector readiness, clear/rebuild vector data, benchmark backends, and recommend a backend.

Source:

- `kgfs/search/backends/base.py`
- `kgfs/search/backends/registry.py`
- `kgfs/search/backends/sqlite_scan.py`
- `kgfs/search/backends/sqlite_vec.py`
- `kgfs/search/backends/hnsw.py`
- `kgfs/search/backends/faiss.py`
- `kgfs/vectors/*.py`

Settings:

- `vectors.backend`
- `vectors.shard_strategy`

Known backends:

- `sqlite_scan`: default, base-install backend. Scans local SQLite `chunks`, unpacks float32 BLOBs, computes cosine similarity in Python, applies filters, and returns nearest chunk hits.
- `sqlite_vec`: optional experimental SQLite-native backend. When installed and enabled, rebuild creates a sqlite-vec table from existing chunk embeddings.
- `hnsw`: optional hnswlib ANN backend. When installed and enabled, rebuild stores an HNSW index artifact under KGFS vector-backend storage.
- `faiss`: optional power-user FAISS flat backend. When installed and enabled, rebuild stores a FAISS index artifact under KGFS vector-backend storage.

Limitations:

- Optional advanced backends are not bundled in the base package.
- Optional backends must not fake successful search when dependencies, artifacts, or metadata are unavailable.
- `vectors.shard_strategy` is present in config but has no behavior beyond the default placeholder.

Tests: `tests/test_vector_backend.py`, `tests/test_vector_backend_registry.py`, `tests/test_vector_status.py`, `tests/test_vector_commands.py`, `tests/test_vector_benchmark.py`, `tests/test_vector_recommend.py`.

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

- Local web dashboard and local JSON API server.

Source:

- `kgfs/web/app.py`
- `kgfs/web/templates/*.html`
- `kgfs/web/static/style.css`
- `kgfs/api/*.py`
- `kgfs/cli/commands/web.py`
- `kgfs/cli/commands/serve.py`
- `pyproject.toml`

Run:

```bash
kgfs web
export KGFS_API_TOKEN="dev-token"
kgfs serve
```

Default:

- Dashboard host `127.0.0.1`, port `8765`
- API host `127.0.0.1`, port `8766`

Safety:

- The HTML dashboard has no auth and should stay localhost-only.
- The JSON API requires a bearer token by default.
- `kgfs serve` refuses non-localhost binds unless `--allow-network` is supplied.
- API open/reveal actions are disabled unless `api.allow_file_actions: true`, and they use latest result IDs rather than arbitrary paths.

Tests: `tests/test_web.py`, `tests/test_phase9_ux_integrations.py`.

## Textual TUI

Purpose:

- Optional terminal UI launcher for everyday local search workflows.

Source:

- `kgfs/tui/*.py`
- `kgfs/cli/commands/tui.py`
- `pyproject.toml`

Install:

```bash
python -m pip install -e ".[tui]"
```

Run:

```bash
kgfs tui --check
kgfs tui
```

Behavior:

- Textual is imported lazily only when `kgfs tui` runs.
- Missing Textual prints an install hint and does not break normal CLI startup.
- The current TUI is a minimal scaffold for search-focused interaction.

Tests: `tests/test_phase9_ux_integrations.py`.

## Launcher and OS Integration Scaffolds

Purpose:

- Generate local templates users can inspect and install manually for Raycast, Alfred, PowerToys Run, Finder Quick Actions, Explorer context-menu experiments, and tray/menu-bar experiments.

Source:

- `kgfs/integrations/*.py`
- `kgfs/cli/commands/integrations.py`

Commands:

```bash
kgfs integrations status
kgfs integrations raycast export --output ./kgfs-raycast
kgfs integrations alfred export --output ./kgfs-alfred
kgfs integrations powertoys scaffold --output ./kgfs-powertoys
kgfs integrations finder scaffold --output ./kgfs-finder
kgfs integrations explorer scaffold --output ./kgfs-explorer
kgfs tray scaffold --output ./kgfs-tray
```

Safety:

- Scaffold commands write only to the chosen output directory or KGFS app-data integration directory.
- They do not edit the Windows registry, Finder services, Raycast, Alfred, PowerToys, startup items, or system paths.
- Explorer `.reg` output is a template only.

Tests: `tests/test_phase9_ux_integrations.py`.

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
- optional vector backend packages such as sqlite-vec, hnswlib, FAISS, and numpy
- optional OCR helper packages such as PIL/pytesseract/EasyOCR/PaddleOCR
- optional media/model packages such as Whisper, CLIP-style stacks, Paddle, TorchVision, and OpenCV
- Tesseract executable and OCR user cache/data
- Textual and tray optional dependencies
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
- External authentication provider beyond the local API bearer-token check.
- Telemetry backend.
- Cloud OCR providers beyond the no-upload scaffold.
- Automatic Raycast/Alfred/PowerToys/Finder/Explorer installation.
- Running tray/menu-bar daemon.
