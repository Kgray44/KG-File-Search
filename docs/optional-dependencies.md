# Optional Dependency Matrix

The base KGFS install stays lightweight. Install optional extras only for the
local workflows you intend to use.

| Extra | Install command | Purpose | Bundled in base package | Readiness | Troubleshooting note |
| --- | --- | --- | --- | --- | --- |
| `semantic` | `python -m pip install -e ".[semantic]"` | Local text embeddings and semantic/hybrid search. | No | Optional | Keep `semantic.local_files_only: true` unless local model files are present. |
| `sqlite-vec` | `python -m pip install -e ".[sqlite-vec]"` | Experimental SQLite-native vector backend. | No | Experimental | Run `kgfs vector rebuild --backend sqlite_vec` after enabling. |
| `hnsw` | `python -m pip install -e ".[hnsw]"` | Optional HNSW approximate vector backend. | No | Optional | Rebuild artifacts under KGFS cache before benchmarking. |
| `faiss` | `python -m pip install -e ".[faiss]"` | Optional FAISS flat vector backend. | No | Power-user | Use CPU flat index; GPU mode is not implemented. |
| `ocr` | `python -m pip install -e ".[ocr]"` | Light OCR helpers; Tesseract executable still installed separately. | No | Optional | Run `kgfs ocr status` to check command/path. |
| `ocr-easyocr` | `python -m pip install -e ".[ocr-easyocr]"` | Optional local EasyOCR backend. | No | Optional | Use `kgfs models validate easyocr`; downloads are disabled by default. |
| `ocr-paddle` | `python -m pip install -e ".[ocr-paddle]"` | Optional guarded PaddleOCR backend. | No | Optional/guarded | Configure local model dirs or explicitly opt into backend downloads. |
| `captions` | `python -m pip install -e ".[captions]"` | Optional Transformers image caption adapter. | No | Optional | Configure a local model path in `media.captions.model_name`. |
| `audio` | `python -m pip install -e ".[audio]"` | Optional faster-whisper transcription adapter. | No | Optional | Configure a local model path and validate before indexing audio. |
| `visual` | `python -m pip install -e ".[visual]"` | Optional CLIP-style visual embedding adapter. | No | Optional | `bytehash-visual` is only plumbing; CLIP needs local model files. |
| `tui` | `python -m pip install -e ".[tui]"` | Optional Textual terminal UI. | No | Optional/scaffold | `kgfs tui --check` reports missing Textual cleanly. |
| `tray` | `python -m pip install -e ".[tray]"` | Optional tray/menu-bar scaffold runtime. | No | Scaffold | Does not install autostart or OS integration automatically. |
| `openai` | `python -m pip install -e ".[openai]"` | Optional AI Assist client after explicit config/user action. | No | Optional | AI is disabled by default and API keys come from environment variables. |
| `package` | `python -m pip install -e ".[package]"` | PyInstaller packaging tools. | No | Release tooling | Build on the target OS and smoke test the exact artifact. |

Use:

```bash
kgfs capabilities
kgfs models status
kgfs models doctor
kgfs vector status
kgfs ocr status
```

to inspect what is available in the current environment.

Sources: `pyproject.toml`, `docs/local-models.md`, `packaging/README-packaging.md`.
