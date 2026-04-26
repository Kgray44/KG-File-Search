"""Optional local audio transcription backend contract and helpers."""

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


class AudioTranscriptionBackend(Protocol):
    name: str

    def available(self, config: KGFSConfig) -> tuple[bool, str] | AudioStatus: ...

    def transcribe(self, path: Path, config: KGFSConfig) -> TranscriptionResult: ...


class NoneAudioBackend:
    name = "none"

    def available(self, config: KGFSConfig) -> tuple[bool, str]:
        return False, "No local audio transcription backend is configured."

    def transcribe(self, path: Path, config: KGFSConfig) -> TranscriptionResult:
        return TranscriptionResult(
            "", "skipped", "No local audio transcription backend is configured.", backend=self.name
        )


class FasterWhisperBackend:
    name = "faster_whisper"

    def available(self, config: KGFSConfig) -> tuple[bool, str]:
        if find_spec("faster_whisper") is None:
            return False, 'Install with python -m pip install -e ".[audio]".'
        if config.media.audio.local_files_only and not config.media.audio.model_name:
            return False, "Set media.audio.model_name to a local model path/name; downloads are disabled by default."
        return True, "faster-whisper backend is available."

    def transcribe(self, path: Path, config: KGFSConfig) -> TranscriptionResult:
        ok, message = self.available(config)
        if not ok:
            return TranscriptionResult(
                "", "skipped", message, backend=self.name, model_name=config.media.audio.model_name
            )
        try:
            from faster_whisper import WhisperModel

            model = WhisperModel(config.media.audio.model_name, local_files_only=config.media.audio.local_files_only)
            segments, _ = model.transcribe(str(path))
            text = "\n".join(segment.text.strip() for segment in segments if segment.text.strip())
        except Exception as exc:  # pragma: no cover - optional model behavior varies
            return TranscriptionResult("", "error", f"Audio transcription failed: {exc}", backend=self.name)
        return TranscriptionResult(
            text, "ok" if text else "skipped", backend=self.name, model_name=config.media.audio.model_name
        )


_AUDIO_BACKENDS: dict[str, AudioTranscriptionBackend] = {
    "none": NoneAudioBackend(),
    "faster_whisper": FasterWhisperBackend(),
}


def register_audio_backend(name: str, backend: AudioTranscriptionBackend) -> None:
    _AUDIO_BACKENDS[name.strip().lower()] = backend


def get_audio_backend(name: str) -> AudioTranscriptionBackend:
    key = (name or "none").strip().lower()
    if key not in _AUDIO_BACKENDS:
        raise ValueError(f"Unknown audio backend '{name}'. Known backends: {', '.join(sorted(_AUDIO_BACKENDS))}.")
    return _AUDIO_BACKENDS[key]


def list_audio_backends() -> list[str]:
    return sorted(_AUDIO_BACKENDS)


def get_audio_status(config: KGFSConfig) -> AudioStatus:
    backend_name = config.media.audio.backend
    if not config.media.audio.enabled or not config.media.audio.transcription_enabled:
        return AudioStatus(False, backend_name, False, "Audio transcription is disabled.")
    try:
        backend = get_audio_backend(backend_name)
    except ValueError as exc:
        return AudioStatus(True, backend_name, False, str(exc))
    available, message = _availability(backend.available(config))
    return AudioStatus(True, backend_name, available, message, None if available else _audio_install_hint(backend_name))


def transcribe_audio(path: Path, config: KGFSConfig) -> TranscriptionResult:
    status = get_audio_status(config)
    if not status.available:
        return TranscriptionResult("", "skipped", status.message, backend=status.backend)
    return get_audio_backend(status.backend).transcribe(path, config)


def index_existing_transcripts(conn: sqlite3.Connection, config: KGFSConfig) -> tuple[int, int]:
    if not config.media.enabled or not config.media.audio.enabled or not config.media.audio.transcription_enabled:
        return 0, 0
    indexed = failed = 0
    rows = _iter_files(conn, set(config.media.audio.include_extensions))
    for row in rows:
        result = transcribe_audio(Path(row["path"]), config)
        if result.status == "ok" and result.text.strip():
            store_media_text(
                conn,
                MediaTextRecord(
                    file_id=int(row["id"]),
                    source_kind="transcript",
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


def _iter_files(conn: sqlite3.Connection, extensions: set[str]) -> list[sqlite3.Row]:
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
            """,
            tuple(sorted(extensions)),
        ).fetchall()
    )


def _availability(value: tuple[bool, str] | AudioStatus) -> tuple[bool, str]:
    if isinstance(value, AudioStatus):
        return value.available, value.message
    return bool(value[0]), str(value[1])


def _audio_install_hint(name: str) -> str | None:
    if name == "faster_whisper":
        return 'Install with python -m pip install -e ".[audio]".'
    return None
