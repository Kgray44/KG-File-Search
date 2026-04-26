# KGFS vs Windows Search, Copilot+ Search, and macOS Spotlight

KGFS is not trying to replace the search box built into Windows or macOS. Windows Search, Copilot+ improved search, Spotlight, and Finder are excellent everyday tools for broad desktop lookup: finding an app, locating a file somewhere on the machine, opening a system setting, searching common user folders, or using OS-managed results across files, apps, cloud/account locations, and system categories.

KGFS is deliberately narrower. It indexes folders the user chooses, stores its own local SQLite database, and is built around project and corpus search over notes, code, PDFs, reports, OCR text, photo metadata, and other selected knowledge files. It is meant for investigating a chosen body of files, not silently becoming another whole-device index.

Spotlight and Windows Search help you find files. KGFS helps you investigate a chosen body of files.

That difference is the product boundary. OS search should be judged by speed, convenience, broad integration, and default availability. KGFS should be judged by control, inspectability, reproducibility, source-file safety, privacy-bounded AI assistance, and whether it helps users work through a selected corpus.

## Quick Comparison

| Capability | KGFS | Windows Search | Windows Copilot+ Improved Search | macOS Spotlight/Finder |
|---|---|---|---|---|
| Primary purpose | Private selected-folder search and knowledge workflows. | OS-wide apps, files, settings, web, help, and account/work results. | OS-integrated semantic improvement to Windows Search on supported Copilot+ PCs. | OS-wide app, file, action, suggestion, metadata, and Finder file search. |
| Default scope | Empty corpus until folders are added. | Common user locations by default, with Classic and Enhanced indexing choices. | Windows Search scope plus semantic indexing where supported. | Spotlight-indexed categories; Finder can search the current folder, whole Mac, or last search scope depending on settings. |
| Whole-device search | Intentionally not the default; risky roots are refused unless explicitly overridden. | Strong fit, especially with Enhanced indexing or File Explorer `This PC` search. | Strong fit on supported devices, with semantic indexing layered onto traditional Windows indexing. | Strong fit for Mac-wide Spotlight search and Finder-scoped file search. |
| Explicit selected-folder corpus | Core model through `indexed_folders`, folder commands, and project-local `.kgfs/` mode. | Possible through indexing options or folder-scoped File Explorer search, but not a separate corpus database workflow. | Possible through Windows indexing settings, within OS-managed search semantics. | Possible through Finder search scope and Spotlight privacy/settings, but not a KGFS-style corpus config. |
| Project-local mode | Implemented with `.kgfs/` via `--project-local`. | Not a project-local search/index database workflow. | Not a project-local search/index database workflow. | Not a project-local search/index database workflow. |
| CLI-first workflow | Implemented through Typer commands such as `kgfs index`, `kgfs search`, `kgfs why`, `kgfs vector`, `kgfs media`, and `kgfs research`. | Primarily taskbar, Start, File Explorer, Settings, and OS UI. | Primarily Windows Search, File Explorer, Photos, and OS UI. | Primarily Spotlight UI, Finder UI, and OS shortcuts. |
| Web/local dashboard | Implemented as a localhost FastAPI dashboard with search mode selection, filters, status, stats, workflow pages, graph, health, and latest-result actions. | OS UI, not a KGFS-style local dashboard/API. | OS UI, not a KGFS-style local dashboard/API. | OS UI, not a KGFS-style local dashboard/API. |
| SQLite inspectable index | Implemented; SQLite stores file records, FTS rows, latest results, chunks, OCR cache, media metadata/text, workflow metadata, intelligence metadata, and schema version. | Uses Windows indexing internals, not a user-facing KGFS SQLite database. | Uses Windows semantic/indexing internals, not a user-facing KGFS SQLite database. | Uses Spotlight/Finder metadata systems, not a user-facing KGFS SQLite database. |
| Keyword search | Implemented with SQLite FTS5, filters, snippets, ranking boosts, and media-derived text when media indexing is enabled. | Implemented by Windows indexing and File Explorer/taskbar search. | Implemented as part of Windows Search. | Implemented by Spotlight/Finder search, including metadata and type filters. |
| Semantic search | Optional and local to KGFS when `semantic.enabled` is true and local dependencies, chunks, and vector backend readiness checks pass. Exposed through CLI, local API, and web search modes. | Traditional Windows Search is primarily lexical/property/content indexing. | Implemented by Windows on supported Copilot+ PCs for supported languages and file types. | Spotlight is OS-integrated search; KGFS-style local embedding search is not documented as a Spotlight/Finder feature. |
| Hybrid search | Implemented when semantic search is ready; combines keyword, semantic, filename, path, exact phrase, and recency signals through CLI/API/web search surfaces. | Not exposed as KGFS-style configurable hybrid ranking. | Microsoft describes semantic indexing alongside traditional indexing, but not KGFS-style configurable hybrid weights. | Not exposed as KGFS-style configurable hybrid ranking. |
| Explainable ranking / `kgfs why` | Implemented for latest KGFS results, including score breakdown, snippets, and notes. Future work can extend explanations to more workflows. | OS ranking is not exposed as a KGFS-style explanation command. | OS ranking is not exposed as a KGFS-style explanation command. | OS ranking is not exposed as a KGFS-style explanation command. |
| Open/reveal results | Implemented from latest KGFS result IDs through platform-specific helpers. | Native OS behavior. | Native OS behavior. | Native OS behavior. |
| AI assistance | Optional OpenAI-only AI Assist, disabled by default, downstream of local snippets, with preview, confirmation, home-path redaction, and snippet limits. | Windows may include web, cloud, account, and Microsoft 365 results depending on settings and account context. It is not KGFS-style bounded context preview. | Semantic indexing is described by Microsoft as stored locally on supported PCs; it is not KGFS-style OpenAI snippet workflow. | Spotlight can show suggestions, actions, calculations, conversions, and app results; it is not KGFS-style OpenAI snippet workflow. |
| Privacy defaults | No folders indexed and no AI calls by default. Index, OCR, media, semantic, workflow, and intelligence data stay in KGFS local/app/project data unless the user opts into AI Assist. | Designed for OS convenience; indexing can cover common or broad locations and may include PC, OneDrive, web, account, or app-integrated results depending on settings. | Microsoft says semantic indexing data is stored locally on the PC, with settings to disable locations or file types. | OS-managed local search with configurable result categories and privacy exclusions. |
| Source-file modification policy | Indexing, OCR, media metadata, prune, reset, rebuild, vector clear, workflows, and intelligence features do not delete, move, rename, overwrite, tag, or write sidecars beside source files. | Search itself finds and opens files; File Explorer can modify files when users take file actions. | Same Windows file-management boundary. | Search itself finds and opens files; Finder can modify files when users take file actions. |
| Advanced workflows / roadmap | Implemented: deep, similar, compare, timeline, research, profiles, saved searches, collections, tags, notes, assignment mode, projects, duplicates, versions, graph, health, metadata backups, OCR, media EXIF metadata, API/TUI/integration scaffolds. Planned/scaffolded: richer web/TUI editing, full scanned-PDF rasterization, captions, audio transcription, visual search, richer graph/research UX. | Best at OS convenience, launch, settings, and broad file lookup. | Best at OS-integrated natural-language search over supported indexed documents/images/photos on supported hardware. | Best at Mac-wide convenience, app launching, Finder organization, metadata criteria, quick actions, and OS shortcuts. |
| Best audience | Users who want controlled project/corpus indexing, reproducible search, inspectable local data, optional semantic/hybrid search, workflow metadata, and privacy-bounded AI assistance. | Everyday Windows users who want fast broad desktop search. | Copilot+ PC users who want natural-language Windows search without managing a separate corpus. | Mac users who want fast built-in search, app launch, previews, Finder criteria, metadata search, actions, and OS workflows. |

