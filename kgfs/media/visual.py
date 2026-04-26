"""Optional visual embedding/search scaffold."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kgfs.core.config import KGFSConfig


@dataclass(frozen=True)
class VisualStatus:
    enabled: bool
    backend: str
    available: bool
    message: str
    install_hint: str | None = None


@dataclass(frozen=True)
class VisualEmbeddingResult:
    vector: list[float]
    status: str
    error: str | None = None
    backend: str = "none"
    model_name: str | None = None


def get_visual_status(config: KGFSConfig) -> VisualStatus:
    if not config.media.visual.enabled:
        return VisualStatus(False, config.media.visual.backend, False, "Visual semantic search is disabled.")
    if config.media.visual.backend == "none":
        return VisualStatus(True, "none", False, "No local visual embedding backend is configured.")
    return VisualStatus(
        True,
        config.media.visual.backend,
        False,
        f"Visual backend '{config.media.visual.backend}' is not implemented in this phase.",
        "Install/use a future local visual embedding backend; base KGFS includes no visual model.",
    )


def visual_embedding_for_file(path: Path, config: KGFSConfig) -> VisualEmbeddingResult:
    status = get_visual_status(config)
    if not status.available:
        return VisualEmbeddingResult([], "skipped", status.message, backend=status.backend)
    return VisualEmbeddingResult([], "skipped", "No visual backend implementation is configured.", backend=status.backend)
