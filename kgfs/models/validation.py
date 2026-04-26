"""Validation and readiness checks for optional local model backends."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from enum import StrEnum
from importlib.util import find_spec
from pathlib import Path

from kgfs.core.config import KGFSConfig
from kgfs.models.paths import model_path_for_backend


class BackendReadiness(StrEnum):
    DISABLED = "disabled"
    READY = "ready"
    MISSING_DEPENDENCY = "missing_dependency"
    MISSING_MODEL = "missing_model"
    CONFIGURATION_NEEDED = "configuration_needed"
    SCAFFOLD = "scaffold"
    ERROR = "error"


@dataclass(frozen=True)
class BackendValidation:
    backend: str
    internal_backend: str
    kind: str
    enabled: bool
    readiness: BackendReadiness
    dependency_available: bool
    model_path: Path | None = None
    local_files_only: bool = True
    download_enabled: bool = False
    install_hint: str | None = None
    messages: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def known_backend_aliases() -> list[str]:
    return [
        "tesseract",
        "easyocr",
        "paddle",
        "metadata-caption",
        "transformers-caption",
        "faster-whisper",
        "bytehash-visual",
        "clip-visual",
    ]


def validate_all_backends(config: KGFSConfig) -> list[BackendValidation]:
    return [validate_backend(name, config) for name in known_backend_aliases()]


def validate_backend(backend: str, config: KGFSConfig) -> BackendValidation:
    alias = _alias(backend)
    if alias == "tesseract":
        return _validate_tesseract(config)
    if alias == "easyocr":
        return _validate_easyocr(config)
    if alias == "paddle":
        return _validate_paddle(config)
    if alias == "metadata-caption":
        return _validate_metadata_caption(config)
    if alias == "transformers-caption":
        return _validate_transformers_caption(config)
    if alias == "faster-whisper":
        return _validate_faster_whisper(config)
    if alias == "bytehash-visual":
        return _validate_bytehash_visual(config)
    if alias == "clip-visual":
        return _validate_clip_visual(config)
    return BackendValidation(
        backend=backend,
        internal_backend=backend,
        kind="unknown",
        enabled=False,
        readiness=BackendReadiness.ERROR,
        dependency_available=False,
        messages=[f"Unknown backend '{backend}'."],
    )


def _validate_tesseract(config: KGFSConfig) -> BackendValidation:
    enabled = config.ocr.enabled and config.ocr.backend == "tesseract"
    dependency = shutil.which(config.ocr.tesseract.command) is not None or Path(config.ocr.tesseract.command).exists()
    readiness = _disabled_or(enabled, BackendReadiness.READY if dependency else BackendReadiness.MISSING_DEPENDENCY)
    return BackendValidation(
        backend="tesseract",
        internal_backend="tesseract",
        kind="ocr",
        enabled=enabled,
        readiness=readiness,
        dependency_available=dependency,
        install_hint=None if dependency else "Install Tesseract locally or set ocr.tesseract.command.",
        messages=["Tesseract executable is configured." if dependency else "Tesseract executable was not found."],
    )


def _validate_easyocr(config: KGFSConfig) -> BackendValidation:
    enabled = config.ocr.easyocr.enabled or (config.ocr.enabled and config.ocr.backend == "easyocr")
    dependency = find_spec("easyocr") is not None
    model_path = config.ocr.easyocr.model_storage_directory
    messages = [_download_message(config.ocr.easyocr.download_enabled)]
    if not enabled:
        readiness = BackendReadiness.DISABLED
    elif not dependency:
        readiness = BackendReadiness.MISSING_DEPENDENCY
    elif not config.ocr.easyocr.download_enabled and model_path is None:
        readiness = BackendReadiness.MISSING_MODEL
        messages.append("Set ocr.easyocr.model_storage_directory to local model files.")
    elif model_path is not None and not model_path.exists():
        readiness = BackendReadiness.MISSING_MODEL
        messages.append(f"Configured model path does not exist: {model_path}")
    else:
        readiness = BackendReadiness.READY
    return BackendValidation(
        backend="easyocr",
        internal_backend="easyocr",
        kind="ocr",
        enabled=enabled,
        readiness=readiness,
        dependency_available=dependency,
        model_path=model_path,
        download_enabled=config.ocr.easyocr.download_enabled,
        install_hint='python -m pip install -e ".[ocr-easyocr]"',
        messages=messages,
        warnings=_path_warnings(model_path, config),
    )


def _validate_paddle(config: KGFSConfig) -> BackendValidation:
    enabled = config.ocr.paddle.enabled or (config.ocr.enabled and config.ocr.backend == "paddle")
    dependency = find_spec("paddleocr") is not None
    model_path = config.ocr.paddle.model_dir
    messages = [_download_message(config.ocr.paddle.download_enabled)]
    if not enabled:
        readiness = BackendReadiness.DISABLED
    elif not dependency:
        readiness = BackendReadiness.MISSING_DEPENDENCY
    elif not config.ocr.paddle.download_enabled and model_path is None:
        readiness = BackendReadiness.MISSING_MODEL
        messages.append("Set ocr.paddle.model_dir to local PaddleOCR model files.")
    elif model_path is not None and not model_path.exists():
        readiness = BackendReadiness.MISSING_MODEL
        messages.append(f"Configured model path does not exist: {model_path}")
    else:
        readiness = BackendReadiness.READY
    return BackendValidation(
        backend="paddle",
        internal_backend="paddle",
        kind="ocr",
        enabled=enabled,
        readiness=readiness,
        dependency_available=dependency,
        model_path=model_path,
        download_enabled=config.ocr.paddle.download_enabled,
        install_hint='python -m pip install -e ".[ocr-paddle]"',
        messages=messages,
        warnings=_path_warnings(model_path, config),
    )


def _validate_metadata_caption(config: KGFSConfig) -> BackendValidation:
    enabled = config.media.enabled and config.media.captions.enabled and config.media.captions.backend == "metadata"
    return BackendValidation(
        backend="metadata-caption",
        internal_backend="metadata",
        kind="caption",
        enabled=enabled,
        readiness=_disabled_or(enabled, BackendReadiness.READY),
        dependency_available=True,
        messages=["Metadata captions use filename/metadata only; no visual understanding."],
    )


def _validate_transformers_caption(config: KGFSConfig) -> BackendValidation:
    enabled = config.media.enabled and config.media.captions.enabled and config.media.captions.backend == "transformers"
    dependency = find_spec("transformers") is not None and find_spec("PIL") is not None
    model_path = model_path_for_backend("transformers-caption", config)
    readiness = _model_backend_readiness(
        enabled=enabled,
        dependency=dependency,
        model_name=config.media.captions.model_name,
        model_path=model_path,
        local_files_only=config.media.captions.local_files_only,
    )
    return BackendValidation(
        backend="transformers-caption",
        internal_backend="transformers",
        kind="caption",
        enabled=enabled,
        readiness=readiness,
        dependency_available=dependency,
        model_path=model_path,
        local_files_only=config.media.captions.local_files_only,
        download_enabled=config.media.captions.download_enabled,
        install_hint='python -m pip install -e ".[captions]"',
        messages=[_download_message(config.media.captions.download_enabled)],
        warnings=_path_warnings(model_path, config),
    )


def _validate_faster_whisper(config: KGFSConfig) -> BackendValidation:
    enabled = (
        config.media.enabled
        and config.media.audio.enabled
        and config.media.audio.transcription_enabled
        and config.media.audio.backend == "faster_whisper"
    )
    dependency = find_spec("faster_whisper") is not None
    model_path = model_path_for_backend("faster-whisper", config)
    readiness = _model_backend_readiness(
        enabled=enabled,
        dependency=dependency,
        model_name=config.media.audio.model_name,
        model_path=model_path,
        local_files_only=config.media.audio.local_files_only,
    )
    return BackendValidation(
        backend="faster-whisper",
        internal_backend="faster_whisper",
        kind="transcription",
        enabled=enabled,
        readiness=readiness,
        dependency_available=dependency,
        model_path=model_path,
        local_files_only=config.media.audio.local_files_only,
        download_enabled=config.media.audio.download_enabled,
        install_hint='python -m pip install -e ".[audio]"',
        messages=[_download_message(config.media.audio.download_enabled)],
        warnings=_path_warnings(model_path, config),
    )


def _validate_bytehash_visual(config: KGFSConfig) -> BackendValidation:
    enabled = config.media.enabled and config.media.visual.enabled and config.media.visual.backend == "bytehash"
    return BackendValidation(
        backend="bytehash-visual",
        internal_backend="bytehash",
        kind="visual_embedding",
        enabled=enabled,
        readiness=_disabled_or(enabled, BackendReadiness.READY),
        dependency_available=True,
        messages=["Bytehash is deterministic plumbing only, not visual understanding."],
    )


def _validate_clip_visual(config: KGFSConfig) -> BackendValidation:
    enabled = config.media.enabled and config.media.visual.enabled and config.media.visual.backend == "clip"
    dependency = find_spec("sentence_transformers") is not None and find_spec("PIL") is not None
    model_path = model_path_for_backend("clip-visual", config)
    readiness = _model_backend_readiness(
        enabled=enabled,
        dependency=dependency,
        model_name=config.media.visual.model_name,
        model_path=model_path,
        local_files_only=config.media.visual.local_files_only,
    )
    return BackendValidation(
        backend="clip-visual",
        internal_backend="clip",
        kind="visual_embedding",
        enabled=enabled,
        readiness=readiness,
        dependency_available=dependency,
        model_path=model_path,
        local_files_only=config.media.visual.local_files_only,
        download_enabled=config.media.visual.download_enabled,
        install_hint='python -m pip install -e ".[visual]"',
        messages=[_download_message(config.media.visual.download_enabled)],
        warnings=_path_warnings(model_path, config),
    )


def _model_backend_readiness(
    *,
    enabled: bool,
    dependency: bool,
    model_name: str | None,
    model_path: Path | None,
    local_files_only: bool,
) -> BackendReadiness:
    if not enabled:
        return BackendReadiness.DISABLED
    if not dependency:
        return BackendReadiness.MISSING_DEPENDENCY
    if local_files_only and not model_name:
        return BackendReadiness.MISSING_MODEL
    if model_path is not None and not model_path.exists():
        return BackendReadiness.MISSING_MODEL
    return BackendReadiness.READY


def _disabled_or(enabled: bool, readiness: BackendReadiness) -> BackendReadiness:
    return readiness if enabled else BackendReadiness.DISABLED


def _download_message(enabled: bool) -> str:
    return "downloads explicitly enabled" if enabled else "downloads disabled by default"


def _path_warnings(path: Path | None, config: KGFSConfig) -> list[str]:
    if path is None:
        return []
    try:
        resolved = path.expanduser().resolve()
    except OSError:
        return []
    for folder in config.indexed_folders:
        try:
            folder_resolved = folder.expanduser().resolve()
        except OSError:
            continue
        if resolved == folder_resolved or folder_resolved in resolved.parents:
            return ["configured model path is inside indexed folder"]
    return []


def _alias(backend: str) -> str:
    key = backend.strip().lower().replace("_", "-")
    aliases = {
        "metadata": "metadata-caption",
        "transformers": "transformers-caption",
        "faster-whisper": "faster-whisper",
        "bytehash": "bytehash-visual",
        "clip": "clip-visual",
    }
    return aliases.get(key, key)
