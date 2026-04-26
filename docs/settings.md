# Settings and Configuration Reference

KGFS settings come from YAML config, CLI flags, environment variables, and runtime options passed by library callers. The main config model is `KGFSConfig` in `kgfs/core/config.py`; the generated example is `config.example.yaml`.

## Resolution Order

| Setting family | Resolution order | Source |
|---|---|---|
| Config path | CLI `--config` > `KGFS_CONFIG_PATH` > app config dir `config.yaml` | `kgfs/core/app_dirs.py` |
| Database path | CLI `--database` > `KGFS_DATABASE_PATH` > `database_path` in YAML > app data dir `kgfs.sqlite3` | `kgfs/core/app_dirs.py`, `kgfs/cli/shared.py` |
| App config/data/cache/log dirs | Project-local `.kgfs/` when enabled, otherwise explicit directory overrides/env vars, otherwise platformdirs | `kgfs/core/app_dirs.py` |
| Search mode | CLI `--hybrid` > CLI `--mode` > `search.default_mode` | `kgfs/cli/commands/search.py` |
| Search limit | CLI `--limit` > `search.default_limit` for search; `ai.max_results_sent` for ask | `kgfs/cli/commands/search.py` |
| AI API key | Environment variable named by `ai.api_key_env` | `kgfs/ai.py` |

## Environment Variables

| Variable | Default | Valid values | Required | Read from | Behavior if missing or invalid |
|---|---:|---|---|---|---|
| `KGFS_CONFIG_PATH` | App config dir `config.yaml` | Path | No | `resolve_config_path()` in `kgfs/core/app_dirs.py` | Missing uses default. Invalid/missing target can cause config-loading commands to fail unless the command uses optional config runtime. |
| `KGFS_DATABASE_PATH` | App data dir `kgfs.sqlite3` or YAML `database_path` | Path | No | `resolve_database_path()` in `kgfs/core/app_dirs.py` | Missing falls back to YAML/default. Parent directory is created by `connect_database()`. |
| `KGFS_CONFIG_DIR` | platformdirs user config dir | Path | No | `get_app_paths()` in `kgfs/core/app_dirs.py` | Used only when not project-local. Missing uses platformdirs. |
| `KGFS_DATA_DIR` | platformdirs user data dir | Path | No | `get_app_paths()` in `kgfs/core/app_dirs.py` | Used only when not project-local. Missing uses platformdirs. |
| `KGFS_CACHE_DIR` | platformdirs user cache dir | Path | No | `get_app_paths()` in `kgfs/core/app_dirs.py` | Used only when not project-local. Missing uses platformdirs. |
| `KGFS_LOG_DIR` | platformdirs user log dir | Path | No | `get_app_paths()` in `kgfs/core/app_dirs.py` | Used only when not project-local. Missing uses platformdirs. |
| `KGFS_PROJECT_LOCAL` | false | `1`, `true`, `yes`, `on` are truthy | No | `get_app_paths(project_local=None)` in `kgfs/core/app_dirs.py`; smoke script also sets it | Prefer CLI `--project-local` for KGFS commands because current CLI commands pass an explicit boolean default. |
| `OPENAI_API_KEY` | None | OpenAI API key string | Required only for AI Assist with default `ai.api_key_env` | `get_openai_api_key()` in `kgfs/ai.py` | Missing raises `AIError`; CLI reports it as a bad parameter. |
| Custom AI key env var | None | Env var named by `ai.api_key_env` | Required if `ai.api_key_env` is changed and AI is used | `kgfs/ai.py` | Missing raises `AIError` naming the configured variable. |
| `KGFS_PYINSTALLER_MODE` | `onedir` | `onedir`, `onefile` | No | `packaging/pyinstaller/kgfs.spec`, set by `scripts/build_package.py` | Controls PyInstaller spec branch. `scripts/build_package.py --mode` should set this. |
| `KGFS_PACKAGE_NAME` | `KGFS` | Folder/name string | No | `packaging/pyinstaller/kgfs.spec`, set by `scripts/build_package.py` | Used for onedir `COLLECT` name. |
| `COLUMNS` | Unset | Integer text | No | `scripts/smoke_test_packaged.py` sets `160` for subprocess output | Only affects packaged smoke-test terminal formatting. |

## Config File Keys

### Top-Level Keys

