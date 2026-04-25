# KGFS Advanced Roadmap
## Quantum Folder Vibrations Edition

**Prepared:** 2026-04-25
**Project:** KG File Search / KGFS
**Purpose:** A phased, implementation-ready roadmap for evolving KGFS from a local-first semantic file searcher into a modular, cross-platform personal search, OCR, and knowledge-workflow system.

Core idea: keep KGFS safe, local, boring where it matters, and gloriously powerful where it helps. Tiny librarian goblin, not feral data raccoon.

---

## How to Use This Roadmap

Implement one phase at a time. Each phase should be independently useful, independently testable, and independently mergeable. The roadmap is designed so KGFS remains usable after every phase rather than becoming a half-built search spaceship held together by caffeine and import errors.

**Recommended workflow for each phase:**
- Create a new Git branch.
- Give Codex only the prompt/scope for that phase.
- Keep the phase tight.
- Run the full test suite.
- Run a project-local dogfood workflow.
- Update docs.
- Merge only when stable.

---

## Global Design Principles

| Principle | Meaning |
|---|---|
| Local-first | KGFS should work without cloud services. |
| Privacy-first | No source files, OCR images, snippets, paths, or documents should leave the machine unless explicitly opted in. |
| Cross-platform | Windows and macOS are first-class targets; Linux is nice-to-have. |
| No source-file modification | KGFS indexes, searches, caches, and stores metadata. It should not modify indexed source files. |
| Optional heavy features | OCR, local ML, FAISS, hnswlib, PaddleOCR, EasyOCR, and OpenAI should be optional. |
| Boring base install | The default install should remain lightweight and reliable. |
| Lazy imports | Optional dependencies should not be imported unless the feature is used. |
| Safe defaults | Generated config should not index real folders until the user adds them. |
| Explainability | When results are ranked or reranked, KGFS should be able to explain why. |

---

## Phase Overview

| Phase | Name | Main Outcome |
|---:|---|---|
| 0 | Stabilization Gate | Verify the current refactor/package branch is safe, stable, testable, packageable, and ready for advanced search work. |
| 1 | Search Kernel Architecture | Create a clean, modular search architecture that supports keyword, semantic, hybrid, and auto modes through a shared interface. |
| 2 | Semantic and Vector Foundation | Formalize local semantic search around embeddings, chunks, and a simple default vector backend. |
| 3 | Hybrid Search Quality and Explainability | Improve ranking, snippets, and result explanations so KGFS search feels useful and trustworthy. |
| 4 | Vector Backend Lab and Benchmarking | Add optional advanced vector backends and a benchmark/recommendation system. |
| 5 | OCR Text Extraction Layer | Add local, free, optional OCR for images and scanned PDFs using Tesseract first, without modifying source files. |
| 6 | Deep Search, Similarity, Ask, Timeline, Research | Add advanced modes that do more than one retrieval pass and can synthesize or organize results with local citations. |
| 7 | Personal Knowledge Workflows | Turn KGFS into a lightweight local knowledge workflow system with profiles, collections, tags, notes, and assignment workflows. |
| 8 | File Intelligence and Knowledge Graph | Analyze relationships between files, versions, duplicates, projects, and topics. |
| 9 | UX, Local App, and Integrations | Move KGFS beyond CLI-only usage with a TUI, better web app, local API, launcher integrations, and OS integration. |
| 10 | Multimodal Expansion and Advanced OCR | Add optional advanced OCR, image understanding, photo metadata, audio transcription, and visual semantic search. |

---

## Cross-Phase Safety Rules
- Never modify indexed source files.
- Never index an entire drive by default.
- Never call a cloud API by default.
- Never upload images, screenshots, snippets, OCR text, paths, or documents unless explicitly configured and confirmed.
- Use project-local mode for testing and dogfooding.
- Use dry-run modes for destructive index/database operations where practical.
- Database prune/reset operations must affect only KGFS index data, never source files.
- Any heavy dependency must live in an optional dependency group.
- Any optional dependency must fail gracefully when missing.
- Any packaged build must remain usable without semantic/OCR/AI extras.

## Cross-Phase Verification Checklist

```bash
python -m pytest
python -m kgfs --help
kgfs --help
kgfs doctor --project-local
kgfs init --project-local
kgfs config --project-local
```

Dogfood workflow:
```bash
mkdir kgfs-dogfood
mkdir kgfs-dogfood/circuits
mkdir kgfs-dogfood/robotics
printf "op amp gain and filters" > kgfs-dogfood/circuits/op_amp_notes.md
printf "motor torque equals force times radius" > kgfs-dogfood/robotics/motor_torque_lab.md
kgfs add-folder ./kgfs-dogfood --project-local
kgfs index --project-local
kgfs search "motor torque" --project-local
kgfs stats --project-local
```

---

# Phase 0 — Stabilization Gate

**Tagline:** Make sure the goblin has shoes before giving it a jetpack.

## Goal
Verify the current refactor/package branch is safe, stable, testable, packageable, and ready for advanced search work.

## Primary Outcomes
- Full tests pass locally and in CI
- Project-local workflow is proven
- Packaging smoke tests work
- No source-file modification
- AI/OCR/semantic extras remain optional and safe

## Subphases
### 0A — Test and CI Verification

**Tasks:**
- Run the full test suite locally.
- Confirm CI covers Windows, macOS, and Ubuntu where configured.
- Confirm Python 3.11/3.12 matrix behavior.
- Fix failures without changing user-facing behavior.

