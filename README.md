# KG File Search (KGFS)

KG File Search is a private local-first file search app. It indexes folders you explicitly choose, extracts text from common document/code formats, searches with SQLite FTS5 keyword ranking, and can optionally add local semantic search with sentence-transformers embeddings.

## Documentation

The detailed documentation set lives in `docs/README.md`. It covers features,
settings, CLI usage, web routes, architecture, data model, integrations,
security, development, troubleshooting, and examples. The docs are written
against the current worktree and include source-file references for verification.

## Safety Model

- KGFS never indexes your whole drive by default.
- You list folders in `config.yaml`; indexing does not start automatically after init.
- KGFS stores its index locally in a platform app-data folder by default.
- KGFS does not delete, move, rename, or overwrite files being indexed.
- Symlinks are not followed unless `follow_symlinks: true`.
- Noisy/system folders like `.git`, `node_modules`, `Library`, `AppData`, `Program Files`, and game install folders are ignored by default.

## Windows Setup

KGFS uses `platformdirs` on Windows, so the default config and database live under your normal per-user AppData locations. Run `kgfs doctor` after `kgfs init` to see the exact paths on your machine. The generated config starts with `indexed_folders: []`; add folders deliberately before indexing.

```powershell
cd "C:\path\to\kg-file-search"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
kgfs init
kgfs doctor
```

Install optional semantic dependencies when you want local embedding search:

```powershell
python -m pip install -e ".[dev,semantic]"
```

Install optional OpenAI AI Assist dependencies only when you want API-backed summaries or reranking:

```powershell
python -m pip install -e ".[dev,openai]"
```

Edit the generated `config.yaml`, add one or more specific folders, then index and search:

```powershell
kgfs index
kgfs search "Find the Python script where I used pandas to plot CSV data"
kgfs open 1
kgfs reveal 1
```

On Windows, `kgfs open` uses `os.startfile`. `kgfs reveal` uses Explorer selection when the file exists and falls back to opening the containing folder.

## macOS Setup

KGFS uses `platformdirs` on macOS, so the default config and database live under your normal per-user Application Support-style locations. Run `kgfs doctor` after `kgfs init` to see the exact paths on your Mac. The generated config starts with `indexed_folders: []`; add folders deliberately before indexing.

```bash
cd /path/to/kg-file-search
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
kgfs init
kgfs doctor
```

Install optional semantic dependencies when you want local embedding search:

```bash
python -m pip install -e ".[dev,semantic]"
```

Install optional OpenAI AI Assist dependencies only when you want API-backed summaries or reranking:

```bash
python -m pip install -e ".[dev,openai]"
```

Edit the generated `config.yaml`, add one or more specific folders, then index and search:

```bash
kgfs index
kgfs search "Find the PDF about PID control"
kgfs open 1
kgfs reveal 1
```

On macOS, `kgfs open` uses the `open` command. `kgfs reveal` uses Finder's reveal behavior when the file exists and falls back to opening the containing folder.

## Installing from Packaged Builds

Packaged KGFS builds are meant for users who do not want to install Python or pip dependencies manually. Each package contains the KGFS CLI executable plus docs and example config files. Runtime config, data, cache, logs, and databases still live in normal platformdirs locations on your machine.

Download the zip artifact for your OS:

- Windows x64: `KGFS-windows-x64.zip`
- macOS Apple Silicon: `KGFS-macos-arm64.zip`
- macOS Intel, when built on an Intel runner: `KGFS-macos-x64.zip`

Unzip the artifact, open a terminal in the extracted folder, and run:

Windows PowerShell:

```powershell
.\kgfs.exe doctor
.\kgfs.exe init
.\kgfs.exe add-folder "~/Documents/Your Notes"
.\kgfs.exe index
.\kgfs.exe search "motor torque"
```

macOS:

```bash
./kgfs doctor
./kgfs init
./kgfs add-folder "~/Documents/Your Notes"
./kgfs index
./kgfs search "motor torque"
```

If the executable is inside a `KGFS/` folder, run the command from that folder. You can also add that folder to your shell `PATH`.

### Windows Packaged Build

The Windows package contains `kgfs.exe`. It uses the same Windows open/reveal behavior as the Python install: `os.startfile` for opening files and Explorer for revealing them.

Unsigned `.exe` files may trigger Microsoft Defender SmartScreen warnings. This pass does not require Authenticode signing. Future releases can add code signing certificates without changing KGFS runtime behavior.