| Key | Type | Default | Required | Valid values | Read from | Missing behavior | Invalid behavior |
|---|---|---|---|---|---|---|---|
| `indexed_folders` | list of paths | `[]` | No | Folder paths or a file path | `KGFSConfig`, discovery, CLI folder commands | Empty list means `kgfs index` prints setup message and does not create DB. | Pydantic validation errors can occur for incompatible types. Missing paths are skipped during discovery. |
| `ignored_folders` | list of names | See default list below | No | Directory names | `should_skip_dir()` | Defaults applied. | Non-strings are converted by Pydantic/model use; matching uses `path.name in set(...)`. |
| `include_extensions` | list of extensions | `.txt`, `.md`, `.py`, `.js`, `.ts`, `.html`, `.css`, `.json`, `.csv`, `.docx`, `.pdf` | No | Extensions with or without leading dot | `KGFSConfig`, `should_index_file()` | Defaults applied. | Values are lowercased and dot-prefixed. Empty list removes allowlist filtering. |
| `ignored_extensions` | list of extensions | See default list below | No | Extensions with or without leading dot | `KGFSConfig`, `should_index_file()` | Defaults applied. | Values are lowercased and dot-prefixed. |
| `exclude_globs` | list of glob patterns | `~$*`, `*.tmp` | No | Filename or path glob patterns | `should_index_file()` | Defaults applied. | Applied with `fnmatch()` to file name and POSIX path text. |
| `max_file_size_mb` | int | `25` | No | Integer megabytes | `KGFSConfig.max_file_size_bytes`, filters | Defaults applied. | Pydantic type validation. Very small values can skip most files. |
| `follow_symlinks` | bool | `false` | No | `true` or `false` | Discovery and filters | Defaults to no symlink traversal. | Pydantic type validation. |
| `database_path` | path or null | `null` | No | Path | CLI runtime and app dirs | Null falls back to app data database path. | Path expansion is applied; parent is created on DB connect. |
| `indexing` | object | See below | No | `IndexingSettings` fields | Indexer | Defaults applied. | Unknown behavior follows Pydantic defaults; extra-key policy is not explicitly configured in source. |
| `extraction` | object | See below | No | `ExtractionSettings` fields | Extractors/indexer | Defaults applied. | Pydantic type validation. |
| `ocr` | object | See below | No | `OCRSettings` fields | Image/PDF extraction, OCR commands, doctor/stats | Defaults disabled. | Image extensions are normalized; source-file modification is forced off in this phase. |
| `semantic` | object | See below | No | `SemanticSettings` fields | Indexer/search/doctor | Defaults disabled. | Some invalid numeric values are clamped in `chunk_text()` rather than rejected. |
| `search` | object | See below | No | `SearchSettings` fields | CLI search | Defaults applied. | Invalid mode is detected when creating `SearchOptions`, not at config load. |
| `deep_search` | object | See below | No | `DeepSearchSettings` fields | `kgfs deep`, `kgfs research` | Defaults enabled for local-only multi-pass search. | Non-positive numeric values fall back to safe defaults. |
| `research` | object | See below | No | `ResearchSettings` fields | `kgfs research` | Defaults applied. | Non-positive numeric values fall back to safe defaults. |
| `similar` | object | See below | No | `SimilarSettings` fields | `kgfs similar`, `kgfs similar-file` | Defaults applied. | Limit is clamped positive; minimum score is clamped non-negative. |
| `timeline` | object | See below | No | `TimelineSettings` fields | `kgfs timeline` | Defaults applied. | Non-positive limit falls back to the default. |
| `profiles` | object | `{}` | No | named `ProfilePresetSettings` fields | Config presets and documentation; user-created profiles live in DB | Empty mapping by default. | Null becomes `{}`; profile extension values are normalized. |
| `assignment` | object | See below | No | `AssignmentSettings` fields | `kgfs assignment` | Defaults applied. | Limit is clamped positive; extensions are normalized. |
| `projects` | object | See below | No | `ProjectsSettings` fields | `kgfs project search` | Defaults applied. | Non-positive limit falls back to the default. |
| `vectors` | object | See below | No | `VectorSettings` fields | Semantic/hybrid search and vector commands | Defaults applied. | Unknown backend names make semantic/hybrid unavailable and vector rebuild/clear fail with known-backend guidance. |
| `hybrid` | object | See below | No | `HybridSettings` fields | Hybrid ranking | Defaults applied. | Numeric weights are coerced; invalid/negative values are made safe at runtime. |
| `ai` | object | See below | No | `AISettings` fields | CLI ask/rerank and `kgfs/ai.py` | Defaults disabled. | Unsupported provider raises `AIError` when AI is used. |

