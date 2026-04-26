# Examples

These examples use only behavior implemented in the repository state at this commit.

## Example 1: Basic Local Index

```bash
python -m pip install -e ".[dev]"
kgfs init
kgfs add-folder "~/Documents/School Notes"
kgfs index
kgfs search "op amp circuit"
kgfs open 1
```

What happens:

- `init` creates config and app dirs.
- `add-folder` writes the folder to `indexed_folders`.
- `index` discovers supported files, extracts text, and writes SQLite rows.
- `search` queries SQLite FTS5 and saves latest result IDs.
- `open 1` opens the first latest result.

Sources: `kgfs/cli/commands/init.py`, `kgfs/cli/commands/folders.py`, `kgfs/cli/commands/index.py`, `kgfs/cli/commands/search.py`, `kgfs/cli/commands/open_reveal.py`.

## Example 2: Project-Local Test Corpus

```bash
mkdir sample-files
printf "Motor torque lab report" > sample-files/notes.md

kgfs init --project-local
kgfs add-folder "./sample-files" --project-local
kgfs index --project-local
kgfs search "motor torque" --project-local
kgfs stats --project-local
kgfs capabilities --project-local
kgfs db check --project-local
```

Project-local files live under `.kgfs/` in the current directory.

Source: `kgfs/core/app_dirs.py`.

## Example 2B: Built-In Demo Corpus

```bash
kgfs init --project-local
kgfs add-folder "./examples/sample-corpus" --project-local
kgfs index --project-local
kgfs search "motor torque" --project-local
kgfs search "op amp gain" --project-local
kgfs why 1 "op amp gain" --project-local
```

The demo corpus is artificial and contains no personal data.

## Example 3: Use Explicit Config and Database Paths

```bash
kgfs init --config ./config.yaml
kgfs add-folder "./docs" --config ./config.yaml
kgfs index --config ./config.yaml --database ./kgfs.sqlite3
kgfs search "pid control" --config ./config.yaml --database ./kgfs.sqlite3
```

Source: `kgfs/core/app_dirs.py`, `kgfs/cli/shared.py`.

## Example 4: Filtered Search

```bash
kgfs search "pid" --ext .pdf
kgfs search "pid" --type pdf
kgfs search "pid" --folder "Controls"
kgfs search "pid" --after 2025-01-01 --before 2025-12-31
kgfs search "failed extraction" --failed-only
```

Filter behavior source: `kgfs/search/filters.py`.

Explain a saved result:

```bash
kgfs search "op amp gain" --mode auto
kgfs why 1 "op amp gain"
```

`kgfs why` uses the latest search result IDs and prints the local score
breakdown and snippet. It does not call AI.

## Example 5: Local Investigation Commands

After a normal search saves latest result IDs:

```bash
kgfs search "speaker crossover"
kgfs deep "active crossover design"
kgfs similar 1
kgfs compare 1 2
kgfs timeline "speaker crossover" --group month
kgfs research "amplifier noise floor"
```

Search from an already indexed path:

```bash
kgfs similar-file ./notes/speaker-crossover.md
```

These commands reuse local indexed text and optional local vectors. They do not
modify source files, create sidecars, or call AI by default.

Sources: `kgfs/cli/commands/deep.py`, `kgfs/cli/commands/similar.py`, `kgfs/cli/commands/compare.py`, `kgfs/cli/commands/timeline.py`, `kgfs/cli/commands/research.py`.

## Example 6: Personal Workflow Metadata

Save and rerun a search:

```bash
kgfs save-search "circuits labs" "op amp OR Thevenin"
kgfs run-search "circuits labs"
```

Collect, tag, and annotate files from latest result IDs:

```bash
kgfs collection create "Motor Project"
kgfs collection add "Motor Project" 1 3 5
kgfs tag 1 circuits lab-report important
kgfs note 1 "Torque derivation is here."
kgfs collection export "Motor Project"
```

Use a profile and a manual project:

```bash
kgfs profile create school --ext .pdf --ext .docx --ext .md
kgfs profile search school "op amp gain"
kgfs project create "Audio Crossover"
kgfs project add "Audio Crossover" 1 3 5
kgfs project search "Audio Crossover" "frequency response"
```

Build a school-style working set:

```bash
kgfs assignment "robotics motor lab"
```

Workflow metadata is stored in KGFS DB/config only. Source files are not
modified.

Sources: `kgfs/workflows/*.py`, `tests/test_phase7_workflows.py`.

## Example 7: File Intelligence

Find exact duplicates:

```bash
kgfs duplicates
```

Find near-duplicates when semantic vectors are already built:

