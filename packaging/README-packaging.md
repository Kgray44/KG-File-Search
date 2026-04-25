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

## Signing

Current packages are unsigned.

On macOS, unsigned executables may trigger Gatekeeper warnings. Future release
work can add Developer ID signing and notarization using Apple credentials.

On Windows, unsigned `.exe` files may trigger SmartScreen warnings. Future
release work can add Authenticode signing with a code-signing certificate.

Unsigned builds must remain usable for local testing and CI smoke tests.
