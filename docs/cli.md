# CLI Reference

The CLI is built with Typer and exposed through the `kgfs` console script in `pyproject.toml` and through `python -m kgfs` in `kgfs/__main__.py`.

Command registration source: `kgfs/cli/app.py`.

## Commands

| Command | Purpose | Source |
|---|---|---|
| `kgfs init` | Create config and app directories without indexing. | `kgfs/cli/commands/init.py` |
| `kgfs doctor` | Print environment/config/database diagnostics. | `kgfs/cli/commands/doctor.py` |
| `kgfs config` | Print active config path and file contents. | `kgfs/cli/commands/config.py` |
| `kgfs add-folder` | Add a path to `indexed_folders`. | `kgfs/cli/commands/folders.py` |
| `kgfs remove-folder` | Remove a path from `indexed_folders`. | `kgfs/cli/commands/folders.py` |
| `kgfs list-folders` | Show configured folders, existence, and safety warning. | `kgfs/cli/commands/folders.py` |
| `kgfs index` | Index configured folders. | `kgfs/cli/commands/index.py` |
| `kgfs search` | Search indexed files, optionally AI-rerank. | `kgfs/cli/commands/search.py` |
| `kgfs ask` | Ask OpenAI using local search snippets. | `kgfs/cli/commands/search.py` |
| `kgfs semantic` | Semantic-only search. | `kgfs/cli/commands/semantic.py` |
| `kgfs semantic-index` | Show semantic status or rebuild semantic chunks. | `kgfs/cli/commands/semantic.py` |
| `kgfs vector status` | Show semantic vector backend/chunk readiness. | `kgfs/cli/commands/vector.py` |
| `kgfs vector rebuild` | Rebuild semantic chunks from indexed extracted text. | `kgfs/cli/commands/vector.py` |
| `kgfs vector clear` | Clear KGFS vector/chunk data only. | `kgfs/cli/commands/vector.py` |
| `kgfs why` | Explain why a latest search result matched a query. | `kgfs/cli/commands/why.py` |
| `kgfs open` | Open a file from latest search results. | `kgfs/cli/commands/open_reveal.py` |
| `kgfs reveal` | Reveal a file from latest search results. | `kgfs/cli/commands/open_reveal.py` |
| `kgfs stats` | Show index/database stats. | `kgfs/cli/commands/stats.py` |
| `kgfs prune` | Remove stale database records. | `kgfs/cli/commands/maintenance.py` |
| `kgfs reset-index` | Remove KGFS database/index files only. | `kgfs/cli/commands/maintenance.py` |
| `kgfs rebuild` | Reset database then index configured folders. | `kgfs/cli/commands/maintenance.py` |
| `kgfs web` | Start local FastAPI dashboard. | `kgfs/cli/commands/web.py` |

Tests: `tests/test_cli.py`.

## Common Path Flags

Most commands expose:

| Flag | Meaning |
|---|---|
| `--config PATH` | Override config path. |
| `--database PATH` | Override database path. |
| `--project-local` | Use `.kgfs/` under current working directory. |

`--database` is not present on commands that only read/edit config: `init`, `config`, `add-folder`, `remove-folder`, `list-folders`.

## `init`

```bash
kgfs init [--config PATH] [--project-local]
```

Creates config/data/cache/log directories and a default config file if missing. It does not overwrite an existing config.

Outputs:

- Config path
- Data path
- Cache path
- Created/already-exists message

Source: `kgfs/cli/commands/init.py`.

## `doctor`

```bash
kgfs doctor [--config PATH] [--database PATH] [--project-local]
```

Reports:

- Platform and Python version
- Packaged/frozen state and executable path
- Config/data/cache/log/database paths
- Database existence and schema version
- Path separator and home directory
- Open/reveal strategy
- SQLite FTS5 availability
- Semantic status
- PDF/DOCX/OpenAI dependency availability
- Configured folder existence/readability/warnings

Source: `kgfs/cli/commands/doctor.py`.

## `config`

```bash
kgfs config [--config PATH] [--project-local]
```

Prints the active config file. It does not create a missing config.