**Definition of done:**
- `python -m pytest` passes.
- No tests depend on real user folders.
- CI is green or failures are documented and understood.

### 0B — CLI and Project-Local Workflow

**Tasks:**
- Confirm `kgfs --help` and `python -m kgfs --help` both work.
- Run `kgfs doctor --project-local`, `kgfs init --project-local`, and `kgfs config --project-local`.
- Confirm generated config starts with `indexed_folders: []`.
- Confirm init does not begin indexing automatically.

**Definition of done:**
- Fresh users cannot accidentally index personal folders.
- Project-local data stays inside the test/project area.

### 0C — Indexing and Maintenance Verification

**Tasks:**
- Index a temporary dogfood folder only.
- Search indexed files.
- Test prune dry-run and prune.
- Test reset/rebuild if implemented.
- Confirm source files remain untouched.

**Definition of done:**
- Index/search works on temp files.
- Prune/reset/rebuild affect only KGFS database/index data.

### 0D — Packaging Verification

**Tasks:**
- Run local packaging if practical.
- Run packaged smoke test.
- Confirm templates/static/config resources work when frozen.
- Confirm packaged `kgfs doctor` works.

**Definition of done:**
- Package smoke tests pass on at least one OS locally and preferably in CI.
- Packaged app can index/search a temporary folder.

## Commands
```bash
python -m pytest
python -m kgfs --help
kgfs doctor --project-local
kgfs init --project-local
kgfs index --project-local
python scripts/smoke_test_packaged.py
```

## Not in Scope
- New features
- New vector backends
- OCR
- AI behavior changes

## Phase Definition of Done
- Full tests pass locally and in CI is implemented or cleanly verified.
- Project-local workflow is proven is implemented or cleanly verified.
- Packaging smoke tests work is implemented or cleanly verified.
- No source-file modification is implemented or cleanly verified.
- AI/OCR/semantic extras remain optional and safe is implemented or cleanly verified.
- Tests pass.
- Documentation is updated.
- No source files are modified by KGFS behavior.

---

# Phase 1 — Search Kernel Architecture

**Tagline:** Build the gearbox before installing the turbo.

## Goal
Create a clean, modular search architecture that supports keyword, semantic, hybrid, and auto modes through a shared interface.

## Primary Outcomes
- SearchEngine interface
- SearchEngineRegistry
- Shared SearchResult/SearchOptions models
- Mode wrappers
- CLI `--mode` support
- Keyword search independent of semantic dependencies

## Subphases
### 1A — Audit Existing Search Flow

**Tasks:**
- Inspect keyword, semantic, and hybrid search.
- Inspect CLI search command and latest result saving.
- Inspect snippets, filters, query parsing, and ranking code.
- Identify compatibility import paths.

**Definition of done:**
- A refactor plan exists before moving code.
- No accidental behavior changes are introduced.

### 1B — Add Search Models

**Tasks:**
- Add `SearchMode`, `SearchRequest`, `SearchOptions`, `SearchFilters`, `SearchResult`, and optionally `SearchExplanation`.
- Ensure results can represent file id, path, file name, extension, modified time, score, score breakdown, snippet, matched chunk, mode/source, and metadata.
- Use dataclasses or existing project model style.

**Definition of done:**
- Existing result types can be normalized into the shared result shape.
- Tests cover defaults and conversions.

### 1C — Add SearchEngine Interface

**Tasks:**
- Create `kgfs/search/engine.py`.
- Define a Protocol/lightweight base with `name`, `available()`, `search()`, optional `explain()`, and optional `stats()`.
- Add a simple `SearchContext` if useful for config/database/app paths.

**Definition of done:**
- Keyword/semantic/hybrid wrappers can share the interface.
- No heavy optional imports happen at engine import time.

### 1D — Add SearchEngineRegistry

**Tasks:**
- Create `kgfs/search/registry.py`.
- Register engines by name.
- Retrieve engines by mode.
- List available modes.
- Resolve auto mode.
- Return helpful errors for unknown/unavailable modes.

**Definition of done:**
- Registry tests cover registration, lookup, duplicate handling, and unavailable modes.

### 1E — Add Mode Wrappers

**Tasks:**
- Create `kgfs/search/modes/keyword.py`, `semantic.py`, `hybrid.py`, and `auto.py`.
- Wrap existing implementations rather than rewriting everything.
- Auto chooses keyword when semantic is disabled/unready and hybrid when semantic is ready.

**Definition of done:**
- `kgfs search --mode keyword` works.
- `kgfs search --mode auto` works.
- Semantic/hybrid unavailable cases fail gracefully.

### 1F — CLI and Config Integration

**Tasks:**
- Add/confirm `kgfs search "query" --mode keyword|semantic|hybrid|auto`.
- Add `search.default_mode`, `default_limit`, `highlight_matches`, and `save_latest_results` config fields.
- Keep old flags such as `--hybrid` as aliases if they exist.

**Definition of done:**
- Existing `kgfs search` remains usable.
- Latest results still support `kgfs open` and `kgfs reveal`.

### 1G — Tests and Documentation

**Tasks:**
- Test model defaults, registry behavior, mode wrappers, auto fallback, CLI mode selection, keyword independence, latest result saving, and filters.
- Document search modes and examples.
- Document future vector/OCR/AI phases as not part of Phase 1.

