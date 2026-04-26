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
- Vector clear deletes KGFS chunk/vector rows or optional backend artifacts only; source files, file rows, and keyword FTS rows remain.
- OCR reads source images/PDFs but writes OCR text only to KGFS database/cache data, never back to the source file or a sidecar beside it.
- Media indexing reads image metadata and writes media-derived rows only to the KGFS database/cache. It never writes EXIF/XMP/JSON sidecars and never modifies images, audio, or PDFs.
- Release-readiness diagnostics such as `kgfs capabilities` and `kgfs db check` are read-only. `kgfs db check` opens an existing SQLite database read-only and does not create a missing database or run migrations.

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
- Media metadata, media-derived searchable text, and optional media embeddings when media features are enabled.
- Workflow metadata such as profiles, saved searches, collections, tags, notes, assignments, and projects.
- File-intelligence metadata such as graph edges, project candidates, and metadata-backup records.

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

## Workflow Metadata Privacy

Profiles, saved searches, collections, tags, notes, assignment runs, and
projects are KGFS metadata. They are stored in the KGFS SQLite database and/or
KGFS config/app-data/project-local paths.

KGFS does not write this metadata into indexed source files and does not create
sidecar files beside source files. If you run `reset-index`, the KGFS database
is removed, so workflow metadata in that database is removed too.

Sources: `kgfs/workflows/*.py`, `kgfs/db/schema.py`, `tests/test_phase7_workflows.py`.

## File Intelligence Privacy

Duplicate detection, version detection, project inference, graph building,
health reports, and metadata backup/import all operate on local KGFS database
rows and existing local vector chunks when available.

KGFS does not delete duplicates, rename versions, move project files, write
tags/notes into source files, or create sidecar metadata beside source files.
Metadata backups contain workflow metadata and stable file identities, but not
source file contents, extracted text, OCR cache text, vector blobs, model
caches, or API keys.

Sources: `kgfs/intelligence/*.py`, `kgfs/cli/commands/metadata.py`, `tests/test_phase8_file_intelligence.py`.

## Secrets

Do not put API keys in `config.yaml`.

OpenAI API keys are read from the environment variable named by `ai.api_key_env`. Default:

```bash
OPENAI_API_KEY
```

Local JSON API bearer tokens are read from the environment variable named by
`api.token_env`. Default:

```bash
KGFS_API_TOKEN
```

Sources: `kgfs/ai.py`, `kgfs/api/auth.py`, `config.example.yaml`.

## Semantic Search Privacy

Semantic search is local at this commit:

- Embeddings are generated with local sentence-transformers.
- Vectors are stored in the local SQLite database.
- Optional accelerated vector backends may store local artifact files and metadata JSON under KGFS vector-backend storage.
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

## Media and Advanced OCR Privacy

Media features are disabled by default.

Default media behavior:

- `media.enabled: false`
- `media.photos.enabled: false`
- `media.photos.store_location_metadata: false`
- caption, audio, and visual backends are `none`
- EasyOCR and PaddleOCR are disabled and lazy
- cloud OCR fallback is disabled and scaffolded to refuse upload

When photo metadata indexing is enabled, KGFS stores safe EXIF/image metadata in
SQLite tables. GPS/location fields are omitted by default, and exact location
storage requires explicit config. Generated media text is labeled, for example
`media:exif`, so search and `kgfs why` can show that a result came from
media-derived metadata.

The cloud OCR fallback scaffold does not upload files in this phase. A future
provider path must pass config enablement, explicit allow-cloud intent, preview,
and confirmation before any upload can be considered.

Sources: `kgfs/media/*.py`, `kgfs/ocr/easyocr.py`, `kgfs/ocr/paddle.py`, `kgfs/ocr/cloud.py`, `tests/test_phase10_media.py`.

## Web Dashboard Exposure

The web dashboard has no authentication at this commit, so it should stay bound to localhost unless you intentionally accept local-network exposure.

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

## Local JSON API Exposure

The JSON API is separate from the HTML dashboard and is started explicitly with:

```bash
kgfs serve
```

Default API behavior:

- Binds to `127.0.0.1:8766`.
- Requires `Authorization: Bearer <token>` by default.
- Reads the token from the environment variable named by `api.token_env`, default `KGFS_API_TOKEN`.
- Refuses non-localhost binds unless `--allow-network` is supplied.
- Keeps open/reveal actions disabled unless `api.allow_file_actions: true`.
- Includes FastAPI's generated `/docs`, `/redoc`, and `/openapi.json` schema endpoints, which expose route metadata but not indexed file contents.

The API does not expose arbitrary path open/reveal endpoints. File actions use latest result IDs from KGFS search results.

Sources: `kgfs/api/*.py`, `kgfs/cli/commands/serve.py`, `tests/test_phase9_ux_integrations.py`.

## TUI and Integration Scaffold Safety

`kgfs tui`, `kgfs integrations`, and `kgfs tray` are local UI/integration
surfaces. They do not install OS plugins, edit registry keys, create Finder
services, write Raycast/Alfred/PowerToys locations, configure startup items, or
require administrator rights.

`kgfs tui` imports Textual lazily and launches only a local terminal UI shell.

Use `--output` to choose where scaffold files are written. Without `--output`, scaffolds are written under KGFS app-data/project-local integration directories.

Sources: `kgfs/tui/*.py`, `kgfs/integrations/*.py`, `kgfs/cli/commands/integrations.py`, `tests/test_phase9_ux_integrations.py`.

## Open and Reveal Actions

`kgfs open`, `kgfs reveal`, web `/open/{result_id}` and `/reveal/{result_id}`, and gated API `/open/{result_id}` and `/reveal/{result_id}` invoke OS file manager behavior for paths saved in latest results.

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
- Optional media/OCR model dependencies such as Pillow, EasyOCR, PaddleOCR, Whisper, CLIP-style stacks, and their caches.
- Optional vector backend packages and artifacts.
- Textual/tray optional UI dependencies in the base package.
- OpenAI SDK in the base package.

Release builds write `SHA256SUMS.txt` beside zip artifacts so users can verify
downloaded packages before running them. The archive writer skips common
user-data, cache, log, database, and model-cache patterns if they appear in
staging by mistake.

Sources: `packaging/README-packaging.md`, `packaging/pyinstaller/kgfs.spec`, `scripts/build_package.py`.

## Not Implemented

No implementation was found for:

- Web dashboard authentication.
- External authentication provider integration beyond the local API bearer-token check.
- Role-based access control.
- Encryption at rest.
- Secure secret storage.
- Audit logs.
- File logging.
- Network sandboxing.
- Remote sync.

Treat the database and config file as local sensitive files because they can contain paths, extracted text, and snippets.
