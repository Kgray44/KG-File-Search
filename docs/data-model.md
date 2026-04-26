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
| `extraction_source` | `TEXT NOT NULL DEFAULT 'text'` | Source label such as `text` or `ocr`. | `ExtractionResult.metadata` / indexer |

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

Stores the latest search result IDs for `open`, `reveal`, `why`, local workflow
commands, web/API file actions, and other follow-up commands that operate on
the latest result set.

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

### `ocr_cache`

Stores local OCR results so unchanged images do not need to be OCRed again.
Rows live in the KGFS database only; no OCR sidecar files are written beside
source files.

| Column | Type | Meaning |
|---|---|---|
| `id` | `INTEGER PRIMARY KEY` | Cache row ID. |
| `file_id` | `INTEGER REFERENCES files(id) ON DELETE CASCADE` | Optional indexed file row. |
| `normalized_path` | `TEXT NOT NULL` | Normalized source path used for lookup. |
| `content_hash` | `TEXT` | Content hash when available. |
| `size` | `INTEGER NOT NULL` | Source file size. |
| `modified_time_ns` | `INTEGER NOT NULL` | Precise source modified time. |
| `backend` | `TEXT NOT NULL` | OCR backend name. |
| `language` | `TEXT NOT NULL` | OCR language setting. |
| `source_kind` | `TEXT NOT NULL` | `image` or `pdf`. |
| `text` | `TEXT NOT NULL` | OCR output text. |
| `status` | `TEXT NOT NULL` | OCR status. |
| `error` | `TEXT` | OCR error if any. |
| `created_at` | `TEXT NOT NULL` | UTC ISO timestamp. |
| `updated_at` | `TEXT NOT NULL` | UTC ISO timestamp. |

Sources: `kgfs/ocr/cache.py`, `kgfs/db/schema.py`, `tests/test_ocr_cache.py`.

### Media Tables

Phase 10 adds optional media metadata tables. They store KGFS-derived metadata
only; no source image/audio bytes are copied and no sidecars are written beside
source files.

| Table | Purpose |
|---|---|
| `media_metadata` | One local media metadata row per indexed file, including image dimensions, camera make/model, captured timestamp, optional redacted/coarse/exact location text, and safe metadata JSON. |
| `media_text` | Searchable generated text from sources such as `exif`, `caption`, `transcript`, `visual_label`, or `ocr`. Keyword search labels these results with `media:<source_kind>`. |
| `media_embeddings` | Optional future/local media embeddings keyed by file, source kind, backend, and model name. |

Location behavior:

- `media.photos.store_location_metadata` defaults to false.
- When disabled, KGFS omits GPS/location/latitude/longitude fields from stored
  metadata JSON and stores `location_precision = "none"`.
- Exact location text requires explicit config and is not the default.

Sources: `kgfs/media/*.py`, `kgfs/db/schema.py`, `tests/test_phase10_media.py`.

### Workflow Metadata Tables

Phase 7 adds local personal workflow metadata. These tables live only in the
KGFS SQLite database and reference indexed files by `file_id`; KGFS does not
write tags, notes, collections, or project metadata into source files.

| Table | Purpose |
|---|---|
| `profiles` | User-created search profile presets with JSON folders/extensions/boost terms. |
| `saved_searches` | Named searches with query, mode, and JSON filters. |
| `collections` | Named manual groups of files. |
| `collection_items` | Files in collections, with optional latest result ID/note. |
| `tags` | Unique normalized tag names. |
| `file_tags` | Many-to-many file/tag rows. |
| `file_notes` | Local notes attached to file IDs. |
| `projects` | Named manual project groups. |
| `project_items` | Files in projects, with optional role. |
| `assignment_runs` | Lightweight local assignment working-set history. |

Workflow reference tables use `REFERENCES files(id) ON DELETE CASCADE` where
they point at indexed files. Pruning stale files or deleting file rows removes
dependent workflow rows through SQLite foreign keys.

Sources: `kgfs/db/schema.py`, `kgfs/workflows/*.py`, `tests/test_phase7_workflows.py`.

### Intelligence Metadata Tables

Phase 8 adds local file-intelligence metadata tables. These tables contain
derived KGFS metadata only; they do not store source file contents.

| Table | Purpose |
|---|---|
| `graph_edges` | Optional cached file-to-file graph edges with type, weight, and evidence JSON. |
| `project_candidates` | Inferred project candidate names, scores, evidence JSON, and accepted project link. |
| `metadata_backups` | Paths and notes for KGFS metadata backup files created by backup/reset workflows. |

Sources: `kgfs/db/schema.py`, `kgfs/intelligence/*.py`, `tests/test_phase8_file_intelligence.py`.

### `schema_version`

