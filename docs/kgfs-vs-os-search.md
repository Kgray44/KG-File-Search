# KGFS vs Windows Search, Copilot+ Search, and macOS Spotlight

KGFS is not an attempt to replace the built-in search box on Windows or macOS. Windows Search, Windows Copilot+ improved search, Spotlight, and Finder search are excellent for broad everyday desktop search: finding an app, locating a file somewhere on the machine, opening a system setting, or searching across OS-integrated locations.

KGFS serves a narrower and more deliberate purpose. It indexes folders the user chooses, stores its own local SQLite index, and supports project or corpus search over notes, code, PDFs, reports, and other text-oriented files. It is designed for people who want to investigate a known body of files rather than search the whole device by default.

Spotlight and Windows Search help you find files. KGFS helps you investigate a chosen body of files.

That difference matters. KGFS should be judged by whether it is controlled, inspectable, reproducible, private by default, and useful for knowledge workflows. OS search should be judged by whether it is fast, integrated, automatic, and convenient across the whole desktop.

## Quick Comparison

| Capability | KGFS | Windows Search | Windows Copilot+ Improved Search | macOS Spotlight/Finder |
|---|---|---|---|---|
| Primary purpose | Private selected-folder search and knowledge workflows. | OS-wide app, file, settings, web, and account search. | OS-integrated semantic improvement to Windows Search on supported Copilot+ PCs. | OS-wide app, file, action, suggestion, and Finder file search. |
| Default scope | Empty corpus until folders are added. | Common user locations by default, with Classic/Enhanced indexing choices. | Windows Search scope plus semantic indexing where supported. | Spotlight-indexed categories and Finder locations. |
| Whole-device search | Intentionally not the default; risky roots are refused unless overridden. | Strong fit, especially with Enhanced indexing or File Explorer `This PC` search. | Strong fit on supported devices, with semantic indexing layered onto Windows Search. | Strong fit for Mac-wide search and Finder-scoped folder search. |
| Explicit selected-folder corpus | Core model through `indexed_folders` and folder commands. | Possible through indexing options or folder-scoped File Explorer search, but not KGFS-style corpus management. | Possible through Windows indexing settings, within OS semantics. | Possible through Finder location search and Spotlight privacy/settings, but not KGFS-style corpus config. |
| Project-local mode | Implemented with `.kgfs/` via `--project-local`. | Not a project-local search/index database workflow. | Not a project-local search/index database workflow. | Not a project-local search/index database workflow. |
| CLI-first workflow | Implemented through Typer commands such as `kgfs index`, `kgfs search`, `kgfs why`, and `kgfs vector`. | Primarily GUI/taskbar/File Explorer. | Primarily GUI/taskbar/File Explorer. | Primarily Spotlight UI and Finder UI. |
| Web/local dashboard | Implemented as a local FastAPI dashboard; current web search is keyword-only. | OS UI, not a KGFS-style local dashboard. | OS UI, not a KGFS-style local dashboard. | OS UI, not a KGFS-style local dashboard. |
| SQLite inspectable index | Implemented; file records, FTS rows, latest results, chunks, and schema version live in SQLite. | Uses Windows indexing internals, not a user-facing KGFS SQLite database. | Uses Windows semantic/indexing internals, not a user-facing KGFS SQLite database. | Uses Spotlight metadata stores, not a user-facing KGFS SQLite database. |
| Keyword search | Implemented with SQLite FTS5, filters, snippets, and ranking boosts. | Implemented by the OS index and File Explorer/taskbar search. | Implemented as part of Windows Search. | Implemented by Spotlight/Finder search. |
| Semantic search | Optional and local when `semantic.enabled` is true and dependencies/chunks/backend are ready; CLI/search kernel only at this commit. | Traditional Windows Search is primarily lexical/property/content indexing. | Implemented by Windows on supported Copilot+ PCs, supported languages, and supported file types. | Spotlight is highly integrated OS search, but KGFS-style local embedding search is not a documented Spotlight/Finder feature. |
| Hybrid search | Implemented in CLI/search kernel when semantic search is ready; combines keyword, semantic, filename, path, phrase, and recency signals. | Not exposed as KGFS-style configurable hybrid ranking. | Microsoft describes semantic indexing alongside traditional indexing, but not KGFS-style configurable hybrid weights. | Not exposed as KGFS-style configurable hybrid ranking. |
| Explainable ranking / `kgfs why` | Implemented for latest saved KGFS results, including score breakdown and snippets. | OS ranking is not exposed as a KGFS-style explanation command. | OS ranking is not exposed as a KGFS-style explanation command. | OS ranking is not exposed as a KGFS-style explanation command. |
| Open/reveal results | Implemented from latest result IDs through platform-specific helpers. | Native OS behavior. | Native OS behavior. | Native OS behavior. |
| AI assistance | Optional OpenAI-only AI Assist, disabled by default, downstream of local snippets, with preview/confirmation/redaction settings. | May include web/cloud/account results depending on Windows settings; not KGFS-style bounded context preview. | Semantic indexing is on-device per Microsoft; not KGFS-style OpenAI snippet workflow. | Spotlight can show suggestions/actions; not KGFS-style bounded context preview. |
| Privacy defaults | No folders indexed and no AI calls by default; selected local folders only. | Indexing is enabled for OS convenience and can include local, cloud, web, and account results depending on settings. | Microsoft says semantic index data is stored locally on the PC, with supported Copilot+ behavior and settings. | OS-managed local search with configurable result categories and privacy exclusions. |
| Source-file modification policy | Indexing, prune, reset, rebuild, and vector clear do not delete, move, rename, or overwrite indexed source files. | Search itself is for finding/opening; File Explorer can modify files when users perform file actions. | Same Windows file-management boundary. | Search itself is for finding/opening; Finder can modify files when users perform file actions. |
| Advanced workflows / roadmap | Planned knowledge workflows include deep search, similar, compare, timeline, research, profiles, collections, tags, notes, OCR, duplicates, versions, and project graphs. | Best at OS convenience, launch, settings, and broad file lookup. | Best at OS-integrated semantic file/photo/settings search on supported hardware. | Best at Mac-wide convenience, app launch, Finder organization, and OS actions. |
| Best audience | Users who want controlled project/corpus indexing, reproducible search, inspectable data, and privacy-bounded AI assistance. | Everyday Windows users who want fast broad desktop search. | Copilot+ PC users who want natural-language Windows search without managing a separate corpus. | Mac users who want fast built-in search, app launching, previews, actions, and Finder workflows. |