## What KGFS Is Good At

### Project and Corpus Search

KGFS starts from explicitly configured folders instead of assuming the whole computer is the right search space. That makes it a better fit for:

- A class folder with notes, PDFs, reports, and code.
- A research folder with papers, drafts, photos, and data notes.
- A repository or project where `.kgfs/` should stay with the working copy.
- A deliberately bounded archive that should be searched without pulling in unrelated desktop files.

Source anchors: `kgfs/core/config.py`, `kgfs/cli/commands/folders.py`, `kgfs/indexing/discovery.py`, `kgfs/core/safety.py`, `docs/settings.md`, `docs/usage.md`.

### Engineering, Student, and Research Workflows

KGFS is useful when the question is not only "where is the file?" but "where in this corpus did I work on this idea?"

Good examples:

- Finding where torque, gain, assignment requirements, experiment assumptions, or design constraints appear.
- Searching notes, code, CSV files, DOCX reports, PDFs, OCR text, and enabled media metadata together.
- Filtering by extension, file type, folder, date range, or extraction failures.
- Explaining why a result matched through `kgfs why`.

Source anchors: `kgfs/search/filters.py`, `kgfs/search/explain.py`, `kgfs/search/keyword.py`, `kgfs/cli/commands/search.py`, `kgfs/cli/commands/why.py`, `docs/features.md`.