### macOS Packaged Build

The macOS package contains a `kgfs` executable. It uses the same macOS open/reveal behavior as the Python install: `open` for files and Finder reveal when possible.

Unsigned macOS binaries may trigger Gatekeeper warnings. This pass does not require Apple Developer ID signing or notarization. Future releases can add signing and notarization while keeping unsigned local builds usable for testing.

### Package Contents

Included:

- `kgfs` or `kgfs.exe`
- Runtime Python modules and base dependencies
- Web dashboard templates and static files
- `README.md`
- `LICENSE`
- `config.example.yaml`
- `QUICKSTART-KGFS.txt`

Not included:

- User config files
- User SQLite databases
- User caches or logs
- Indexed personal files
- `.kgfs/`
- `.git/`
- Test fixtures
- Downloaded semantic model caches
- OpenAI SDK, unless a future AI-specific package is intentionally built

### Packaged Build Limitations

The base package keeps semantic search optional and avoids bundling heavyweight local embedding models. Keyword search, indexing, stats, doctor, open/reveal, config management, and the web dashboard are included. For semantic search, use a Python install with `kg-file-search[semantic]` or build a future semantic-specific package.

OpenAI AI Assist is not bundled in the base package unless an AI-specific package is intentionally produced later. The local-first search/indexing path does not depend on OpenAI.

## Development Mode

Project-local mode stores config and the SQLite database in `.kgfs/` under the repo:

```bash
kgfs init --project-local
kgfs index --project-local
kgfs search "op amps" --project-local
```

You can also override paths with:

- CLI flags: `--config`, `--database`
- Environment variables: `KGFS_CONFIG_PATH`, `KGFS_DATABASE_PATH`, `KGFS_PROJECT_LOCAL`
- Config value: `database_path`

Paths can use `~`, spaces, unicode characters, apostrophes, and parentheses. Both `~/Documents` and `~\Documents` are expanded as home-relative config paths.

## Project Structure

KGFS keeps the source layout small and predictable:

- `kgfs/cli/` contains the Typer app and command modules.
- `kgfs/core/` contains shared config, path, platform, resource, and model helpers.
- `kgfs/db/` contains SQLite connection, schema, migrations, repositories, latest results, and stats helpers.
- `kgfs/indexing/` contains discovery, filtering, hashing, indexing, and pruning.
- `kgfs/search/` contains FTS query helpers, filters, ranking, snippets, semantic helpers, and search orchestration.
- `kgfs/extractors/` contains file text extraction by type.
- `kgfs/web/` contains the FastAPI dashboard.

See `docs/architecture.md` for maintainer guidance on where to add future commands, extractors, migrations, search modes, and packaging changes.

## Example Config

```yaml
indexed_folders:
  - "~/Documents/School Notes"
  - "~/Documents/Projects/KGFS Test Corpus"

ignored_folders:
  - ".git"
  - "node_modules"
  - ".venv"
  - "venv"
  - "__pycache__"
  - "build"
  - "dist"

include_extensions:
  - ".txt"
  - ".md"
  - ".py"
  - ".js"
  - ".ts"
  - ".html"
  - ".css"
  - ".json"
  - ".csv"
  - ".docx"
  - ".pdf"

ignored_extensions:
  - ".exe"
  - ".dll"
  - ".dylib"
  - ".so"
  - ".app"
  - ".mp4"
  - ".mov"
  - ".mp3"
  - ".wav"
  - ".zip"
  - ".7z"
  - ".rar"

max_file_size_mb: 25
follow_symlinks: false

indexing:
  store_extracted_text: true
  skip_unchanged_files: true
  hash_files: true

semantic:
  enabled: false
  model_name: "sentence-transformers/all-MiniLM-L6-v2"
  chunk_size_chars: 1200
  chunk_overlap_chars: 200
  local_files_only: true
  batch_size: 16

search:
  default_mode: "auto"
  default_limit: 10
  highlight_matches: true
  save_latest_results: true

vectors:
  backend: "sqlite_scan"
  shard_strategy: "none"

ai:
  enabled: false
  provider: "openai"
  model: "gpt-5.4-nano"
  api_key_env: "OPENAI_API_KEY"
  require_confirmation: true
  preview_context_before_send: true
  send_file_paths: false
  redact_home_path: true
  send_full_file_text: false
  max_results_sent: 12
  max_chars_per_result: 1500
  max_total_chars_sent: 12000
  allow_query_expansion: true
  allow_rerank: true
  allow_answer_synthesis: true
```