**Definition of done:**
- Full tests pass.
- Docs explain keyword, semantic, hybrid, and auto clearly.

## Commands
```bash
kgfs search "motor torque" --mode keyword
kgfs search "motor torque" --mode semantic
kgfs search "motor torque" --mode hybrid
kgfs search "motor torque" --mode auto
```

## Not in Scope
- FAISS
- hnswlib
- sqlite-vec
- OCR
- deep search
- ask mode
- OpenAI/API support
- multimodal search

## Phase Definition of Done
- SearchEngine interface is implemented or cleanly verified.
- SearchEngineRegistry is implemented or cleanly verified.
- Shared SearchResult/SearchOptions models is implemented or cleanly verified.
- Mode wrappers is implemented or cleanly verified.
- CLI `--mode` support is implemented or cleanly verified.
- Keyword search independent of semantic dependencies is implemented or cleanly verified.
- Tests pass.
- Documentation is updated.
- No source files are modified by KGFS behavior.

---

# Phase 2 — Semantic and Vector Foundation

**Tagline:** Give the goblin a map of meaning, but keep it local.

## Goal
Formalize local semantic search around embeddings, chunks, and a simple default vector backend.

## Primary Outcomes
- VectorBackend interface
- sqlite_scan backend
- Embedding provider layer
- Vector status/rebuild/clear commands
- Semantic readiness checks
- Chunk lifecycle cleanup

## Subphases
### 2A — Vector Backend Interface

**Tasks:**
- Create `kgfs/search/backends/base.py` and `sqlite_scan.py`.
- Define `available`, `build`, `add`, `remove_file`, `search`, `stats`, and `clear`.
- Keep optional advanced backend names out of runtime unless requested.

**Definition of done:**
- sqlite_scan implements the interface.
- No new heavy dependency is required.

### 2B — Embedding Provider Layer

**Tasks:**
- Create `kgfs/vectors/embeddings.py`, `chunks.py`, `index_manager.py`, and `status.py`.
- Load local embedding models lazily.
- Chunk documents and store vectors locally.
- Track vector readiness and stale chunks.

**Definition of done:**
- No cloud calls.
- sentence-transformers is not imported unless semantic features are used.

### 2C — Vector Commands

**Tasks:**
- Add `kgfs vector status`.
- Add `kgfs vector rebuild`.
- Add `kgfs vector clear --yes`.

**Definition of done:**
- Vector commands work with project-local data.
- Clear removes only KGFS vector data.

### 2D — Semantic Search Wiring

**Tasks:**
- Wire semantic mode through the vector backend interface.
- Keep keyword mode unaffected.
- Allow hybrid to consume semantic results through the new foundation.

**Definition of done:**
- Semantic search works through sqlite_scan.
- Keyword search remains dependency-light.

### 2E — Tests and Docs

**Tasks:**
- Use fake/deterministic embeddings in tests.
- Test vector status/rebuild/clear.
- Test semantic readiness behavior.
- Document local embeddings and where data is stored.

**Definition of done:**
- Tests pass without requiring real models unless optional tests are explicitly enabled.

## Commands
```bash
kgfs vector status
kgfs vector rebuild
kgfs vector clear --yes
kgfs search "speaker crossover" --mode semantic
```

## Not in Scope
- sqlite-vec
- hnswlib
- FAISS
- benchmarking
- OCR
- deep search

## Phase Definition of Done
- VectorBackend interface is implemented or cleanly verified.
- sqlite_scan backend is implemented or cleanly verified.
- Embedding provider layer is implemented or cleanly verified.
- Vector status/rebuild/clear commands is implemented or cleanly verified.
- Semantic readiness checks is implemented or cleanly verified.
- Chunk lifecycle cleanup is implemented or cleanly verified.
- Tests pass.
- Documentation is updated.
- No source files are modified by KGFS behavior.

---

# Phase 3 — Hybrid Search Quality and Explainability

**Tagline:** Make the results feel smart, not just technically correct.

## Goal
Improve ranking, snippets, and result explanations so KGFS search feels useful and trustworthy.

## Primary Outcomes
- Improved hybrid fusion
- Auto mode polish
- Better snippets
- Highlighted terms
- Score breakdowns
- `kgfs why` command

## Subphases
### 3A — Auto Mode Polish

**Tasks:**
- Make auto mode the preferred default where config supports it.
- Use keyword fallback when semantic is not ready.
- Ensure fallback messaging is clear and not scary.

**Definition of done:**
- Auto mode never crashes because semantic is unavailable.

### 3B — Hybrid Fusion Improvements

**Tasks:**
- Combine keyword score, semantic score, filename bonus, path bonus, exact phrase bonus, and modest recency bonus.
- Expose config weights.
- Prevent recency from overpowering relevance.

**Definition of done:**
- Ranking tests prove exact/good matches beat weak recent matches.

### 3C — Better Snippets

**Tasks:**
- Find best match context.
- Handle multiline text, punctuation, and unicode.
- Highlight terms using Rich where practical.

**Definition of done:**
- Snippets are readable and tested.

### 3D — Score Breakdown Foundation

**Tasks:**
- Track keyword, semantic, filename, path, exact phrase, and recency contributions.
- Store breakdown on SearchResult metadata or a dedicated field.

**Definition of done:**
- Result explanations can consume score data.

### 3E — `kgfs why`

**Tasks:**
- Add `kgfs why <result_id> "query"`.
- Explain matched terms, snippet/chunk, score components, and mode/backend.