### Local-First Experimentation

KGFS is a good place to experiment with local search and ranking because the base layers are small and inspectable:

- SQLite FTS5 keyword search.
- Optional local sentence-transformers embeddings.
- Configurable hybrid ranking weights.
- Local vector backend registry with `sqlite_scan` as the default backend.
- Optional accelerated `sqlite_vec`, `hnsw`, and `faiss` backends when installed, enabled, and rebuilt.
- Optional local Tesseract OCR.
- Optional local photo/EXIF metadata extraction.

Source anchors: `kgfs/search/keyword.py`, `kgfs/search/semantic.py`, `kgfs/search/modes/*.py`, `kgfs/search/backends/*.py`, `kgfs/vectors/*.py`, `kgfs/ocr/*.py`, `kgfs/media/*.py`, `docs/integrations.md`.

### CLI and Reproducible Workflows

KGFS works well when commands should be repeatable, scriptable, and tied to a project:

```bash
kgfs init --project-local
kgfs add-folder "./research-notes" --project-local
kgfs index --project-local
kgfs search "motor torque" --project-local --mode auto
kgfs why 1 "motor torque" --project-local
```

Source anchors: `kgfs/cli/app.py`, `kgfs/cli/commands/*.py`, `kgfs/core/app_dirs.py`, `docs/cli.md`, `docs/usage.md`.

### Inspectable SQLite Storage

KGFS stores its index and workflow data in documented SQLite tables. That makes the system easier to debug than opaque OS search indexes.

Important tables include:

- `files`
- `files_fts`
- `latest_results`
- `chunks`
- `ocr_cache`
- `media_metadata`
- `media_text`
- `media_embeddings`
- workflow tables for profiles, saved searches, collections, tags, notes, projects, and assignment runs
- intelligence tables for graph edges, project candidates, and metadata backups
- `schema_version`

Source anchors: `kgfs/db/schema.py`, `kgfs/db/repositories.py`, `kgfs/db/latest_results.py`, `docs/data-model.md`.

### Optional Semantic and Hybrid Search

Semantic search is optional and local to KGFS when enabled. Hybrid search is available when semantic/vector readiness checks pass. The CLI, local JSON API, and web dashboard use the search registry; the web dashboard exposes keyword, semantic, hybrid, and auto search modes, but it does not expose AI rerank or vector backend override controls.

Source anchors: `kgfs/search/semantic.py`, `kgfs/search/registry.py`, `kgfs/search/modes/*.py`, `kgfs/web/app.py`, `kgfs/api/routes.py`, `docs/features.md`.

### Optional AI Assist With Preview, Confirmation, and Redaction

KGFS AI Assist is not an always-on assistant. It is disabled by default, supports only OpenAI at this commit, and runs downstream of local KGFS search results. By default, it sends bounded snippets rather than full file text, omits file paths, redacts the home path, previews context, and asks for confirmation.