Source: `kgfs/cli/commands/config.py`.

## Folder Commands

```bash
kgfs add-folder PATH [--config PATH] [--project-local]
kgfs remove-folder PATH [--config PATH] [--project-local]
kgfs list-folders [--config PATH] [--project-local]
```

Notes:

- These commands edit or read `indexed_folders`.
- They do not index immediately.
- Add/list output includes warnings for risky roots.
- Add output warns when the target folder does not exist.
- Adding/removing rewrites the YAML through `yaml.safe_dump`.

Sources: `kgfs/cli/commands/folders.py`, `kgfs/core/config_commands.py`.

## `index`

```bash
kgfs index [--config PATH] [--database PATH] [--project-local]
           [--dry-run] [--rebuild-embeddings] [--force]
           [--verify-hashes] [--prune] [--allow-risky-root]
```

Options:

| Flag | Behavior |
|---|---|
| `--dry-run` | Discover files without writing to the database. |
| `--rebuild-embeddings` | Rebuild semantic chunks and embeddings. |
| `--force` | Re-extract and re-index files even if metadata is unchanged. |
| `--verify-hashes` | Hash-check files even when size and mtime look unchanged. |
| `--prune` | Remove stale KGFS database records after indexing. |
| `--allow-risky-root` | Allow roots such as `/`, `C:\`, or home folder. |

If `indexed_folders` is empty, the command prints setup guidance and exits without creating a database.

Sources: `kgfs/cli/commands/index.py`, `kgfs/indexing/indexer.py`.

## `search`

```bash
kgfs search QUERY [--config PATH] [--database PATH] [--project-local]
                  [--limit N] [--ext EXT] [--type TYPE] [--folder TEXT]
                  [--after YYYY-MM-DD] [--before YYYY-MM-DD]
                  [--failed-only] [--mode MODE] [--hybrid]
                  [--ai-rerank] [--preview-ai-context]
```

Options:

| Flag | Behavior |
|---|---|
| `--limit`, `-n` | Maximum results. Defaults to `search.default_limit`. |
| `--ext` | Filter by extension. Can be repeated by Typer list semantics. |
| `--type` | Filter by file type/extension, with or without dot. |
| `--folder` | Case-insensitive path substring filter. |
| `--after` | Only files modified on/after ISO date. |
| `--before` | Only files modified on/before ISO date; KGFS treats this as the end of that day. |
| `--failed-only` | Return extraction-failure records only. |
| `--mode` | `keyword`, `semantic`, `hybrid`, or `auto`. |
| `--hybrid` | Forces hybrid mode. Takes precedence over `--mode`. |
| `--ai-rerank` | Uses OpenAI AI Assist to rerank local results when enabled. |
| `--preview-ai-context` | Prints AI context and makes no API call. |

The CLI saves latest result IDs when `search.save_latest_results` is true.

Sources: `kgfs/cli/commands/search.py`, `kgfs/search/filters.py`, `kgfs/search/registry.py`.

## `why`

```bash
kgfs why RESULT_ID QUERY [--config PATH] [--database PATH] [--project-local]
                         [--mode MODE]
```

Explains a result from the latest saved search without opening or revealing the
file. KGFS reruns the requested/configured local search mode, matches the saved
result by file ID/path, and prints the file name, path, mode used, final score,
score breakdown, matched snippet/chunk, and a short explanation summary.

If the saved result cannot be reproduced exactly, KGFS shows the saved indexed
file with the best available local context. `why` does not call AI.

Source: `kgfs/cli/commands/why.py`, `kgfs/search/explain.py`.

## `ask`

```bash
kgfs ask QUESTION [--config PATH] [--database PATH] [--project-local]
                  [--limit N] [--ext EXT] [--folder TEXT]
                  [--after YYYY-MM-DD] [--before YYYY-MM-DD]
                  [--preview-ai-context]