**Definition of done:**
- Users can understand why a result matched.

### 3F — Tests and Docs

**Tasks:**
- Test ranking components.
- Test `why` output.
- Document scoring weights and explainability.

**Definition of done:**
- Tests pass and docs include examples.

## Commands
```bash
kgfs search "PID overshoot" --mode auto
kgfs search "op amp gain" --mode hybrid
kgfs why 3 "op amp gain"
```

## Not in Scope
- Advanced vector backends
- OCR
- deep/ask modes

## Phase Definition of Done
- Improved hybrid fusion is implemented or cleanly verified.
- Auto mode polish is implemented or cleanly verified.
- Better snippets is implemented or cleanly verified.
- Highlighted terms is implemented or cleanly verified.
- Score breakdowns is implemented or cleanly verified.
- `kgfs why` command is implemented or cleanly verified.
- Tests pass.
- Documentation is updated.
- No source files are modified by KGFS behavior.

---

# Phase 4 — Vector Backend Lab and Benchmarking

**Tagline:** Now install the turbo, carefully, with goggles.

## Goal
Add optional advanced vector backends and a benchmark/recommendation system.

## Primary Outcomes
- Backend selector
- sqlite-vec optional backend
- hnswlib optional backend
- FAISS optional backend
- Benchmark command
- Recommendation command

## Subphases
### 4A — Backend Selection Framework

**Tasks:**
- Expand vector config with backend and shard strategy.
- Add backend-specific rebuild/status plumbing.
- Keep sqlite_scan as safe default.

**Definition of done:**
- Selected backend is visible in status.

### 4B — sqlite-vec Backend

**Tasks:**
- Add optional dependency group.
- Use only when installed.
- Fail gracefully if missing.
- Mark experimental if appropriate.

**Definition of done:**
- sqlite-vec backend works or cleanly reports unavailable.

### 4C — hnswlib Backend

**Tasks:**
- Store HNSW index under KGFS data/cache.
- Store label-to-chunk mapping in SQLite.
- Support rebuild and stale handling.

**Definition of done:**
- hnsw backend can search vectors when installed.

### 4D — FAISS Backend

**Tasks:**
- Treat as power-user backend.
- Document install limitations.
- Store FAISS index under KGFS data/cache.
- Do not bundle in base packages.

**Definition of done:**
- FAISS backend works or is scaffolded with clear install docs.

### 4E — Benchmark Command

**Tasks:**
- Add `kgfs vector benchmark`.
- Measure availability, chunk count, query time, and notes.
- Use representative queries safely.

**Definition of done:**
- Benchmark output is clear and useful.

### 4F — Recommendation Command

**Tasks:**
- Add `kgfs vector recommend`.
- Recommend backend based on chunk count, installed deps, and performance data if available.

**Definition of done:**
- Recommendation explains reasoning.

### 4G — Tests and Docs

**Tasks:**
- Test optional dependency handling.
- Test benchmark output shape.
- Test recommendation logic.
- Optional backend tests skip cleanly.

**Definition of done:**
- Base install remains lightweight.

## Commands
```bash
kgfs vector benchmark
kgfs vector recommend
kgfs vector rebuild --backend sqlite_vec
kgfs vector rebuild --backend hnsw
kgfs vector rebuild --backend faiss
```

## Not in Scope
- OCR
- deep/ask modes
- media indexing

## Phase Definition of Done
- Backend selector is implemented or cleanly verified.
- sqlite-vec optional backend is implemented or cleanly verified.
- hnswlib optional backend is implemented or cleanly verified.
- FAISS optional backend is implemented or cleanly verified.
- Benchmark command is implemented or cleanly verified.
- Recommendation command is implemented or cleanly verified.
- Tests pass.
- Documentation is updated.
- No source files are modified by KGFS behavior.

---

# Phase 5 — OCR Text Extraction Layer

**Tagline:** Teach KGFS to read screenshots without sending them to the mothership.

## Goal
Add local, free, optional OCR for images and scanned PDFs using Tesseract first, without modifying source files.

## Primary Outcomes
- OCR architecture
- Tesseract backend
- Image OCR indexing
- OCR cache
- Scanned PDF fallback
- OCR status/stats
- OCR search labels

## Subphases
### 5A — OCR Architecture

**Tasks:**
- Create `kgfs/ocr/base.py`, `registry.py`, `tesseract.py`, `preprocessing.py`, and `status.py`.
- Add OCR config with `enabled: false`, backend, extensions, max size, cache, and `modify_source_files: false`.
- Treat OCR as an extraction source, not a separate search universe.

**Definition of done:**
- OCR architecture exists but is disabled by default.

### 5B — Tesseract Backend

**Tasks:**
- Add `kgfs ocr status`, `kgfs ocr test <image>`, and `kgfs ocr index`.
- Call Tesseract locally.
- Fail gracefully when Tesseract is missing.
- Respect language and command config.

**Definition of done:**
- OCR test command works with mocked or installed Tesseract.

### 5C — Image OCR Indexing

**Tasks:**
- OCR configured image extensions only.
- Skip files above size limit.
- Cache OCR by file hash.
- Store OCR text in KGFS database.
- Skip unchanged images.

**Definition of done:**
- Image OCR results appear in normal search when enabled.
- Source images are never modified.

### 5D — Scanned PDF OCR Fallback

