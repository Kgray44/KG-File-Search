"""Local photo/EXIF metadata helpers."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kgfs.core.config import KGFSConfig
from kgfs.media.cache import dumps_json, store_media_text, utc_now
from kgfs.media.models import MediaTextRecord


@dataclass(frozen=True)
class PhotoMetadata:
    media_kind: str = "image"
    width: int | None = None
    height: int | None = None
    camera_make: str | None = None
    camera_model: str | None = None
    captured_at: str | None = None
    duration_seconds: float | None = None
    gps_latitude: float | None = None
    gps_longitude: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)


def extract_exif_metadata(path: Path) -> PhotoMetadata:
    """Read basic image metadata locally when Pillow is available."""

    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow is not installed; install the optional media/photo extra to read EXIF.") from exc

    with Image.open(path) as image:
        width, height = image.size
        exif = image.getexif()
        metadata: dict[str, object] = {}
        if exif:
            try:
                from PIL.ExifTags import TAGS
            except ImportError:
                TAGS = {}
            for key, value in exif.items():
                name = TAGS.get(key, str(key))
                if isinstance(value, bytes):
                    continue
                metadata[str(name)] = str(value)
        return PhotoMetadata(
            width=width,
            height=height,
            camera_make=_string_or_none(metadata.get("Make")),
            camera_model=_string_or_none(metadata.get("Model")),
            captured_at=_string_or_none(metadata.get("DateTimeOriginal") or metadata.get("DateTime")),
            metadata=metadata,
        )


def store_photo_metadata(conn: sqlite3.Connection, config: KGFSConfig, *, file_id: int, metadata: PhotoMetadata) -> str:
    location_text, location_precision = _location_fields(config, metadata)
    safe_metadata = _safe_metadata(metadata.metadata)
    now = utc_now()
    conn.execute(
        """
        INSERT INTO media_metadata(
            file_id, media_kind, width, height, duration_seconds, camera_make,
            camera_model, captured_at, location_text, location_precision,
            metadata_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(file_id) DO UPDATE SET
            media_kind = excluded.media_kind,
            width = excluded.width,
            height = excluded.height,
            duration_seconds = excluded.duration_seconds,
            camera_make = excluded.camera_make,
            camera_model = excluded.camera_model,
            captured_at = excluded.captured_at,
            location_text = excluded.location_text,
            location_precision = excluded.location_precision,
            metadata_json = excluded.metadata_json,
            updated_at = excluded.updated_at
        """,
        (
            file_id,
            metadata.media_kind,
            metadata.width,
            metadata.height,
            metadata.duration_seconds,
            metadata.camera_make,
            metadata.camera_model,
            metadata.captured_at,
            location_text,
            location_precision,
            dumps_json(safe_metadata),
            now,
            now,
        ),
    )
    text = photo_metadata_text(metadata, location_text=location_text)
    if text:
        conn.execute("DELETE FROM media_text WHERE file_id = ? AND source_kind = 'exif'", (file_id,))
        store_media_text(
            conn,
            MediaTextRecord(
                file_id=file_id,
                source_kind="exif",
                backend="exif",
                text=text,
                metadata={"location_precision": location_precision},
            ),
        )
    conn.commit()
    return text


def photo_metadata_text(metadata: PhotoMetadata, *, location_text: str | None = None) -> str:
    parts: list[str] = ["EXIF photo metadata"]
    if metadata.camera_make:
        parts.append(str(metadata.camera_make))
    if metadata.camera_model:
        parts.append(str(metadata.camera_model))
    if metadata.width and metadata.height:
        parts.append(f"{metadata.width}x{metadata.height}")
    if metadata.captured_at:
        parts.append(str(metadata.captured_at))
    if location_text:
        parts.append(location_text)
    for key, value in sorted(_safe_metadata(metadata.metadata).items()):
        if value not in (None, ""):
            parts.append(f"{key}: {value}")
    return "\n".join(dict.fromkeys(str(part) for part in parts if str(part).strip()))


def _location_fields(config: KGFSConfig, metadata: PhotoMetadata) -> tuple[str | None, str]:
    if not config.media.photos.store_location_metadata:
        return None, "none"
    if metadata.gps_latitude is None or metadata.gps_longitude is None:
        return None, config.media.photos.location_precision
    if config.media.photos.location_precision == "exact":
        return f"{metadata.gps_latitude:.6f},{metadata.gps_longitude:.6f}", "exact"
    if config.media.photos.location_precision == "coarse":
        return f"{round(metadata.gps_latitude, 1):.1f},{round(metadata.gps_longitude, 1):.1f}", "coarse"
    return None, "none"


def _safe_metadata(value: dict[str, Any]) -> dict[str, object]:
    safe: dict[str, object] = {}
    for key, item in value.items():
        lowered = str(key).lower()
        if "gps" in lowered or "location" in lowered or "latitude" in lowered or "longitude" in lowered:
            continue
        safe[str(key)] = item
    return safe


def _string_or_none(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None