### Default Ignored Folders

Defined in `DEFAULT_IGNORED_FOLDERS` in `kgfs/core/config.py` and mirrored in `config.example.yaml`:

```yaml
ignored_folders:
  - ".git"
  - ".svn"
  - ".hg"
  - "node_modules"
  - ".venv"
  - "venv"
  - "env"
  - "__pycache__"
  - ".pytest_cache"
  - ".mypy_cache"
  - "build"
  - "dist"
  - "target"
  - ".idea"
  - ".vscode"
  - "vendor"
  - "Library"
  - "AppData"
  - "Windows"
  - "Program Files"
  - "Program Files (x86)"
  - "$Recycle.Bin"
  - "System Volume Information"
  - "Applications"
  - "System"
  - "Steam"
  - "SteamLibrary"
  - "Epic Games"
  - "XboxGames"
```

### Default Ignored Extensions

Defined in `DEFAULT_IGNORED_EXTENSIONS`:

```yaml
ignored_extensions:
  - ".exe"
  - ".dll"
  - ".dylib"
  - ".so"
  - ".app"
  - ".bin"
  - ".png"
  - ".jpg"
  - ".jpeg"
  - ".gif"
  - ".bmp"
  - ".tiff"
  - ".mp4"
  - ".mov"
  - ".avi"
  - ".mkv"
  - ".mp3"
  - ".wav"
  - ".flac"
  - ".zip"
  - ".7z"
  - ".rar"
  - ".tar"
  - ".gz"
```

## Nested Config Sections

### `indexing`

| Key | Type | Default | Read from | Behavior |
|---|---|---:|---|---|
| `store_extracted_text` | bool | `true` | `kgfs/indexing/indexer.py` | When false, indexed records store empty `extracted_text`; keyword search and semantic indexing have less or no text to use. |
| `skip_unchanged_files` | bool | `true` | `kgfs/indexing/indexer.py` | When true, matching size and mtime skip extraction. |
| `hash_files` | bool | `true` | `kgfs/indexing/indexer.py` | When true, SHA-256 is stored for indexed files. `--verify-hashes` can hash even when this is false. |

### `extraction`

| Key | Type | Default | Read from | Behavior |
|---|---|---:|---|---|
| `pdf_max_pages` | int | `250` | `kgfs/indexing/indexer.py`, `kgfs/extractors/pdf.py` | Limits pages read from PDF files. |

### `ocr`

OCR is local-only and disabled by default. The first backend is Tesseract, which KGFS calls as a local executable. Tesseract itself is installed separately; the optional `ocr` Python extra only adds light image-library room for future preprocessing.

| Key | Type | Default | Read from | Behavior |
|---|---|---:|---|---|
| `enabled` | bool | `false` | filters, extractors, OCR CLI | Enables indexing configured image extensions through OCR. |
| `backend` | str | `tesseract` | `kgfs/ocr/registry.py` | Selects OCR backend. Only `tesseract` is implemented. |
| `include_extensions` | list | `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp` | file filters | These image extensions are indexable only when OCR is enabled. |
| `max_image_size_mb` | float | `15` | file filters | Separate size cap for OCR images. Invalid/non-positive values fall back to 15 MB. |
| `cache_results` | bool | `true` | `kgfs/ocr/cache.py` | Reuses OCR text for unchanged files through the local KGFS SQLite cache. |
| `modify_source_files` | bool | `false` | config validation | Forced false in this phase. KGFS never writes OCR output into source files. |
| `min_pdf_text_chars` | int | `20` | PDF extractor | PDFs below this extracted-text threshold are treated as scanned-PDF candidates when OCR is enabled. |
| `pdf_max_pages` | int or null | `null` | reserved | Present for future scanned-PDF page limits. |
| `image_preprocessing` | bool | `true` | reserved | Placeholder for optional local preprocessing; no heavy dependency is required. |
| `tesseract.command` | str | `tesseract` | Tesseract backend | Command name or full path to the local Tesseract executable. |
| `tesseract.language` | str | `eng` | Tesseract backend | Passed to Tesseract with `-l`. |