## Basic Commands

```bash
kgfs init
kgfs doctor
kgfs add-folder "~/Documents/School Notes"
kgfs list-folders
kgfs index
kgfs search "Find the lab report where I calculated motor torque"
kgfs ask "Which local notes mention motor torque?"
kgfs open 1
kgfs reveal 1
kgfs stats
kgfs prune --dry-run
kgfs config
kgfs web
```

The web dashboard binds to `127.0.0.1` by default.

If `indexed_folders` is empty, `kgfs index` prints a setup message and exits without creating a database.

KGFS refuses risky broad roots by default, including `/`, drive roots like `C:\`, your home directory itself, and obvious system roots. Use `--allow-risky-root` only when you intentionally want a very broad scan:

```bash
kgfs index --allow-risky-root
```

## Building Packages Locally

PyInstaller packaging is optional and separate from normal dev/test dependencies:

Windows PowerShell:

```powershell
python -m pip install -e ".[package]"
python scripts/build_package.py --clean
python scripts/smoke_test_packaged.py --package dist-packages/KGFS
```

macOS:

```bash
python -m pip install -e ".[package]"
python scripts/build_package.py --clean
python scripts/smoke_test_packaged.py --package dist-packages/KGFS
```

The default build mode is PyInstaller `onedir`, which is easier to debug and more reliable with data files. An experimental onefile mode is available:

```bash
python scripts/build_package.py --clean --mode onefile
```

Build output and zip artifacts are written under `dist-packages/`. The build script also creates a packaged quickstart and includes `README.md`, `LICENSE`, and `config.example.yaml` in the zip.

## Building Packages in GitHub Actions

The packaging workflow is `.github/workflows/package.yml`, shown in GitHub as **Package**. It runs on:

- pushes to `main`
- pull requests
- manual `workflow_dispatch`
- tags matching `v*`

The workflow builds on:

- `windows-latest`
- `macos-latest`

For each runner it installs `.[dev,package]`, runs `python -m pytest`, builds with `python scripts/build_package.py --clean --mode onedir`, runs `python scripts/smoke_test_packaged.py --package dist-packages/KGFS`, and uploads the zip artifact.

Artifacts appear on the workflow run page under **Artifacts** with names like:

- `KGFS-windows-x64`
- `KGFS-macos-arm64`
- `KGFS-macos-x64`

This pass uploads workflow artifacts only. Creating GitHub Releases and attaching artifacts can be added later for version tags.

## Troubleshooting Packaged Builds

Run:

```bash
kgfs doctor
```

In packaged builds, doctor reports whether KGFS is frozen/packaged, the executable path, config path, data path, cache path, database path, platform info, and SQLite FTS5 availability.

If the web dashboard cannot find templates or static files, rebuild from a clean checkout:

```bash
python scripts/build_package.py --clean
```

If SmartScreen or Gatekeeper blocks the executable, verify the artifact source and allow the unsigned local build according to your OS security prompts.

## Managing Indexed Folders

You can edit `config.yaml` directly or use the folder commands. These commands only update KGFS config; they do not start indexing by themselves.

```bash
kgfs add-folder "~/Documents/School Notes"
kgfs add-folder "/path/with spaces/Project Notes"
kgfs list-folders
kgfs remove-folder "~/Documents/School Notes"
```

KGFS expands `~` safely on Windows and macOS, avoids duplicate folders, and warns when a folder is missing or looks risky, such as a drive root, home root, `Library`, `AppData`, `Program Files`, or another broad/system location.

## Indexing Performance

Incremental indexing checks file size and precise modified time first. Unchanged files are skipped without hashing, which makes daily re-indexing faster. When you need stronger verification or a full refresh, use:

```bash
kgfs index --verify-hashes
kgfs index --force
kgfs index --prune
```

- `--verify-hashes` hashes files even when size and modified time look unchanged.
- `--force` re-extracts and re-indexes every discovered file.
- `--prune` removes stale KGFS database records after indexing. It never deletes source files.

## Search Filters

Keyword search, hybrid search, and AI reranking all start from local KGFS results and can use filters:

```bash
kgfs search "pid control" --ext .pdf
kgfs search "op amps" --folder "Circuits Class"
kgfs search "motor torque" --after 2025-01-01 --before 2026-01-01
kgfs search "speaker crossover" --limit 25
kgfs search "pdf extraction issue" --failed-only
kgfs search "motor torque" --hybrid --ext .md
kgfs search "motor torque" --mode auto
kgfs search "motor torque" --mode keyword
kgfs search "motor torque" --ai-rerank --ext .md --preview-ai-context
```

Extension matching is case-insensitive. Folder filtering matches path text in a way that works with Windows `\` and POSIX `/` separators. Date filters use each file's modified time.

Search ranking still uses SQLite FTS5 as the base, then applies lightweight boosts for filename matches, path matches, exact phrase matches in extracted text, and a modest recent-modification bonus.

## Search Modes

KGFS now routes search through a small search kernel. The CLI behavior stays familiar, but internally each mode implements the same simple engine interface.

- `keyword` is the reliable local SQLite FTS5 mode. It does not require semantic dependencies.
- `semantic` searches local semantic chunks when semantic search is enabled and embeddings have been built.
- `hybrid` combines keyword, semantic, filename, path, exact phrase, and recency scoring when semantic search is ready.
- `auto` picks hybrid when semantic/vector data is ready; otherwise it uses keyword and prints a warning if semantic was enabled but unavailable.

Examples:

```bash
kgfs search "motor torque" --mode keyword
kgfs search "motor torque" --mode semantic
kgfs search "motor torque" --mode hybrid
kgfs search "motor torque" --mode auto
```

`--hybrid` remains supported as a compatibility shortcut for `--mode hybrid`. Advanced vector backends, deep search, similar-file search, and multimodal/OCR search are planned for later phases and are not part of this phase.

Explain a saved result from the latest search:

```bash
kgfs why 1 "motor torque"
```

`kgfs why` reruns local search, shows the mode used, final score, score breakdown, and matching snippet, and never calls AI.

## Semantic Search

KGFS keeps SQLite FTS5 keyword search and adds an optional semantic layer. When `semantic.enabled: true`, indexing splits extracted text into chunks, embeds each chunk with a local sentence-transformers model, and stores those vectors in the same local SQLite database in a `chunks` table.

Semantic chunk rows include:

- `file_id`
- `chunk_index`
- chunk `text`
- `embedding` as a SQLite BLOB
- `start_char` and `end_char`
- `model_name`

KGFS does not call cloud APIs. The default model is the small practical `sentence-transformers/all-MiniLM-L6-v2`, and `local_files_only: true` is enabled by default. That means the model must already be available in the local sentence-transformers cache or you can set `model_name` to a local model directory.

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

Build or rebuild embeddings:

```bash
kgfs index --rebuild-embeddings
kgfs semantic-index --rebuild
kgfs vector rebuild
```

Check semantic index status:

```bash
kgfs semantic-index
kgfs vector status
```

Run semantic-only search:

```bash
kgfs semantic "motor torque calculation"
```

Run hybrid search:

```bash
kgfs search "motor torque calculation" --hybrid
```

Hybrid search combines SQLite FTS5 keyword score, semantic chunk similarity, filename relevance, path relevance, exact phrase relevance, and a small recent-modification bonus. Results show the best matching snippet or semantic chunk and carry a serializable score breakdown.

Tune hybrid scoring in config if needed:

```yaml
hybrid:
  keyword_weight: 0.35
  semantic_weight: 0.45
  filename_weight: 0.15
  path_weight: 0.05
  exact_phrase_weight: 0.10
  recency_weight: 0.05
  candidate_limit_multiplier: 5