**Tasks:**
- Try normal PDF extraction first.
- If text is empty/low and OCR enabled, rasterize/OCR pages into KGFS cache/temp.
- Store OCR text in DB.
- Mark scanned PDFs when OCR is disabled.

**Definition of done:**
- Original PDFs are never overwritten.
- Temporary OCR artifacts stay in KGFS cache/temp.

### 5E — OCR Stats and Health

**Tasks:**
- Show OCR enabled/backend/availability.
- Show OCR indexed files, failures, scanned PDFs, cache size, and last OCR time.

**Definition of done:**
- `kgfs ocr status` and `kgfs stats --ocr` are useful.

### 5F — Tests and Docs

**Tasks:**
- Test OCR disabled behavior.
- Test missing backend message.
- Test cache skip.
- Test no source modifications.
- Document local OCR and Tesseract setup.

**Definition of done:**
- OCR is safe, documented, and optional.

## Commands
```bash
kgfs ocr status
kgfs ocr test ./screenshot.png
kgfs ocr index
kgfs stats --ocr
```

## Not in Scope
- EasyOCR
- PaddleOCR
- cloud OCR
- image captions
- audio transcription
- visual semantic search

## Phase Definition of Done
- OCR architecture is implemented or cleanly verified.
- Tesseract backend is implemented or cleanly verified.
- Image OCR indexing is implemented or cleanly verified.
- OCR cache is implemented or cleanly verified.
- Scanned PDF fallback is implemented or cleanly verified.
- OCR status/stats is implemented or cleanly verified.
- OCR search labels is implemented or cleanly verified.
- Tests pass.
- Documentation is updated.
- No source files are modified by KGFS behavior.

---

# Phase 6 — Deep Search, Similarity, Ask, Timeline, Research

**Tagline:** Turn search into investigation.

## Goal
Add advanced modes that do more than one retrieval pass and can synthesize or organize results with local citations.

## Primary Outcomes
- Deep search
- Similar search
- Compare mode
- Timeline mode
- Research mode
- Ask mode
- Optional privacy-protected AI Assist

## Subphases
### 6A — Deep Search

**Tasks:**
- Parse the query.
- Generate local query variants.
- Run keyword/semantic searches.
- Fuse and rerank candidates.
- Show why top results matched.
- Suggest follow-up searches.

**Definition of done:**
- `kgfs deep` works locally without cloud calls.

### 6B — Similar Search

**Tasks:**
- Add `kgfs similar <result_id>` and optionally `kgfs similar-file <path>`.
- Find related chunks/files through vectors.
- Group by file and explain similarity.

**Definition of done:**
- Similar files are useful and not duplicates-only.

### 6C — Compare Mode

**Tasks:**
- Add `kgfs compare <id1> <id2>`.
- Show similarities, differences, overlapping topics, and unique snippets.

**Definition of done:**
- Compare output is readable and grounded in indexed text.

### 6D — Timeline Mode

**Tasks:**
- Add `kgfs timeline "topic"`.
- Sort matching files by modified date.
- Show sequence of work over time.

**Definition of done:**
- Timeline answers 'when did I work on this?' clearly.

### 6E — Research Mode

**Tasks:**
- Add `kgfs research "topic"`.
- Show best files, best chunks, related concepts, gaps, and suggested next searches.

**Definition of done:**
- Research mode feels like a local project map.

### 6F — Ask Mode

**Tasks:**
- Add `kgfs ask "question"`.
- Run local search first.
- Collect top snippets/chunks.
- Answer with local result IDs.

**Definition of done:**
- Ask mode works from local context.

### 6G — Optional AI Assist

**Tasks:**
- Keep AI disabled by default.
- API key comes from environment variable.
- No full file text by default.
- Preview context before sending.
- Redact home path by default.
- Mock API tests.

**Definition of done:**
- No cloud calls happen unless explicitly enabled and confirmed.

## Commands
```bash
kgfs deep "active crossover design"
kgfs similar 3
kgfs compare 3 7
kgfs timeline "speaker crossover"
kgfs research "amplifier noise floor"
kgfs ask "Where did I calculate motor torque?"
```

## Not in Scope
- Collections/tags
- TUI
- multimodal search

## Phase Definition of Done
- Deep search is implemented or cleanly verified.
- Similar search is implemented or cleanly verified.
- Compare mode is implemented or cleanly verified.
- Timeline mode is implemented or cleanly verified.
- Research mode is implemented or cleanly verified.
- Ask mode is implemented or cleanly verified.
- Optional privacy-protected AI Assist is implemented or cleanly verified.
- Tests pass.
- Documentation is updated.
- No source files are modified by KGFS behavior.

---

# Phase 7 — Personal Knowledge Workflows

**Tagline:** Search is cool. Organized search is dangerous—in the best way.

## Goal
Turn KGFS into a lightweight local knowledge workflow system with profiles, collections, tags, notes, and assignment workflows.

## Primary Outcomes
- Search profiles
- Saved searches
- Collections
- Tags
- Notes
- Assignment mode
- Project mode

## Subphases
### 7A — Search Profiles

**Tasks:**
- Add profile create/list/search commands.
- Allow folder/extension/mode/boost-term defaults.
- Support school/audio/photography style profiles.

**Definition of done:**
- Profiles constrain and tune search without modifying source files.

### 7B — Saved Searches

**Tasks:**
- Add save, run, list, and delete saved searches.
- Store saved searches in KGFS DB/config.

