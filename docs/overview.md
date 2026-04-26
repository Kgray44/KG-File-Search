# KGFS Overview

KG File Search (KGFS) is a private, local-first search and knowledge workflow tool for folders you choose. It indexes selected projects, notes, code, PDFs, documents, and optional media metadata into a local SQLite database so you can search, investigate, organize, and explain your own file corpus without turning KGFS into a whole-computer crawler.

The big idea is simple: OS search helps you find something somewhere on your computer; KGFS helps you work through a deliberate body of files. Point it at a class folder, engineering project, research archive, documentation set, or notes collection, then use KGFS to search across formats, trace why results matched, and build local knowledge workflows around the files.

For the complete source-backed feature inventory, see [Features](features.md). This page is the short, user-friendly tour.

## Local-First Search

KGFS starts safe. A new config begins with `indexed_folders: []`, and nothing is indexed until you add a folder. App data normally lives in platform app-data locations, while `--project-local` mode keeps config, database, cache, and logs under `.kgfs/` in the current project.

Indexing reads files, extracts text or metadata, and stores KGFS data locally. It does not delete, move, rename, rewrite, tag, annotate, or modify your source files.

## Search Modes

KGFS supports several ways to search the same chosen corpus:

- **Keyword search** uses SQLite FTS5 for fast local text matching.
- **Semantic search** is optional and local when enabled, using local embeddings over indexed chunks.
- **Hybrid search** combines semantic, keyword, filename, path, phrase, and recency signals.
- **Auto mode** uses hybrid when semantic search is ready and falls back to keyword when it is not.

The CLI is the most complete interface. The current web dashboard provides local keyword search and browsing, while advanced semantic/hybrid workflows are CLI-first.

## Explainable Results

KGFS is built to make search less mysterious. Search results receive stable latest-result IDs, and `kgfs why` explains why a result matched a query using local file text, snippets, highlights, metadata, and scoring signals.

That explainability matters when you are trying to answer questions like, "Where did I calculate this?" or "Why is this file showing up?" instead of only opening the first result and hoping it is right.

## Semantic, OCR, and Media Support

Semantic/vector search is optional. KGFS can chunk extracted text, embed it locally, and store vector data in local KGFS storage. The default vector path is intentionally boring and inspectable; optional accelerated backends are available only when installed and configured.

OCR is also optional and disabled by default. KGFS can use local OCR backends such as Tesseract, plus optional EasyOCR/PaddleOCR adapters, to make image or scanned-PDF text searchable. OCR output is stored in KGFS data locations and never written back into the source image or PDF.

Media/local model support is opt-in. KGFS has local scaffolding for photo/EXIF metadata, captions, audio transcripts, and visual embeddings. Model downloads are disabled by default, local model paths can be checked before use, and cloud OCR remains a no-upload scaffold rather than an automatic upload path.

## Deep and Research Tools

KGFS includes investigation commands for going beyond a single search:

- `kgfs deep` runs deterministic multi-pass local search.
- `kgfs similar` and `kgfs similar-file` find related indexed files.
- `kgfs compare` compares two latest-result files.
- `kgfs timeline` groups matching files chronologically.
- `kgfs research` builds a local citation-backed research brief without AI.

These tools are useful for research folders, class assignments, engineering notes, project archives, and documentation sets where the goal is to understand a body of files, not just locate one filename.

## Knowledge Workflows

KGFS can store local workflow metadata in its own database:

- saved searches
- profiles
- collections
- tags
- notes
- assignments
- manual projects

This lets you build a working set around files without writing sidecars or changing the source files themselves.

## File Intelligence

KGFS can inspect the indexed corpus for local file intelligence:

- exact and semantic duplicates
- likely versions of a file
- project candidates
- file/topic graph views
- metadata backups
- health checks and fix suggestions

These commands analyze KGFS data and existing files. They are designed to be useful without taking ownership of your filesystem.

## Web, API, and Integrations

KGFS is CLI-first, but it also includes:

- a local FastAPI web dashboard for browser-based search and browsing
- a token-gated local JSON API
- an optional Textual TUI launcher
- scaffold exporters for local launcher/file-manager integrations
- PyInstaller packaging scripts for unsigned Windows and macOS builds

Integration commands write scaffold files only. They do not install OS integrations or change system settings by themselves.

## Safety and Privacy

KGFS is designed around controlled indexing and local data boundaries:

- no whole-drive indexing by default
- no source-file modification during indexing
- symlinks disabled by default
- risky roots refused unless explicitly allowed
- noisy/system/cache/dependency/application/game folders ignored by default
- OCR, media, semantic, and AI features disabled or optional by default
- AI Assist is opt-in, OpenAI-only at this commit, and downstream of local snippets

KGFS is not a permissions system or a backup tool. It respects your existing filesystem and gives you a local index over folders you deliberately selected.

## Example Workflows

Search a project locally:

```bash
kgfs init --project-local
kgfs add-folder "./examples/sample-corpus" --project-local
kgfs index --project-local
kgfs search "motor torque" --project-local
kgfs why 1 "motor torque" --project-local
```

Build a small research trail:

```bash
kgfs deep "active crossover design"
kgfs timeline "speaker crossover"
kgfs research "amplifier noise floor"
```

Organize useful results without touching source files:

```bash
kgfs save-search "circuits labs" "op amp OR Thevenin"
kgfs collection create "Motor Project"
kgfs tag 1 circuits lab-report important
kgfs note 1 "Torque derivation is here."
```

Inspect local capability and database health:

```bash
kgfs capabilities
kgfs db check
kgfs doctor
```

## What KGFS Is Not

KGFS is not trying to replace Windows Search, Copilot+ Search, Spotlight, or Finder for everyday whole-device search and app launching. It is also not a cloud sync service, backup system, antivirus scanner, permission manager, or automatic personal assistant.

Use OS search when you need broad desktop convenience. Use KGFS when you want a private, inspectable, selected-folder workbench for search, research, and knowledge workflows.

## Where To Go Next

- [Features](features.md): full detailed feature inventory.
- [Usage](usage.md): practical commands and workflows.
- [Settings](settings.md): complete configuration reference.
- [KGFS vs OS Search](kgfs-vs-os-search.md): honest positioning against OS-wide search tools.
- [Security](security.md): privacy and safety boundaries.
