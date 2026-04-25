# KG File Search (KGFS)

KG File Search is a private local-first file search app. It indexes folders you explicitly choose, extracts text from common document/code formats, searches with SQLite FTS5 keyword ranking, and can optionally add local semantic search with sentence-transformers embeddings.

## Safety Model

- KGFS never indexes your whole drive by default.
- You list folders in `config.yaml`; indexing does not start automatically after init.
- KGFS stores its index locally in a platform app-data folder by default.
- KGFS does not delete, move, rename, or overwrite files being indexed.
- Symlinks are not followed unless `follow_symlinks: true`.
- Noisy/system folders like `.git`, `node_modules`, `Library`, `AppData`, `Program Files`, and game install folders are ignored by default.

## Windows Setup

KGFS uses `platformdirs` on Windows, so the default config and database live under your normal per-user AppData locations. Run `kgfs doctor` after `kgfs init` to see the exact paths on your machine.

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

Edit the generated `config.yaml`, then index and search:

```powershell
kgfs index
kgfs search "Find the Python script where I used pandas to plot CSV data"
kgfs open 1
kgfs reveal 1
```

On Windows, `kgfs open` uses `os.startfile`. `kgfs reveal` uses Explorer selection when the file exists and falls back to opening the containing folder.

## macOS Setup

KGFS uses `platformdirs` on macOS, so the default config and database live under your normal per-user Application Support-style locations. Run `kgfs doctor` after `kgfs init` to see the exact paths on your Mac.

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

Edit the generated `config.yaml`, then index and search:

```bash
kgfs index
kgfs search "Find the PDF about PID control"
kgfs open 1
kgfs reveal 1
```

On macOS, `kgfs open` uses the `open` command. `kgfs reveal` uses Finder's reveal behavior when the file exists and falls back to opening the containing folder.

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

## Example Config

```yaml
indexed_folders:
  - "~/Documents"
  - "~/Downloads"

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
```

## Basic Commands

```bash
kgfs init
kgfs doctor
kgfs index
kgfs search "Find the lab report where I calculated motor torque"
kgfs open 1
kgfs reveal 1
kgfs stats
kgfs config
kgfs web
```

The web dashboard binds to `127.0.0.1` by default.

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
```

Run semantic-only search:

```bash
kgfs semantic "motor torque calculation"
```

Run hybrid search:

```bash
kgfs search "motor torque calculation" --hybrid
```

Hybrid search combines SQLite FTS5 keyword score, semantic chunk similarity, filename/path relevance, and a small recent-modification bonus. Results show the best matching snippet or semantic chunk.

Embeddings are stored wherever the KGFS SQLite database is stored. Run `kgfs doctor` to see the database path and `kgfs stats` to see semantic chunk count and embedding storage size.

Expected embedding disk usage depends on chunk count and vector dimensions. With MiniLM-style 384-dimensional float32 vectors, the raw vector payload is about 1.5 KB per chunk, plus SQLite row overhead and stored chunk text. A few thousand chunks are usually tens of MB rather than GB.

## Add a Folder to Index

Open your generated `config.yaml` and add a path under `indexed_folders`. Paths may use `~`, spaces, unicode characters, apostrophes, and parentheses.

Then run:

```bash
kgfs doctor
kgfs index
kgfs search "notes about op-amps"
```

## Reset or Rebuild the Index

KGFS indexes into a SQLite database shown by `kgfs doctor`. To rebuild, stop KGFS and delete only that database file, then run:

```bash
kgfs index
```

Do not delete your source folders. KGFS does not need elevated privileges.

## Troubleshooting Permissions

Run:

```bash
kgfs doctor
```

It checks configured folders, readability, config/data/cache/log paths, database path, Python version, OS, path separator, home directory, open/reveal strategy, and SQLite FTS5 support. If a folder is unreadable, remove it from `indexed_folders` or grant normal user read permissions.

## Tests

```bash
python -m pytest
```
