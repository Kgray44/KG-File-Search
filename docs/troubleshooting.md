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
| PDF support is missing | `pypdf` not installed. | Install base package dependencies with `python -m pip install -e ".[dev]"` or install `pypdf`. | `pyproject.toml`, `kgfs/extractors/pdf.py` |
| DOCX support is missing | `python-docx` not installed. | Install base package dependencies with `python -m pip install -e ".[dev]"` or install `python-docx`. | `pyproject.toml`, `kgfs/extractors/docx.py` |
| `kgfs search --mode semantic` reports unavailable | `semantic.enabled` false, dependency missing, model unavailable, or no chunks indexed for model. | Enable semantic config, install `.[semantic]`, ensure local model availability, run `kgfs semantic-index --rebuild`. | `kgfs/search/modes/semantic.py`, `kgfs/cli/commands/semantic.py` |
| Auto mode warns and uses keyword search | Semantic is enabled but hybrid is unavailable. | Run `kgfs semantic-index --rebuild` and check `kgfs doctor`. | `kgfs/search/registry.py`, `kgfs/search/modes/auto.py` |
| AI Assist says disabled | `ai.enabled` is false. | Set `ai.enabled: true` after confirming privacy settings. | `kgfs/cli/shared.py`, `kgfs/ai.py` |
| AI Assist says missing API key | Env var named by `ai.api_key_env` is unset. | Set `OPENAI_API_KEY` or the configured env var. Do not put API keys in config. | `kgfs/ai.py`, `tests/test_ai.py` |
| AI Assist says OpenAI SDK missing | Optional `openai` extra is not installed. | `python -m pip install -e ".[openai]"`. | `kgfs/ai.py`, `pyproject.toml` |
| `open` or `reveal` cannot find result ID | Latest results were not saved or a new search replaced them. | Run `kgfs search` again; ensure `search.save_latest_results: true`. | `kgfs/db/latest_results.py`, `kgfs/cli/commands/open_reveal.py` |
| Search mode is unknown | `--mode` or `SearchOptions.mode` is not one of `keyword`, `semantic`, `hybrid`, or `auto`. | Use a supported mode. | `kgfs/search/options.py`, `kgfs/search/registry.py` |
| Search limit error | `SearchOptions.limit` is below 1. | Use `--limit 1` or higher. | `kgfs/search/options.py` |
| Date filter fails | `--after` or `--before` is not parseable by `datetime.fromisoformat`. | Use ISO dates such as `2026-04-25`. | `kgfs/search/filters.py` |
| Web dashboard search does not use semantic/hybrid | Current web route calls keyword `search()` directly. | Use CLI for semantic/hybrid search. | `kgfs/web/app.py`, `kgfs/search/keyword.py` |
| Web dashboard accessible beyond localhost | `kgfs web --host` was changed from default. | Bind to `127.0.0.1` unless you intentionally expose it. No auth is implemented. | `kgfs/cli/commands/web.py`, `kgfs/web/app.py` |
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
SELECT * FROM schema_version;
```

Schema source: `kgfs/db/schema.py`.

## Logs

`kgfs doctor` reports a log path, but the current worktree does not implement file logging. Runtime diagnostics are primarily CLI output, web responses, tests, and SQLite state.

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
- `search.default_mode` is invalid.
- `ai.enabled` is true but the API key env var is missing.

## Known Limitations

- No auth is implemented for the web dashboard.
- Web search is keyword-only in the current worktree.
- No structured logging pipeline is implemented.
- No lint/typecheck tooling is configured.
- AI query expansion has a config key (`ai.allow_query_expansion`) but no implemented command path was found.
- Search explanations and backend selection have runtime fields but are not exposed in CLI/web.
- Base packaged builds exclude semantic dependencies and OpenAI SDK.
