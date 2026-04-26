"""Small media dataclasses used by optional local media features."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MediaStatus:
    enabled: bool
    photo_metadata_enabled: bool
    exif_available: bool
    caption_backend: str
    caption_available: bool
    audio_backend: str
    audio_available: bool
    visual_backend: str
    visual_available: bool
    cloud_fallback_enabled: bool
    media_metadata_count: int = 0
    media_text_count: int = 0
    media_embedding_count: int = 0
    cache_size_bytes: int = 0
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MediaTextRecord:
    file_id: int
    source_kind: str
    text: str
    backend: str | None = None
    model_name: str | None = None
    confidence: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)