## What KGFS Is Good At

### Project and Corpus Search

KGFS starts from explicitly configured folders instead of assuming the whole computer is the right search space. That makes it a better fit for:

- A class folder with notes, PDFs, reports, and code.
- A research folder with papers, drafts, and data notes.
- A repository or project where `.kgfs/` should travel with the working copy.
- A deliberately bounded archive that should be searched without pulling in unrelated desktop files.

Implemented sources: `kgfs/core/config.py`, `kgfs/cli/commands/folders.py`, `kgfs/indexing/discovery.py`, `docs/settings.md`, `docs/usage.md`.

### Engineering, Student, and Research Workflows

KGFS is useful when the question is not only "where is the file?" but "where in this corpus did I work on this idea?" Examples include:

- Finding where torque, gain, assignment requirements, or experimental assumptions appear.
- Searching notes, code, CSV files, DOCX reports, and PDFs together.
- Filtering by extension, file type, folder, date range, or extraction failures.
- Explaining why a result matched through `kgfs why`.

Implemented sources: `kgfs/search/filters.py`, `kgfs/search/explain.py`, `kgfs/cli/commands/search.py`, `kgfs/cli/commands/why.py`, `docs/features.md`.

### Local-First Experimentation

KGFS is a good place to experiment with local indexing and ranking because the base layers are small and inspectable:

- SQLite FTS5 keyword search.
- Optional local sentence-transformers embeddings.
- Configurable hybrid ranking weights.
- Local vector backend registry with `sqlite_scan` as the base backend.
- Optional accelerated backends for `sqlite_vec`, `hnsw`, and `faiss` when their dependencies are installed.

Implemented sources: `kgfs/search/keyword.py`, `kgfs/search/semantic.py`, `kgfs/search/modes/hybrid.py`, `kgfs/search/backends/*.py`, `kgfs/vectors/*.py`, `docs/integrations.md`.

### CLI and Reproducible Workflows

KGFS works well when commands should be repeatable, scriptable, and tied to a project:

```bash
kgfs init --project-local
kgfs add-folder "./research-notes" --project-local
kgfs index --project-local
kgfs search "motor torque" --project-local --mode auto
kgfs why 1 "motor torque" --project-local
```

Implemented sources: `kgfs/cli/app.py`, `kgfs/cli/commands/*.py`, `kgfs/core/app_dirs.py`, `docs/cli.md`, `docs/usage.md`.

### Inspectable SQLite Storage

KGFS stores its index in SQLite tables documented in the data model. That makes the system easier to debug and reason about than opaque OS search indexes:

- `files`
- `files_fts`
- `latest_results`
- `chunks`
- `schema_version`

Implemented sources: `kgfs/db/schema.py`, `kgfs/db/repositories.py`, `kgfs/db/latest_results.py`, `docs/data-model.md`.

### Optional Semantic and Hybrid Search

Semantic search is optional and local when enabled. Hybrid search is available through the CLI/search kernel when semantic/vector readiness checks pass. The web dashboard search is keyword-only at this commit.

Implemented sources: `kgfs/search/semantic.py`, `kgfs/search/registry.py`, `kgfs/search/modes/*.py`, `kgfs/web/app.py`, `docs/features.md`.

### Optional AI Assist With Preview, Confirmation, and Redaction

KGFS AI Assist is not an always-on assistant. It is disabled by default, supports only OpenAI at this commit, and runs downstream of local search results. By default it sends bounded snippets rather than full file text, omits file paths, redacts the home path, previews context, and asks for confirmation.

Implemented sources: `kgfs/ai.py`, `kgfs/cli/shared.py`, `kgfs/cli/commands/search.py`, `docs/security.md`, `docs/settings.md`.

### Future Knowledge Tools

