# API and Programmatic Interfaces

KGFS does not expose a JSON REST API at this commit. It exposes:

- An HTML/plain-text FastAPI dashboard.
- Python module functions and dataclasses.
- CLI commands documented in [CLI](cli.md).

## FastAPI Dashboard

App factory source: `kgfs/web/app.py`.

Start through CLI:

```bash
kgfs web
```

Default bind:

```text
http://127.0.0.1:8765
```

### Routes

| Method | Path | Query/path parameters | Response | Behavior | Source |
|---|---|---|---|---|---|
| `GET` | `/` | None | HTML | Shows summary metrics from `get_database_stats()`. | `kgfs/web/app.py`, `kgfs/web/templates/index.html` |
| `GET` | `/search` | `q`, `ext`, `folder`, `after`, `before`, `limit`, `failed_only` | HTML | Runs keyword search when `q` is provided, saves latest results, renders results. | `kgfs/web/app.py`, `kgfs/web/templates/search.html` |
| `GET` | `/stats` | None | HTML | Shows database/index stats. | `kgfs/web/app.py`, `kgfs/web/templates/stats.html` |
| `GET` | `/config` | None | HTML | Shows resolved config path, indexed folders, and config dump. | `kgfs/web/app.py`, `kgfs/web/templates/config.html` |
| `GET` | `/failures` | None | HTML | Shows up to 100 extraction failures ordered by latest indexed time. | `kgfs/web/app.py`, `kgfs/web/templates/failures.html` |
| `GET` | `/open/{result_id}` | `result_id` integer | Plain text | Opens file from latest results or returns 404 text. | `kgfs/web/app.py` |
| `GET` | `/reveal/{result_id}` | `result_id` integer | Plain text | Reveals file from latest results or returns 404 text. | `kgfs/web/app.py` |
| `GET` | `/static/style.css` | None | CSS | Static stylesheet mounted from bundled/source resource path. | `kgfs/web/app.py`, `kgfs/web/static/style.css` |

Tests: `tests/test_web.py`.

Framework-provided FastAPI endpoints are also present because `FastAPI(title="KG File Search")` is created without disabling default docs/schema URLs:

| Method | Path | Response | Notes | Source |
|---|---|---|---|---|
| `GET` | `/openapi.json` | JSON | FastAPI-generated OpenAPI schema for the dashboard app. | `kgfs/web/app.py` |
| `GET` | `/docs` | HTML | FastAPI Swagger UI. Not customized by KGFS. | `kgfs/web/app.py` |
| `GET` | `/redoc` | HTML | FastAPI ReDoc UI. Not customized by KGFS. | `kgfs/web/app.py` |

### Search Route Parameters

| Parameter | Type | Default | Behavior |
|---|---|---:|---|
| `q` | string | `""` | Search query. Empty query renders no results. |
| `ext` | string | `""` | Single extension filter, such as `.pdf`. |
| `folder` | string | `""` | Case-insensitive path substring filter. |
| `after` | string | `""` | Modified on/after ISO date. |
| `before` | string | `""` | Modified on/before ISO date. |
| `limit` | int | `10` | Max results. |
| `failed_only` | bool | `false` | Only extraction failures. |

Current limitation: web search calls direct keyword `search()` and does not expose registry `auto`, semantic, hybrid, or AI rerank.

## Python Modules

Compatibility aliases allow older flat imports such as `kgfs.config`, `kgfs.database`, `kgfs.semantic`, and `kgfs.snippets`. New code should prefer the package locations when possible.

### Config and Paths

| API | Purpose | Source |
|---|---|---|
| `KGFSConfig` | Pydantic YAML config model. | `kgfs/core/config.py` |
| `load_config(path)` | Load and validate config YAML. | `kgfs/core/config.py` |
| `create_default_config_file(path)` | Create default config if missing. | `kgfs/core/config.py` |
| `get_app_paths(...)` | Resolve platform/project-local app directories. | `kgfs/core/app_dirs.py` |
| `resolve_config_path(...)` | Resolve config path with CLI/env/default order. | `kgfs/core/app_dirs.py` |
| `resolve_database_path(...)` | Resolve database path with CLI/env/config/default order. | `kgfs/core/app_dirs.py` |
| `expand_user_path(...)` | Expand env vars and portable tilde paths. | `kgfs/core/path_utils.py` |

