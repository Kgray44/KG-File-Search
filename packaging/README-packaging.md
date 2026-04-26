# KGFS Packaging

KG File Search packages are built with PyInstaller. Build on the target OS:
Windows artifacts should be produced on Windows, and macOS artifacts should be
produced on macOS.

## Local Build

Install packaging dependencies:

```bash
python -m pip install -e ".[package]"
```

Build the default onedir package:

```bash
python scripts/build_package.py --clean
```

Run the smoke test:

```bash
python scripts/smoke_test_packaged.py --package dist-packages/KGFS
```

The release zip appears in `dist-packages/`:

- `KGFS-windows-x64.zip` on Windows x64
- `KGFS-macos-arm64.zip` on Apple Silicon macOS
- `KGFS-macos-x64.zip` on Intel macOS

## Included

- The packaged `kgfs` or `kgfs.exe` CLI executable
- KGFS runtime Python modules and required base dependencies
- Web dashboard templates and static files
- `README.md`
- `LICENSE`
- `config.example.yaml`
- `QUICKSTART-KGFS.txt`

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
