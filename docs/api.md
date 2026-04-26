# API and Programmatic Interfaces

KGFS exposes three programmatic surfaces in the current worktree:

- A token-gated local JSON API started with `kgfs serve`.
- An HTML/plain-text FastAPI dashboard started with `kgfs web`.
- Python module functions and dataclasses.

CLI commands are documented separately in [CLI](cli.md).

## Local JSON API

App factory source: `kgfs/api/app.py`; route source: `kgfs/api/routes.py`.

Start through CLI:

```bash
export KGFS_API_TOKEN="dev-token"
kgfs serve
```

Default bind:

```text
http://127.0.0.1:8766
```

The API is local-first. `kgfs serve` refuses non-localhost binds unless
`--allow-network` is supplied. Token auth is required by default and uses the
environment variable named by `api.token_env`, default `KGFS_API_TOKEN`.

### API Auth

Protected requests use:

```text
Authorization: Bearer <KGFS_API_TOKEN>
```

Auth and bind behavior:

| Setting/flag | Default | Behavior | Source |
|---|---:|---|---|
| `api.require_token` | `true` | Requires bearer token on protected routes. | `kgfs/api/auth.py` |
| `api.token_env` | `KGFS_API_TOKEN` | Names the token environment variable. | `kgfs/api/auth.py` |
| `--no-token` | `false` | Disables token requirement for that run. | `kgfs/cli/commands/serve.py` |
| `api.host` / `--host` | `127.0.0.1` | API bind host. | `kgfs/cli/commands/serve.py` |
| `--allow-network` | `false` | Explicitly allows non-localhost binds. | `kgfs/api/auth.py` |
| `api.allow_file_actions` | `false` | Allows POST open/reveal latest-result actions only when true. | `kgfs/api/routes.py` |

`api.enabled` exists in config, but the explicit `kgfs serve` command can start
the API when invoked and does not require that flag to be true in the current
implementation.

### API Routes

All routes below are protected by the bearer-token dependency unless token auth
is disabled.

| Method | Path | Query/path parameters | Response | Behavior | Source |
|---|---|---|---|---|---|
| `GET` | `/health` | None | JSON `APIHealth` | Reports API/local/file-action status, indexed-file count, and schema version. | `kgfs/api/routes.py`, `kgfs/api/models.py` |
| `GET` | `/status` | None | JSON health report dict | Returns the same local index/workflow health report used by CLI health. | `kgfs/api/routes.py`, `kgfs/intelligence/health.py` |
| `GET` | `/search` | `q`, `mode`, `limit`, `ext`, `folder`, `after`, `before`, `failed_only` | JSON `APISearchResponse` | Runs registry search, clamps limit to 1..100, saves latest results, and returns mode/warnings/results. | `kgfs/api/routes.py`, `kgfs/search/registry.py` |
| `GET` | `/deep` | `q`, `limit`, `mode` | JSON | Runs deterministic local deep search and returns variants, followups, and results. | `kgfs/api/routes.py`, `kgfs/search/deep.py` |
| `GET` | `/research` | `q`, `limit`, `mode` | JSON | Builds local citation-backed research data without AI. | `kgfs/api/routes.py`, `kgfs/search/research.py` |
| `GET` | `/file/{file_id}` | indexed `file_id` | JSON file row subset | Returns indexed file metadata or 404. | `kgfs/api/routes.py` |
| `GET` | `/collections` | None | JSON list | Lists collections. | `kgfs/api/routes.py`, `kgfs/workflows/collections.py` |
| `GET` | `/collections/{name}` | collection name | JSON list | Lists collection items or 404. | `kgfs/api/routes.py`, `kgfs/workflows/collections.py` |
| `GET` | `/tags` | optional `tag` | JSON list | Lists all tags, or files for one tag. | `kgfs/api/routes.py`, `kgfs/workflows/tags.py` |
| `GET` | `/projects` | optional `name` | JSON list | Lists projects, or project items for one project. | `kgfs/api/routes.py`, `kgfs/workflows/projects.py` |
| `GET` | `/graph` | `q` | JSON graph | Builds a bounded topic graph. | `kgfs/api/routes.py`, `kgfs/intelligence/graph.py` |
| `GET` | `/metadata/export` | None | JSON | Exports KGFS workflow/intelligence metadata, excluding source contents and vector/OCR payloads. | `kgfs/api/routes.py`, `kgfs/intelligence/export.py` |
| `POST` | `/open/{result_id}` | latest `result_id` | JSON | Opens a latest result only when `api.allow_file_actions` is true. | `kgfs/api/routes.py`, `kgfs/core/platform_utils.py` |
| `POST` | `/reveal/{result_id}` | latest `result_id` | JSON | Reveals a latest result only when `api.allow_file_actions` is true. | `kgfs/api/routes.py`, `kgfs/core/platform_utils.py` |

Example:

```bash
curl -H "Authorization: Bearer $KGFS_API_TOKEN" \
  "http://127.0.0.1:8766/search?q=motor%20torque&mode=keyword&limit=5"
```

Tests: `tests/test_phase9_ux_integrations.py`.

Framework-provided FastAPI endpoints are also present on the JSON API app
because `FastAPI(title="KGFS Local API")` is created without disabling default
docs/schema URLs. These expose API schema/docs, not KGFS index contents, and are
not customized by KGFS:

| Method | Path | Response | Notes | Source |
|---|---|---|---|---|
| `GET` | `/openapi.json` | JSON | FastAPI-generated OpenAPI schema for the local API app. | `kgfs/api/app.py` |
| `GET` | `/docs` | HTML | FastAPI Swagger UI. Not customized by KGFS. | `kgfs/api/app.py` |
| `GET` | `/redoc` | HTML | FastAPI ReDoc UI. Not customized by KGFS. | `kgfs/api/app.py` |

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
| `GET` | `/` | None | HTML | Shows summary metrics, vector backend, OCR state, and health issue count. | `kgfs/web/app.py`, `kgfs/web/templates/index.html` |
| `GET` | `/search` | `q`, `mode`, `ext`, `folder`, `after`, `before`, `limit`, `failed_only` | HTML | Runs registry search when `q` is provided, saves latest results, renders mode/warnings/errors, tags, notes, and results. | `kgfs/web/app.py`, `kgfs/web/templates/search.html` |
| `GET` | `/collections` | None | HTML | Lists local collections. | `kgfs/web/app.py`, `kgfs/web/templates/collections.html` |
| `GET` | `/tags` | None | HTML | Lists local tag names. | `kgfs/web/app.py`, `kgfs/web/templates/tags.html` |
| `GET` | `/projects` | None | HTML | Lists local manual projects. | `kgfs/web/app.py`, `kgfs/web/templates/projects.html` |
| `GET` | `/graph` | optional `q` | HTML | Builds and renders a topic graph when a query is supplied. | `kgfs/web/app.py`, `kgfs/web/templates/graph.html` |
| `GET` | `/health` | None | HTML | Renders the local health report. | `kgfs/web/app.py`, `kgfs/web/templates/health.html` |
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
| `mode` | string | `auto` | `auto`, `keyword`, `semantic`, or `hybrid`; errors are rendered in the page. |
| `limit` | int | `10` | Max results, clamped to 1..100 in the route. |
| `failed_only` | bool | `false` | Only extraction failures. |

Current limitation: the web dashboard has no authentication and does not expose
AI reranking/answer synthesis. It now routes search through the local registry,
so semantic/hybrid results are available when configured and ready.

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

### Local API Helpers

| API | Purpose | Source |
|---|---|---|
| `create_api_app(config_path=..., database_path=..., project_local=...)` | Build the local JSON FastAPI app and attach routes with config-derived auth settings. | `kgfs/api/app.py` |
| `build_router(runtime, auth_settings)` | Build API routes for health, search, workflows, graph, metadata export, and file actions. | `kgfs/api/routes.py` |
| `APIAuthSettings` | Dataclass carrying token requirement and token env var name. | `kgfs/api/auth.py` |
| `validate_api_bind(host, allow_network=...)` | Refuse non-localhost binds unless explicitly allowed. | `kgfs/api/auth.py` |
| `require_api_token(settings, authorization=...)` | FastAPI dependency that checks bearer token header. | `kgfs/api/auth.py` |
| `APIHealth`, `APIResult`, `APISearchResponse` | Pydantic response models for JSON API health/search payloads. | `kgfs/api/models.py` |

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

### OCR Helpers

| API | Purpose | Source |
|---|---|---|
| `list_ocr_backends()` | List registered OCR backend names. | `kgfs/ocr/registry.py` |
| `get_ocr_backend(name)` | Resolve an OCR backend by name. | `kgfs/ocr/registry.py` |
| `get_ocr_status(config, conn=None)` | Return OCR enabled/backend/cache/index status and warnings. | `kgfs/ocr/status.py` |
| `get_cached_ocr_result(...)`, `store_ocr_cache_result(...)` | Read/write local OCR cache rows. | `kgfs/ocr/cache.py` |
| `count_ocr_cache_entries(conn)` | Count OCR cache rows for stats/status. | `kgfs/ocr/cache.py` |
| `extract_scanned_pdf(...)` | Scanned-PDF fallback scaffold that reports unsupported rasterization safely. | `kgfs/ocr/pdf.py` |

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
| `deep_search(conn, query, config, ...)` | Run deterministic local query variants and fuse results. | `kgfs/search/deep.py` |
| `similar_from_result(...)`, `similar_file(...)` | Find similar indexed files using vectors or term-overlap fallback. | `kgfs/search/similar.py` |
| `compare_results(...)` | Compare two latest results locally. | `kgfs/search/compare.py` |
| `timeline_search(...)` | Sort/group local search results chronologically. | `kgfs/search/timeline.py` |
| `research_query(...)` | Build local citation-backed research data without AI. | `kgfs/search/research.py` |
| `format_citation(...)`, `format_citation_block(...)` | Format KGFS local citation labels and blocks. | `kgfs/search/citations.py` |

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

### TUI and Integration Helpers

| API | Purpose | Source |
|---|---|---|
| `textual_available()` | Check whether optional Textual dependency can be imported. | `kgfs/tui/app.py` |
| `launch_tui(...)` | Launch the minimal Textual UI or raise `TextualUnavailableError`. | `kgfs/tui/app.py` |
| `build_tui_search_options(mode=..., limit=...)` | Build search options for future non-interactive TUI search plumbing. | `kgfs/tui/actions.py` |
| `get_integration_status()` | Return read-only support/scaffold/installed status rows. | `kgfs/integrations/status.py` |
| `export_raycast()`, `export_alfred()` | Write local launcher script scaffolds. | `kgfs/integrations/raycast.py`, `kgfs/integrations/alfred.py` |
| `scaffold_powertoys()`, `scaffold_finder()`, `scaffold_explorer()`, `scaffold_tray()` | Write local template/scaffold files without changing system settings. | `kgfs/integrations/*.py` |

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