### Database

| API | Purpose | Source |
|---|---|---|
| `connect_database(path)` | Create parent directory, connect SQLite, enable foreign keys, set custom row factory. | `kgfs/db/connection.py` |
| `initialize_database(conn)` | Create tables and run migrations. | `kgfs/db/schema.py` |
| `check_fts5_available()` | Test SQLite FTS5 support. | `kgfs/db/schema.py` |
| `get_database_stats(conn, path)` | Return index/database stats. | `kgfs/db/stats.py` |
| `save_latest_results(conn, query, results)` | Replace latest result ID rows. | `kgfs/db/latest_results.py` |
| `get_latest_result_path(conn, result_id)` | Resolve latest result ID to a path. | `kgfs/db/latest_results.py` |

### Indexing

| API | Purpose | Source |
|---|---|---|
| `discover_files(config)` | Yield indexable paths under configured roots. | `kgfs/indexing/discovery.py` |
| `should_index_file(path, config)` | Apply file filters. | `kgfs/indexing/filters.py` |
| `should_skip_dir(path, config)` | Apply directory-name filters. | `kgfs/indexing/filters.py` |
| `index_configured_folders(config, conn, ...)` | Main indexing entry point. | `kgfs/indexing/indexer.py` |
| `index_single_file(config, conn, file_path)` | Index one file by using a temporary one-file config. | `kgfs/indexing/indexer.py` |
| `prune_stale_files(conn, dry_run=False)` | Remove stale DB rows and related rows. | `kgfs/indexing/prune.py` |
| `reset_index(database_path, ...)` | Remove KGFS DB files only. | `kgfs/reset.py` |
| `rebuild_index(config, database_path, ...)` | Reset DB and index. | `kgfs/reset.py` |

### Search

| API | Purpose | Source |
|---|---|---|
| `search(conn, query, ...)` | Keyword search using SQLite FTS5. | `kgfs/search/keyword.py` |
| `semantic_search(conn, query, embedder, ...)` | Semantic chunk search. | `kgfs/search/keyword.py` |
| `hybrid_search(conn, query, embedder, ...)` | Combined semantic/keyword search. | `kgfs/search/keyword.py` |
| `build_fts_query(query, use_or=False)` | Build FTS5 query string. | `kgfs/search/query.py` |
| `SearchFilters` | Extension/folder/date/failure filters. | `kgfs/search/filters.py` |
| `SearchOptions` | Registry search options. | `kgfs/search/options.py` |
| `SearchContext` | Registry search context with DB/config/embedder. | `kgfs/search/engine.py` |
| `SearchRegistry.available_modes(context)` | Return concrete modes whose engines report available. | `kgfs/search/registry.py` |
| `build_default_search_registry()` | Register keyword, semantic, and hybrid engines. | `kgfs/search/registry.py` |
| `explain_result(result, query, ...)` | Build a lightweight local explanation with score breakdown and snippet. | `kgfs/search/explain.py` |

### Workflow Helpers

| API | Purpose | Source |
|---|---|---|
| `create_profile()`, `profile_search()` | Store and run local search profiles. | `kgfs/workflows/profiles.py` |
| `save_search()`, `run_saved_search()` | Store and run named saved searches. | `kgfs/workflows/saved_searches.py` |
| `create_collection()`, `add_results_to_collection()`, `export_collection_markdown()` | Manage local file collections. | `kgfs/workflows/collections.py` |
| `tag_result()`, `list_tagged_files()` | Attach tags to files resolved from latest result IDs. | `kgfs/workflows/tags.py` |
| `add_note()`, `list_notes()` | Store local notes for indexed files. | `kgfs/workflows/notes.py` |
| `assignment_working_set()` | Build a local assignment working set. | `kgfs/workflows/assignments.py` |
| `create_project()`, `add_results_to_project()`, `project_search()` | Manage manual local projects and project-scoped search. | `kgfs/workflows/projects.py` |

### Intelligence Helpers

