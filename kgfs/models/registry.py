"""Lazy registry for optional local model backends."""

from __future__ import annotations

from importlib.util import find_spec

from kgfs.core.config import KGFSConfig
from kgfs.models.base import BackendDescriptor, BackendStatus
from kgfs.models.validation import validate_backend
from kgfs.ocr.registry import get_ocr_backend, list_ocr_backends


def list_model_backends() -> list[BackendDescriptor]:
    """Return known optional/local model backends without importing heavy packages."""

    return [
        BackendDescriptor("tesseract", "ocr", "ocr.backend"),
        BackendDescriptor("easyocr", "ocr", "ocr.easyocr", 'python -m pip install -e ".[ocr-easyocr]"'),
        BackendDescriptor("paddle", "ocr", "ocr.paddle", 'python -m pip install -e ".[ocr-paddle]"'),
        BackendDescriptor("none", "caption", "media.captions.backend"),
        BackendDescriptor("metadata", "caption", "media.captions.backend"),
        BackendDescriptor("transformers", "caption", "media.captions", 'python -m pip install -e ".[captions]"'),
        BackendDescriptor("none", "transcription", "media.audio.backend"),
        BackendDescriptor("faster_whisper", "transcription", "media.audio", 'python -m pip install -e ".[audio]"'),
        BackendDescriptor("none", "visual_embedding", "media.visual.backend"),
        BackendDescriptor("bytehash", "visual_embedding", "media.visual.backend"),
        BackendDescriptor("clip", "visual_embedding", "media.visual", 'python -m pip install -e ".[visual]"'),
    ]


def collect_model_statuses(config: KGFSConfig) -> list[BackendStatus]:
    statuses: list[BackendStatus] = []
    for name in list_ocr_backends():
        backend = get_ocr_backend(name)
        availability = backend.available(config)
        validation = validate_backend(name, config)
        statuses.append(
            BackendStatus(
                name=name,
                kind="ocr",
                enabled=_ocr_enabled(name, config),
                available=availability.available,
                message=availability.message,
                install_hint=availability.install_hint,
                local_files_only=True,
                download_enabled=_ocr_download_enabled(name, config),
                readiness=validation.readiness.value,
                model_path=validation.model_path,
                notes=["downloads disabled by default"] if not _ocr_download_enabled(name, config) else [],
            )
        )
    statuses.extend(
        [
            _media_backend_status(
                name=config.media.captions.backend,
                kind="caption",
                enabled=config.media.captions.enabled,
                available=_caption_available(config.media.captions.backend),
                dependency=_caption_dependency(config.media.captions.backend),
                local_files_only=config.media.captions.local_files_only,
                download_enabled=config.media.captions.download_enabled,
                config=config,
            ),
            _media_backend_status(
                name=config.media.audio.backend,
                kind="transcription",
                enabled=config.media.audio.enabled and config.media.audio.transcription_enabled,
                available=_audio_available(config.media.audio.backend),
                dependency=_audio_dependency(config.media.audio.backend),
                local_files_only=config.media.audio.local_files_only,
                download_enabled=config.media.audio.download_enabled,
                config=config,
            ),
            _media_backend_status(
                name=config.media.visual.backend,
                kind="visual_embedding",
                enabled=config.media.visual.enabled,
                available=_visual_available(config.media.visual.backend),
                dependency=_visual_dependency(config.media.visual.backend),
                local_files_only=config.media.visual.local_files_only,
                download_enabled=config.media.visual.download_enabled,
                config=config,
            ),
        ]
    )
    return statuses


def _ocr_enabled(name: str, config: KGFSConfig) -> bool:
    if name == "tesseract":
        return config.ocr.enabled and config.ocr.backend == "tesseract"
    if name == "easyocr":
        return config.ocr.easyocr.enabled
    if name == "paddle":
        return config.ocr.paddle.enabled
    return False


def _ocr_download_enabled(name: str, config: KGFSConfig) -> bool:
    if name == "easyocr":
        return config.ocr.easyocr.download_enabled
    if name == "paddle":
        return config.ocr.paddle.download_enabled
    return False


def _media_backend_status(
    *,
    name: str,
    kind: str,
    enabled: bool,
    available: bool,
    dependency: str | None,
    local_files_only: bool,
    download_enabled: bool,
    config: KGFSConfig,
) -> BackendStatus:
    if not enabled:
        message = f"{kind} backend is disabled."
    elif name == "none":
        message = f"No {kind} backend is configured."
    elif available:
        message = f"{kind} backend '{name}' is available."
    elif dependency:
        message = f"{kind} backend '{name}' requires optional dependency '{dependency}'."
    else:
        message = f"{kind} backend '{name}' is unknown."
    validation_name = {
        ("caption", "metadata"): "metadata-caption",
        ("caption", "transformers"): "transformers-caption",
        ("transcription", "faster_whisper"): "faster-whisper",
        ("visual_embedding", "bytehash"): "bytehash-visual",
        ("visual_embedding", "clip"): "clip-visual",
    }.get((kind, name), name)
    if name == "none":
        readiness = "configuration_needed" if enabled else "disabled"
        model_path = None
    else:
        validation = validate_backend(validation_name, config)
        readiness = validation.readiness.value
        model_path = validation.model_path
    return BackendStatus(
        name=name,
        kind=kind,
        enabled=enabled,
        available=available and enabled,
        message=message,
        install_hint=_install_hint(kind, name, dependency),
        local_files_only=local_files_only,
        download_enabled=download_enabled,
        readiness=readiness,
        model_path=model_path,
        notes=["downloads disabled by default"] if not download_enabled else ["downloads explicitly enabled"],
    )


def _caption_available(name: str) -> bool:
    return name in {"metadata"} or (name == "transformers" and find_spec("transformers") is not None)


def _audio_available(name: str) -> bool:
    return name == "faster_whisper" and find_spec("faster_whisper") is not None


def _visual_available(name: str) -> bool:
    return name == "bytehash" or (
        name == "clip" and find_spec("sentence_transformers") is not None and find_spec("PIL") is not None
    )


def _caption_dependency(name: str) -> str | None:
    return "transformers" if name == "transformers" else None


def _audio_dependency(name: str) -> str | None:
    return "faster_whisper" if name == "faster_whisper" else None


def _visual_dependency(name: str) -> str | None:
    return "sentence-transformers + pillow" if name == "clip" else None


def _install_hint(kind: str, name: str, dependency: str | None) -> str | None:
    if not dependency:
        return None
    extras = {"caption": "captions", "transcription": "audio", "visual_embedding": "visual"}
    return f'Install with python -m pip install -e ".[{extras.get(kind, "local-models")}]".'
