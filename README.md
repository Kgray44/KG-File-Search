# KG File Search (KGFS)

KGFS is a private, local-first file search tool. It indexes only folders you choose, extracts text from common document and code formats, stores the index in local SQLite, and searches with SQLite FTS5 keyword ranking plus optional local semantic search, OCR, workflow metadata, and file-intelligence tools.

## What KGFS Is / Is Not

KGFS is:

- A local search index for folders you explicitly add.
- A SQLite-backed CLI, web dashboard, and local API for private file discovery.
- A place for local workflow metadata such as tags, notes, collections, projects, and saved searches.
- A release-candidate project with stable core search and many optional/lazy advanced surfaces.

KGFS is not:

- A cloud sync service.
- A drive-wide crawler by default.
- A tool that edits, tags, annotates, moves, deletes, or rewrites your source files.
- A replacement for backups or filesystem permissions.
- A promise that every optional experimental backend is installed or enabled in the base package.

## 5-Minute Quickstart

```bash
python -m pip install -e ".[dev]"
kgfs version
kgfs init
kgfs doctor
kgfs add-folder "./examples/sample-corpus"
kgfs index
kgfs search "motor torque"
kgfs why 1 "motor torque"
```

Generated config starts with `indexed_folders: []`, and KGFS never indexes the
whole drive by default. Add only the folders you want KGFS to search.

Project-local development keeps config and index files under `.kgfs/` in the current directory:

```bash
kgfs init --project-local
kgfs add-folder "./examples/sample-corpus" --project-local
kgfs index --project-local
kgfs search "op amp gain" --project-local
kgfs quickstart
```

## Stable Core

- Safe, explicit-folder indexing with risky-root protection.
- Text extraction for text-like files, Markdown, code, CSV, PDF, and DOCX.
- SQLite `files`, FTS5, latest-results, semantic `chunks`, and schema-version tables.
- Keyword, semantic, hybrid, and auto search modes.
- Result explanations with `kgfs why`.
- Typer CLI, local FastAPI dashboard, token-gated local JSON API, and PyInstaller packaging scripts.
- Release-readiness commands: `kgfs version`, `kgfs quickstart`, `kgfs capabilities`, and `kgfs db check`.

## Optional / Experimental Surfaces

- Local vector backend registry with the default `sqlite_scan` backend, optional accelerated backends, and vector benchmark/recommend commands.
- Optional local Tesseract OCR for image files and scanned-PDF detection, disabled by default.
- Optional local media metadata expansion: photo/EXIF indexing, media-derived search text, advanced OCR backend scaffolds, caption/audio/visual scaffolds, and no-upload cloud OCR planning.
- Local investigation commands: `kgfs deep`, `kgfs similar`, `kgfs similar-file`, `kgfs compare`, `kgfs timeline`, and `kgfs research`.
- Local personal workflow metadata: profiles, saved searches, collections, tags, notes, assignment mode, and manual projects.
- Local file intelligence: exact/semantic duplicates, versions, project candidates, file/topic graphs, health reports, and metadata backups.
- Optional OpenAI AI Assist for answer synthesis and reranking after local search.
- Optional Textual TUI launcher and local integration scaffolds.
- Optional accelerated vector/OCR/media dependencies stay out of the base install unless requested.

## Safety Defaults

- KGFS does not index a whole drive by default.
- `kgfs init` creates config but does not start indexing.
- `indexed_folders` starts empty.
- Symlinks are not followed unless `follow_symlinks: true`.
- Noisy, system, dependency, cache, application, game, binary, media, archive, and over-size files are ignored by default.
- Prune/reset/vector-clear operations remove only KGFS index data, not source files.
- OCR is off by default, never writes back to images/PDFs, and stores OCR cache data only in KGFS database/cache locations.
- Media indexing is off by default, never writes sidecars, and stores EXIF/caption/transcript/visual scaffold data only in KGFS database/cache locations. Exact GPS storage is disabled by default.
- Workflow metadata is stored in KGFS config/database only; KGFS never writes tags, notes, or collections into source files.
- File intelligence metadata and backups stay in KGFS database/app-data/project-local paths; KGFS never writes analysis sidecars beside source files.
- AI Assist is off by default and sends bounded snippets only after opt-in.

## Documentation

The full documentation hub is [docs/README.md](docs/README.md). Start there for:

- [Features](docs/features.md)
- [KGFS vs OS Search](docs/kgfs-vs-os-search.md)
- [Settings](docs/settings.md)
- [CLI](docs/cli.md)
- [Usage](docs/usage.md)
- [Architecture](docs/architecture.md)
- [Data Model](docs/data-model.md)
- [Security](docs/security.md)
- [Development](docs/development.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Examples](docs/examples.md)

## Roadmap

See [docs/roadmap.md](docs/roadmap.md).

