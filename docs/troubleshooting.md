# Troubleshooting

Start with:

```bash
kgfs doctor
kgfs stats
```

Use explicit paths when debugging a specific config/database:

```bash
kgfs doctor --config ./config.yaml --database ./kgfs.sqlite3
kgfs stats --config ./config.yaml --database ./kgfs.sqlite3
```

Sources: `kgfs/cli/commands/doctor.py`, `kgfs/cli/commands/stats.py`.

## Common Issues

| Symptom | Likely cause | Fix | Source |
|---|---|---|---|
| `kgfs index` says no indexed folders configured | `indexed_folders` is empty. This is the default. | Add a folder with `kgfs add-folder "path"` or edit config. | `kgfs/cli/commands/index.py`, `kgfs/core/config.py` |
| `kgfs index` refuses risky root folders | Config includes `/`, `C:\`, home root, or known system root. | Choose a narrower folder or pass `--allow-risky-root` only when intentional. | `kgfs/core/safety.py`, `tests/test_safety.py` |
| Expected files are not indexed | Extension not in `include_extensions`, extension is ignored, path matches `exclude_globs`, file is too large, folder is ignored, symlink skipped, or root missing. | Run `kgfs config`; check filters; run `kgfs index --dry-run`; adjust config. | `kgfs/indexing/filters.py`, `kgfs/indexing/discovery.py` |
| Files under symlinked directories are missing | `follow_symlinks` defaults to false. | Set `follow_symlinks: true` only if the target scope is safe. | `kgfs/indexing/discovery.py`, `tests/test_file_discovery.py` |
| Search returns no results after editing a file | Incremental metadata check may think the file is unchanged, or the index is stale. | Run `kgfs index --verify-hashes` or `kgfs index --force`. | `kgfs/indexing/indexer.py`, `tests/test_indexing.py` |
| Old/deleted files still appear in search | KGFS does not delete stale DB rows during normal indexing unless asked. | Run `kgfs prune --dry-run`, then `kgfs prune`; or `kgfs index --prune`. | `kgfs/indexing/prune.py`, `kgfs/cli/commands/maintenance.py` |
| Extraction failures appear | Parser dependency missing or parser could not read file. | Run `kgfs doctor`; inspect `kgfs web /failures` or DB `extraction_error`; install dependencies if missing. | `kgfs/extractors/pdf.py`, `kgfs/extractors/docx.py`, `kgfs/web/app.py` |
| Image files are not indexed | OCR is disabled by default, or the image extension is not in `ocr.include_extensions`. | Set `ocr.enabled: true`, confirm extensions, then run `kgfs ocr status` and `kgfs ocr index`. | `kgfs/indexing/filters.py`, `kgfs/ocr/status.py` |
| `kgfs ocr status` says Tesseract is missing | The configured Tesseract command is not on PATH or the command path is wrong. | Install Tesseract locally and set `ocr.tesseract.command` to `tesseract` or a full executable path. | `kgfs/ocr/tesseract.py` |
| OCR result is an extraction error | Tesseract could not read the image or exited non-zero. | Try `kgfs ocr test PATH`; check language and command settings. | `kgfs/cli/commands/ocr.py`, `kgfs/ocr/tesseract.py` |
| Scanned PDF text is not extracted | Full scanned-PDF rasterization is not implemented in this pass. | KGFS detects likely scanned PDFs and records a helpful error; use image OCR for screenshots/images until PDF rasterization is added. | `kgfs/extractors/pdf.py`, `kgfs/ocr/pdf.py` |
| OCR keeps rerunning | Cache disabled, source metadata changed, or hash changed. | Leave `ocr.cache_results: true`; rerun without `--force` for unchanged files. | `kgfs/ocr/cache.py`, `kgfs/indexing/indexer.py` |
| PDF support is missing | `pypdf` not installed. | Install base package dependencies with `python -m pip install -e ".[dev]"` or install `pypdf`. | `pyproject.toml`, `kgfs/extractors/pdf.py` |
| DOCX support is missing | `python-docx` not installed. | Install base package dependencies with `python -m pip install -e ".[dev]"` or install `python-docx`. | `pyproject.toml`, `kgfs/extractors/docx.py` |
| `kgfs search --mode semantic` reports unavailable | `semantic.enabled` false, dependency missing, model unavailable, or no chunks indexed for model. | Enable semantic config, install `.[semantic]`, ensure local model availability, run `kgfs semantic-index --rebuild`. | `kgfs/search/modes/semantic.py`, `kgfs/cli/commands/semantic.py` |
| Auto mode warns and uses keyword search | Semantic is enabled but hybrid is unavailable. | Run `kgfs semantic-index --rebuild` and check `kgfs doctor`. | `kgfs/search/registry.py`, `kgfs/search/modes/auto.py` |
| `kgfs vector status` warns about unknown backend | `vectors.backend` is not one of the registered names. | Use `sqlite_scan`, `sqlite_vec`, `hnsw`, or `faiss`; prefer `sqlite_scan` unless testing advanced backends. | `kgfs/search/backends/registry.py`, `kgfs/vectors/status.py` |
| Optional vector backend reports unavailable | Optional dependency is missing, backend is disabled, artifact metadata is stale, or the backend artifact has not been rebuilt. | Use `sqlite_scan`, install the relevant extra such as `.[hnsw]`, `.[sqlite-vec]`, or `.[faiss]`, enable the backend config, then run `kgfs vector rebuild --backend NAME`. | `kgfs/search/backends/registry.py`, `kgfs/search/backends/hnsw.py`, `kgfs/search/backends/sqlite_vec.py`, `kgfs/search/backends/faiss.py` |
| `kgfs vector benchmark` has no query timings | No semantic chunks/vectors exist. | Enable semantic search and rebuild vectors, then rerun the benchmark. | `kgfs/vectors/benchmark.py`, `kgfs/vectors/index_manager.py` |
| `kgfs vector recommend` suggests building vectors first | The database has no chunks for the configured model. | Run `kgfs vector rebuild` after enabling semantic search and ensuring local embedding dependencies/model are available. | `kgfs/vectors/recommend.py` |
| `kgfs vector rebuild` says semantic is disabled | `semantic.enabled` is false. | Set `semantic.enabled: true`, ensure semantic dependencies/model are available, then rebuild. | `kgfs/cli/commands/vector.py`, `kgfs/vectors/index_manager.py` |
| `kgfs vector rebuild --no-force` skips files | Chunks already exist for the configured model. | Use the default `--force` behavior when you intentionally want to rebuild existing chunks. | `kgfs/vectors/index_manager.py` |
| `kgfs vector clear` fails without `--yes` | Clear requires explicit confirmation. | Run `kgfs vector clear --yes` after verifying the database/config target. | `kgfs/cli/commands/vector.py` |
| Semantic/hybrid search ignores some chunks | Stored vector BLOB is malformed or its dimension differs from the query vector. | Rebuild vectors with `kgfs vector rebuild` or `kgfs semantic-index --rebuild`. | `kgfs/search/backends/sqlite_scan.py` |
| Tags/notes/collections disappear after reset | Workflow metadata is stored in the KGFS database. | Keep `metadata.auto_backup_before_reset: true`, or run `kgfs metadata export` / `kgfs metadata backup` before reset and restore after reindexing. | `kgfs/workflows/*.py`, `kgfs/reset.py`, `kgfs/intelligence/export.py` |
| `kgfs tag` or `kgfs note` says latest result missing | Tags and notes attach through latest search result IDs. | Run `kgfs search`, `kgfs deep`, `kgfs run-search`, or another command that saves latest results first. | `kgfs/db/latest_results.py`, `kgfs/workflows/tags.py`, `kgfs/workflows/notes.py` |
| `kgfs duplicates --semantic` finds nothing | Semantic duplicate detection uses existing local vector chunks. | Run `kgfs vector status` and `kgfs vector rebuild`, or use exact duplicate mode. | `kgfs/intelligence/duplicates.py` |
| `kgfs metadata import` reports unmatched files | Backup metadata is matched to the current index by hash/path/name/size. | Re-index the same folders first, then rerun import with `--yes`. | `kgfs/intelligence/export.py` |
| `kgfs graph export` is not a command | The export command is top-level `graph-export` so path flags can appear after the query reliably. | Run `kgfs graph-export "topic" --format markdown`. | `kgfs/cli/commands/graph.py` |
| AI Assist says disabled | `ai.enabled` is false. | Set `ai.enabled: true` after confirming privacy settings. | `kgfs/cli/shared.py`, `kgfs/ai.py` |
| AI Assist says missing API key | Env var named by `ai.api_key_env` is unset. | Set `OPENAI_API_KEY` or the configured env var. Do not put API keys in config. | `kgfs/ai.py`, `tests/test_ai.py` |
| AI Assist says OpenAI SDK missing | Optional `openai` extra is not installed. | `python -m pip install -e ".[openai]"`. | `kgfs/ai.py`, `pyproject.toml` |
| `open` or `reveal` cannot find result ID | Latest results were not saved or a new search replaced them. | Run `kgfs search` again; ensure `search.save_latest_results: true`. | `kgfs/db/latest_results.py`, `kgfs/cli/commands/open_reveal.py` |
| `kgfs why` cannot find result ID | Latest results were not saved or a new search replaced them. | Run `kgfs search` again, then use the displayed result ID. | `kgfs/db/latest_results.py`, `kgfs/cli/commands/why.py` |
| Search mode is unknown | `--mode` or `SearchOptions.mode` is not one of `keyword`, `semantic`, `hybrid`, or `auto`. | Use a supported mode. | `kgfs/search/options.py`, `kgfs/search/registry.py` |
| Search limit error | `SearchOptions.limit` is below 1. | Use `--limit 1` or higher. | `kgfs/search/options.py` |
| Date filter fails | `--after` or `--before` is not parseable by `datetime.fromisoformat`. | Use ISO dates such as `2026-04-25`. | `kgfs/search/filters.py` |
| Web dashboard mode returns an error | The requested semantic/hybrid mode is unavailable, usually because semantic config/dependencies/chunks or the configured vector backend are not ready. | Use `--mode keyword`, run `kgfs vector status`, or rebuild semantic vectors. | `kgfs/web/app.py`, `kgfs/search/registry.py`, `kgfs/vectors/status.py` |
| Web dashboard accessible beyond localhost | `kgfs web --host` was changed from default. | Bind to `127.0.0.1` unless you intentionally expose it. No auth is implemented. | `kgfs/cli/commands/web.py`, `kgfs/web/app.py` |
| `kgfs serve` says API token is missing | `api.require_token` is true and the env var named by `api.token_env` is unset. | Set `KGFS_API_TOKEN` or pass `--no-token` only for localhost development. | `kgfs/cli/commands/serve.py`, `kgfs/api/auth.py` |
| `kgfs serve` refuses a host | The host is not localhost and `--allow-network` was not supplied. | Use `127.0.0.1`, or pass `--allow-network --no-local-only` only if you intend network exposure. | `kgfs/api/auth.py`, `kgfs/cli/commands/serve.py` |
| API returns 401 | Missing or wrong `Authorization: Bearer <token>` header. | Send the configured token header or disable token auth only for local development. | `kgfs/api/auth.py` |
| API returns 403 for open/reveal | `api.allow_file_actions` is false. | Set `api.allow_file_actions: true` only when you want API-triggered latest-result file actions. | `kgfs/api/routes.py` |
| `kgfs tui` says Textual is missing | The optional TUI dependency is not installed. | Run `python -m pip install -e ".[tui]"`, or continue using CLI/web. | `kgfs/tui/app.py`, `pyproject.toml` |
| Integration scaffold command wrote files but did not install anything | Scaffolds are manual-install templates by design. | Inspect the README/scripts in the output directory and install manually if desired. | `kgfs/integrations/*.py` |
| Packaged app cannot find templates/static files | Package was built without web asset data or from stale output. | Rebuild cleanly with `python scripts/build_package.py --clean`; smoke test. | `packaging/pyinstaller/kgfs.spec`, `scripts/build_package.py` |
| Packaged semantic search missing | Base package excludes semantic dependencies/model caches. | Use Python install with `.[semantic]` or build a future semantic-specific package. | `packaging/pyinstaller/kgfs.spec`, `packaging/README-packaging.md` |
| Build script refuses to remove a path | `scripts/build_package.py --clean` only removes build/dist paths inside the project root. | Use paths under the project or remove external paths manually if you really intend to. | `scripts/build_package.py` |
| Packaged smoke test cannot find executable | `--package` points somewhere without `kgfs` or `kgfs.exe`. | Point `--package` at the packaged executable or onedir folder. | `scripts/smoke_test_packaged.py` |
| Packaged smoke test search fails | The smoke test did not find `qfv.md` in search output. | Rebuild package and inspect smoke output for earlier command failure. | `scripts/smoke_test_packaged.py` |
| Database schema version is newer than code | Database was created by a future KGFS version. | Use matching/newer KGFS code or a separate database. | `kgfs/db/migrations.py` |

## Debug Commands

Show effective paths and dependency status:

```bash
kgfs doctor
```

Show index contents summary:

```bash
kgfs stats
```

Show active config:

```bash
kgfs config
```

List configured folders and warnings:

```bash
kgfs list-folders
```

Dry-run index:

```bash
kgfs index --dry-run
```

Find stale records:

```bash
kgfs prune --dry-run
```

Check semantic state:

```bash
kgfs semantic-index
kgfs vector status
kgfs vector benchmark
kgfs vector recommend
```

Check OCR state and one-image behavior:

```bash
kgfs ocr status
kgfs ocr test ./screenshot.png
```

Check local API/TUI/integration surfaces:

```bash
kgfs serve --dry-run
kgfs tui --check
kgfs integrations status
kgfs tray status
```

Preview AI context without API calls:

```bash
kgfs ask "question" --preview-ai-context
kgfs search "query" --ai-rerank --preview-ai-context
```

## Inspect SQLite Manually

Use a temporary script so paths and quoting are explicit.

PowerShell:

```powershell
@'
from pathlib import Path
from kgfs.database import connect_database

conn = connect_database(Path("kgfs.sqlite3"))
for row in conn.execute("SELECT id, path, extraction_status, extraction_error FROM files LIMIT 20"):
    print(row["id"], row["path"], row["extraction_status"], row["extraction_error"])
'@ | python -
```

Useful queries:

```sql
SELECT COUNT(*) FROM files;
SELECT extension, COUNT(*) FROM files GROUP BY extension ORDER BY COUNT(*) DESC;
SELECT file_name, extraction_error FROM files WHERE extraction_status = 'error';
SELECT COUNT(*) FROM chunks;
SELECT COUNT(*) FROM ocr_cache;
SELECT file_name, extraction_source, extraction_error FROM files WHERE extraction_source LIKE 'ocr%';
SELECT * FROM schema_version;
```

Schema source: `kgfs/db/schema.py`.

## Logs

`kgfs doctor` reports a log path, but file logging is not implemented at this commit. Runtime diagnostics are primarily CLI output, web responses, tests, and SQLite state.

Sources: `kgfs/core/app_dirs.py`, `kgfs/cli/commands/doctor.py`.

## Configuration Mistakes to Check

- `indexed_folders` accidentally points at a root or home directory.
- `indexed_folders` points to a folder that does not exist.
- `include_extensions` omits a needed suffix.
- `ignored_extensions` includes a needed suffix.
- `ignored_folders` matches a folder name used in your corpus.
- `exclude_globs` matches more paths than intended.
- `max_file_size_mb` is too low.
- `follow_symlinks` is false when your files live behind symlinks.
- `semantic.enabled` is true but chunks have not been rebuilt.
- `ocr.enabled` is false when you expected image OCR.
- `ocr.tesseract.command` is not on PATH or not an absolute executable path.
- `ocr.include_extensions` omits a desired image suffix.
- `vectors.backend` is not a registered backend name, or an optional backend is selected without its dependency, enablement, or rebuilt artifact.
- `vectors.shard_strategy` is changed even though no behavior beyond the `none` placeholder was found.
- `search.default_mode` is invalid.
- `ai.enabled` is true but the API key env var is missing.
- `api.require_token` is true but the env var named by `api.token_env` is missing.
- `api.host` is non-local and `kgfs serve` is run without `--allow-network`.
- `api.allow_file_actions` is false when API open/reveal is expected.

## Known Limitations

- No auth is implemented for the web dashboard.
- The local JSON API has bearer-token auth by default but no external auth provider or role model.
- Web search exposes local registry modes, but not AI rerank or vector backend overrides.
- The TUI is an optional minimal launcher scaffold at this commit.
- Integration scaffolds are generated for manual installation; KGFS does not auto-install them.
- No structured logging pipeline is implemented.
- No lint/typecheck tooling is configured.
- AI query expansion has a config key (`ai.allow_query_expansion`) but no implemented command path was found.
- Backend selection is exposed for vector management commands, but `kgfs search` does not expose a `--backend` flag at this commit.
- Base packaged builds exclude semantic dependencies, optional vector backend dependencies, optional TUI/tray dependencies, OCR helper dependencies, and OpenAI SDK.
- OCR PDF rasterization is scaffolded; scanned/image-only PDFs are detected and reported, while image OCR is implemented through Tesseract.