OCR results are stored in `files.extracted_text` so keyword, semantic, hybrid, snippets, and `kgfs why` all use the same search pipeline. Cache rows live in the KGFS database, not beside source files.

### `semantic`

| Key | Type | Default | Read from | Behavior |
|---|---|---:|---|---|
| `enabled` | bool | `false` | `kgfs/indexing/indexer.py`, `kgfs/search/modes/semantic.py`, `kgfs/cli/commands/semantic.py` | Enables local chunk embedding and semantic search paths. |
| `model_name` | str | `sentence-transformers/all-MiniLM-L6-v2` | `kgfs/search/semantic.py` | Passed to `SentenceTransformer`; also stored in chunk rows and used to select chunks. |
| `chunk_size_chars` | int | `1200` | `chunk_text()` | Maximum chunk length before overlap. Values below 1 are clamped to 1. |
| `chunk_overlap_chars` | int | `200` | `chunk_text()` | Overlap between chunks; clamped to `[0, chunk_size - 1]`. |
| `local_files_only` | bool | `true` | `SentenceTransformerEmbedder` | Passed to `SentenceTransformer`. Default avoids model downloads. |
| `batch_size` | int | `16` | `SentenceTransformerEmbedder.embed()` | Batch size for embedding model encoding. |

### `search`

| Key | Type | Default | Valid values | Read from | Behavior |
|---|---|---:|---|---|---|
| `default_mode` | str | `auto` | `keyword`, `semantic`, `hybrid`, `auto` | CLI search | Used when `--mode` and `--hybrid` are omitted. Invalid values raise when search runs. |
| `default_limit` | int | `10` | `>= 1` at search runtime | CLI search | Used when `--limit` is omitted. `SearchOptions` rejects values below 1. |
| `highlight_matches` | bool | `true` | bool | CLI search | Adds Rich `[bold]` markup in snippets. |
| `save_latest_results` | bool | `true` | bool | CLI search | Saves latest result IDs for `open` and `reveal`. |

### `deep_search`

Deep search is local-only. It expands the query deterministically, runs several KGFS searches, fuses candidates by file ID, and saves latest results for follow-up commands.

| Key | Type | Default | Read from | Behavior |
|---|---|---:|---|---|
| `enabled` | bool | `true` | `kgfs deep` | Disables the command when false. |
| `max_passes` | int | `3` | `kgfs/search/deep.py` | Maximum local query variants used by default. |
| `max_candidates` | int | `50` | `kgfs/search/deep.py` | Candidate pool per query variant. |
| `rerank_top_n` | int | `20` | Config only at this commit | Reserved for future local reranking. |
| `query_expansion` | bool | `true` | `kgfs/search/deep.py` | Enables deterministic phrase/token/plural-ish variants. |
| `suggest_followups` | bool | `true` | `kgfs/search/deep.py` | Prints local follow-up search suggestions. |

### `research`

| Key | Type | Default | Read from | Behavior |
|---|---|---:|---|---|
| `max_files` | int | `12` | `kgfs/search/research.py` | Default number of files included in the local research brief. |
| `max_chunks` | int | `20` | Config only at this commit | Reserved for future chunk-level research summaries. |
| `suggest_related_terms` | bool | `true` | `kgfs/search/research.py` | Extracts related local terms from filenames/snippets. |

### `similar`

| Key | Type | Default | Read from | Behavior |
|---|---|---:|---|---|
| `default_limit` | int | `10` | `kgfs/search/similar.py` | Default number of similar files. |
| `min_score` | float | `0.0` | `kgfs/search/similar.py` | Minimum local similarity score for fallback term-overlap results. |

### `timeline`

| Key | Type | Default | Read from | Behavior |
|---|---|---:|---|---|
| `default_limit` | int | `50` | `kgfs/search/timeline.py` | Default maximum timeline items. |

### `profiles`

Config profiles are optional presets. User-created profiles from `kgfs profile
create` are stored in SQLite so they travel with the project-local/app-data DB.

Each profile can define:

| Key | Type | Default | Behavior |
|---|---|---:|---|
| `folders` | list of paths | `[]` | Folder/path substring constraints for profile search. |
| `extensions` | list of extensions | `[]` | Extension constraints for profile search. |
| `default_mode` | str | `hybrid` | Default search mode for the preset. |
| `boost_terms` | list of strings | `[]` | Terms appended to profile search queries. |

