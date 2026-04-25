# KG File Search (KGFS)

KGFS is a private, local-first file search tool. It indexes only folders you choose, extracts text from common document and code formats, stores the index in local SQLite, and searches with SQLite FTS5 keyword ranking plus optional local semantic search.

## Quickstart

```bash
python -m pip install -e ".[dev]"
kgfs init
kgfs add-folder "~/Documents/Your Notes"
kgfs index
kgfs search "motor torque"
kgfs why 1 "motor torque"
kgfs open 1
```

Project-local development keeps config and index files under `.kgfs/` in the current directory:

```bash
kgfs init --project-local
kgfs add-folder "./sample-files" --project-local
kgfs index --project-local
kgfs search "sample query" --project-local
```

## What Is Implemented

- Safe, explicit-folder indexing with risky-root protection.
- Text extraction for text-like files, Markdown, code, CSV, PDF, and DOCX.
- SQLite `files`, FTS5, latest-results, semantic `chunks`, and schema-version tables.
- Keyword, semantic, hybrid, and auto search modes.
- Local vector backend registry with the default `sqlite_scan` backend, optional accelerated backends, and vector benchmark/recommend commands.
- Optional local Tesseract OCR for image files and scanned-PDF detection, disabled by default.
- Result explanations with `kgfs why`.
- Optional OpenAI AI Assist for answer synthesis and reranking after local search.
- Typer CLI and a local FastAPI dashboard.
- PyInstaller packaging scripts and GitHub Actions workflows.

## Safety Defaults

- KGFS does not index a whole drive by default.
- `kgfs init` creates config but does not start indexing.
- `indexed_folders` starts empty.
- Symlinks are not followed unless `follow_symlinks: true`.
- Noisy, system, dependency, cache, application, game, binary, media, archive, and over-size files are ignored by default.
- Prune/reset/vector-clear operations remove only KGFS index data, not source files.
- OCR is off by default, never writes back to images/PDFs, and stores OCR cache data only in KGFS database/cache locations.
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
```

Optional extras:

```bash
python -m pip install -e ".[semantic]"
python -m pip install -e ".[ocr]"
python -m pip install -e ".[openai]"
python -m pip install -e ".[package]"
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

Build a packaged executable:

```bash
python scripts/build_package.py --clean
python scripts/smoke_test_packaged.py --package dist-packages/KGFS
```