**Definition of done:**
- Recurring searches are easy to rerun.

### 7C — Collections

**Tasks:**
- Add create/add/show/export collection commands.
- Use collections for reports, projects, and source sets.

**Definition of done:**
- Users can curate search results into local bundles.

### 7D — Tags and Notes

**Tasks:**
- Add local tags and notes on result/file IDs.
- Store all metadata in KGFS DB.
- Never write tags/notes into source files.

**Definition of done:**
- Tags/notes are searchable/filterable later.

### 7E — Assignment Mode

**Tasks:**
- Add `kgfs assignment "topic"`.
- Find related notes, reports, PDFs, rubrics, data files, scripts, and plots.

**Definition of done:**
- Assignment mode produces a useful working set.

### 7F — Project Mode

**Tasks:**
- Add manual project show/list first.
- Later infer projects using folders/content/dates.

**Definition of done:**
- Project mode helps group related files.

## Commands
```bash
kgfs profile create school
kgfs profile search school "op amp gain"
kgfs save-search "circuits labs" "op amp OR Thevenin"
kgfs collection create "Motor Project"
kgfs tag 1 circuits lab-report
kgfs note 1 "Torque derivation is here."
kgfs assignment "robotics motor lab"
```

## Not in Scope
- Graph algorithms
- TUI
- media indexing

## Phase Definition of Done
- Search profiles is implemented or cleanly verified.
- Saved searches is implemented or cleanly verified.
- Collections is implemented or cleanly verified.
- Tags is implemented or cleanly verified.
- Notes is implemented or cleanly verified.
- Assignment mode is implemented or cleanly verified.
- Project mode is implemented or cleanly verified.
- Tests pass.
- Documentation is updated.
- No source files are modified by KGFS behavior.

---

# Phase 8 — File Intelligence and Knowledge Graph

**Tagline:** Now KGFS does archaeology.

## Goal
Analyze relationships between files, versions, duplicates, projects, and topics.

## Primary Outcomes
- Exact duplicates
- Semantic duplicates
- Version finder
- Project detection
- File graph
- Topic graph
- Health dashboard

## Subphases
### 8A — Exact Duplicate Finder

**Tasks:**
- Use hashes to find exact duplicate files.
- Group duplicates and show sizes/paths.

**Definition of done:**
- `kgfs duplicates` works without modifying files.

### 8B — Semantic Duplicate Finder

**Tasks:**
- Use embeddings to find near-duplicate documents.
- Keep threshold configurable.

**Definition of done:**
- Near-duplicate reports/notes are discoverable.

### 8C — Version Finder

**Tasks:**
- Find older/newer versions using filename similarity, content similarity, dates, and suffixes like v2/final/revised/draft.

**Definition of done:**
- `kgfs versions <id>` is useful for final-final chaos.

### 8D — Project Detection

**Tasks:**
- Infer projects from folder structure, file similarity, dates, and linked code/data/report files.

**Definition of done:**
- `kgfs projects` lists useful candidate projects.

### 8E — File and Topic Graphs

**Tasks:**
- Create graph edges for same folder, similar content, duplicates, versions, tags, collections, and references.

**Definition of done:**
- CLI or web graph output exists.

### 8F — Health Dashboard

**Tasks:**
- Show stale records, failures, skipped files, duplicates, semantic health, OCR failures, cache size, and risky folders.

**Definition of done:**
- `kgfs health` acts like a check-engine light for the index.

## Commands
```bash
kgfs duplicates
kgfs duplicates --semantic
kgfs versions 4
kgfs projects
kgfs graph "speaker crossover"
kgfs health
```

## Not in Scope
- TUI/tray integrations
- advanced multimedia

## Phase Definition of Done
- Exact duplicates is implemented or cleanly verified.
- Semantic duplicates is implemented or cleanly verified.
- Version finder is implemented or cleanly verified.
- Project detection is implemented or cleanly verified.
- File graph is implemented or cleanly verified.
- Topic graph is implemented or cleanly verified.
- Health dashboard is implemented or cleanly verified.
- Tests pass.
- Documentation is updated.
- No source files are modified by KGFS behavior.

---

# Phase 9 — UX, Local App, and Integrations

**Tagline:** Make it something you actually use every day.

## Goal
Move KGFS beyond CLI-only usage with a TUI, better web app, local API, launcher integrations, and OS integration.

## Primary Outcomes
- TUI
- Better web dashboard
- Local-only API
- macOS launcher integration
- Windows launcher integration
- Tray/menu-bar app
- VS Code extension path

## Subphases
### 9A — Terminal UI

**Tasks:**
- Add `kgfs tui`.
- Provide live search, result list, preview pane, filters, open/reveal, and mode selector.

**Definition of done:**
- TUI makes daily search fast without a browser.

### 9B — Web Dashboard Upgrade

**Tasks:**
- Improve search UI, filters, mode selector, vector/OCR status, open/reveal, collections/tags, and health dashboard.

**Definition of done:**
- Web UI becomes a real dashboard.

### 9C — Local API

**Tasks:**
- Add `kgfs serve --local-only`.
- Bind to 127.0.0.1 by default.
- Add token/auth option if API grows.

**Definition of done:**
- Other local tools can query KGFS safely.

### 9D — macOS Integrations

**Tasks:**
- Consider Raycast, Alfred, Finder Quick Action, and menu-bar app.