Source anchors: `kgfs/ai.py`, `kgfs/cli/shared.py`, `kgfs/cli/commands/search.py`, `docs/security.md`, `docs/settings.md`.

### Optional OCR and Media Metadata

KGFS can index more than normal document text, but the boundary is important:

- Implemented now: optional local Tesseract OCR for configured image files.
- Implemented now: scanned-PDF candidate detection and safe "not implemented yet" rasterization behavior.
- Implemented now: optional local photo/EXIF metadata indexing into `media_metadata` and `media_text`.
- Implemented now: media-derived text can participate in keyword search and semantic chunking when enabled.
- Scaffolded/planned: EasyOCR, PaddleOCR, image captions, audio transcription, visual embeddings/search, and cloud OCR fallback.
- Not implemented: fake captioning, fake transcription, fake visual understanding, automatic cloud uploads, or source-file media edits.

Source anchors: `kgfs/extractors/image_ocr.py`, `kgfs/extractors/pdf.py`, `kgfs/ocr/*.py`, `kgfs/media/*.py`, `kgfs/cli/commands/ocr.py`, `kgfs/cli/commands/media.py`, `tests/test_phase10_media.py`.

### Knowledge Workflow Tools

KGFS is becoming a local knowledge workbench, not an OS launcher clone. Current workflows include:

- Deep search.
- Similar result and similar-file search.
- Compare mode.
- Timeline mode.
- Research mode.
- Profiles and saved searches.
- Collections.
- Tags and notes.
- Assignment mode.
- Manual projects and project search.
- Duplicate and version finding.
- Project candidates.
- File/topic graphs.
- Health reports.
- Metadata export/import/backups.
- Token-gated local JSON API.
- Optional minimal Textual TUI launcher.
- Manual Raycast, Alfred, PowerToys, Finder, Explorer, and tray scaffold writers.

Planned or scaffolded workflow expansion includes richer web/TUI workflow editing, deeper graph/research UX, full scanned-PDF OCR rasterization, real local caption/audio/visual backends, collections/tags/notes polish, and possible OS integrations as entry points into selected KGFS corpora.

Roadmap anchors: `docs/roadmap.md`, `KGFS_Advanced_Roadmap_Canvas.md`.

## What KGFS Is Not Trying to Beat

KGFS should not try to beat OS search at:

- App launching.
- Instant whole-computer search.
- OS settings search.
- Universal shell integration.
- Photos, app, email, account, web, and system-wide personal assistant behavior.
- Default convenience for casual users who do not want to manage a corpus.

Those are natural strengths of Windows Search, Copilot+ improved search, Spotlight, and Finder. KGFS can integrate with operating systems later, but those integrations should act as entry points into KGFS corpora, not as replacements for the native search stack.

## When to Use Each Tool

Use Windows Search, Copilot+ improved search, Spotlight, or Finder when:

- "Where is this file?"
- "Open this app."
- "Find something somewhere on my whole computer."
- "Open a system setting."
- "Search photos, apps, email, cloud/account locations, or OS-managed categories."
- "I want the fastest default thing built into the machine."

Use KGFS when:

- "Search only this class, project, or research folder."
- "Find where I calculated motor torque."
- "Search my PDFs, notes, code, CSV files, reports, OCR text, and enabled photo metadata together."
- "Run project-local search in a repo."
- "Use semantic or hybrid search over a controlled corpus."
- "Preview exactly what context would be sent to AI."
- "Keep search data in an inspectable local SQLite database."
- "Build future collections, tags, notes, research, assignment, project, duplicate/version, graph, OCR, media, API, TUI, or local integration workflows."

## Product Positioning

KGFS is a private local search and knowledge workflow tool for selected folders. It is designed for users who want controlled indexing, reproducible project search, inspectable local data, optional semantic search, and privacy-aware AI assistance.

Possible taglines:

- "Spotlight finds files. KGFS investigates folders."
- "A local-first knowledge workbench for your chosen files."
- "Search less like a desktop, more like a research assistant."
- "A tiny private librarian goblin for your projects."

