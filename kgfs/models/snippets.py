"""YAML config snippets for optional local model backends."""

from __future__ import annotations


def config_snippet(backend: str) -> str:
    key = backend.strip().lower()
    snippets = {
        "easyocr": _easyocr,
        "paddle": _paddle,
        "metadata-caption": _metadata_caption,
        "metadata": _metadata_caption,
        "transformers-caption": _transformers_caption,
        "transformers": _transformers_caption,
        "faster-whisper": _faster_whisper,
        "faster_whisper": _faster_whisper,
        "bytehash-visual": _bytehash_visual,
        "bytehash": _bytehash_visual,
        "clip-visual": _clip_visual,
        "clip": _clip_visual,
        "tesseract": _tesseract,
    }
    if key not in snippets:
        valid = ", ".join(sorted(snippets))
        raise ValueError(f"Unknown model backend '{backend}'. Known snippet backends: {valid}.")
    return snippets[key]().strip() + "\n"


def _tesseract() -> str:
    return """
ocr:
  enabled: true
  default_backend: "tesseract"
  backend: "tesseract"
  tesseract:
    command: "tesseract"
    language: "eng"
"""


def _easyocr() -> str:
    return """
ocr:
  enabled: true
  default_backend: "easyocr"
  backend: "easyocr"
  easyocr:
    enabled: true
    languages:
      - "en"
    gpu: false
    model_storage_directory: ".kgfs/cache/models/easyocr"
    download_enabled: false
"""


def _paddle() -> str:
    return """
ocr:
  enabled: true
  default_backend: "paddle"
  backend: "paddle"
  paddle:
    enabled: true
    language: "en"
    use_angle_cls: true
    use_gpu: false
    model_dir: ".kgfs/cache/models/paddleocr"
    download_enabled: false
"""


def _metadata_caption() -> str:
    return """
media:
  enabled: true
  captions:
    enabled: true
    backend: "metadata"
    local_files_only: true
    download_enabled: false
"""


def _transformers_caption() -> str:
    return """
media:
  enabled: true
  captions:
    enabled: true
    backend: "transformers"
    model_name: ".kgfs/cache/models/caption-model"
    local_files_only: true
    download_enabled: false
"""


def _faster_whisper() -> str:
    return """
media:
  enabled: true
  audio:
    enabled: true
    transcription_enabled: true
    backend: "faster_whisper"
    model_name: ".kgfs/cache/models/faster-whisper-model"
    local_files_only: true
    download_enabled: false
"""


def _bytehash_visual() -> str:
    return """
media:
  enabled: true
  visual:
    enabled: true
    backend: "bytehash"
    local_files_only: true
    download_enabled: false
"""


def _clip_visual() -> str:
    return """
media:
  enabled: true
  visual:
    enabled: true
    backend: "clip"
    model_name: ".kgfs/cache/models/clip-model"
    local_files_only: true
    download_enabled: false
"""
