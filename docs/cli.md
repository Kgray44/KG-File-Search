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
| `kgfs deep` | Run deterministic multi-pass local search. | `kgfs/cli/commands/deep.py` |
| `kgfs similar` | Find files similar to a latest result ID. | `kgfs/cli/commands/similar.py` |
| `kgfs similar-file` | Find files similar to an already indexed file path. | `kgfs/cli/commands/similar.py` |
| `kgfs compare` | Compare two latest result IDs. | `kgfs/cli/commands/compare.py` |
| `kgfs timeline` | Show matching files chronologically. | `kgfs/cli/commands/timeline.py` |
| `kgfs research` | Build a local citation-backed research brief. | `kgfs/cli/commands/research.py` |
| `kgfs profile` | Manage search profiles and profile-scoped search. | `kgfs/cli/commands/profiles.py` |
| `kgfs save-search` | Save a named search. | `kgfs/cli/commands/saved_searches.py` |
| `kgfs run-search` | Run a saved search. | `kgfs/cli/commands/saved_searches.py` |
| `kgfs list-searches` | List saved searches. | `kgfs/cli/commands/saved_searches.py` |
| `kgfs delete-search` | Delete a saved search. | `kgfs/cli/commands/saved_searches.py` |
| `kgfs collection` | Manage local file collections. | `kgfs/cli/commands/collections.py` |
| `kgfs tag` / `kgfs untag` / `kgfs tags` | Attach, remove, and list tags for latest result IDs. | `kgfs/cli/commands/tags.py` |
| `kgfs tagged` / `kgfs tag-list` | Show tagged files or all tag names. | `kgfs/cli/commands/tags.py` |
| `kgfs note` / `kgfs notes` / `kgfs note-delete` | Add, list, and delete local notes. | `kgfs/cli/commands/notes.py` |
| `kgfs assignment` | Build a local assignment working set. | `kgfs/cli/commands/assignment.py` |
| `kgfs project` | Manage manual local projects. | `kgfs/cli/commands/projects.py` |
| `kgfs duplicates` | Find exact or semantic duplicate files. | `kgfs/cli/commands/duplicates.py` |
| `kgfs versions` / `kgfs versions-file` | Find likely file versions. | `kgfs/cli/commands/versions.py` |
| `kgfs graph` / `kgfs graph-export` | Build or export a bounded local file/topic graph. | `kgfs/cli/commands/graph.py` |
| `kgfs health` | Show a read-only local index health report. | `kgfs/cli/commands/health.py` |
| `kgfs metadata` | Export/import/backup/restore KGFS metadata. | `kgfs/cli/commands/metadata.py` |
| `kgfs semantic` | Semantic-only search. | `kgfs/cli/commands/semantic.py` |
| `kgfs semantic-index` | Show semantic status or rebuild semantic chunks. | `kgfs/cli/commands/semantic.py` |
| `kgfs vector status` | Show semantic vector backend/chunk readiness. | `kgfs/cli/commands/vector.py` |
| `kgfs vector rebuild` | Rebuild semantic chunks from indexed extracted text. | `kgfs/cli/commands/vector.py` |
| `kgfs vector clear` | Clear KGFS vector/chunk data only. | `kgfs/cli/commands/vector.py` |
| `kgfs vector benchmark` | Benchmark available vector backends against existing local vectors. | `kgfs/cli/commands/vector.py` |
| `kgfs vector recommend` | Recommend a vector backend based on local index size and availability. | `kgfs/cli/commands/vector.py` |
| `kgfs ocr status` | Show OCR config and Tesseract availability. | `kgfs/cli/commands/ocr.py` |
| `kgfs ocr test` | OCR one image without indexing it. | `kgfs/cli/commands/ocr.py` |
| `kgfs ocr index` | Run indexing with OCR-enabled extraction. | `kgfs/cli/commands/ocr.py` |
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
- OCR status and cache/index counts
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

## Advanced Local Search

These commands are CLI-first local investigation tools. They reuse the existing KGFS index, search registry, snippets, latest-result IDs, and optional local vectors. They do not call AI or cloud services.