```

Runs local keyword search, builds AI context from local snippets, optionally previews/confirms, then asks OpenAI.

Requirements:

- `ai.enabled: true`
- `ai.allow_answer_synthesis: true`
- OpenAI SDK installed
- Env var named by `ai.api_key_env` set

Source: `kgfs/cli/commands/search.py`, `kgfs/ai.py`.

## Semantic Commands

```bash
kgfs semantic QUERY [--config PATH] [--database PATH] [--project-local] [--limit N]
kgfs semantic-index [--config PATH] [--database PATH] [--project-local]
                    [--rebuild] [--allow-risky-root]
```

`semantic` requires `semantic.enabled: true`.

`semantic-index` always reports:

- Semantic dependency/status message
- Model name
- Chunk count
- Embedding storage size

With `--rebuild`, it rebuilds semantic chunks and embeddings.

Source: `kgfs/cli/commands/semantic.py`.

## Vector Commands

```bash
kgfs vector status [--config PATH] [--database PATH] [--project-local]
kgfs vector rebuild [--config PATH] [--database PATH] [--project-local] [--force/--no-force]
kgfs vector clear [--config PATH] [--database PATH] [--project-local] --yes
```

`vector status` reports semantic enablement, model name, configured backend, backend availability, semantic dependency availability, chunk count, files-with-chunks count, readiness, and warnings.

`vector rebuild` rebuilds semantic chunks from already indexed `files.extracted_text`. It requires `semantic.enabled: true` and a known `vectors.backend`. `--force` is the default; `--no-force` skips files that already have chunks for the configured model.

`vector clear` requires `--yes`, clears KGFS chunk/vector rows for the configured semantic model, and leaves source files, file records, and keyword FTS rows unchanged.

Sources: `kgfs/cli/commands/vector.py`, `kgfs/vectors/index_manager.py`, `kgfs/vectors/status.py`, `kgfs/search/backends/*.py`.

## Open and Reveal

```bash
kgfs open RESULT_ID [--config PATH] [--database PATH] [--project-local]
kgfs reveal RESULT_ID [--config PATH] [--database PATH] [--project-local]
```

These commands look up `RESULT_ID` in `latest_results`.

Platform behavior:

- Windows open: `os.startfile`
- Windows reveal: Explorer `/select` with folder fallback
- macOS open: `open`
- macOS reveal: `open -R` with folder fallback
- Other platforms: `xdg-open`

Sources: `kgfs/cli/commands/open_reveal.py`, `kgfs/core/platform_utils.py`.

## `stats`

```bash
kgfs stats [--config PATH] [--database PATH] [--project-local]
```

Reports totals, extraction counts, semantic counts, stale records, database size, schema version, file types, and largest indexed files.

Sources: `kgfs/cli/commands/stats.py`, `kgfs/db/stats.py`.

## Maintenance Commands

```bash
kgfs prune [--config PATH] [--database PATH] [--project-local] [--dry-run]
kgfs reset-index [--config PATH] [--database PATH] [--project-local] [--dry-run] [--yes]
kgfs rebuild [--config PATH] [--database PATH] [--project-local] [--yes] [--allow-risky-root]
```

Notes:

- `prune` removes stale DB/FTS/chunk/latest-result rows only.
- `reset-index` removes database files and SQLite sidecars only.
- `rebuild` resets index data and indexes configured folders again.
- Source files are not deleted by these commands.

Sources: `kgfs/cli/commands/maintenance.py`, `kgfs/indexing/prune.py`, `kgfs/reset.py`.

## `web`

```bash
kgfs web [--config PATH] [--database PATH] [--project-local]
         [--host HOST] [--port PORT]
```

Defaults:

- Host: `127.0.0.1`
- Port: `8765`

Starts Uvicorn with the FastAPI app from `kgfs/web/app.py`.

Source: `kgfs/cli/commands/web.py`.

## Script CLIs

Packaging script:

```bash
python scripts/build_package.py [--clean] [--mode onedir|onefile]
                                [--name NAME] [--dist-dir PATH]
                                [--work-dir PATH] [--spec PATH]
```

Packaged smoke test:

```bash
python scripts/smoke_test_packaged.py [--package PATH]
```

Sources: `scripts/build_package.py`, `scripts/smoke_test_packaged.py`.