## Design Implications

This comparison suggests a clear product direction:

- Do not spend huge effort cloning OS launcher or global desktop search behavior.
- Double down on selected-corpus workflows.
- Double down on explainability, including `kgfs why`, score breakdowns, source labels, and future workflow explanations.
- Double down on profiles, collections, tags, notes, assignment mode, and project mode.
- Double down on deep search, similar search, compare, timeline, research, media metadata, OCR, and graph workflows.
- Keep privacy and local-first defaults central.
- Keep optional heavy dependencies optional and lazy.
- Treat OS integrations as launch points into KGFS, not replacements for Spotlight or Windows Search.
- Keep the web/API/TUI surfaces honest about current capability: the dashboard can search with registry modes, AI Assist remains CLI-only, API file actions are disabled by default, and TUI/integration features are still lightweight or scaffolded.

## Current Status vs Roadmap

| Category | Implemented now | Partially implemented / CLI-only / scaffolded | Planned | Not a KGFS goal |
|---|---|---|---|---|
| Scope and safety | Explicit-folder indexing, empty default config, risky-root refusal, source-file-safe maintenance, symlink opt-in. | Broad scans require `--allow-risky-root`. | Better corpus/profile UX. | Whole-drive indexing by default. |
| Project workflows | `--project-local` stores config/data under `.kgfs/`; profiles, saved searches, collections, tags, notes, assignment mode, and manual projects are implemented. | Workflow management is mostly CLI-driven, with web list/read pages for some metadata. | Richer web/TUI workflow editing and export polish. | Replacing OS project/file managers. |
| Keyword search | SQLite FTS5 search, snippets, filters, latest result IDs, ranking boosts, and media-derived text when enabled. | Web/API expose registry search modes. | Better everyday UX and more polished dashboard controls. | Replacing OS global instant search. |
| Semantic search | Optional local embeddings, chunk storage, vector backend readiness, semantic mode, and vector management commands. | Requires optional dependencies, enabled config, local model/cache readiness, indexed chunks, and backend availability. | More backend quality, tuning, and larger-index UX. | Cloud semantic indexing by default. |
| Hybrid search | Hybrid mode with configurable weights and score breakdowns. | Requires semantic/vector readiness. | Better ranking quality and richer controls. | Opaque ranking without explanation. |
| Explainability | `kgfs why` explains latest saved results with snippets, mode data, and score breakdown. | Explanation is CLI-only. | Broader explanations for deep/research/graph workflows. | Hiding why results ranked. |
| Vector backends | Default `sqlite_scan`, backend registry, `vector status`, `rebuild`, `clear`, `benchmark`, and `recommend`. | Optional `sqlite_vec`, `hnsw`, and `faiss` require extras, config enablement, and rebuild/artifacts. | More backend tuning and persistence polish. | Base install requiring heavy vector dependencies. |
| OCR | Optional local Tesseract image OCR, OCR cache, status/test/index commands, scanned-PDF candidate detection. | Scanned-PDF rasterization is safely scaffolded and reports that it is not implemented. EasyOCR/PaddleOCR are optional/lazy advanced backend scaffolds. | Full scanned-PDF rasterization and richer OCR backend support. | Modifying source images/PDFs or writing OCR sidecars. |
| Media | Optional local photo/EXIF metadata indexing, `media_metadata`, `media_text`, media status/exif/index/clear commands, GPS storage disabled by default. | Caption, audio, and visual commands/status objects exist as safe scaffolds with `none` backends. | Real local captioning, audio transcription, visual embeddings/search, and richer media UX. | Fake visual/audio understanding or automatic cloud uploads. |
| Web UI | Local FastAPI dashboard for home, search modes, workflow pages, graph, health, stats, config, failures, open, and reveal. | No dashboard authentication; keep bound to localhost. Workflow pages are not full editing workspaces. | Richer local dashboard UX. | Public hosted search service. |
| Local API and integrations | Token-gated localhost JSON API plus launcher scaffold exports. | API file actions are disabled by default. Scaffolds are manual-install only. TUI is minimal. | Optional launcher workflows, richer TUI, possible OS entry points. | Remote sync or public API service by default. |
| AI Assist | Optional OpenAI answer synthesis and reranking, disabled by default, bounded by local snippets, preview/confirmation/redaction defaults. | OpenAI-only. `ai.allow_query_expansion` exists but no AI query expansion path was found. AI Assist is CLI-only. | Privacy-protected advanced ask/research workflows. | Always-on cloud assistant behavior. |
| Knowledge workflows | Deep, similar, compare, timeline, research, profiles, collections, tags, notes, assignments, projects, duplicates, versions, graph, health, and metadata backup/import/export. | Most workflows are CLI-first; web/API support is partial by workflow. | Richer web/TUI workflow surfaces and graph/research visualization. | Replacing the operating system shell. |
| Deployment | PyInstaller package scripts and GitHub Actions CI/package workflow. | Packaging excludes optional heavy dependencies from base builds. | Release publishing polish. | Docker/Kubernetes/cloud deployment in the current tree. |

