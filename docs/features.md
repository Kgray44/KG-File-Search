# Features

This page inventories features implemented in the repository state at this commit. If behavior is ambiguous, partially surfaced, or represented only as an extension point, it is called out under [Unclear or Needs Verification](#unclear-or-needs-verification).

## Safety and Configuration

### No-Scan Initialization

- What it does: creates config/app directories and a default YAML config with `indexed_folders: []`; it does not index files.
- Use it with: `kgfs init`, optionally `--config` or `--project-local`.
- Inputs: destination config path.
- Outputs: config file and app directories.
- Settings: `KGFS_CONFIG_PATH`, `KGFS_CONFIG_DIR`, `KGFS_PROJECT_LOCAL`, `--project-local`.
- Edge cases: existing config files are left unchanged; `kgfs config` fails if the resolved config file does not exist.
- Sources: `kgfs/cli/commands/init.py`, `kgfs/core/config.py`.
- Tests: `tests/test_config.py`, `tests/test_cli.py`.

### Platform App Directories

- What it does: resolves config, data, cache, and log paths through platformdirs unless project-local mode or explicit overrides are used.
- Use it with: most CLI commands and web app runtime; project-local mode uses `.kgfs/` under the current directory.
- Inputs: optional path overrides, environment variables, and `--project-local`.
- Outputs: `AppPaths` with config/database defaults.
- Settings: `KGFS_CONFIG_DIR`, `KGFS_DATA_DIR`, `KGFS_CACHE_DIR`, `KGFS_LOG_DIR`, `KGFS_PROJECT_LOCAL`.
- Edge cases: CLI commands pass an explicit boolean default for project-local mode, so prefer `--project-local` over relying on `KGFS_PROJECT_LOCAL` from CLI.
- Sources: `kgfs/core/app_dirs.py`, `kgfs/cli/shared.py`.
- Tests: `tests/test_app_dirs.py`, `tests/test_cli.py`.

### Path Expansion

- What it does: expands `~`, `~/...`, `~\...`, POSIX env vars, and Windows `%VAR%` variables.
- Use it with: config paths, database paths, indexed folders, and app-dir environment overrides.
- Inputs: path-like strings.
- Outputs: `pathlib.Path` values.
- Edge cases: undefined environment variables remain unchanged.
- Sources: `kgfs/core/path_utils.py`, `kgfs/core/config.py`.
- Tests: `tests/test_path_utils.py`, `tests/test_config.py`.

### Risky Root Refusal

- What it does: refuses filesystem roots, Windows drive roots, home root, and obvious system roots unless explicitly overridden.
- Use it with: default `kgfs index`; override with `--allow-risky-root`.
- Inputs: configured `indexed_folders`.
- Outputs: CLI error or `RiskyRootError` before broad indexing.
- Settings: `--allow-risky-root`.
- Edge cases: the override is broad and should be used only for intentional scans.
- Sources: `kgfs/core/safety.py`, `kgfs/cli/commands/index.py`, `kgfs/indexing/indexer.py`.
- Tests: `tests/test_safety.py`, `tests/test_indexing.py`, `tests/test_cli.py`.

### Folder Config Commands

- What it does: adds, removes, and lists configured indexed folders without indexing immediately.
- Use it with: `kgfs add-folder`, `kgfs remove-folder`, `kgfs list-folders`.
- Inputs: folder/file path for add/remove.
- Outputs: updated YAML and console tables.
- Settings: `indexed_folders`, `--config`, `--project-local`.
- Edge cases: add/remove rewrites YAML through `yaml.safe_dump`, so comments from the generated config are not preserved after edits.
- Sources: `kgfs/cli/commands/folders.py`, `kgfs/core/config_commands.py`.
- Tests: `tests/test_config_commands.py`, `tests/test_cli.py`.

### Config Display

- What it does: prints the active config path and file contents.
- Use it with: `kgfs config`.
- Inputs: config path.
- Outputs: console output.
- Settings: `--config`, `--project-local`, `KGFS_CONFIG_PATH`.
- Edge cases: does not create a missing config.
- Sources: `kgfs/cli/commands/config.py`.
- Tests: `tests/test_cli.py`, `tests/test_resources.py`.

### Doctor Diagnostics

- What it does: reports platform, Python version, packaged status, app paths, DB state, schema version, FTS5, semantic status, optional dependencies, and folder warnings.
- Use it with: `kgfs doctor`.
- Inputs: optional config/database/project-local flags.
- Outputs: Rich diagnostic tables.
- Settings: app path env vars, `semantic.*`.
- Edge cases: if config is missing, doctor uses default `KGFSConfig()` for diagnostics.
- Sources: `kgfs/cli/commands/doctor.py`, `kgfs/core/platform_utils.py`, `kgfs/core/resources.py`.
- Tests: `tests/test_cli.py`, `tests/test_resources.py`.

## Indexing and Extraction

### File Discovery

- What it does: walks each configured root and yields supported, small, non-ignored files in sorted order; a configured root may also be a file.
- Use it with: `kgfs index` or `index_configured_folders()`.
- Inputs: `KGFSConfig.indexed_folders`.
- Outputs: indexable `Path` objects.
- Settings: `indexed_folders`, `ignored_folders`, `include_extensions`, `ignored_extensions`, `exclude_globs`, `max_file_size_mb`, `follow_symlinks`.
- Edge cases: missing configured roots are skipped; symlinks are skipped unless enabled.
- Sources: `kgfs/indexing/discovery.py`, `kgfs/indexing/filters.py`.
- Tests: `tests/test_file_discovery.py`, `tests/test_file_filters.py`.

### Directory and File Filters

- What it does: skips default noisy/system directories, ignored extensions, unsupported extensions, exclude globs, symlinks, over-size files, and unreadable stat failures.
- Use it with: automatic discovery filtering.
- Inputs: file and directory paths.
- Outputs: boolean index/skip decisions.
- Settings: all filter-related config keys.
- Edge cases: directory matching is by directory name; extension matching is lowercase and dot-normalized during config load.
- Sources: `kgfs/indexing/filters.py`, `kgfs/core/config.py`.
- Tests: `tests/test_file_filters.py`.

### Extractor Dispatch

- What it does: routes file suffixes to extractor modules.
- Use it with: automatic indexing.
- Inputs: file path and extraction settings.
- Outputs: `ExtractionResult`.
- Settings: `include_extensions`, `extraction.pdf_max_pages`.
- Edge cases: unsupported extensions return `status="skipped"`.
- Sources: `kgfs/extractors/__init__.py`, `kgfs/extractors/base.py`.
- Tests: `tests/test_extractors.py`.

### Text, Markdown, Code, CSV, PDF, and DOCX Extraction

- What it does: extracts text from `.txt`, `.html`, `.css`, `.json`, `.md`, `.py`, `.js`, `.ts`, `.csv`, `.pdf`, and `.docx`.
- Use it with: enabled default include extensions during indexing.
- Inputs: matching files.
- Outputs: extracted text or stored extraction errors.
- Settings: `include_extensions`, `extraction.pdf_max_pages`.
- Edge cases: Markdown/code extraction is plain text, not syntax-aware; missing `pypdf` or `python-docx` becomes an extraction error; CSV falls back to latin-1 text on decode failure.
- Sources: `kgfs/extractors/text.py`, `kgfs/extractors/markdown.py`, `kgfs/extractors/code.py`, `kgfs/extractors/csv.py`, `kgfs/extractors/pdf.py`, `kgfs/extractors/docx.py`.
- Tests: `tests/test_extractors.py`, `tests/test_indexing.py`, `tests/test_cli.py`.

### Incremental Indexing

- What it does: skips unchanged files by comparing size and precise modified time before hashing.
- Use it with: default `kgfs index`.
- Inputs: indexed files and existing DB rows.
- Outputs: `IndexSummary.skipped_unchanged`.
- Settings: `indexing.skip_unchanged_files`.
- Edge cases: if disabled, files are re-extracted; stale rows are not deleted unless prune is requested.
- Sources: `kgfs/indexing/indexer.py`, `kgfs/db/repositories.py`.
- Tests: `tests/test_indexing.py`.

### Hash Verification

- What it does: stores SHA-256 hashes and can verify hashes even when size/mtime look unchanged.
- Use it with: default hashing and `kgfs index --verify-hashes`.
- Inputs: file bytes.
- Outputs: `content_hash` in the DB and reindex decisions.
- Settings: `indexing.hash_files`, `--verify-hashes`.
- Edge cases: unchanged files can skip hashing unless `--verify-hashes` is supplied.
- Sources: `kgfs/indexing/hashing.py`, `kgfs/indexing/indexer.py`.
- Tests: `tests/test_indexing.py`.

### Force, Dry Run, and Prune-on-Index

- What it does: `--force` re-extracts existing records, `--dry-run` discovers without writing, and `--prune` removes stale DB rows after indexing.
- Use it with: `kgfs index --force`, `kgfs index --dry-run`, `kgfs index --prune`.
- Inputs: configured files and existing database.
- Outputs: index/prune summaries.
- Settings: CLI flags.
- Edge cases: dry-run still stats files, so inaccessible files can count as failures.
- Sources: `kgfs/cli/commands/index.py`, `kgfs/indexing/indexer.py`, `kgfs/indexing/prune.py`.
- Tests: `tests/test_cli.py`, `tests/test_indexing.py`, `tests/test_prune.py`.

### Semantic Chunk Creation During Indexing

- What it does: when semantic is enabled, splits extracted text into overlapping chunks, embeds locally, and stores vector BLOBs in SQLite.
- Use it with: `semantic.enabled: true` and `kgfs index --rebuild-embeddings` or `kgfs semantic-index --rebuild`.
- Inputs: extracted text.
- Outputs: `chunks` rows.
- Settings: `semantic.*`, `--rebuild-embeddings`, `--rebuild`.
- Edge cases: requires sentence-transformers unless tests inject a fake embedder; local-only model loading is the default.
- Sources: `kgfs/indexing/indexer.py`, `kgfs/search/semantic.py`, `kgfs/db/schema.py`.
- Tests: `tests/test_semantic.py`, `tests/test_search_kernel.py`.

## Search and Retrieval

### FTS Query Building

- What it does: tokenizes natural-language queries, removes fixed stopwords, and builds prefix FTS terms joined by `AND` or fallback `OR`.
- Use it with: keyword search.
- Inputs: query string.
- Outputs: SQLite FTS5 query string.
- Edge cases: empty meaningful tokens return no results.
- Sources: `kgfs/search/query.py`, `kgfs/search/keyword.py`.
- Tests: `tests/test_search.py`, `tests/test_ranking.py`.

### Keyword Search

- What it does: searches `files_fts`, falls back from `AND` to `OR`, filters candidates, ranks with BM25-derived score plus local boosts, and returns stable result IDs.
- Use it with: `kgfs search --mode keyword` or `search()`.
- Inputs: query, DB connection, filters, limit.
- Outputs: `SearchResult` list.
- Settings: `search.default_limit`, `search.highlight_matches`, filters.
- Edge cases: SQLite `OperationalError` during FTS search returns no results.
- Sources: `kgfs/search/keyword.py`, `kgfs/search/ranking.py`.
- Tests: `tests/test_search.py`, `tests/test_search_filters.py`, `tests/test_ranking.py`.

### Search Filters

- What it does: filters by extension, file type, folder/path substring, modified-date range, and extraction failures.
- Use it with: CLI flags or web `/search` parameters.
- Inputs: filter values.
- Outputs: filtered search results.
- Settings: `--ext`, `--type`, `--folder`, `--after`, `--before`, `--failed-only`; web query params.
- Edge cases: `before` expands to the end of the given day; invalid dates are parsed with `datetime.fromisoformat`.
- Sources: `kgfs/search/filters.py`, `kgfs/cli/commands/search.py`, `kgfs/web/app.py`.
- Tests: `tests/test_search_filters.py`, `tests/test_web.py`.

### Snippets and Highlighting

- What it does: builds compact snippets near matching terms, compacts multiline text, handles Unicode/punctuation terms, and can add Rich `[bold]` markup.
- Use it with: search result rendering and AI context building.
- Inputs: extracted text and query.
- Outputs: snippet string.
- Settings: `search.highlight_matches`.
- Edge cases: AI context strips Rich bold markup before sending snippets.
- Sources: `kgfs/search/snippets.py`, `kgfs/ai.py`.
- Tests: `tests/test_snippets.py`, `tests/test_ai.py`.

### Semantic Search

- What it does: embeds the query locally, searches configured vector backend chunks, and returns the best chunk per file.
- Use it with: `kgfs semantic "query"` or `kgfs search --mode semantic`.
- Inputs: query, chunks, embedder.
- Outputs: semantic `SearchResult` list.
- Settings: `semantic.enabled`, `semantic.model_name`, `semantic.local_files_only`, `semantic.batch_size`, `vectors.backend`.
- Edge cases: explicit semantic mode is unavailable when semantic config/dependencies/backend/chunks are not ready.
- Sources: `kgfs/search/keyword.py`, `kgfs/search/semantic.py`, `kgfs/search/modes/semantic.py`.
- Tests: `tests/test_semantic.py`, `tests/test_search_kernel.py`, `tests/test_cli.py`.

### Hybrid Search

- What it does: combines semantic score, keyword score, filename relevance, path relevance, exact phrase relevance, and recency.
- Use it with: `kgfs search --hybrid` or `kgfs search --mode hybrid`.
- Inputs: query, chunks, FTS rows.
- Outputs: hybrid `SearchResult` list with score breakdown.
- Settings: `semantic.*`, `vectors.backend`, `hybrid.*`, `search.default_mode`.
- Edge cases: requires semantic availability; candidate limit is controlled by `hybrid.candidate_limit_multiplier` with a floor of 25.
- Sources: `kgfs/search/keyword.py`, `kgfs/search/modes/hybrid.py`, `kgfs/search/ranking.py`.
- Tests: `tests/test_semantic.py`, `tests/test_search_kernel.py`, `tests/test_ranking.py`.

### Auto Search Mode

- What it does: uses hybrid when semantic is enabled, dependencies are available, vector backend is available, and chunks exist; otherwise falls back to keyword.
- Use it with: default `search.default_mode: auto` or `kgfs search --mode auto`.
- Inputs: `SearchContext`.
- Outputs: `SearchExecution` with `mode_used` and warnings.
- Settings: `search.default_mode`, `semantic.*`, `vectors.backend`.
- Edge cases: if semantic is enabled but unavailable, auto emits a warning; `auto` is not a concrete registry engine.
- Sources: `kgfs/search/registry.py`, `kgfs/search/modes/auto.py`.
- Tests: `tests/test_search_kernel.py`, `tests/test_cli.py`.

### Search Engine Registry

- What it does: registers keyword, semantic, and hybrid engines; resolves mode names; reports availability; executes searches.
- Use it with: CLI search and library callers.
- Inputs: `SearchOptions`, `SearchContext`.
- Outputs: `SearchExecution`.
- Settings: `SearchOptions.mode`, `SearchOptions.limit`, `SearchOptions.filters`.
- Edge cases: web search currently calls keyword search directly and does not use registry modes.
- Sources: `kgfs/search/engine.py`, `kgfs/search/registry.py`, `kgfs/search/modes/*.py`.
- Tests: `tests/test_search_kernel.py`, `tests/test_cli.py`.

### Vector Backend Interface and `sqlite_scan`

- What it does: defines a vector backend protocol and provides the default SQLite scan backend for chunk search, status, stats, and clearing.
- Use it with: semantic/hybrid search and vector commands.
- Inputs: query vector, `VectorSearchOptions`, `SearchContext`.
- Outputs: `VectorSearchHit` rows sorted by cosine score.
- Settings: `vectors.backend` (`sqlite_scan` at this commit), `semantic.model_name`.
- Edge cases: malformed vector BLOBs and dimension mismatches are skipped; unknown backend names make semantic/hybrid unavailable.
- Sources: `kgfs/search/backends/base.py`, `kgfs/search/backends/__init__.py`, `kgfs/search/backends/sqlite_scan.py`.
- Tests: `tests/test_vector_backend.py`, `tests/test_search_kernel.py`.

### Vector Management Commands

- What it does: reports vector readiness, rebuilds chunks from already indexed extracted text, and clears only vector/chunk rows.
- Use it with: `kgfs vector status`, `kgfs vector rebuild`, `kgfs vector clear --yes`.
- Inputs: config/database runtime and indexed file records.
- Outputs: status table, `VectorRebuildSummary`, or deleted chunk count.
- Settings: `semantic.enabled`, `semantic.*`, `vectors.backend`, `--force/--no-force`, `--yes`.
- Edge cases: rebuild requires `semantic.enabled: true`; clear requires `--yes`; clear leaves source files, `files`, and keyword FTS rows unchanged.
- Sources: `kgfs/cli/commands/vector.py`, `kgfs/vectors/index_manager.py`, `kgfs/vectors/status.py`, `kgfs/vectors/chunks.py`.
- Tests: `tests/test_vector_commands.py`, `tests/test_vector_status.py`.

### Latest Result IDs

- What it does: stores the most recent search result IDs for `open`, `reveal`, and `why`.
- Use it with: automatic CLI/web search saving when enabled.
- Inputs: query and results.
- Outputs: `latest_results` rows.
- Settings: `search.save_latest_results`.
- Edge cases: only one latest-result set is stored; new searches replace old rows.
- Sources: `kgfs/db/latest_results.py`, `kgfs/cli/commands/search.py`, `kgfs/web/app.py`.
- Tests: `tests/test_search.py`, `tests/test_web.py`, `tests/test_cli.py`.

### Result Explanations

- What it does: explains why a saved latest search result matched a query, including score breakdown and snippet.
- Use it with: `kgfs why RESULT_ID QUERY [--mode MODE]`.
- Inputs: latest result ID and query.
- Outputs: console explanation table and notes.
- Settings: `search.default_mode`, `search.default_limit`, `search.highlight_matches`, `--mode`.
- Edge cases: reruns search with `save_latest_results=False`; if the result is not present in the fresh rerun, it loads the saved file and reports that limitation.
- Sources: `kgfs/cli/commands/why.py`, `kgfs/search/explain.py`, `kgfs/search/result.py`.
- Tests: `tests/test_cli.py`.

## User Interfaces

### Typer CLI

- What it does: exposes KGFS commands through the `kgfs` console script and `python -m kgfs`.
- Use it with: `kgfs --help`.
- Inputs: CLI args.
- Outputs: console output and database updates.
- Settings: command flags, config, environment variables.
- Edge cases: no shell-completion setup is documented in source.
- Sources: `pyproject.toml`, `kgfs/__main__.py`, `kgfs/cli/app.py`.
- Tests: `tests/test_cli.py`.

### Stats Command

- What it does: shows indexed file counts, sizes, semantic chunk count, embedding storage, failures, stale records, DB size, schema version, file types, and largest files.
- Use it with: `kgfs stats`.
- Inputs: database path.
- Outputs: Rich tables.
- Settings: `--config`, `--database`, `--project-local`.
- Edge cases: stale record count checks source path existence at runtime.
- Sources: `kgfs/cli/commands/stats.py`, `kgfs/db/stats.py`.
- Tests: `tests/test_cli.py`, `tests/test_prune.py`.

### Open and Reveal Commands

- What it does: opens or reveals a file from latest search results using platform-specific behavior.
- Use it with: `kgfs open 1`, `kgfs reveal 1`, web `/open/{result_id}`, web `/reveal/{result_id}`.
- Inputs: latest result ID.
- Outputs: OS open/reveal side effect.
- Settings: `search.save_latest_results`.
- Edge cases: fails if no latest result has that ID; missing files reveal/open parent folder where possible.
- Sources: `kgfs/cli/commands/open_reveal.py`, `kgfs/core/platform_utils.py`, `kgfs/web/app.py`.
- Tests: `tests/test_platform_utils.py`, `tests/test_web.py`.

### Web Dashboard

- What it does: provides local HTML pages for home, keyword search, stats, config, extraction failures, and latest-result open/reveal.
- Use it with: `kgfs web` at `http://127.0.0.1:8765` by default.
- Inputs: browser requests.
- Outputs: HTML/plain text responses.
- Settings: `--host`, `--port`, config/database flags.
- Edge cases: web search is keyword-only; no authentication is implemented.
- Sources: `kgfs/cli/commands/web.py`, `kgfs/web/app.py`, `kgfs/web/templates/*.html`.
- Tests: `tests/test_web.py`.

## Maintenance

### Prune Stale Records

- What it does: removes DB records, FTS rows, chunks, and latest-result rows for files that no longer exist.
- Use it with: `kgfs prune`, `kgfs prune --dry-run`, `kgfs index --prune`.
- Inputs: DB rows.
- Outputs: `PruneSummary` and console output.
- Settings: `--dry-run`.
- Edge cases: displays only the first 20 stale paths in CLI output; does not delete source files.
- Sources: `kgfs/indexing/prune.py`, `kgfs/cli/commands/maintenance.py`.
- Tests: `tests/test_prune.py`.

### Reset and Rebuild Index

- What it does: reset removes KGFS database files only; rebuild resets and indexes configured folders again.
- Use it with: `kgfs reset-index --dry-run`, `kgfs reset-index --yes`, `kgfs rebuild --yes`.
- Inputs: database path and config.
- Outputs: removed database files and new indexed data.
- Settings: `--yes`, `--dry-run`, `--allow-risky-root`.
- Edge cases: source files and config files are not removed; rebuild force-indexes by default.
- Sources: `kgfs/reset.py`, `kgfs/cli/commands/maintenance.py`.
- Tests: `tests/test_reset_rebuild.py`.

### Schema Initialization and Migrations

- What it does: creates the current schema, runs idempotent migrations, and tracks schema version.
- Use it with: automatic CLI/web DB connection.
- Inputs: SQLite connection.
- Outputs: tables and `schema_version` row.
- Settings: `CURRENT_SCHEMA_VERSION = 1`.
- Edge cases: newer DB schema versions raise `RuntimeError`.
- Sources: `kgfs/db/schema.py`, `kgfs/db/migrations.py`.
- Tests: `tests/test_migrations.py`.

## Optional AI Assist

### AI Context Preview

- What it does: builds and prints the exact OpenAI context without making an API call when preview-only is used.
- Use it with: `kgfs ask ... --preview-ai-context` or `kgfs search ... --ai-rerank --preview-ai-context`.
- Inputs: local results and AI settings.
- Outputs: console preview.
- Settings: `ai.preview_context_before_send`, `ai.max_*`, `ai.send_*`, `ai.redact_home_path`.
- Edge cases: preview can also print before confirmation when configured.
- Sources: `kgfs/ai.py`, `kgfs/cli/shared.py`, `kgfs/cli/commands/search.py`.
- Tests: `tests/test_ai.py`, `tests/test_cli.py`.

### AI Answer Synthesis

- What it does: sends local result snippets to OpenAI and prints an answer constrained by prompt text.
- Use it with: `kgfs ask "question"` after enabling AI.
- Inputs: question and local search results.
- Outputs: `AIResult` and console answer.
- Settings: `ai.enabled`, `ai.allow_answer_synthesis`, `ai.model`, `ai.api_key_env`.
- Edge cases: requires OpenAI SDK and API key; disabled by default.
- Sources: `kgfs/ai.py`, `kgfs/cli/commands/search.py`.
- Tests: `tests/test_ai.py`, `tests/test_cli.py`.

### AI Reranking

- What it does: sends local result snippets to OpenAI and expects JSON result IDs ordered by relevance.
- Use it with: `kgfs search "query" --ai-rerank` after enabling AI.
- Inputs: query and local results.
- Outputs: reordered result list.
- Settings: `ai.enabled`, `ai.allow_rerank`, `ai.max_*`.
- Edge cases: non-JSON output is parsed best-effort; unmentioned results remain after reranked IDs.
- Sources: `kgfs/ai.py`, `kgfs/cli/commands/search.py`.
- Tests: `tests/test_ai.py`, `tests/test_cli.py`.

## Packaging and CI

### PyInstaller Packaging

- What it does: builds onedir by default or experimental onefile; includes runtime modules, web assets, README, LICENSE, config example, and generated quickstart.
- Use it with: `python scripts/build_package.py --clean`.
- Inputs: build flags.
- Outputs: `dist-packages/KGFS-<os>-<arch>.zip`.
- Settings: `KGFS_PYINSTALLER_MODE`, `KGFS_PACKAGE_NAME`.
- Edge cases: base package excludes tests, semantic dependencies/model caches, and OpenAI SDK.
- Sources: `scripts/build_package.py`, `packaging/pyinstaller/kgfs.spec`.
- Tests: `tests/test_packaging_scripts.py`.

### Packaged Smoke Test

- What it does: finds the packaged executable and runs help, doctor, init, config, add-folder, index, and search against a temporary project-local corpus.
- Use it with: `python scripts/smoke_test_packaged.py --package dist-packages/KGFS`.
- Inputs: package path.
- Outputs: pass/fail smoke result.
- Settings: `KGFS_PROJECT_LOCAL`, `COLUMNS` in smoke-test subprocess environment.
- Edge cases: temporary smoke corpus is deleted after the test.
- Sources: `scripts/smoke_test_packaged.py`.
- Tests: `tests/test_packaging_scripts.py`.

### GitHub Actions CI

- What it does: runs tests on Windows, macOS, and Ubuntu for Python 3.11 and 3.12; package workflow builds Windows and macOS artifacts.
- Use it with: push, pull request, or manual packaging workflow.
- Inputs: GitHub workflow events.
- Outputs: test runs and uploaded package artifacts.
- Settings: workflow YAML.
- Edge cases: no GitHub Release publishing workflow is implemented.
- Sources: `.github/workflows/ci.yml`, `.github/workflows/package.yml`.
- Tests: `tests/test_ci_workflow.py`.

## Unclear or Needs Verification

- `KGFS_PROJECT_LOCAL` is implemented in `kgfs/core/app_dirs.py` when `get_app_paths(project_local=None)` is used, but most CLI commands pass an explicit default `False` unless `--project-local` is supplied. For CLI use, prefer `--project-local`.
- `SearchOptions.backend` exists in `kgfs/search/options.py`, but no CLI/web path currently exposes backend selection.
- `SearchOptions.explain` and `SearchEngine.explain()` exist as runtime fields/hooks. User-facing explanation is implemented through `kgfs why`, not through a generic `--explain` search flag.
- `ai.allow_query_expansion` exists in `kgfs/core/config.py`, but no implemented query expansion command path was found.
- `vectors.shard_strategy` exists in config defaults and `VectorSettings`, but no behavior beyond storing/validating the setting was found.