```

Embeddings are stored wherever the KGFS SQLite database is stored. Run `kgfs doctor` to see the database path and `kgfs stats` to see semantic chunk count and embedding storage size.

Expected embedding disk usage depends on chunk count and vector dimensions. With MiniLM-style 384-dimensional float32 vectors, the raw vector payload is about 1.5 KB per chunk, plus SQLite row overhead and stored chunk text. A few thousand chunks are usually tens of MB rather than GB.

## Vector Foundation

Semantic search goes through a local vector backend interface. The default backend is `sqlite_scan`, which reads the existing SQLite `chunks` table, unpacks stored embedding BLOBs, and computes similarity in Python. It is simple and dependency-light; it does not use FAISS, hnswlib, sqlite-vec, cloud APIs, OCR, or a separate vector database.

Vector commands manage only KGFS vector/chunk data:

```bash
kgfs vector status
kgfs vector rebuild
kgfs search "motor torque" --mode semantic
kgfs search "motor torque" --mode hybrid
kgfs vector clear --yes
```

`kgfs vector rebuild` uses extracted text already stored in the KGFS database, so it does not need to re-read or modify source files. `kgfs vector clear --yes` deletes semantic chunks for the configured model only; it leaves source files, file records, and keyword FTS rows intact. Keyword search remains independent and works without semantic dependencies.

Advanced vector backends are planned for a later phase.

## OpenAI AI Assist

AI Assist is optional and off by default. KGFS remains local-first: indexing, keyword search, semantic search, open/reveal, and stats work without OpenAI and do not call cloud APIs.

OpenAI API billing is separate from any ChatGPT subscription. If you enable AI Assist, usage is billed to the OpenAI API account associated with your API key.

Install the optional dependency:

```bash
python -m pip install -e ".[openai]"
```

Set your API key in the environment. Do not put API keys in `config.yaml`.

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="sk-..."
```

