"""Tiny local test operations for optional model backends."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kgfs.core.config import KGFSConfig
from kgfs.media.audio import transcribe_audio
from kgfs.media.captions import caption_image
from kgfs.media.visual import visual_embedding_for_file
from kgfs.ocr.base import OCRRequest
from kgfs.ocr.registry import get_ocr_backend


@dataclass(frozen=True)
class ModelTestResult:
    backend: str
    status: str
    output: str
    detail: str = ""


def test_backend(backend: str, path: Path, config: KGFSConfig) -> ModelTestResult:
    key = backend.strip().lower().replace("_", "-")
    if key in {"tesseract", "easyocr", "paddle"}:
        result = get_ocr_backend(key).extract_image(OCRRequest(path=path, config=config, source_kind="image"))
        return ModelTestResult(key, result.status, result.text, result.error or "")
    if key in {"metadata-caption", "metadata"}:
        config = _with_caption_backend(config, "metadata")
        result = caption_image(path, config)
        return ModelTestResult("metadata-caption", result.status, result.text, result.error or "")
    if key in {"transformers-caption", "transformers"}:
        config = _with_caption_backend(config, "transformers")
        result = caption_image(path, config)
        return ModelTestResult("transformers-caption", result.status, result.text, result.error or "")
    if key.endswith("-caption") or key in {"fake-caption"}:
        result = caption_image(path, config)
        return ModelTestResult(key, result.status, result.text, result.error or "")
    if key == "faster-whisper":
        config = _with_audio_backend(config, "faster_whisper")
        result = transcribe_audio(path, config)
        return ModelTestResult("faster-whisper", result.status, result.text, result.error or "")
    if key in {"bytehash-visual", "bytehash"}:
        config = _with_visual_backend(config, "bytehash")
        result = visual_embedding_for_file(path, config)
        return ModelTestResult(
            "bytehash-visual",
            result.status,
            f"embedding_dim={len(result.vector)}" if result.vector else "",
            result.error or "",
        )
    if key in {"clip-visual", "clip"}:
        config = _with_visual_backend(config, "clip")
        result = visual_embedding_for_file(path, config)
        return ModelTestResult(
            "clip-visual",
            result.status,
            f"embedding_dim={len(result.vector)}" if result.vector else "",
            result.error or "",
        )
    raise ValueError(f"Unknown model test backend '{backend}'.")


def _with_caption_backend(config: KGFSConfig, backend: str) -> KGFSConfig:
    return config.model_copy(
        update={
            "media": config.media.model_copy(
                update={
                    "enabled": True,
                    "captions": config.media.captions.model_copy(update={"enabled": True, "backend": backend}),
                }
            )
        }
    )


def _with_audio_backend(config: KGFSConfig, backend: str) -> KGFSConfig:
    return config.model_copy(
        update={
            "media": config.media.model_copy(
                update={
                    "enabled": True,
                    "audio": config.media.audio.model_copy(
                        update={"enabled": True, "transcription_enabled": True, "backend": backend}
                    ),
                }
            )
        }
    )


def _with_visual_backend(config: KGFSConfig, backend: str) -> KGFSConfig:
    return config.model_copy(
        update={
            "media": config.media.model_copy(
                update={
                    "enabled": True,
                    "visual": config.media.visual.model_copy(update={"enabled": True, "backend": backend}),
                }
            )
        }
    )
