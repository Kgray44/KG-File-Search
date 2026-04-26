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
