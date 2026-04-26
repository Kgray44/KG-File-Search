"""Optional audio transcription scaffold."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kgfs.core.config import KGFSConfig


@dataclass(frozen=True)
class AudioStatus:
    enabled: bool
    backend: str
    available: bool
    message: str
    install_hint: str | None = None


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    status: str
    error: str | None = None
    backend: str = "none"
    model_name: str | None = None
    confidence: float | None = None


def get_audio_status(config: KGFSConfig) -> AudioStatus:
    if not config.media.audio.enabled or not config.media.audio.transcription_enabled:
        return AudioStatus(False, config.media.audio.backend, False, "Audio transcription is disabled.")
    if config.media.audio.backend == "none":
        return AudioStatus(True, "none", False, "No local audio transcription backend is configured.")
    return AudioStatus(
        True,
        config.media.audio.backend,
        False,
        f"Audio backend '{config.media.audio.backend}' is not implemented in this phase.",
        "Install/use a future local transcription backend; base KGFS includes no audio model.",
    )


def transcribe_audio(path: Path, config: KGFSConfig) -> TranscriptionResult:
    status = get_audio_status(config)
    if not status.available:
        return TranscriptionResult("", "skipped", status.message, backend=status.backend)
    return TranscriptionResult("", "skipped", "No audio backend implementation is configured.", backend=status.backend)
