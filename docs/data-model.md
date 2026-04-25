# Data Model

KGFS stores local index state in SQLite. It also uses Python dataclasses and Pydantic settings objects to pass structured data between modules.

## SQLite Database

Database creation source: `kgfs/db/schema.py`.

Connection behavior:

- `connect_database()` expands the database path, creates the parent directory, connects with `sqlite3`, enables foreign keys, and uses a custom row factory.
- `initialize_database()` creates tables, creates indexes, runs migrations, and commits.

Sources: `kgfs/db/connection.py`, `kgfs/db/schema.py`.

## Tables

### `files`

Stores one row per indexed file.

| Column | Type | Meaning | Written from |
|---|---|---|---|
| `id` | `INTEGER PRIMARY KEY` | File ID. | SQLite |
| `path` | `TEXT NOT NULL` | Display/open path. | `FileRecord.path` |
| `normalized_path` | `TEXT NOT NULL UNIQUE` | Stable uniqueness/lookup path. | `normalize_path()` |
| `file_name` | `TEXT NOT NULL` | File name only. | `Path.name` |
| `extension` | `TEXT NOT NULL` | Lowercase suffix. | `Path.suffix.lower()` |
| `size` | `INTEGER NOT NULL` | File size in bytes. | `stat().st_size` |
| `modified_time` | `REAL NOT NULL` | File modified time seconds. | `stat().st_mtime` |
| `modified_time_ns` | `INTEGER` | Precise modified time when available. | `stat().st_mtime_ns` |
| `content_hash` | `TEXT` | SHA-256 hex digest or null. | `sha256_file()` |
| `extracted_text` | `TEXT NOT NULL` | Stored extracted text, or empty if disabled/failure. | extractors/indexer |
| `indexed_at` | `TEXT NOT NULL` | UTC ISO timestamp. | indexer |
| `platform_indexed_from` | `TEXT NOT NULL` | Platform name, such as Windows or Darwin. | `current_platform_name()` |
| `extraction_status` | `TEXT NOT NULL` | `ok`, `skipped`, or `error`. | `ExtractionResult.status` |
| `extraction_error` | `TEXT` | Error/skipped reason. | `ExtractionResult.error` |

Sources: `kgfs/db/schema.py`, `kgfs/core/models.py`, `kgfs/indexing/indexer.py`.

### `files_fts`

SQLite FTS5 virtual table.

| Column | Meaning |
|---|---|
| `file_name` | Searchable file name. |
| `path` | Searchable display path. |
| `extracted_text` | Searchable extracted text. |

Options:

```sql
tokenize='porter unicode61'
```

Rows use `rowid = files.id`. The row is deleted and reinserted on each file update.

Sources: `kgfs/db/schema.py`, `kgfs/db/repositories.py`.

### `latest_results`

Stores the latest search result IDs for `open` and `reveal`.

| Column | Type | Meaning |
|---|---|---|
| `result_id` | `INTEGER PRIMARY KEY` | User-facing result number from latest search. |
| `file_id` | `INTEGER NOT NULL` | File ID. |
| `file_path` | `TEXT NOT NULL` | Path used for open/reveal. |
| `query` | `TEXT NOT NULL` | Query that produced the result. |
| `created_at` | `TEXT NOT NULL` | UTC ISO timestamp. |

Saving latest results deletes all previous rows first.

Sources: `kgfs/db/latest_results.py`, `tests/test_search.py`.

### `chunks`

Stores semantic chunks and embeddings.

| Column | Type | Meaning |
|---|---|---|
| `id` | `INTEGER PRIMARY KEY` | Chunk row ID. |
| `file_id` | `INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE` | Parent file. |
| `chunk_index` | `INTEGER NOT NULL` | Chunk order within file/model. |
| `text` | `TEXT NOT NULL` | Chunk text. |
| `embedding` | `BLOB NOT NULL` | Packed float32 vector. |
| `embedding_dim` | `INTEGER NOT NULL` | Vector dimension. |
| `start_char` | `INTEGER` | Start offset in extracted text. |
| `end_char` | `INTEGER` | End offset in extracted text. |
| `model_name` | `TEXT NOT NULL` | Semantic model name. |
| `created_at` | `TEXT NOT NULL` | UTC ISO timestamp. |

Constraints and indexes:

- Unique `(file_id, chunk_index, model_name)`.
- Index on `file_id`.
- Index on `model_name`.

Sources: `kgfs/db/schema.py`, `kgfs/search/semantic.py`, `tests/test_semantic.py`.

### `schema_version`

Created by migrations.

| Column | Type | Meaning |
|---|---|---|
| `id` | `INTEGER PRIMARY KEY CHECK (id = 1)` | Singleton row. |
| `version` | `INTEGER NOT NULL` | Current schema version. |
| `applied_at` | `TEXT NOT NULL` | UTC ISO timestamp. |

Current version: `1`.

Sources: `kgfs/db/migrations.py`, `tests/test_migrations.py`.

## Dataclasses and Structured Runtime Models

Defined in `kgfs/core/models.py`.

| Dataclass | Fields | Used for |
|---|---|---|
| `FileRecord` | path, normalized path, name, extension, size, mtime, hash, text, index timestamp, platform, extraction status/error, precise mtime | DB upsert payload. |
| `IndexSummary` | discovered, indexed, skipped unchanged, failed, bytes indexed, dry-run flag | Indexing command and library results. |
| `SearchResult` | result ID, file ID, file name, path, extension, modified time, score, snippet, normalized path, score breakdown, matched chunk ID, mode, source, metadata | Search results across keyword/semantic/hybrid/AI/open/reveal. |
| `TextChunk` | chunk index, text, start char, end char | Semantic chunking before embedding. |