Created by migrations.

| Column | Type | Meaning |
|---|---|---|
| `id` | `INTEGER PRIMARY KEY CHECK (id = 1)` | Singleton row. |
| `version` | `INTEGER NOT NULL` | Current schema version. |
| `applied_at` | `TEXT NOT NULL` | UTC ISO timestamp. |

Current version: `5`.

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
| `ExtractionResult` | text, status, error, metadata | Extractor return value. Status values are produced by helpers as `ok`, `skipped`, or `error`; metadata carries labels such as OCR source. | `kgfs/extractors/base.py` |
| `PruneSummary` | stale paths, removed count, dry-run flag | Stale-record prune result. | `kgfs/indexing/prune.py` |
| `ResetSummary` | database path, removed paths, would-remove flag, dry-run flag | Reset-index result. | `kgfs/reset.py` |
| `SearchAvailability` | available, message | Search engine availability checks. | `kgfs/search/engine.py` |
| `SearchContext` | SQLite connection, config, optional semantic embedder, metadata | Search engine registry execution context. | `kgfs/search/engine.py` |
| `SearchExecution` | results, requested mode, used mode, warnings | Registry search result wrapper. | `kgfs/search/registry.py` |
| `SearchOptions` | mode, limit, filters, backend, explain, save-latest-results flag, highlight flag | Registry search options. `backend` is not exposed by CLI/web; `why` exposes user-facing explanations. | `kgfs/search/options.py` |
| `SearchExplanation` | mode, summary, score breakdown, result ID, file name, path, final score, snippet, notes | Explanation object used by `kgfs why` and default `SearchEngine.explain()`. | `kgfs/search/result.py` |
| `SemanticStatus` | enabled, available, message | Semantic dependency/config status for doctor and semantic-index output. | `kgfs/search/semantic.py` |
| `AIResult` | text, context | AI answer result with returned text and context used. | `kgfs/ai.py` |
| `Profile`, `SavedSearch`, `Collection`, `WorkflowItem`, `FileNote`, `AssignmentReport`, `Project` | local workflow metadata and report fields | Profiles, saved searches, collections, tags, notes, assignments, and projects. | `kgfs/workflows/models.py` |
| `DuplicateGroup`, `VersionCandidate`, `ProjectCandidate`, `GraphResult`, `HealthReport`, `MetadataExportSummary` | local intelligence and metadata backup result fields | Duplicates, versions, project candidates, graphs, health, and metadata import/export. | `kgfs/intelligence/models.py` |
| `APIHealth`, `APIResult`, `APISearchResponse` | JSON API response payloads | Local API health/search routes. | `kgfs/api/models.py` |
| `TUIState` | query, mode, selected result ID | Optional TUI state. | `kgfs/tui/state.py` |
| `IntegrationStatus` | name, supported, scaffold availability, installed flag, command, notes | Integration scaffold status rows. | `kgfs/integrations/status.py` |

OCR models:

| Model | Fields | Used for | Source |
|---|---|---|---|
| `OCRAvailability` | available, message, install hint | Local OCR backend availability checks. | `kgfs/ocr/base.py` |
| `OCRRequest` | path, config, source kind, optional page number | Backend extraction request. | `kgfs/ocr/base.py` |
| `OCRResult` | text, status, error, backend, language, source kind, confidence, metadata | OCR backend extraction result. | `kgfs/ocr/base.py` |
| `OCRStatus` | enabled, backend, availability, command/language, supported extensions, cache/index counts, warnings | `kgfs ocr status`, doctor integration, tests. | `kgfs/ocr/status.py` |

Media models:

| Model | Fields | Used for | Source |
|---|---|---|---|
| `MediaStatus` | enabled flags, backend availability, media row counts, cache size, warnings | `kgfs media status`, health/stats/web status. | `kgfs/media/models.py`, `kgfs/media/status.py` |
| `MediaTextRecord` | file ID, source kind, backend/model, text, confidence, metadata | Local media-derived searchable text storage. | `kgfs/media/models.py`, `kgfs/media/cache.py` |
| `PhotoMetadata` | image dimensions, camera make/model, captured time, optional GPS fields, metadata dict | EXIF/photo metadata extraction and storage. | `kgfs/media/exif.py` |
| `CaptionResult`, `TranscriptionResult`, `VisualEmbeddingResult` | scaffold result payloads with text/vector/status/error metadata | Optional caption/audio/visual scaffold behavior. | `kgfs/media/captions.py`, `kgfs/media/audio.py`, `kgfs/media/visual.py` |

Vector models:

| Model | Fields | Used for | Source |
|---|---|---|---|
| `BackendAvailability` | available, message, optional install hint | Vector backend readiness checks. | `kgfs/search/backends/base.py` |
| `VectorSearchOptions` | model name, limit, filters | Options passed to vector backends. | `kgfs/search/backends/base.py` |
| `VectorSearchHit` | chunk/file IDs, chunk index/text, vector dimension, file metadata, score, offsets, metadata | Backend search result before conversion to `SearchResult`. | `kgfs/search/backends/base.py`, `kgfs/search/backends/sqlite_scan.py` |
| `VectorIndexStatus` | backend name, semantic enabled, model, chunk counts, dependency/backend readiness, install hint, optional artifact metadata, warnings | Status returned by vector status helpers and `kgfs vector status`. | `kgfs/search/backends/base.py`, `kgfs/vectors/status.py` |
| `VectorRebuildSummary` | files considered/indexed, chunks indexed, skipped without text, skipped existing | Summary returned by vector rebuild helper. | `kgfs/vectors/index_manager.py` |
| `VectorBenchmarkResult` | backend, availability, chunk/file counts, artifact status, query timings, notes | Result rows for `kgfs vector benchmark`. | `kgfs/vectors/benchmark.py` |
| `VectorRecommendation` | recommended backend, configured backend, chunk count, reasons, warnings | Recommendation payload for `kgfs vector recommend`. | `kgfs/vectors/recommend.py` |
| `VectorBackendMetadata` | backend, model, embedding dimension, chunk count/fingerprint, config hash, schema version, artifact files, timestamps | JSON metadata for backend artifact health. | `kgfs/vectors/metadata.py` |

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
| `OCRSettings` / `TesseractOCRSettings` / `EasyOCRSettings` / `PaddleOCRSettings` / `CloudOCRFallbackSettings` | Local OCR settings, optional advanced OCR backend flags, and strict no-upload cloud fallback scaffold settings. |
| `MediaSettings`, `PhotoSettings`, `CaptionSettings`, `AudioSettings`, `VisualSettings` | Optional local media metadata/caption/audio/visual settings, disabled by default. |
| `SemanticSettings` | Local embedding settings. |
| `SearchSettings` | CLI search defaults. |
| `DeepSearchSettings`, `ResearchSettings`, `SimilarSettings`, `TimelineSettings` | Advanced local search defaults. |
| `ProfilePresetSettings`, `AssignmentSettings`, `ProjectsSettings` | Phase 7 workflow presets and limits. |
| `IntelligenceSettings`, `MetadataSettings` | Phase 8 file intelligence thresholds/limits and metadata backup behavior. |
| `UISettings` | UI surface defaults and placeholder launch preferences. |
| `APISettings` | Local JSON API host/port/token/file-action settings. |
| `IntegrationSettings` | Local launcher/tray scaffold feature flags. |
| `VectorSettings` | Vector backend selection, shard strategy placeholder, and optional sqlite-vec/HNSW/FAISS settings. |
| `HybridSettings` | Hybrid score weights and candidate pool multiplier. |
| `AISettings` | AI Assist privacy, provider, and size settings. |

See [Settings](settings.md) for all fields and defaults.

## Vector Storage Format

Semantic vectors are stored as little-endian float32 values:

- Pack: `struct.pack(f"<{len(vector)}f", ...)`
- Unpack: `struct.unpack(f"<{dimension}f", blob)`

Sources: `kgfs/search/semantic.py`, `tests/test_semantic.py`.

Optional accelerated backend artifacts live under KGFS vector-backend storage
resolved from the database/app-data/project-local path. HNSW and FAISS store
index files plus metadata JSON there. sqlite-vec stores its vector table in the
KGFS SQLite database and stores metadata JSON in the same backend artifact area.
Source files are not used for backend artifacts.

At CLI runtime, KGFS resolves `config.database_path`, so backend artifacts
normally live beside the selected KGFS database under `vector-backends/`.
Programmatic callers that build a config without `database_path` fall back to a
project-local/current-working-directory `.kgfs/vector-backends` location.

## Result ID Model

Search functions renumber results from `1` for each result list. These IDs are user-facing and transient. `save_latest_results()` persists the latest search set for open/reveal commands. New searches replace the previous latest-result set.

Sources: `kgfs/search/keyword.py`, `kgfs/db/latest_results.py`.

## Migration Model

`migrate_database()` is idempotent:

1. Ensures `schema_version`.
2. Ensures `files.modified_time_ns` exists for older schemas.
3. Reads current schema version.
4. Raises if database version is newer than code.
5. Ensures `files.extraction_source`.
6. Ensures `ocr_cache`.
7. Ensures workflow metadata tables.
8. Ensures intelligence metadata tables.
9. Ensures media metadata/text/embedding tables.
10. Sets version to `5` for fresh/older DBs.

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