```bash
kgfs deep QUERY [--limit N] [--mode MODE] [--passes N]
                [--ext EXT] [--folder TEXT] [--after YYYY-MM-DD] [--before YYYY-MM-DD]
kgfs similar RESULT_ID [--limit N] [--include-self]
kgfs similar-file PATH [--limit N] [--include-self]
kgfs compare RESULT_ID_A RESULT_ID_B
kgfs timeline QUERY [--limit N] [--group day|month|year] [--mode MODE]
kgfs research QUERY [--limit N] [--mode MODE]
```

`deep` creates deterministic local query variants, runs multiple searches, fuses duplicate candidates by file ID, saves latest results, and suggests follow-up searches.

`similar` starts from the latest result table. It uses stored chunk vectors when available and falls back to local term overlap when semantic data is missing. `similar-file` only works for files already in the KGFS index; it does not silently index arbitrary paths.

`compare` shows shared terms, terms unique to each file, text similarity, and semantic similarity when local vectors exist.

`timeline` runs local search and sorts/group matches by file modified time.

`research` runs local deep search, prints best files/snippets, related terms, suggested follow-ups, and KGFS local citations like `[1] notes.md`.

Sources: `kgfs/search/deep.py`, `kgfs/search/similar.py`, `kgfs/search/compare.py`, `kgfs/search/timeline.py`, `kgfs/search/research.py`, `kgfs/search/citations.py`.

## Personal Workflows

Workflow metadata is local KGFS metadata. Tags, notes, collections, projects,
and saved searches are stored in the KGFS SQLite database; source files are not
modified and sidecars are not written beside indexed files.

```bash
kgfs profile list
kgfs profile create school --ext .pdf --ext .docx --ext .md
kgfs profile show school
kgfs profile search school "op amp gain"
kgfs profile delete school

kgfs save-search "circuits labs" "op amp OR Thevenin"
kgfs run-search "circuits labs"
kgfs list-searches
kgfs delete-search "circuits labs"

kgfs collection create "Motor Project"
kgfs collection add "Motor Project" 1 3 5
kgfs collection show "Motor Project"
kgfs collection export "Motor Project"

kgfs tag 1 circuits lab-report important
kgfs untag 1 important
kgfs tags 1
kgfs tagged circuits
kgfs tag-list

kgfs note 1 "Torque derivation is here."
kgfs notes 1
kgfs note-delete 4

kgfs assignment "robotics motor lab"

kgfs project create "Audio Crossover"
kgfs project add "Audio Crossover" 1 3 5
kgfs project show "Audio Crossover"
kgfs project search "Audio Crossover" "op amp filter"
kgfs project infer
kgfs project candidates
kgfs project accept-candidate 1 --name "Audio Crossover"
```

Collections and projects add files by latest search result ID. Notes and tags
also attach to file IDs resolved through latest search result IDs. `reset-index`
removes the KGFS database, so workflow metadata in that database is removed too.

Sources: `kgfs/workflows/*.py`, `kgfs/cli/commands/profiles.py`, `kgfs/cli/commands/saved_searches.py`, `kgfs/cli/commands/collections.py`, `kgfs/cli/commands/tags.py`, `kgfs/cli/commands/notes.py`, `kgfs/cli/commands/assignment.py`, `kgfs/cli/commands/projects.py`.

## File Intelligence

These commands analyze local KGFS database metadata. They do not delete,
rename, move, tag, annotate, or write sidecar files beside indexed source
files.

```bash
kgfs duplicates [--exact] [--semantic] [--min-score 0.92]
kgfs versions RESULT_ID
kgfs versions-file PATH
kgfs graph "speaker crossover"
kgfs graph --file 3
kgfs graph --project "Audio Crossover"
kgfs graph-export "speaker crossover" --format markdown
kgfs health [--json] [--fix-suggestions]
kgfs metadata export --output kgfs-metadata-backup.json
kgfs metadata import kgfs-metadata-backup.json --yes
kgfs metadata backup
kgfs metadata restore PATH --yes
```

