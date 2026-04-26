"""Optional local image caption backend contract and helpers."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Protocol

from kgfs.core.config import KGFSConfig
from kgfs.media.cache import store_media_text
from kgfs.media.models import MediaTextRecord


@dataclass(frozen=True)
class CaptionStatus:
    enabled: bool
    backend: str
    available: bool
    message: str
    install_hint: str | None = None


@dataclass(frozen=True)
class CaptionResult:
    text: str
    status: str
    error: str | None = None
    backend: str = "none"
    model_name: str | None = None
    confidence: float | None = None


class CaptionBackend(Protocol):
    name: str

    def available(self, config: KGFSConfig) -> tuple[bool, str] | CaptionStatus: ...

    def caption(self, path: Path, config: KGFSConfig) -> CaptionResult: ...


class NoneCaptionBackend:
    name = "none"

    def available(self, config: KGFSConfig) -> tuple[bool, str]:
        return False, "No local image caption backend is configured."

    def caption(self, path: Path, config: KGFSConfig) -> CaptionResult:
        return CaptionResult("", "skipped", "No local image caption backend is configured.", backend=self.name)


class MetadataCaptionBackend:
    """A tiny local caption source based only on filename and image metadata."""

    name = "metadata"

    def available(self, config: KGFSConfig) -> tuple[bool, str]:
        return True, "Metadata-derived image captions are available."

    def caption(self, path: Path, config: KGFSConfig) -> CaptionResult:
        words = path.stem.replace("_", " ").replace("-", " ").strip()
        text = f"Image file {words}" if words else f"Image file {path.name}"
        return CaptionResult(text, "ok", backend=self.name, model_name="metadata")


class TransformersCaptionBackend:
    name = "transformers"

    def available(self, config: KGFSConfig) -> tuple[bool, str]:
        if find_spec("transformers") is None or find_spec("PIL") is None:
            return False, 'Install with python -m pip install -e ".[captions]".'
        if config.media.captions.local_files_only and not config.media.captions.model_name:
            return False, "Set media.captions.model_name to a local model path/name; downloads are disabled by default."
        return True, "Transformers caption backend is available."

    def caption(self, path: Path, config: KGFSConfig) -> CaptionResult:
        ok, message = self.available(config)
        if not ok:
            return CaptionResult("", "skipped", message, backend=self.name, model_name=config.media.captions.model_name)
        try:
            from PIL import Image
            from transformers import pipeline

            image = Image.open(path)
            generator = pipeline(
                "image-to-text",
                model=config.media.captions.model_name,
                local_files_only=config.media.captions.local_files_only,
            )
            rows = generator(image)
        except Exception as exc:  # pragma: no cover - optional model behavior varies
            return CaptionResult("", "error", f"Caption backend failed: {exc}", backend=self.name)
        text = ""
        if rows:
            first = rows[0]
            text = str(first.get("generated_text", "") if isinstance(first, dict) else first).strip()
        return CaptionResult(
            text, "ok" if text else "skipped", backend=self.name, model_name=config.media.captions.model_name
        )


_CAPTION_BACKENDS: dict[str, CaptionBackend] = {
    "none": NoneCaptionBackend(),
    "metadata": MetadataCaptionBackend(),
    "transformers": TransformersCaptionBackend(),
}


def register_caption_backend(name: str, backend: CaptionBackend) -> None:
    _CAPTION_BACKENDS[name.strip().lower()] = backend


def get_caption_backend(name: str) -> CaptionBackend:
    key = (name or "none").strip().lower()
    if key not in _CAPTION_BACKENDS:
        raise ValueError(f"Unknown caption backend '{name}'. Known backends: {', '.join(sorted(_CAPTION_BACKENDS))}.")
    return _CAPTION_BACKENDS[key]


def list_caption_backends() -> list[str]:
    return sorted(_CAPTION_BACKENDS)


def get_caption_status(config: KGFSConfig) -> CaptionStatus:
    backend_name = config.media.captions.backend
    if not config.media.captions.enabled:
        return CaptionStatus(False, backend_name, False, "Image captions are disabled.")
    try:
        backend = get_caption_backend(backend_name)
    except ValueError as exc:
        return CaptionStatus(True, backend_name, False, str(exc))
    available, message = _availability(backend.available(config))
    return CaptionStatus(
        True,
        backend_name,
        available,
        message,
        None if available else _caption_install_hint(backend_name),
    )


def caption_image(path: Path, config: KGFSConfig) -> CaptionResult:
    status = get_caption_status(config)
    if not status.available:
        return CaptionResult("", "skipped", status.message, backend=status.backend)
    return get_caption_backend(status.backend).caption(path, config)


def index_existing_captions(conn: sqlite3.Connection, config: KGFSConfig) -> tuple[int, int]:
    if not config.media.enabled or not config.media.captions.enabled:
        return 0, 0
    indexed = failed = 0
    limit = config.media.captions.max_images_per_run
    extensions = set(config.media.photos.include_extensions)
    rows = _iter_files(conn, extensions, limit)
    for row in rows:
        result = caption_image(Path(row["path"]), config)
        if result.status == "ok" and result.text.strip():
            store_media_text(
                conn,
                MediaTextRecord(
                    file_id=int(row["id"]),
                    source_kind="caption",
                    text=result.text.strip(),
                    backend=result.backend,
                    model_name=result.model_name,
                    confidence=result.confidence,
                    metadata={"status": result.status},
                ),
            )
            indexed += 1
        elif result.status == "error":
            failed += 1
    return indexed, failed


def _iter_files(conn: sqlite3.Connection, extensions: set[str], limit: int) -> list[sqlite3.Row]:
    placeholders = ",".join("?" for _ in extensions)
    if not placeholders:
        return []
    return list(
        conn.execute(
            f"""
            SELECT id, path, extension
            FROM files
            WHERE lower(extension) IN ({placeholders})
            ORDER BY id
            LIMIT ?
            """,
            tuple(sorted(extensions)) + (limit,),
        ).fetchall()
    )


def _availability(value: tuple[bool, str] | CaptionStatus) -> tuple[bool, str]:
    if isinstance(value, CaptionStatus):
        return value.available, value.message
    return bool(value[0]), str(value[1])


def _caption_install_hint(name: str) -> str | None:
    if name == "transformers":
        return 'Install with python -m pip install -e ".[captions]".'
    return None
