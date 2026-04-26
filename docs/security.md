# Security, Privacy, and Safety

KGFS is designed as a local-first file search tool. This page documents the security and privacy behavior implemented in the repository state at this commit.

## Local-First Defaults

KGFS does not index or transmit files by default.

Implemented safeguards:

- Generated config starts with `indexed_folders: []`.
- `kgfs init` does not index.
- `kgfs index` exits early when no folders are configured.
- Database and generated app data live in platform-specific user app directories by default.
- Project-local mode is explicit via `--project-local`.

Sources: `kgfs/core/config.py`, `kgfs/cli/commands/init.py`, `kgfs/cli/commands/index.py`, `kgfs/core/app_dirs.py`, `tests/test_config.py`, `tests/test_cli.py`.

## Indexing Boundaries

KGFS indexes only paths listed in `indexed_folders`.

Default skip behavior:

- Does not follow symlinks unless `follow_symlinks: true`.
- Skips default ignored folders such as `.git`, dependency folders, app/system folders, and game install folders.
- Skips ignored binary/media/archive/app extensions.
- Skips files larger than `max_file_size_mb`.
- Skips paths matching `exclude_globs`.

Sources: `kgfs/indexing/discovery.py`, `kgfs/indexing/filters.py`, `kgfs/core/config.py`.

## Risky Root Protection

KGFS refuses broad roots unless explicitly overridden.

Risky roots include:

- Filesystem root `/`.
- Windows drive roots such as `C:\`.
- User home directory itself.
- Obvious system roots such as `/System`, `/Applications`, `C:\Windows`, and `C:\Program Files`.

Override:

```bash
kgfs index --allow-risky-root
```

Use the override only for intentional broad scans.

Sources: `kgfs/core/safety.py`, `kgfs/cli/commands/index.py`, `tests/test_safety.py`.

## Source File Safety

Indexing, pruning, resetting, and rebuilding do not delete, move, rename, or overwrite source files.

Operations:

- Indexing reads files and writes KGFS database rows.
- Pruning deletes stale KGFS database rows and related FTS/chunk/latest-result rows.
- Reset deletes KGFS database files and SQLite sidecars.
- Rebuild resets the database and reindexes configured folders.
- Vector clear deletes KGFS chunk/vector rows only for the configured model.
- OCR reads source images/PDFs but writes OCR text only to KGFS database/cache data, never back to the source file or a sidecar beside it.

Sources: `kgfs/indexing/indexer.py`, `kgfs/indexing/prune.py`, `kgfs/reset.py`, `tests/test_prune.py`, `tests/test_reset_rebuild.py`.

## Local Database Contents

The SQLite database can contain:

- File paths.
- File names and extensions.
- File sizes and modified times.
- Extracted text.
- Content hashes.
- Extraction errors.
- Latest result IDs.
- Semantic chunks and embeddings when enabled.
- OCR cache rows and OCR-derived text when OCR is enabled.

If `indexing.store_extracted_text` is false, stored extracted text is empty, which also limits keyword and semantic usefulness.

Sources: `kgfs/db/schema.py`, `kgfs/indexing/indexer.py`, [Data Model](data-model.md).

## AI Assist Privacy

AI Assist is disabled by default and must be explicitly enabled.

Default AI privacy settings:

- `ai.enabled: false`
- `ai.require_confirmation: true`
- `ai.preview_context_before_send: true`
- `ai.send_file_paths: false`
- `ai.redact_home_path: true`
- `ai.send_full_file_text: false`

When enabled, AI Assist:

1. Runs local search first.
2. Builds a bounded context from result snippets and KGFS local citations by default.
3. Omits file paths unless configured otherwise.
4. Redacts home path variants.
5. Limits results and characters.
6. Prompts before sending unless confirmation is disabled.

Preview without sending:

```bash
kgfs ask "question" --preview-ai-context
kgfs search "query" --ai-rerank --preview-ai-context
```

Sources: `kgfs/ai.py`, `kgfs/cli/shared.py`, `tests/test_ai.py`.

## Advanced Search Privacy

`kgfs deep`, `kgfs similar`, `kgfs similar-file`, `kgfs compare`,
`kgfs timeline`, and `kgfs research` operate on local KGFS database rows,
snippets, latest-result IDs, and optional local vectors. They do not call cloud
services and do not write annotations or sidecar files beside source files.

`similar-file` requires the target path to already be indexed. It does not
silently index arbitrary files.

Sources: `kgfs/search/deep.py`, `kgfs/search/similar.py`, `kgfs/search/compare.py`, `kgfs/search/timeline.py`, `kgfs/search/research.py`, `tests/test_phase6_advanced_search.py`.

## Secrets

Do not put API keys in `config.yaml`.

OpenAI API keys are read from the environment variable named by `ai.api_key_env`. Default:

```bash
OPENAI_API_KEY
```

Sources: `kgfs/ai.py`, `config.example.yaml`.

## Semantic Search Privacy

Semantic search is local at this commit:

- Embeddings are generated with local sentence-transformers.
- Vectors are stored in the local SQLite database.
- `semantic.local_files_only` defaults to true.

No cloud call is made by KGFS semantic search code. The local model must exist in cache or be available as a local path when local-only loading is enabled.

Sources: `kgfs/search/semantic.py`, `tests/test_semantic.py`.

## OCR Privacy

OCR is disabled by default and local-only in this phase.

Default OCR behavior:

- `ocr.enabled: false`
- Backend: local `tesseract` executable.
- No cloud OCR calls.
- No EasyOCR, PaddleOCR, image captioning, or multimodal embeddings.
- Source images and PDFs are never modified.
- OCR sidecar files are not created next to source files.
- OCR cache rows are stored in the KGFS SQLite database/app data/project-local paths.

Tesseract must be installed separately. Missing Tesseract produces status or extraction errors instead of stack traces.

Sources: `kgfs/ocr/*.py`, `kgfs/extractors/image_ocr.py`, `tests/test_ocr_*.py`.

## Web Dashboard Exposure

The web dashboard has no authentication at this commit.

Default bind:

```text
127.0.0.1:8765
```

Avoid binding to `0.0.0.0` or a LAN/public interface unless you intentionally expose:

- Search queries.
- File paths in rendered pages.
- Config values.
- Extraction failure messages.
- Open/reveal actions for latest result IDs.

Sources: `kgfs/cli/commands/web.py`, `kgfs/web/app.py`.

## Open and Reveal Actions

`kgfs open`, `kgfs reveal`, and web `/open/{result_id}` and `/reveal/{result_id}` invoke OS file manager behavior for paths saved in latest results.

Boundaries:

- They use latest search result IDs, not arbitrary path input.
- They rely on paths already stored in the local KGFS database.
- Missing files reveal/open parent folder when platform helper falls back.

Sources: `kgfs/cli/commands/open_reveal.py`, `kgfs/core/platform_utils.py`, `kgfs/web/app.py`.

## Packaging Safety

Packaged builds do not include:

- User config files.
- User SQLite databases.
- User caches or logs.
- Indexed personal files.
- `.kgfs/`.
- Downloaded semantic model caches.
- Tesseract itself and OCR cache/user data.
- OpenAI SDK in the base package.

Sources: `packaging/README-packaging.md`, `packaging/pyinstaller/kgfs.spec`, `scripts/build_package.py`.

## Not Implemented

No implementation was found for:

- User authentication.
- Role-based access control.
- Encryption at rest.
- Secure secret storage.
- Audit logs.
- File logging.
- Network sandboxing.
- Remote sync.

Treat the database and config file as local sensitive files because they can contain paths, extracted text, and snippets.