`duplicates` uses content hashes for exact groups. `--semantic` uses existing
local semantic chunk vectors and reports a helpful warning when vectors are not
built. `versions` combines filename markers, same-folder evidence, size,
modified time, extracted-text overlap, and semantic similarity when available.

`graph` builds a bounded local graph from a topic, latest result ID, or project.
The export command is named `graph-export` so query arguments and path flags work
reliably across Typer/Click parsing.

`metadata export` intentionally excludes source file contents, extracted text,
OCR cache text, vector blobs, API keys, and model caches. Imports match metadata
back to currently indexed files using content hash, normalized path, and
filename/size fallback.

Sources: `kgfs/intelligence/*.py`, `kgfs/cli/commands/duplicates.py`, `kgfs/cli/commands/versions.py`, `kgfs/cli/commands/graph.py`, `kgfs/cli/commands/health.py`, `kgfs/cli/commands/metadata.py`.

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

Runs local keyword search, builds AI context from local snippets and KGFS result citations, optionally previews/confirms, then asks OpenAI.

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
kgfs vector rebuild [--config PATH] [--database PATH] [--project-local]
                    [--backend BACKEND] [--force/--no-force]
kgfs vector clear [--config PATH] [--database PATH] [--project-local]
                  [--backend BACKEND] [--all-backends] --yes
kgfs vector benchmark [--config PATH] [--database PATH] [--project-local]
                      [--backend BACKEND] [--query TEXT] [--limit N]
kgfs vector recommend [--config PATH] [--database PATH] [--project-local]
```

`vector status` reports semantic enablement, model name, configured backend, backend availability, optional dependency install hints, chunk count, files-with-chunks count, readiness, and warnings.

`vector rebuild` rebuilds semantic chunks from already indexed `files.extracted_text` for `sqlite_scan`. It requires `semantic.enabled: true` and a known backend. `--force` is the default; `--no-force` skips files that already have chunks for the configured model. Optional accelerated backends can be selected with `--backend`; they rebuild backend artifacts from existing chunks and print install/rebuild guidance when unavailable.

`vector clear` requires `--yes`. Without `--backend`, it preserves current behavior and clears KGFS chunk/vector rows for the configured semantic model. With `--backend hnsw`, `--backend faiss`, or `--backend sqlite_vec`, it clears backend artifacts only. It leaves source files, file records, and keyword FTS rows unchanged.

`vector benchmark` uses existing stored vectors when no query text is supplied, so it can benchmark `sqlite_scan` without loading sentence-transformers. Optional backends that are missing, disabled, stale, or missing artifacts appear as unavailable rows with notes.

`vector recommend` chooses a conservative backend recommendation. Small and moderate local indexes prefer `sqlite_scan`; larger indexes may recommend `hnsw` only when it is available.

Sources: `kgfs/cli/commands/vector.py`, `kgfs/vectors/index_manager.py`, `kgfs/vectors/status.py`, `kgfs/search/backends/*.py`.

## OCR Commands

```bash
kgfs ocr status [--config PATH] [--database PATH] [--project-local]
kgfs ocr test IMAGE_PATH [--config PATH] [--project-local]
kgfs ocr index [--config PATH] [--database PATH] [--project-local]
               [--dry-run] [--force] [--allow-risky-root]
```

`ocr status` reports whether OCR is enabled, the configured backend, Tesseract command/language, supported image extensions, cache settings, and install hints when Tesseract is missing.

`ocr test` runs local OCR on one image and prints a preview. It does not add the image to the index and does not create a database.

`ocr index` reuses the normal indexing pipeline with OCR-capable extraction. It requires `ocr.enabled: true`, writes OCR text to the KGFS database/cache only, and never modifies source images or PDFs.

Source: `kgfs/cli/commands/ocr.py`, `kgfs/ocr/*.py`.

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

Reports totals, extraction counts, OCR counts/cache entries, semantic counts, stale records, database size, schema version, file types, and largest indexed files.

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