Additional dataclasses and runtime models:

| Model | Fields | Used for | Source |
|---|---|---|---|
| `AppPaths` | config dir, data dir, cache dir, log dir, default config path, default database path | Platform/project-local path resolution. | `kgfs/core/app_dirs.py` |
| `FolderChange` | path, display path, added, removed, exists, warning | Folder config command results. | `kgfs/core/config_commands.py` |
| `ExtractionResult` | text, status, error | Extractor return value. Status values are produced by helpers as `ok`, `skipped`, or `error`. | `kgfs/extractors/base.py` |
| `PruneSummary` | stale paths, removed count, dry-run flag | Stale-record prune result. | `kgfs/indexing/prune.py` |
| `ResetSummary` | database path, removed paths, would-remove flag, dry-run flag | Reset-index result. | `kgfs/reset.py` |
| `SearchAvailability` | available, message | Search engine availability checks. | `kgfs/search/engine.py` |
| `SearchContext` | SQLite connection, config, optional semantic embedder, metadata | Search engine registry execution context. | `kgfs/search/engine.py` |
| `SearchExecution` | results, requested mode, used mode, warnings | Registry search result wrapper. | `kgfs/search/registry.py` |
| `SearchOptions` | mode, limit, filters, backend, explain, save-latest-results flag, highlight flag | Registry search options. `backend` is not exposed by CLI/web; `why` exposes user-facing explanations. | `kgfs/search/options.py` |
| `SearchExplanation` | mode, summary, score breakdown, result ID, file name, path, final score, snippet, notes | Explanation object used by `kgfs why` and default `SearchEngine.explain()`. | `kgfs/search/result.py` |
| `SemanticStatus` | enabled, available, message | Semantic dependency/config status for doctor and semantic-index output. | `kgfs/search/semantic.py` |
| `AIResult` | text, context | AI answer result with returned text and context used. | `kgfs/ai.py` |

Vector models:

| Model | Fields | Used for | Source |
|---|---|---|---|
| `BackendAvailability` | available, message | Vector backend readiness checks. | `kgfs/search/backends/base.py` |
| `VectorSearchOptions` | model name, limit, filters | Options passed to vector backends. | `kgfs/search/backends/base.py` |
| `VectorSearchHit` | chunk/file IDs, chunk index/text, vector dimension, file metadata, score, offsets, metadata | Backend search result before conversion to `SearchResult`. | `kgfs/search/backends/base.py`, `kgfs/search/backends/sqlite_scan.py` |
| `VectorIndexStatus` | backend name, semantic enabled, model, chunk counts, dependency/backend readiness, warnings | Status returned by vector status helpers and `kgfs vector status`. | `kgfs/search/backends/base.py`, `kgfs/vectors/status.py` |
| `VectorRebuildSummary` | files considered/indexed, chunks indexed, skipped without text, skipped existing | Summary returned by vector rebuild helper. | `kgfs/vectors/index_manager.py` |

Protocols:

| Protocol | Method/attributes | Used for | Source |
|---|---|---|---|
| `SearchEngine` | `name`, `available()`, `search()`, optional `explain()`, optional `stats()` | Search mode implementations. | `kgfs/search/engine.py` |
| `VectorBackend` | `name`, `available()`, `status()`, `search()`, `clear()`, optional `stats()` | Semantic vector backend implementations. | `kgfs/search/backends/base.py` |
| `Embedder` | `model_name`, `embed(texts)` | Semantic indexing/search; tests inject fake embedders. | `kgfs/search/semantic.py` |
| `AIClient` | `create_response(model=..., input_text=...)` | OpenAI client abstraction and tests. | `kgfs/ai.py` |

## Config Models

Defined in `kgfs/core/config.py`.

| Model | Purpose |
|---|---|
| `KGFSConfig` | Main YAML config. |
| `IndexingSettings` | Indexing flags. |
| `ExtractionSettings` | Extractor settings. |
| `SemanticSettings` | Local embedding settings. |
| `SearchSettings` | CLI search defaults. |
| `VectorSettings` | Vector backend selection and shard strategy placeholder. |
| `HybridSettings` | Hybrid score weights and candidate pool multiplier. |
| `AISettings` | AI Assist privacy, provider, and size settings. |

See [Settings](settings.md) for all fields and defaults.

## Vector Storage Format

Semantic vectors are stored as little-endian float32 values:

- Pack: `struct.pack(f"<{len(vector)}f", ...)`
- Unpack: `struct.unpack(f"<{dimension}f", blob)`

Sources: `kgfs/search/semantic.py`, `tests/test_semantic.py`.

## Result ID Model

Search functions renumber results from `1` for each result list. These IDs are user-facing and transient. `save_latest_results()` persists the latest search set for open/reveal commands. New searches replace the previous latest-result set.

Sources: `kgfs/search/keyword.py`, `kgfs/db/latest_results.py`.

## Migration Model

`migrate_database()` is idempotent:

1. Ensures `schema_version`.
2. Ensures `files.modified_time_ns` exists for older schemas.
3. Reads current schema version.
4. Raises if database version is newer than code.
5. Sets version to `1` for fresh/older DBs.

Sources: `kgfs/db/migrations.py`, `tests/test_migrations.py`.

## Ignored Generated Data

Generated data and package outputs are ignored by `.gitignore`, including:

- `.kgfs/`
- `data/*` except `data/.gitkeep`
- SQLite files and sidecars
- caches/logs
- vector/index artifacts
- Python caches
- build/dist/dist-packages
- zip/spec artifacts, with `packaging/pyinstaller/kgfs.spec` explicitly allowed

Sources: `.gitignore`, `tests/test_project_structure.py`.