The advanced roadmap points KGFS toward a local knowledge workbench rather than an OS launcher clone. Planned work includes:

- Deep search.
- Similar-file search.
- Compare mode.
- Timeline mode.
- Research mode.
- Profiles.
- Collections.
- Tags and notes.
- Assignment mode.
- Project mode.
- OCR.
- Duplicate and version finding.
- File/topic/project graph features.

Roadmap sources: `docs/roadmap.md`, `KGFS_Advanced_Roadmap_Canvas.md`.

## What KGFS Is Not Trying to Beat

KGFS should not spend its energy trying to beat OS search at:

- App launching.
- Instant whole-computer search.
- OS settings search.
- Universal shell integration.
- Photos, email, account, web, and system-wide personal assistant behavior.
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
- "Search my PDFs, notes, code, CSV files, and reports together."
- "Run project-local search in a repo."
- "Use semantic or hybrid search over a controlled corpus."
- "Preview exactly what context would be sent to AI."
- "Keep search data in an inspectable local SQLite database."
- "Build future collections, tags, notes, profiles, research, or project workflows."

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
- Double down on explainability, including `kgfs why` and future ranking/source explanations.
- Double down on profiles, collections, tags, notes, assignment mode, and project mode.
- Double down on deep search, similar search, compare, timeline, and research workflows.
- Keep privacy and local-first defaults central.
- Keep optional heavy dependencies optional.
- Treat OS integrations as launch points into KGFS, not replacements for Spotlight or Windows Search.
- Keep the web dashboard honest about current capability; at this commit, dashboard search is keyword-only.

## Current Status vs Roadmap

| Area | Implemented now | Partially implemented / CLI-only | Planned | Not a KGFS goal |
|---|---|---|---|---|
| Scope and safety | Explicit-folder indexing, empty default config, risky-root refusal, source-file-safe maintenance. | Broad scans require `--allow-risky-root`. | Better profiles and corpus management. | Whole-drive indexing by default. |
| Project workflows | `--project-local` stores config/data under `.kgfs/`. | Project workflow is CLI-driven. | Project mode, saved searches, collections, tags, and notes. | Replacing OS project/file managers. |
| Keyword search | SQLite FTS5 keyword search, snippets, filters, latest result IDs. | Web dashboard search is keyword-only. | Better dashboard search UX. | Replacing OS global instant search. |
| Semantic search | Optional local embeddings and chunk storage when enabled. | CLI/search kernel only; requires readiness checks and local dependencies. | More advanced vector backends and quality work. | Cloud semantic indexing by default. |
| Hybrid search | CLI/search kernel hybrid mode with configurable ranking weights. | Not exposed in the current web dashboard. | Better hybrid quality and dashboard controls. | Opaque ranking without explanation. |
| Explainability | `kgfs why` explains latest saved results with snippets and score breakdown. | Explanation is a CLI command, not a web feature. | Broader explanations for future deep/research modes. | Hiding why results ranked. |
| Vector backends | Default `sqlite_scan`, backend registry, vector status/rebuild/clear/benchmark/recommend. | Optional `sqlite_vec`, `hnsw`, and `faiss` work when their dependencies are installed, enabled, and rebuilt. | More backend tuning, persistence polish, and larger-index UX. | Base install that requires heavy vector dependencies. |
| Web UI | Local FastAPI dashboard for home, keyword search, stats, config, failures, open, and reveal. | No authentication; semantic/hybrid search not exposed in web search. | Better dashboard, local API, TUI, launcher integrations. | Becoming a public hosted search service. |
| AI Assist | Optional OpenAI answer synthesis and reranking, disabled by default, bounded by local snippets. | OpenAI-only; no implemented query expansion despite config key. | Privacy-protected advanced ask/research workflows. | Always-on cloud assistant behavior. |
| OCR and media | Not implemented as a user-facing feature. | Roadmap only. | OCR, photos/image metadata, audio transcription, visual search. | Modifying source images, PDFs, or media files. |
| Knowledge workflows | Basic search, open/reveal, stats, doctor, prune/reset/rebuild. | Reproducible corpus workflows exist mostly through CLI. | Deep, similar, compare, timeline, research, profiles, collections, tags, notes, duplicates, versions, graphs. | Replacing the operating system shell. |

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
- [Roadmap](roadmap.md)
- [Advanced Roadmap Canvas](../KGFS_Advanced_Roadmap_Canvas.md)

External OS-search references:

- [Microsoft: Find your files and apps in Windows](https://support.microsoft.com/en-us/windows/find-your-files-and-apps-in-windows-5c7c8cfe-c289-fae4-f5f8-6b3fdba418d2)
- [Microsoft: Search indexing in Windows](https://support.microsoft.com/en-gb/windows/search-indexing-in-windows-da061c83-af6b-095c-0f7a-4dfecda4d15a)
- [Apple: Search for anything with Spotlight on Mac](https://support.apple.com/guide/mac-help/search-with-spotlight-mchlp1008/mac)
- [Apple: If searching your Mac returns unexpected results](https://support.apple.com/guide/mac-help/searching-mac-returns-unexpected-results-mchlp2962/mac)
