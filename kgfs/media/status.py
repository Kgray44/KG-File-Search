"""Status helpers for optional local media features."""

from __future__ import annotations

import sqlite3
from importlib.util import find_spec

from kgfs.core.config import KGFSConfig
from kgfs.media.audio import get_audio_status
from kgfs.media.cache import media_counts
from kgfs.media.captions import get_caption_status
from kgfs.media.models import MediaStatus
from kgfs.media.visual import get_visual_status


def get_media_status(config: KGFSConfig, conn: sqlite3.Connection | None = None) -> MediaStatus:
    caption = get_caption_status(config)
    audio = get_audio_status(config)
    visual = get_visual_status(config)
    counts = {"media_metadata": 0, "media_text": 0, "media_embeddings": 0, "cache_size_bytes": 0}
    if conn is not None:
        counts.update(media_counts(conn))
    warnings: list[str] = []
    if config.media.photos.store_location_metadata:
        warnings.append(f"Photo location metadata storage is enabled ({config.media.photos.location_precision}).")
    if config.ocr.cloud_fallback.enabled:
        warnings.append("Cloud OCR fallback is enabled in config and still requires explicit command confirmation.")
    return MediaStatus(
        enabled=config.media.enabled,
        photo_metadata_enabled=config.media.enabled and config.media.photos.enabled and config.media.photos.index_exif,
        exif_available=find_spec("PIL") is not None,
        caption_backend=config.media.captions.backend,
        caption_available=caption.available,
        audio_backend=config.media.audio.backend,
        audio_available=audio.available,
        visual_backend=config.media.visual.backend,
        visual_available=visual.available,
        cloud_fallback_enabled=config.ocr.cloud_fallback.enabled,
        media_metadata_count=counts["media_metadata"],
        media_text_count=counts["media_text"],
        media_embedding_count=counts["media_embeddings"],
        cache_size_bytes=counts["cache_size_bytes"],
        warnings=warnings,
    )