### `assignment`

| Key | Type | Default | Read from | Behavior |
|---|---|---:|---|---|
| `default_limit` | int | `20` | `kgfs/workflows/assignments.py` | Default number of assignment working-set results. |
| `include_extensions` | list | `.pdf`, `.docx`, `.md`, `.txt`, `.csv`, `.py` | `kgfs/workflows/assignments.py` | File types preferred for assignment mode. |

### `projects`

| Key | Type | Default | Read from | Behavior |
|---|---|---:|---|---|
| `default_limit` | int | `20` | `kgfs/workflows/projects.py` | Default project search result limit. |
| `infer_from_folders` | bool | `false` | config only at this commit | Reserved for future project inference; Phase 7 uses manual projects only. |

### `vectors`

| Key | Type | Default | Valid values | Read from | Behavior |
|---|---|---:|---|---|---|
| `backend` | str | `sqlite_scan` | `sqlite_scan`, `sqlite_vec`, `hnsw`, `faiss` | `kgfs/search/backends/registry.py`, semantic/hybrid search, vector commands | Selects the vector backend. Unknown values make vector status warn, semantic/hybrid unavailable, and vector rebuild/clear fail with valid-name guidance. |
| `shard_strategy` | str | `none` | No behavioral values found beyond `none` | Config model/default only | Present in config and tests, but no runtime behavior was found at this commit. |

Nested optional backend settings:

| Key | Type | Default | Behavior |
|---|---|---:|---|
| `sqlite_vec.enabled` | bool | `false` | Enables the experimental sqlite-vec backend when the optional dependency is installed. |
| `sqlite_vec.experimental` | bool | `true` | Marks sqlite-vec as experimental in config/status. |
| `hnsw.enabled` | bool | `false` | Enables the optional hnswlib backend when the optional dependency is installed. |
| `hnsw.space` | str | `cosine` | Accepted values are `cosine`, `l2`, and `ip`; invalid values fall back to `cosine`. |
| `hnsw.m` | int | `16` | HNSW graph parameter; non-positive values fall back to the default. |
| `hnsw.ef_construction` | int | `200` | Build-time search parameter; non-positive values fall back to the default. |
| `hnsw.ef_search` | int | `50` | Query-time search parameter; non-positive values fall back to the default. |
| `faiss.enabled` | bool | `false` | Enables the optional FAISS backend when the optional dependency is installed. |
| `faiss.index_type` | str | `flat` | Currently accepted value is `flat`; invalid values fall back to `flat`. |
| `faiss.use_gpu` | bool | `false` | GPU mode is not implemented; set false for the supported flat CPU index. |

The base install does not include `sqlite-vec`, `hnswlib`, or `faiss-cpu`. Install optional extras only when testing those backends.

### `hybrid`

| Key | Type | Default | Read from | Behavior |
|---|---|---:|---|---|
| `keyword_weight` | float | `0.35` | `combine_hybrid_score()` | Weight for SQLite FTS5 keyword relevance. Invalid values coerce to `0.0`; negative values are ignored at scoring time. |
| `semantic_weight` | float | `0.45` | `combine_hybrid_score()` | Weight for semantic chunk similarity. |
| `filename_weight` | float | `0.15` | `combine_hybrid_score()` | Weight for filename term matches. |
| `path_weight` | float | `0.05` | `combine_hybrid_score()` | Weight for folder/path term matches. |
| `exact_phrase_weight` | float | `0.10` | `combine_hybrid_score()` | Weight for exact query phrase in extracted text. |
| `recency_weight` | float | `0.05` | `combine_hybrid_score()` | Modest boost for recently modified files. |
| `candidate_limit_multiplier` | int | `5` | `hybrid_search()` | Candidate pool multiplier before final reranking. Values below 1 are clamped to 1; hybrid search still uses a floor of 25 candidates. |

Hybrid weights are normalized internally, so they do not need to sum to 1.0.

### `ai`