macOS/Linux:

```bash
export OPENAI_API_KEY="sk-..."
```

Enable AI Assist explicitly:

```yaml
ai:
  enabled: true
  provider: "openai"
  model: "gpt-5.4-nano"
  api_key_env: "OPENAI_API_KEY"
  require_confirmation: true
  preview_context_before_send: true
  send_file_paths: false
  redact_home_path: true
  send_full_file_text: false
  max_results_sent: 12
  max_chars_per_result: 1500
  max_total_chars_sent: 12000
  allow_query_expansion: true
  allow_rerank: true
  allow_answer_synthesis: true
```

Privacy defaults:

- KGFS runs local search first and sends only top snippets/chunks.
- Search filters are applied before AI Assist sees any result snippets.
- Full file text is not sent unless `send_full_file_text: true`.
- File paths are not sent unless `send_file_paths: true`.
- Your home path is redacted by default.
- `--preview-ai-context` prints the exact context and makes no API call.
- By default, KGFS asks for confirmation before sending context.

Preview context:

```bash
kgfs ask "What do my notes say about op-amps?" --preview-ai-context
kgfs search "motor torque" --ai-rerank --preview-ai-context
```

Ask a question using local result snippets:

```bash
kgfs ask "What do my notes say about op-amps?"
```

Rerank local results with AI Assist:

```bash
kgfs search "speaker crossover design" --ai-rerank
```

## Add a Folder to Index

Open your generated `config.yaml` and add a path under `indexed_folders`, or use `kgfs add-folder`. Paths may use `~`, spaces, unicode characters, apostrophes, and parentheses.

The generated config does not index `~/Documents`, `~/Downloads`, or `~/Desktop` automatically. Those appear only as commented examples so KGFS starts from a no-scan default.

Then run:

```bash
kgfs list-folders
kgfs doctor
kgfs index
kgfs search "notes about op-amps"
```

## Prune, Reset, or Rebuild the Index

Prune removes stale KGFS database records whose source files no longer exist. It never deletes source files:

```bash
kgfs prune --dry-run
kgfs prune
```

Reset removes only KGFS database/index files, never indexed source folders:

```bash
kgfs reset-index --dry-run
kgfs reset-index --yes
```

Rebuild resets the KGFS database and then indexes the configured folders:

```bash
kgfs rebuild --yes
```

Do not delete your source folders. KGFS does not need elevated privileges.

## Schema Versions and Migrations

KGFS stores the SQLite schema version in the database and runs idempotent migrations during initialization. Current schema version is reported by:

```bash
kgfs doctor
kgfs stats
```

Version 1 is the initial KGFS schema, including `files`, `files_fts`, `latest_results`, semantic `chunks`, and precise `modified_time_ns` metadata for faster incremental indexing.

## Troubleshooting Permissions

Run:

```bash
kgfs doctor
```

It checks configured folders, readability, config/data/cache/log paths, database path, Python version, OS, path separator, home directory, open/reveal strategy, and SQLite FTS5 support. If a folder is unreadable, remove it from `indexed_folders` or grant normal user read permissions.

`kgfs doctor` also reports config/database existence, schema version, risky-folder warnings, semantic dependency status, and optional PDF/DOCX/OpenAI dependency availability.

## Tests

```bash
python -m pytest
```
