# Local Model Setup

KGFS can use optional local model backends for OCR and media workflows, but the
base install does not include heavy model stacks and KGFS does not download model
files by default.

This page covers the setup workflow for:

- Tesseract OCR
- EasyOCR
- PaddleOCR
- metadata-derived captions
- Transformers image captions
- faster-whisper transcription
- bytehash visual embeddings
- CLIP-style visual embeddings

All generated text, transcripts, captions, and embeddings live in the KGFS
database/cache. KGFS never writes model output into indexed source files and
never creates model sidecars beside source files.

## Setup Philosophy

- Install only the optional backend you intend to use.
- Keep `download_enabled: false` unless you intentionally opt into a backend's
  model-fetch behavior outside the base KGFS safety defaults.
- Prefer KGFS app-data/cache paths or project-local `.kgfs/cache/models`.
- Do not place model directories inside folders listed in `indexed_folders`.
- Use `kgfs models validate` before running OCR/media indexing at scale.

## Commands

```bash
kgfs models status
kgfs models doctor
kgfs models paths
kgfs models validate
kgfs models validate easyocr
kgfs models config-snippet easyocr
kgfs models test easyocr ./screenshot.png
```

`models status` and `models doctor` are read-only. They inspect config,
optional dependency availability, configured model paths, local-only settings,
download guard state, and KGFS path warnings.

`models config-snippet BACKEND` prints YAML only. It does not edit config.

`models test BACKEND PATH` runs one tiny local backend operation against one
file. It does not index the file, modify it, or create source sidecars.

## Readiness States

| State | Meaning |
| --- | --- |
| `disabled` | The backend is known but not enabled by config. |
| `ready` | Config, dependency, and model path checks are sufficient for a local run. |
| `missing_dependency` | Install the optional extra or external executable. |
| `missing_model` | Configure local model files or a local model directory. |
| `configuration_needed` | The backend needs more config before it can run. |
| `scaffold` | The backend surface exists but is intentionally not a full model implementation. |
| `error` | KGFS could not validate the backend cleanly. |

## Model Paths

KGFS reports a default model cache path with:

```bash
kgfs models paths
```

In project-local mode this defaults to `.kgfs/cache/models` under the current
working directory. The command does not create directories. If a configured
model path is inside an indexed source folder, KGFS warns because model caches
should not become searchable source content by accident.

## Backend Snippets

Each snippet keeps downloads disabled by default:

```bash
kgfs models config-snippet easyocr
kgfs models config-snippet paddle
kgfs models config-snippet transformers-caption
kgfs models config-snippet faster-whisper
kgfs models config-snippet clip-visual
kgfs models config-snippet bytehash-visual
```

Paste the snippet into `config.yaml`, then edit paths to point at local model
files you have already installed or staged.

## OCR Backends

Tesseract remains the simplest OCR setup. Install the Tesseract executable for
your OS, then configure:

```yaml
ocr:
  enabled: true
  backend: "tesseract"
  tesseract:
    command: "tesseract"
    language: "eng"
```

EasyOCR and PaddleOCR are optional. Their Python packages are not base
dependencies:

```bash
python -m pip install -e ".[ocr-easyocr]"
python -m pip install -e ".[ocr-paddle]"
```

Validate before indexing:

```bash
kgfs models validate easyocr
kgfs ocr test ./screenshot.png --backend easyocr
```

## Captions, Audio, and Visual Embeddings

`metadata-caption` is the safe baseline. It derives text from file/metadata
only and does not claim visual understanding.

`bytehash-visual` is a deterministic development/plumbing backend. It can prove
that media embeddings store/query correctly, but it is not visual semantic
search.

Transformers captions, faster-whisper transcription, and CLIP-style visual
embeddings require optional dependencies and local model files:

```bash
python -m pip install -e ".[captions]"
python -m pip install -e ".[audio]"
python -m pip install -e ".[visual]"
```

Use local paths in `model_name` when `local_files_only: true`.

## Privacy Notes

- KGFS does not call cloud OCR or cloud model APIs in these local model commands.
- API keys are not stored in model config.
- Model downloads are off by default.
- Source files are not modified.
- Generated OCR text, captions, transcripts, and embeddings are KGFS metadata.

Sources: `kgfs/models/*.py`, `kgfs/cli/commands/models.py`,
`kgfs/ocr/*.py`, and `kgfs/media/*.py`.