| API | Purpose | Source |
|---|---|---|
| `find_exact_duplicates()`, `find_semantic_duplicates()` | Return duplicate groups from hashes or existing local vectors. | `kgfs/intelligence/duplicates.py` |
| `find_versions_for_result()`, `find_versions_for_path()` | Return likely version candidates. | `kgfs/intelligence/versions.py` |
| `infer_project_candidates()`, `list_project_candidates()`, `accept_project_candidate()` | Infer and accept local project candidates. | `kgfs/intelligence/projects.py` |
| `build_topic_graph()`, `build_file_graph()`, `build_project_graph()` | Build bounded local graph results. | `kgfs/intelligence/graph.py` |
| `build_health_report()` | Return read-only index/workflow health data. | `kgfs/intelligence/health.py` |
| `export_metadata()`, `import_metadata()`, `create_metadata_backup()` | Export/import KGFS workflow metadata without source contents. | `kgfs/intelligence/export.py` |

### Semantic Helpers

| API | Purpose | Source |
|---|---|---|
| `chunk_text(text, ...)` | Split text with overlap and offsets. | `kgfs/search/semantic.py` |
| `vector_to_blob(vector)` | Pack float vector to SQLite BLOB. | `kgfs/search/semantic.py` |
| `unpack_vector(blob, dimension)` | Unpack BLOB to float vector. | `kgfs/search/semantic.py` |
| `cosine_similarity(left, right)` | Compute vector similarity. | `kgfs/search/semantic.py` |
| `get_semantic_status(settings)` | Report enabled/dependency status. | `kgfs/search/semantic.py` |
| `get_embedder(settings, embedder=None)` | Return injected embedder or create sentence-transformers embedder. | `kgfs/search/semantic.py` |

### Vector Backends

| API | Purpose | Source |
|---|---|---|
| `get_vector_backend(name)` | Resolve a registered vector backend lazily. | `kgfs/search/backends/registry.py` |
| `list_vector_backend_names()` | Return known backend names. | `kgfs/search/backends/registry.py` |
| `backend_availability_by_name(context)` | Report availability for all registered backends. | `kgfs/search/backends/registry.py` |
| `get_vector_status(conn, config)` | Report semantic/vector readiness. | `kgfs/vectors/status.py` |
| `current_backend_metadata(conn, config, backend, model)` | Build metadata used to detect stale backend artifacts. | `kgfs/vectors/metadata.py` |
| `backend_metadata_health(conn, config, backend, model)` | Compare stored backend metadata to current chunks/config. | `kgfs/vectors/metadata.py` |
| `benchmark_vector_backends(conn, config, ...)` | Run bounded local vector backend timings. | `kgfs/vectors/benchmark.py` |
| `recommend_vector_backend(conn, config)` | Recommend a backend from local index state and availability. | `kgfs/vectors/recommend.py` |

### AI Assist

| API | Purpose | Source |
|---|---|---|
| `build_ai_context(question, results, settings, home=None)` | Build bounded/redacted OpenAI context. | `kgfs/ai.py` |
| `answer_question_with_ai(question, results, settings, client)` | Create answer from local snippets. | `kgfs/ai.py` |
| `rerank_results_with_ai(query, results, settings, client)` | Rerank local results with OpenAI result ID order. | `kgfs/ai.py` |
| `get_openai_client(settings)` | Build OpenAI Responses client. | `kgfs/ai.py` |
| `get_openai_api_key(settings)` | Read API key env var. | `kgfs/ai.py` |
| `redact_home_path(text, homes=...)` | Replace home path variants with `[HOME]`. | `kgfs/ai.py` |

## Example Programmatic Search

```python
from pathlib import Path

from kgfs.config import KGFSConfig
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.search import SearchContext, SearchOptions, build_default_search_registry

config = KGFSConfig(indexed_folders=[Path("sample-files")])
conn = connect_database(Path("kgfs.sqlite3"))
initialize_database(conn)
index_configured_folders(config, conn)

registry = build_default_search_registry()
context = SearchContext(conn=conn, config=config)
execution = registry.search("motor torque", SearchOptions(mode="auto"), context)

for result in execution.results:
    print(result.result_id, result.file_name, result.score)
```

Tests: `tests/test_search_kernel.py`.
