# Known Limitations

KGFS v0.1.0 is a local-first release candidate with a stable core search path
and many optional/lazy advanced surfaces. These are the limits to know before a
v0.1 release.

## Packaging and Platform Trust

- Unsigned executables can trigger SmartScreen on Windows and Gatekeeper on
  macOS. KGFS does not require signing/notarization secrets for v0.1 packaging.
- Base packaged builds exclude heavy optional dependencies and model caches.
- Package zips include the KGFS executable, README, config example, quickstart,
  and artificial sample corpus; they must not include user `.kgfs` folders,
  logs, databases, API keys, indexed source files, or model caches.

## Optional Models and Media

- Optional model backends require user-installed dependencies and local model
  files. KGFS does not download models by default.
- EasyOCR, PaddleOCR, faster-whisper, Transformers captioning, and CLIP-style
  visual embeddings are not base dependencies.
- `bytehash-visual` is a development/plumbing backend, not visual
  understanding.
- Cloud OCR is a no-upload scaffold in this release candidate.
- Exact GPS/location storage is disabled by default.

## UI and Integrations

- The web dashboard is localhost-first and not a full replacement for the CLI.
- The local JSON API is token-gated by default and local-only unless explicitly
  overridden.
- TUI and tray/menu-bar surfaces remain optional/scaffold-level where their
  optional runtime dependencies are absent.
- Launcher integration commands generate scaffolds/templates; they do not modify
  OS registry, Finder, Raycast, Alfred, or PowerToys locations automatically.

## Search and Intelligence

- Keyword search is the most stable baseline.
- Semantic/vector search requires optional dependencies, local model readiness,
  indexed chunks, and backend artifacts.
- Semantic duplicates, similar search, and project inference degrade when
  semantic/vector data is missing.
- AI Assist is off by default and remains optional; KGFS does not add cloud AI
  behavior in v0.1.

## Development Checks

- Ruff lint and format checks are enforced for release readiness.
- Mypy is intentionally scoped to selected release-readiness modules; full-repo
  strict mypy is not yet enforced.
- Coverage reporting exists, but a coverage threshold is not enforced yet.

Sources: `README.md`, `packaging/README-packaging.md`, `docs/local-models.md`,
`pyproject.toml`, and `.github/workflows/package.yml`.
