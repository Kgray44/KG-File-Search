"""Extractor result types."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    status: str
    error: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


def ok(text: str, *, metadata: dict[str, object] | None = None) -> ExtractionResult:
    return ExtractionResult(text=text, status="ok", metadata=metadata or {})


def skipped(reason: str, *, metadata: dict[str, object] | None = None) -> ExtractionResult:
    return ExtractionResult(text="", status="skipped", error=reason, metadata=metadata or {})


def failed(message: str, *, metadata: dict[str, object] | None = None) -> ExtractionResult:
    return ExtractionResult(text="", status="error", error=message, metadata=metadata or {})