```bash
kgfs duplicates --semantic --min-score 0.92
```

Find likely versions and infer project candidates:

```bash
kgfs search "motor torque final"
kgfs versions 1
kgfs project infer
kgfs project candidates
kgfs project accept-candidate 1 --name "Motor Lab"
```

Build a bounded graph and export metadata before a reset:

```bash
kgfs graph "motor torque"
kgfs graph-export "motor torque" --format markdown
kgfs health --fix-suggestions
kgfs metadata export --output kgfs-metadata-backup.json
kgfs metadata import kgfs-metadata-backup.json --yes
```

These commands analyze the KGFS database only. They do not delete duplicates,
rename versions, move project files, or write sidecars beside source files.

Sources: `kgfs/intelligence/*.py`, `tests/test_phase8_file_intelligence.py`.

## Example 8: Reindex When Metadata Is Not Enough

If a file changed but size and modified time look unchanged:

```bash
kgfs index --verify-hashes
```

If you want to re-extract every discovered file:

```bash
kgfs index --force
```

Sources: `kgfs/indexing/indexer.py`, `tests/test_indexing.py`.

## Example 9: Prune Deleted Files

Show stale database records without changing the DB:

```bash
kgfs prune --dry-run
```

Remove stale rows and related FTS/chunk/latest-result rows:

```bash
kgfs prune
```

Source: `kgfs/indexing/prune.py`.

## Example 10: Semantic Search

Install semantic support:

```bash
python -m pip install -e ".[semantic]"
```

Enable in config:

```yaml
semantic:
  enabled: true
  model_name: "sentence-transformers/all-MiniLM-L6-v2"
  chunk_size_chars: 1200
  chunk_overlap_chars: 200
  local_files_only: true
  batch_size: 16
```

Build chunks:

```bash
kgfs semantic-index --rebuild
```

Search:

```bash
kgfs semantic "rotational force"
kgfs search "rotational force" --mode semantic
kgfs search "rotational force" --hybrid
```

Hybrid scoring can be tuned without changing the database:

```yaml
hybrid:
  keyword_weight: 0.35
  semantic_weight: 0.45
  filename_weight: 0.15
  path_weight: 0.05
  exact_phrase_weight: 0.10
  recency_weight: 0.05
  candidate_limit_multiplier: 5
```

Sources: `kgfs/cli/commands/semantic.py`, `kgfs/search/semantic.py`.

## Example 11: Vector Backend Lab

After enabling semantic search and indexing files:

```bash
kgfs vector status
kgfs vector rebuild
kgfs vector benchmark
kgfs vector recommend
kgfs vector clear --yes
```

`sqlite_scan` is the default backend and does not need extra packages. Optional
backend names can be inspected without installing them:

```bash
kgfs vector benchmark --backend sqlite_scan
kgfs vector rebuild --backend hnsw
kgfs vector clear --backend hnsw --yes
```

Missing optional dependencies produce install hints. `vector clear --yes` removes
KGFS chunk/vector rows for the configured model only; `vector clear --backend`
clears backend artifacts only. Neither form deletes source files or keyword
index rows.

Sources: `kgfs/cli/commands/vector.py`, `kgfs/vectors/*.py`, `tests/test_vector_commands.py`, `tests/test_vector_benchmark.py`, `tests/test_vector_recommend.py`.

## Example 12: Local OCR for Images

Install optional light OCR Python dependencies if you want future preprocessing support, then install Tesseract separately for your OS:

```bash
python -m pip install -e ".[ocr]"
```

Enable OCR:

```yaml
ocr:
  enabled: true
  backend: "tesseract"
  tesseract:
    command: "tesseract"
    language: "eng"
```

Check status and test one image without indexing:

```bash
kgfs ocr status
kgfs ocr test ./screenshots/circuit-label.png
```

Index configured folders and search OCR text:

```bash
kgfs ocr index
kgfs search "text from screenshot"
kgfs why 1 "text from screenshot"
```

KGFS stores OCR text in its local database/cache and never writes back to the image or PDF source file.

Sources: `kgfs/cli/commands/ocr.py`, `kgfs/ocr/*.py`, `tests/test_ocr_*.py`.

## Example 13: AI Preview Without API Call

## Example 13: Optional Media Metadata

Enable photo metadata without storing GPS/location:

```yaml
media:
  enabled: true
  photos:
    enabled: true
    index_exif: true
    store_location_metadata: false
```

Inspect and index local metadata:

```bash
kgfs media status
kgfs media exif ./photos/lab-bench.jpg
kgfs media index --photos
kgfs search "iPhone photo"
kgfs why 1 "iPhone photo"
```

