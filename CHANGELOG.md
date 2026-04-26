# Changelog

All notable KGFS changes should be recorded here before a release.

KGFS uses semantic-version style guidance:

- Patch releases: bug fixes, docs, tests, internal cleanup, packaging, and release-readiness checks.
- Minor releases: new local-first user-visible features or command families.
- Major releases: incompatible CLI, config, database, or storage behavior.

Keep the package version in sync in:

- `kgfs/version.py`

Package metadata is generated from that version source through `pyproject.toml`.

## 0.1.0 - Release Candidate

### Added

- Local-first indexing/search foundation with keyword, semantic, hybrid, and auto modes.
- Optional vector backend lab, OCR, media metadata scaffolds, advanced local search, workflow metadata, file intelligence, web/API/TUI/integration scaffolds.
- Post-roadmap release-readiness tooling:
  - Ruff lint and format configuration.
  - Scoped mypy configuration.
  - Coverage configuration through pytest-cov.
  - `kgfs capabilities`.
  - `kgfs db check`.
  - `scripts/check_docs_consistency.py`.
- v0.1 release-candidate polish:
  - Single version source in `kgfs/version.py`.
  - `kgfs version` and `kgfs --version`.
  - `kgfs quickstart` and expanded packaged `QUICKSTART-KGFS.txt`.
  - Artificial demo corpus under `examples/sample-corpus`.
  - SHA256 checksum generation for packaged zip artifacts.
  - Tag-triggered GitHub Release workflow support for `v*` tags.
  - GitHub issue templates for bugs, features, packaging/install, search quality, and security/privacy.
- Phase 10.1 local model backend readiness:
  - `kgfs models status/list/benchmark/recommend`.
  - `kgfs ocr backends` and `--backend` selection for OCR test/index.
  - EasyOCR and PaddleOCR adapters with lazy imports and download guards.
  - Caption, audio transcription, and visual embedding backend contracts with searchable media-derived text/embeddings.
  - Optional extras for captions, audio, visual, and local-model status without adding heavy base dependencies.
- Phase 10.2 local model setup UX:
  - `kgfs models doctor`, `kgfs models paths`, `kgfs models validate`, `kgfs models config-snippet`, and `kgfs models test`.
  - Explicit backend readiness states for disabled, ready, missing dependency, missing model, configuration-needed, scaffold, and error cases.
  - Local model path checks that warn when model directories sit inside indexed source folders.
  - Copy-paste YAML snippets that keep downloads disabled and local-only defaults intact.
  - `docs/local-models.md` for manual optional backend setup.
- v0.1 release-candidate polish:
  - Standalone `scripts/generate_checksums.py` and `scripts/release_check.py`.
  - Dedicated `docs/known-limitations.md` and `docs/optional-dependencies.md`.
  - Optional model/backend issue template and expanded release-support issue fields.
  - Sample corpus files for duplicate and version-finder examples.

### Release Checklist

```bash
kgfs version
python -m pytest -q --basetemp .pytest-tmp
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m pytest --cov=kgfs --cov-report=term-missing
python scripts/check_docs_consistency.py
python scripts/build_package.py --clean --mode onedir
python scripts/smoke_test_packaged.py --package dist-packages/KGFS
Get-Content dist-packages/SHA256SUMS.txt
```