**Definition of done:**
- At least one macOS integration exists or is scaffolded.

### 9E — Windows Integrations

**Tasks:**
- Consider PowerToys Run, Explorer context menu, system tray app, and Terminal command palette.

**Definition of done:**
- At least one Windows integration exists or is scaffolded.

### 9F — VS Code Extension

**Tasks:**
- Search project notes/docs from editor.
- Open KGFS results in VS Code.
- Search current workspace.

**Definition of done:**
- VS Code path is documented or scaffolded.

## Commands
```bash
kgfs tui
kgfs serve --local-only
kgfs integrations status
```

## Not in Scope
- New search algorithms
- new OCR backends

## Phase Definition of Done
- TUI is implemented or cleanly verified.
- Better web dashboard is implemented or cleanly verified.
- Local-only API is implemented or cleanly verified.
- macOS launcher integration is implemented or cleanly verified.
- Windows launcher integration is implemented or cleanly verified.
- Tray/menu-bar app is implemented or cleanly verified.
- VS Code extension path is implemented or cleanly verified.
- Tests pass.
- Documentation is updated.
- No source files are modified by KGFS behavior.

---

# Phase 10 — Multimodal Expansion and Advanced OCR

**Tagline:** Search things that are not just text.

## Goal
Add optional advanced OCR, image understanding, photo metadata, audio transcription, and visual semantic search.

## Primary Outcomes
- EasyOCR
- PaddleOCR
- Image captions
- Photo/EXIF indexing
- Audio transcription
- Visual semantic search
- Cloud OCR fallback with confirmation

## Subphases
### 10A — Optional ML OCR Backends

**Tasks:**
- Add `kgfs[ocr-easyocr]` and `kgfs[ocr-paddle]` optional groups.
- Do not include PyTorch/Paddle in base install.
- Do not bundle ML models in standard packages.

**Definition of done:**
- Advanced OCR is optional and documented.

### 10B — Image Captions

**Tasks:**
- Generate local captions for images where configured.
- Index captions as searchable text.

**Definition of done:**
- Search can find photos/images by rough visual content.

### 10C — Photo Metadata / EXIF

**Tasks:**
- Index camera model, date/time, dimensions, location if present, and lens/settings where available.

**Definition of done:**
- Photo search by metadata works.

### 10D — Audio Transcription

**Tasks:**
- Transcribe lecture recordings, voice memos, and meetings using local tools where possible.
- Store transcripts in KGFS DB/cache.

**Definition of done:**
- Audio becomes searchable without modifying audio files.

### 10E — Visual Semantic Search

**Tasks:**
- Search images by visual similarity/content.
- Find diagrams/screenshots by conceptual similarity.

**Definition of done:**
- Visual embeddings are optional and local-first.

### 10F — Cloud OCR Fallback

**Tasks:**
- Add disabled-by-default cloud OCR provider config.
- Require confirmation and preview before upload.
- Never make cloud OCR automatic.

**Definition of done:**
- Cloud fallback is privacy-protected and clearly documented.

## Commands
```bash
kgfs media status
kgfs media index
kgfs ocr advanced-status
kgfs search "photo of sailboat at sunset"
kgfs search "lecture where PID control was explained"
```

## Not in Scope
- Base package bloat
- default cloud calls

## Phase Definition of Done
- EasyOCR is implemented or cleanly verified.
- PaddleOCR is implemented or cleanly verified.
- Image captions is implemented or cleanly verified.
- Photo/EXIF indexing is implemented or cleanly verified.
- Audio transcription is implemented or cleanly verified.
- Visual semantic search is implemented or cleanly verified.
- Cloud OCR fallback with confirmation is implemented or cleanly verified.
- Tests pass.
- Documentation is updated.
- No source files are modified by KGFS behavior.

---

# Command Roadmap

| Phase | Commands Added or Upgraded |
|---:|---|
| 0 | `python -m pytest; python -m kgfs --help; kgfs doctor --project-local; kgfs init --project-local; ...` |
| 1 | `kgfs search "motor torque" --mode keyword; kgfs search "motor torque" --mode semantic; kgfs search "motor torque" --mode hybrid; kgfs search "motor torque" --mode auto` |
| 2 | `kgfs vector status; kgfs vector rebuild; kgfs vector clear --yes; kgfs search "speaker crossover" --mode semantic` |
| 3 | `kgfs search "PID overshoot" --mode auto; kgfs search "op amp gain" --mode hybrid; kgfs why 3 "op amp gain"` |
| 4 | `kgfs vector benchmark; kgfs vector recommend; kgfs vector rebuild --backend sqlite_vec; kgfs vector rebuild --backend hnsw; ...` |
| 5 | `kgfs ocr status; kgfs ocr test ./screenshot.png; kgfs ocr index; kgfs stats --ocr` |
| 6 | `kgfs deep "active crossover design"; kgfs similar 3; kgfs compare 3 7; kgfs timeline "speaker crossover"; ...` |
| 7 | `kgfs profile create school; kgfs profile search school "op amp gain"; kgfs save-search "circuits labs" "op amp OR Thevenin"; kgfs collection create "Motor Project"; ...` |
| 8 | `kgfs duplicates; kgfs duplicates --semantic; kgfs versions 4; kgfs projects; ...` |
| 9 | `kgfs tui; kgfs serve --local-only; kgfs integrations status` |
| 10 | `kgfs media status; kgfs media index; kgfs ocr advanced-status; kgfs search "photo of sailboat at sunset"; ...` |