Implemented vs planned: this README and the docs describe source-backed behavior in the repository state at this commit. The roadmap separates implemented capabilities from planned or intentionally absent work.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m pytest --cov=kgfs --cov-report=term-missing
python scripts/check_docs_consistency.py
```

Optional extras:

```bash
python -m pip install -e ".[semantic]"
python -m pip install -e ".[ocr]"
python -m pip install -e ".[openai]"
python -m pip install -e ".[package]"
python -m pip install -e ".[tui]"
python -m pip install -e ".[tray]"
python -m pip install -e ".[media]"
python -m pip install -e ".[ocr-easyocr]"
python -m pip install -e ".[ocr-paddle]"
python -m pip install -e ".[hnsw]"          # optional advanced vector backend dependency
python -m pip install -e ".[sqlite-vec]"    # optional experimental SQLite vector dependency
python -m pip install -e ".[faiss]"         # optional power-user vector dependency
```

Vector backend lab commands:

```bash
kgfs vector status
kgfs vector benchmark
kgfs vector recommend
kgfs vector rebuild --backend sqlite_scan
```

The base install and base packaged build keep advanced vector dependencies out unless you install the relevant optional extra.

Local OCR uses the external Tesseract executable. Install Tesseract separately, then enable it in `config.yaml`:

```yaml
ocr:
  enabled: true
  backend: "tesseract"
  tesseract:
    command: "tesseract"
    language: "eng"
```

Useful OCR commands:

```bash
kgfs ocr status
kgfs ocr test ./screenshot.png
kgfs ocr index
kgfs search "text from screenshot"
kgfs why 1 "text from screenshot"
```

Optional media features are disabled by default and stay local:

```bash
kgfs media status
kgfs media exif ./photo.jpg
kgfs media index --photos
kgfs media captions status
kgfs media audio status
kgfs media visual status
kgfs ocr advanced-status
kgfs search "TestCam photo"
```

Photo/EXIF indexing can make safe metadata searchable without modifying images. Captioning, audio transcription, visual embeddings, EasyOCR, PaddleOCR, and cloud OCR fallback remain optional/lazy scaffolds unless explicitly enabled and installed; cloud OCR cannot upload in this phase.

Local investigation commands stay grounded in indexed KGFS data and do not call AI:

```bash
kgfs deep "active crossover design"
kgfs similar 3
kgfs similar-file ./notes.md
kgfs compare 3 7
kgfs timeline "speaker crossover"
kgfs research "amplifier noise floor"
```

`kgfs ask` remains optional AI Assist. It now includes local KGFS result citations such as `[1] notes.md` in the bounded snippet context, while keeping AI disabled by default.

Local personal workflow commands store metadata in the KGFS database/config only:

```bash
kgfs profile create school --ext .pdf --ext .docx --ext .md
kgfs profile search school "op amp gain"
kgfs save-search "circuits labs" "op amp OR Thevenin"
kgfs run-search "circuits labs"
kgfs collection create "Motor Project"
kgfs collection add "Motor Project" 1 3 5
kgfs tag 1 circuits lab-report important
kgfs note 1 "Torque derivation is here."
kgfs assignment "robotics motor lab"
kgfs project create "Audio Crossover"
kgfs project search "Audio Crossover" "frequency response"
```

Local file intelligence commands analyze the existing KGFS index without editing source files:

```bash
kgfs duplicates
kgfs duplicates --semantic
kgfs versions 4
kgfs project infer
kgfs project candidates
kgfs project accept-candidate 1 --name "Audio Crossover"
kgfs graph "speaker crossover"
kgfs health --fix-suggestions
kgfs metadata export --output kgfs-metadata-backup.json
kgfs metadata import kgfs-metadata-backup.json --yes
```

`reset-index` can automatically create a KGFS metadata backup when `metadata.auto_backup_before_reset: true`, but it still deletes the active KGFS database/index files after the backup.

Local UX and integration commands are opt-in and keep their boundaries local:

```bash
kgfs web
export KGFS_API_TOKEN="dev-token"
kgfs serve
kgfs tui --check
kgfs integrations status
kgfs integrations raycast export --output ./kgfs-raycast
kgfs integrations alfred export --output ./kgfs-alfred
kgfs integrations powertoys scaffold --output ./kgfs-powertoys
kgfs integrations finder scaffold --output ./kgfs-finder
kgfs integrations explorer scaffold --output ./kgfs-explorer
kgfs tray scaffold --output ./kgfs-tray
```

The dashboard binds to localhost by default. The JSON API requires a bearer token by default and refuses non-localhost binds unless explicitly allowed. Integration commands write scaffold files only; they do not install OS integrations or change system settings.

Build a packaged executable:

```bash
python scripts/build_package.py --clean
python scripts/smoke_test_packaged.py --package dist-packages/KGFS
```

The package build writes `KGFS-<os>-<arch>.zip` plus `SHA256SUMS.txt` under
`dist-packages/`. Verify a release artifact by comparing its SHA256 digest with
the matching line in `SHA256SUMS.txt`.

Release-readiness checks:

```bash
kgfs version
kgfs capabilities
kgfs db check
python scripts/check_docs_consistency.py
```

See [CHANGELOG.md](CHANGELOG.md) and [packaging/README-packaging.md](packaging/README-packaging.md) for versioning and packaging guidance.