| Key | Type | Default | Read from | Behavior |
|---|---|---:|---|---|
| `enabled` | bool | `false` | `ensure_ai_ready()`, `ensure_ai_enabled()` | AI commands fail unless true. |
| `provider` | str | `openai` | `kgfs/ai.py` | Only `openai` is supported. Other values raise `AIError`. |
| `model` | str | `gpt-5.4-nano` | `OpenAIResponsesClient`, AI calls | Sent to OpenAI Responses API. |
| `api_key_env` | str | `OPENAI_API_KEY` | `get_openai_api_key()` | Names the env var used for the API key. |
| `require_confirmation` | bool | `true` | `preview_or_confirm_ai_context()` | Prompts before sending context unless preview-only. |
| `preview_context_before_send` | bool | `true` | `preview_or_confirm_ai_context()` | Prints context before confirmation/API call. |
| `send_file_paths` | bool | `false` | `_result_context_block()` | Includes paths in AI context only when true. |
| `redact_home_path` | bool | `true` | `build_ai_context()` | Replaces home path variants with `[HOME]`. |
| `send_full_file_text` | bool | `false` | `_result_context_block()` | Reads file text instead of snippet only when true. |
| `max_results_sent` | int | `12` | `build_ai_context()`, `ask_cmd()` | Limits result count sent to AI. |
| `max_chars_per_result` | int | `1500` | `build_ai_context()` | Truncates each result block. |
| `max_total_chars_sent` | int | `12000` | `build_ai_context()` | Truncates full context. |
| `allow_query_expansion` | bool | `true` | Config model only at this commit | Present but no implemented query expansion path was found. |
| `allow_rerank` | bool | `true` | `ensure_ai_ready()` | Allows `kgfs search --ai-rerank`. |
| `allow_answer_synthesis` | bool | `true` | `ensure_ai_ready()` | Allows `kgfs ask`. |

## CLI Flags

For command-specific behavior, see [CLI](cli.md). Global path flags appear on most commands:

| Flag | Commands | Default | Behavior |
|---|---|---:|---|
| `--config PATH` | Most commands | `None` | Overrides config path. |
| `--database PATH` | Commands that use the DB | `None` | Overrides database path. |
| `--project-local` | Most commands | `false` | Uses `.kgfs/` under current working directory. |

Important feature flags:

| Flag | Command | Default | Behavior |
|---|---|---:|---|
| `--allow-risky-root` | `index`, `rebuild`, `semantic-index --rebuild` | `false` | Allows broad/root scans. |
| `--dry-run` | `index`, `prune`, `reset-index` | `false` | Reports without DB writes or deletion depending on command. |
| `--force` | `index` | `false` | Re-extracts files even when metadata is unchanged. |
| `--verify-hashes` | `index` | `false` | Hash-checks metadata-matching files. |
| `--rebuild-embeddings` | `index` | `false` | Rebuilds semantic chunks/embeddings for unchanged files. |
| `ocr status/test/index` | `ocr` | n/a | Inspect OCR availability, run one-file OCR preview, or run indexing with OCR-enabled extraction. |
| `--mode` | `search` | config `search.default_mode` | Selects `keyword`, `semantic`, `hybrid`, or `auto`. |
| `--hybrid` | `search` | `false` | Forces hybrid mode. |
| `--ai-rerank` | `search` | `false` | Opt-in OpenAI reranking of local results. |
| `--preview-ai-context` | `search`, `ask` | `false` | Prints AI context and makes no API call. |
| `--mode` | `why` | config `search.default_mode` | Reruns a specific search mode while explaining a latest result. |
| `--rebuild` | `semantic-index` | `false` | Builds or rebuilds semantic chunks. |
| `--force/--no-force` | `vector rebuild` | `--force` | Rebuilds chunks even when chunks already exist, or skips existing chunks with `--no-force`. |
| `--yes` | `vector clear` | `false` | Required confirmation before clearing KGFS vector/chunk rows. |
| `--yes` | `reset-index`, `rebuild` | `false` | Confirms index reset operations. |
| `--host` | `web` | `127.0.0.1` | Uvicorn bind host. |
| `--port` | `web` | `8765` | Uvicorn bind port. |

## Runtime Options and Library Objects