Check optional multimodal scaffolds:

```bash
kgfs ocr advanced-status
kgfs media captions status
kgfs media audio status
kgfs media visual status
```

KGFS stores generated media metadata/text in the KGFS database only. Source
images are not modified and no sidecars are created.

Sources: `kgfs/media/*.py`, `kgfs/cli/commands/media.py`, `tests/test_phase10_media.py`.

## Example 14: AI Preview Without API Call

Enable AI in config for preview:

```yaml
ai:
  enabled: true
  require_confirmation: true
  preview_context_before_send: true
```

Preview answer context:

```bash
kgfs ask "What do my notes say about op-amps?" --preview-ai-context
```

Preview rerank context:

```bash
kgfs search "speaker crossover" --ai-rerank --preview-ai-context
```

No API call is made when `--preview-ai-context` is used.

Sources: `kgfs/cli/shared.py`, `kgfs/cli/commands/search.py`, `tests/test_cli.py`.

## Example 15: OpenAI Answer Synthesis

Install OpenAI dependency:

```bash
python -m pip install -e ".[openai]"
```

Set API key:

```bash
export OPENAI_API_KEY="sk-..."
```

Enable AI:

```yaml
ai:
  enabled: true
  require_confirmation: true
  send_file_paths: false
  send_full_file_text: false
  redact_home_path: true
```

Ask:

```bash
kgfs ask "What do my notes say about motor torque?"
```

Source: `kgfs/ai.py`.

## Example 16: Start Web Dashboard

```bash
kgfs web
```

Open:

```text
http://127.0.0.1:8765
```

Use `/search?q=pid&mode=auto&ext=.pdf` for a filtered search URL. The dashboard also includes local collection, tag, project, graph, and health pages.

Sources: `kgfs/cli/commands/web.py`, `kgfs/web/app.py`.

## Example 17: Local API, TUI, and Integration Scaffolds

Start the token-gated local API:

```bash
export KGFS_API_TOKEN="dev-token"
kgfs serve
```

Validate API settings without starting a server:

```bash
kgfs serve --dry-run
```

Query the API:

```bash
curl -H "Authorization: Bearer $KGFS_API_TOKEN" \
  "http://127.0.0.1:8766/search?q=motor%20torque&mode=keyword"
```

Check the optional TUI dependency:

```bash
kgfs tui --check
```

Generate local launcher scaffolds into chosen directories:

```bash
kgfs integrations status
kgfs integrations raycast export --output ./kgfs-raycast
kgfs integrations alfred export --output ./kgfs-alfred
kgfs integrations powertoys scaffold --output ./kgfs-powertoys
kgfs integrations finder scaffold --output ./kgfs-finder
kgfs integrations explorer scaffold --output ./kgfs-explorer
kgfs tray scaffold --output ./kgfs-tray
```

These commands do not edit system settings, install OS integrations, or modify indexed source files. API open/reveal actions stay disabled unless `api.allow_file_actions: true`.

Sources: `kgfs/api/*.py`, `kgfs/tui/*.py`, `kgfs/integrations/*.py`, `tests/test_phase9_ux_integrations.py`.

## Example 18: Reset and Rebuild

Dry-run reset:

```bash
kgfs reset-index --dry-run
```

Reset database files:

```bash
kgfs reset-index --yes
```

Reset and index again:

```bash
kgfs rebuild --yes
```

Sources: `kgfs/reset.py`, `kgfs/cli/commands/maintenance.py`.

`reset-index` creates a KGFS metadata backup first when
`metadata.auto_backup_before_reset: true`.

## Example 19: Release-Readiness Checks

```bash
python -m pip install -e ".[dev,package]"
python -m pytest -q --basetemp .pytest-tmp
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m pytest --cov=kgfs --cov-report=term-missing
python scripts/check_docs_consistency.py
kgfs capabilities --project-local
```

Use `kgfs db check --project-local` after indexing a project-local test corpus
to verify SQLite integrity, schema version, foreign keys, orphaned metadata, and
vector artifact placement.

Sources: `pyproject.toml`, `scripts/check_docs_consistency.py`, `kgfs/capabilities.py`, `kgfs/db/checks.py`.

## Example 20: Build a Package

```bash
python -m pip install -e ".[dev,package]"
python scripts/build_package.py --clean --mode onedir
python scripts/smoke_test_packaged.py --package dist-packages/KGFS
```

Expected artifact:

```text
dist-packages/KGFS-<os>-<arch>.zip
```

Sources: `scripts/build_package.py`, `scripts/smoke_test_packaged.py`.
