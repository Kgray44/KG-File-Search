# KGFS Packaging

KG File Search packages are built with PyInstaller. Build on the target OS:
Windows artifacts should be produced on Windows, and macOS artifacts should be
produced on macOS.

## Local Build

Install packaging dependencies:

```bash
python -m pip install -e ".[dev,package]"
```

Run release-readiness checks before building:

```bash
python scripts/release_check.py --dry-run
```

Remove `--dry-run` to run the whole local release ladder. Use
`--skip-package` if you want the test/lint/type/docs/coverage checks without
building PyInstaller artifacts.

Build the default onedir package:

```bash
python scripts/build_package.py --clean
```

Run the smoke test:

```bash
python scripts/smoke_test_packaged.py --package dist-packages/KGFS
```

The smoke test runs command-help checks, package diagnostics, indexing/search,
`kgfs capabilities`, and `kgfs db check` against a temporary project-local
workspace. It must not touch user source folders.

The release zip appears in `dist-packages/`:

- `KGFS-windows-x64.zip` on Windows x64
- `KGFS-macos-arm64.zip` on Apple Silicon macOS
- `KGFS-macos-x64.zip` on Intel macOS

The build also writes `dist-packages/SHA256SUMS.txt`.

Regenerate checksums for existing release zips:

```bash
python scripts/generate_checksums.py dist-packages
```

Verify an artifact with PowerShell:

```powershell
Get-FileHash .\dist-packages\KGFS-windows-x64.zip -Algorithm SHA256
Get-Content .\dist-packages\SHA256SUMS.txt
```

Or with common Unix tools:

```bash
shasum -a 256 dist-packages/KGFS-macos-arm64.zip
cat dist-packages/SHA256SUMS.txt
```

## Included

- The packaged `kgfs` or `kgfs.exe` CLI executable
- KGFS runtime Python modules and required base dependencies
- Web dashboard templates and static files
- `README.md`
- `LICENSE`
- `config.example.yaml`
- `QUICKSTART-KGFS.txt`
- Artificial `examples/sample-corpus`
- `SHA256SUMS.txt` beside the zip in release output

## Not Included

- User config files
- User SQLite databases
- User caches or logs
- Indexed source files
- `.kgfs/`
- `.git/`
- Test fixtures
- Downloaded semantic embedding model caches
- Optional advanced vector backend packages such as sqlite-vec, hnswlib, FAISS, and their caches/artifacts
- Optional OCR Python helper packages such as Pillow/pytesseract/EasyOCR/PaddleOCR, unless a future OCR-specific package opts in
- Optional media/model packages such as Whisper, CLIP-style stacks, Paddle, TorchVision, OpenCV, and their caches/artifacts
- Optional Textual TUI and pystray tray dependencies
- Tesseract executable, OCR cache rows, or OCR user data
- OpenAI SDK, unless a future AI-specific package is intentionally created
- API keys, `.env` files, local app data, test databases, or generated index artifacts

The archive writer skips common user-data, cache, log, database, and model-cache
patterns even if they appear in staging by mistake.

## GitHub Releases

The package workflow runs on pushes, pull requests, manual dispatches, and tags
matching `v*`. Tag builds produce Windows and macOS zip artifacts, generate
checksums, then create a draft GitHub Release with:

- `KGFS-windows-*.zip`
- `KGFS-macos-*.zip`
- `SHA256SUMS.txt`

The workflow does not require signing or notarization secrets yet, and it does
not fail just because signing secrets are absent. Signing remains a later
release-hardening step.

## Semantic Search

The base package excludes heavyweight semantic dependencies and model caches.
Keyword search, indexing, config management, stats, doctor, open/reveal, and the
web dashboard work in the base package. Semantic search can be packaged later as
a larger variant, or users can run from a Python environment with
`kg-file-search[semantic]`.

## Advanced Vector Backends

The base package keeps `sqlite_scan` as the vector backend. Optional backend
names such as `sqlite_vec`, `hnsw`, and `faiss` are implemented in source, but
the base PyInstaller spec excludes their heavy dependencies. A future
backend-specific package can opt into those extras intentionally. Base packaged
builds should report missing optional backends cleanly through `kgfs vector
status`, `kgfs vector benchmark`, and `kgfs vector recommend`.

## OCR

OCR commands are included in the base package, but Tesseract itself is not
bundled. Users who enable OCR must install Tesseract locally and configure
`ocr.tesseract.command` if it is not on PATH. `kgfs ocr status` should explain a
missing command cleanly. Packaged builds must not include user OCR caches or
indexed image/PDF data.

## Media and Multimodal Scaffolds

Media commands are included in the base package, but optional media/model
dependencies are excluded. `kgfs media status`, `kgfs media captions status`,
`kgfs media audio status`, `kgfs media visual status`, and `kgfs ocr
advanced-status` should report disabled or missing optional backends cleanly.
Photo/EXIF indexing requires an optional Python environment with Pillow, for
example `python -m pip install -e ".[media]"`; generated media metadata/text is
stored only in KGFS database/cache paths.

## Local API, TUI, and Integration Scaffolds

The base package includes the local web dashboard, token-gated local JSON API
code, and integration scaffold writers. Optional Textual TUI and tray runtime
dependencies are excluded from the base package; `kgfs tui --check` and scaffold
commands should fail/report cleanly when those optional dependencies are not
present. Scaffold commands must not install OS integrations or modify system
settings during packaging smoke tests.

## Signing

Current packages are unsigned.

On macOS, unsigned executables may trigger Gatekeeper warnings. Future release
work can add Developer ID signing and notarization using Apple credentials.

On Windows, unsigned `.exe` files may trigger SmartScreen warnings. Future
release work can add Authenticode signing with a code-signing certificate.

Unsigned builds must remain usable for local testing and CI smoke tests.

## Versioning Guidance

KGFS keeps its package version in one source:

- `kgfs/version.py`

`pyproject.toml` uses setuptools dynamic metadata to read that version.

For each release:

1. Update `kgfs/version.py`.
2. Add a dated entry to `CHANGELOG.md`.
3. Run the release-readiness checks above.
4. Build on each target OS.
5. Smoke test the exact packaged artifact that will be shared.
6. Verify the zip against `SHA256SUMS.txt`.
7. Tag the release, for example `git tag v0.1.0 && git push origin v0.1.0`.

Use semantic-version style increments:

- Patch: bug fixes, docs, internal cleanup, release-readiness checks.
- Minor: new user-visible local features or command families.
- Major: incompatible CLI/config/database behavior.
