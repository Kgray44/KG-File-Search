"""Common data structures for optional local model backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from kgfs.core.config import KGFSConfig


@dataclass(frozen=True)
class BackendAvailability:
    available: bool
    message: str
    install_hint: str | None = None


@dataclass(frozen=True)
class BackendDescriptor:
    name: str
    kind: str
    config_key: str
    install_hint: str | None = None
    experimental: bool = False


@dataclass(frozen=True)
class BackendStatus:
    name: str
    kind: str
    enabled: bool
    available: bool
    message: str
    install_hint: str | None = None
    local_files_only: bool = True
    download_enabled: bool = False
    readiness: str = "disabled"
    model_path: Path | None = None
    cache_path: Path | None = None
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BackendBenchmarkResult:
    name: str
    kind: str
    available: bool
    elapsed_ms: float | None
    notes: str


class LocalModelBackend(Protocol):
    name: str
    kind: str

    def status(self, config: KGFSConfig) -> BackendStatus: ...