# Branch Plan

| Phase | Suggested Branch |
|---:|---|
| 0 | `stabilize/current-refactor` |
| 1 | `feature/search-kernel` |
| 2 | `feature/vector-foundation` |
| 3 | `feature/hybrid-explainability` |
| 4 | `feature/vector-backend-lab` |
| 5 | `feature/ocr-text-extraction` |
| 6 | `feature/deep-search-ask` |
| 7 | `feature/knowledge-workflows` |
| 8 | `feature/file-intelligence-graph` |
| 9 | `feature/ux-integrations` |
| 10 | `feature/multimodal-advanced-ocr` |

# Optional Dependency Strategy

| Group | Purpose | Base Package Required? |
|---|---|---|
| `dev` | pytest, lint/test helpers | No, dev only |
| `semantic` | sentence-transformers/local embeddings | No |
| `sqlite-vec` | SQLite-native vector backend | No |
| `hnsw` | hnswlib approximate nearest-neighbor backend | No |
| `faiss` | FAISS vector search backend | No |
| `ocr` | Tesseract wrapper / image preprocessing | No |
| `ocr-easyocr` | EasyOCR ML backend | No |
| `ocr-paddle` | PaddleOCR ML backend | No |
| `openai` | Optional AI assist | No |
| `package` | PyInstaller/build tooling | No |
| `advanced-search` | Semantic + local vector optional stack | No |

# Config Evolution

Do not add this whole config at once. Add each section only when its phase arrives. The cockpit of a 747 is cool, but KGFS should not ask users to configure a spaceship before searching for a lab report.

```yaml
search:
  default_mode: "auto"
  default_limit: 10
  highlight_matches: true
  save_latest_results: true

semantic:
  enabled: false
  model_name: "sentence-transformers/all-MiniLM-L6-v2"
  local_files_only: true
  chunk_size_chars: 1200
  chunk_overlap_chars: 200
  batch_size: 16

vectors:
  backend: "sqlite_scan"
  shard_strategy: "none"

  sqlite_vec:
    enabled: false

  hnsw:
    enabled: false
    space: "cosine"
    m: 16
    ef_construction: 200
    ef_search: 50

  faiss:
    enabled: false
    index_type: "flat"
    use_gpu: false

hybrid:
  keyword_weight: 0.35
  semantic_weight: 0.45
  filename_weight: 0.15
  path_weight: 0.05
  exact_phrase_weight: 0.10
  recency_weight: 0.05
  candidate_limit_multiplier: 5

ocr:
  enabled: false
  backend: "tesseract"
  include_extensions:
    - ".png"
    - ".jpg"
    - ".jpeg"
    - ".tiff"
    - ".bmp"
  max_image_size_mb: 15
  cache_results: true
  modify_source_files: false

  tesseract:
    command: "tesseract"
    language: "eng"

deep_search:
  enabled: true
  max_passes: 3
  max_candidates: 50
  rerank_top_n: 20

ai:
  enabled: false
  provider: "openai"
  model: "gpt-5.4-nano"
  api_key_env: "OPENAI_API_KEY"
  require_confirmation: true
  preview_context_before_send: true
  send_file_paths: false
  redact_home_path: true
  send_full_file_text: false
  max_results_sent: 12
  max_chars_per_result: 1500
  max_total_chars_sent: 12000

profiles:
  school:
    folders:
      - "~/Documents/College"
    extensions:
      - ".pdf"
      - ".docx"
      - ".md"
    default_mode: "hybrid"

  audio:
    folders:
      - "~/Documents/Audio Projects"
    boost_terms:
      - "filter"
      - "crossover"
      - "op amp"
      - "frequency response"
    default_mode: "hybrid"

media:
  enabled: false

  photos:
    index_exif: true
    generate_captions: false

  audio:
    transcription_enabled: false
```

# Implementation Order Summary

1. Phase 0: Stabilization Gate
2. Phase 1: Search Kernel Architecture
3. Phase 2: Semantic and Vector Foundation
4. Phase 3: Hybrid Search Quality and Explainability
5. Phase 4: Vector Backend Lab and Benchmarking
6. Phase 5: OCR Text Extraction Layer
7. Phase 6: Deep Search, Similarity, Ask, Timeline, Research
8. Phase 7: Personal Knowledge Workflows
9. Phase 8: File Intelligence and Knowledge Graph
10. Phase 9: UX, Local App, and Integrations
11. Phase 10: Multimodal Expansion and Advanced OCR

# Roadmap Philosophy

KGFS should become powerful through clean layers:

```text
Safe file discovery
→ robust extraction
→ reliable local database
→ keyword search
→ semantic search
→ hybrid ranking
→ OCR text extraction
→ deep investigation modes
→ personal knowledge workflows
→ UX integrations
→ advanced multimodal search
```

That path keeps the base useful at every step. It also prevents the classic software tragedy where version 0.2 becomes a 14GB dependency walrus that launches slowly, breaks packaging, and has opinions about your screenshots.

# Immediate Next Step

The next implementation phase should be **Phase 1 — Search Kernel Architecture**.

Why:
- It creates the structure needed for everything else.
- It keeps existing behavior stable.
- It makes future modes and backends clean to add.
- It prevents advanced search features from becoming a pile of special cases.

After Phase 1 is complete, proceed to Phase 2: Semantic and Vector Foundation.