## Source Notes

KGFS behavior in this document is based on the repository docs and source files at this commit, especially:

- [Project README](../README.md)
- [Documentation hub](README.md)
- [Features](features.md)
- [Usage](usage.md)
- [Settings](settings.md)
- [Security](security.md)
- [Architecture](architecture.md)
- [Integrations](integrations.md)
- [Data model](data-model.md)
- [API](api.md)
- [CLI](cli.md)
- [Roadmap](roadmap.md)
- [Advanced Roadmap Canvas](../KGFS_Advanced_Roadmap_Canvas.md)

Key implementation anchors:

- Config and safety: `kgfs/core/config.py`, `kgfs/core/app_dirs.py`, `kgfs/core/safety.py`
- CLI: `kgfs/cli/app.py`, `kgfs/cli/commands/*.py`
- Indexing/extraction: `kgfs/indexing/*.py`, `kgfs/extractors/*.py`
- Search: `kgfs/search/*.py`, `kgfs/search/modes/*.py`, `kgfs/search/backends/*.py`
- Vectors: `kgfs/vectors/*.py`
- OCR/media: `kgfs/ocr/*.py`, `kgfs/media/*.py`
- Web/API/TUI/integrations: `kgfs/web/app.py`, `kgfs/api/*.py`, `kgfs/tui/*.py`, `kgfs/integrations/*.py`
- Workflow/intelligence: `kgfs/workflows/*.py`, `kgfs/intelligence/*.py`
- Tests: `tests/test_search_kernel.py`, `tests/test_web.py`, `tests/test_phase6_advanced_search.py`, `tests/test_phase7_workflows.py`, `tests/test_phase8_file_intelligence.py`, `tests/test_phase9_ux_integrations.py`, `tests/test_phase10_media.py`

External OS-search references:

- [Microsoft: Find your files and apps in Windows](https://support.microsoft.com/en-us/windows/find-your-files-and-apps-in-windows-5c7c8cfe-c289-fae4-f5f8-6b3fdba418d2)
- [Microsoft: Search indexing in Windows](https://support.microsoft.com/en-au/windows/search-indexing-in-windows-da061c83-af6b-095c-0f7a-4dfecda4d15a)
- [Microsoft: Search photos](https://support.microsoft.com/en-us/windows/search-photos-27b3e790-05d6-4d86-8b69-7a0ffbf72d84)
- [Apple: Search for anything with Spotlight on Mac](https://support.apple.com/guide/mac-help/search-with-spotlight-mchlp1008/mac)
- [Apple: Narrow your search results in Finder on Mac](https://support.apple.com/en-afri/guide/mac-help/mh15155/mac)
- [Apple: Prevent Spotlight searches in specific folders or disks on Mac](https://support.apple.com/guide/mac-help/prevent-spotlight-searches-specific-folders-mchl1bb43b84/mac)
- [Apple: Change Finder settings on Mac](https://support.apple.com/en-asia/guide/mac-help/mchlp2803/mac)