| Object or function | Options | Source | Notes |
|---|---|---|---|
| `get_app_paths()` | `project_local`, `project_root`, `config_dir_override`, `data_dir_override`, `cache_dir_override`, `log_dir_override` | `kgfs/core/app_dirs.py` | Used by CLI/web runtime; project-local puts config/data under `.kgfs/`. |
| `index_configured_folders()` | `dry_run`, `semantic_embedder`, `rebuild_embeddings`, `allow_risky_root`, `force`, `verify_hashes` | `kgfs/indexing/indexer.py` | Main library indexing entry point. |
| `SearchFilters` | `extensions`, `file_type`, `folder`, `after`, `before`, `failed_only` | `kgfs/search/filters.py` | Used by CLI, web, and search functions. |
| `SearchOptions` | `mode`, `limit`, `filters`, `backend`, `explain`, `save_latest_results`, `highlight` | `kgfs/search/options.py` | `backend` is not exposed in CLI/web. `explain` exists as an option field, while user-facing explanations are exposed by `kgfs why`. |
| `SearchContext` | `conn`, `config`, `semantic_embedder`, `metadata` | `kgfs/search/engine.py` | Supplies DB/config and optional injected embedder to registry engines. |
| `get_vector_backend()` | `name` | `kgfs/search/backends/registry.py` | Returns the configured vector backend. Known names are `sqlite_scan`, `sqlite_vec`, `hnsw`, and `faiss`; optional backend dependencies are lazy. |
| `VectorSearchOptions` | `model_name`, `limit`, `filters` | `kgfs/search/backends/base.py` | Passed to vector backends for semantic/hybrid chunk search. |
| `get_vector_status()` | `conn`, `config` | `kgfs/vectors/status.py` | Reports backend availability, chunk counts, semantic dependency status, and warnings. |
| `rebuild_vector_index()` | `config`, `conn`, `embedder`, `force` | `kgfs/vectors/index_manager.py` | Rebuilds vector chunks from already indexed extracted text. Requires semantic enabled. |
| `clear_chunks()` | `conn`, optional `model_name` | `kgfs/vectors/chunks.py` | Deletes KGFS chunk/vector rows only and returns the removed count. |
| `benchmark_vector_backends()` | `conn`, `config`, backend names, queries, limit | `kgfs/vectors/benchmark.py` | Measures bounded vector query timings using existing vectors when possible. |
| `recommend_vector_backend()` | `conn`, `config` | `kgfs/vectors/recommend.py` | Returns a conservative local backend recommendation with reasons and warnings. |
| `create_app()` | `config_path`, `database_path`, `project_local` | `kgfs/web/app.py` | Builds FastAPI app. |
| `build_package.py` | `--clean`, `--mode`, `--name`, `--dist-dir`, `--work-dir`, `--spec` | `scripts/build_package.py` | Writes package archive under dist dir. |
| `smoke_test_packaged.py` | `--package` | `scripts/smoke_test_packaged.py` | Finds executable and runs CLI smoke workflow. |

## Example Config

```yaml
indexed_folders:
  - "~/Documents/School Notes"

max_file_size_mb: 25
follow_symlinks: false
database_path: null

indexing:
  store_extracted_text: true
  skip_unchanged_files: true
  hash_files: true

extraction:
  pdf_max_pages: 250

ocr:
  enabled: false
  backend: "tesseract"
  include_extensions:
    - ".png"
    - ".jpg"
    - ".jpeg"
    - ".tiff"
    - ".bmp"
  max_image_size_mb: 15
  cache_results: true
  modify_source_files: false
  min_pdf_text_chars: 20
  pdf_max_pages: null
  image_preprocessing: true
  tesseract:
    command: "tesseract"
    language: "eng"

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

deep_search:
  enabled: true
  max_passes: 3
  max_candidates: 50
  rerank_top_n: 20
  query_expansion: true
  suggest_followups: true

research:
  max_files: 12
  max_chunks: 20
  suggest_related_terms: true

similar:
  default_limit: 10
  min_score: 0.0

timeline:
  default_limit: 50

profiles: {}

assignment:
  default_limit: 20
  include_extensions:
    - ".pdf"
    - ".docx"
    - ".md"
    - ".txt"
    - ".csv"
    - ".py"

projects:
  default_limit: 20
  infer_from_folders: false

vectors:
  backend: "sqlite_scan"
  shard_strategy: "none"

hybrid:
  keyword_weight: 0.35
  semantic_weight: 0.45
  filename_weight: 0.15
  path_weight: 0.05
  exact_phrase_weight: 0.10
  recency_weight: 0.05
  candidate_limit_multiplier: 5

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
