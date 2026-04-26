"""Small OCR backend data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from kgfs.core.config import KGFSConfig


@dataclass(frozen=True)
class OCRAvailability:
    available: bool
    message: str
    install_hint: str | None = None


@dataclass(frozen=True)
class OCRRequest:
    path: Path
    config: KGFSConfig
    source_kind: str = "image"
    page_number: int | None = None


@dataclass(frozen=True)
class OCRResult:
    text: str
    status: str
    error: str | None = None
    backend: str = "tesseract"
    language: str = "eng"
    source_kind: str = "image"
    confidence: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class OCRStatus:
    enabled: bool
    backend_name: str
    available: bool
    message: str
    command: str
    language: str
    supported_extensions: list[str]
    max_image_size_mb: float
    cache_enabled: bool
    cache_entries: int = 0
    cache_size_bytes: int = 0
    indexed_file_count: int = 0
    failure_count: int = 0
    install_hint: str | None = None
    warnings: list[str] = field(default_factory=list)


class OCRBackend(Protocol):
    name: str

    def available(self, config: KGFSConfig) -> OCRAvailability: ...

    def extract_image(self, request: OCRRequest) -> OCRResult: ...
