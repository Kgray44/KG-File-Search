"""Optional image captioning scaffold."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kgfs.core.config import KGFSConfig


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


def get_caption_status(config: KGFSConfig) -> CaptionStatus:
    if not config.media.captions.enabled:
        return CaptionStatus(False, config.media.captions.backend, False, "Image captions are disabled.")
    if config.media.captions.backend == "none":
        return CaptionStatus(True, "none", False, "No local caption backend is configured.")
    return CaptionStatus(
        True,
        config.media.captions.backend,
        False,
        f"Caption backend '{config.media.captions.backend}' is not implemented in this phase.",
        "Use a future local caption backend; no heavy caption dependency is included in base KGFS.",
    )


def caption_image(path: Path, config: KGFSConfig) -> CaptionResult:
    status = get_caption_status(config)
    if not status.available:
        return CaptionResult("", "skipped", status.message, backend=status.backend)
    return CaptionResult("", "skipped", "No caption backend implementation is configured.", backend=status.backend)
