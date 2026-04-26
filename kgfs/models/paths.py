"""Path helpers for optional local model backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from kgfs.core.config import KGFSConfig


@dataclass(frozen=True)
class ModelPathInfo:
    backend: str
    label: str
    path: Path | None
    configured: bool
    exists: bool
    readable: bool
    warnings: list[str] = field(default_factory=list)


def default_model_cache_dir(config: KGFSConfig, *, project_root: Path | None = None) -> Path:
    if config.models.cache_dir is not None:
        return config.models.cache_dir.expanduser()
    root = project_root or Path.cwd()
    return root / ".kgfs" / "cache" / "models"


def collect_model_paths(config: KGFSConfig, *, project_root: Path | None = None) -> list[ModelPathInfo]:
    paths: list[ModelPathInfo] = [
        _path_info(
            "kgfs-cache",
            "KGFS model cache",
            default_model_cache_dir(config, project_root=project_root),
            configured=config.models.cache_dir is not None,
            config=config,
        )
    ]
    configured = [
        ("easyocr", "EasyOCR model storage", config.ocr.easyocr.model_storage_directory),
        ("paddle", "PaddleOCR model directory", config.ocr.paddle.model_dir),
        ("transformers-caption", "Transformers caption model", _path_from_model_name(config.media.captions.model_name)),
        ("faster-whisper", "faster-whisper model", _path_from_model_name(config.media.audio.model_name)),
        ("clip-visual", "CLIP visual model", _path_from_model_name(config.media.visual.model_name)),
    ]
    for backend, label, path in configured:
        paths.append(_path_info(backend, label, path, configured=path is not None, config=config))
    return paths


def model_path_for_backend(backend: str, config: KGFSConfig) -> Path | None:
    key = backend.strip().lower()
    if key == "easyocr":
        return config.ocr.easyocr.model_storage_directory
    if key == "paddle":
        return config.ocr.paddle.model_dir
    if key in {"metadata-caption", "metadata", "bytehash-visual", "bytehash", "tesseract"}:
        return None
    if key in {"transformers-caption", "transformers"}:
        return _path_from_model_name(config.media.captions.model_name)
    if key in {"faster-whisper", "faster_whisper"}:
        return _path_from_model_name(config.media.audio.model_name)
    if key in {"clip-visual", "clip"}:
        return _path_from_model_name(config.media.visual.model_name)
    return None


def _path_info(
    backend: str,
    label: str,
    path: Path | None,
    *,
    configured: bool,
    config: KGFSConfig,
) -> ModelPathInfo:
    warnings: list[str] = []
    exists = bool(path and path.exists())
    readable = bool(path and path.exists() and _is_readable(path))
    if path is not None and _inside_indexed_folder(path, config):
        warnings.append("Configured model path is inside indexed folder; prefer KGFS app/cache paths.")
    return ModelPathInfo(
        backend=backend,
        label=label,
        path=path,
        configured=configured,
        exists=exists,
        readable=readable,
        warnings=warnings,
    )


def _path_from_model_name(value: str | None) -> Path | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if any(separator in text for separator in ("/", "\\")) or text.startswith((".", "~")):
        return Path(text).expanduser()
    return None


def _inside_indexed_folder(path: Path, config: KGFSConfig) -> bool:
    try:
        resolved = path.expanduser().resolve()
    except OSError:
        return False
    for folder in config.indexed_folders:
        try:
            folder_resolved = folder.expanduser().resolve()
        except OSError:
            continue
        if resolved == folder_resolved or folder_resolved in resolved.parents:
            return True
    return False


def _is_readable(path: Path) -> bool:
    try:
        if path.is_dir():
            next(path.iterdir(), None)
        else:
            with path.open("rb"):
                pass
    except (OSError, StopIteration):
        return path.exists() and path.is_dir()
    return True
