"""Extractor result types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    status: str
    error: str | None = None


def ok(text: str) -> ExtractionResult:
    return ExtractionResult(text=text, status="ok")


def skipped(reason: str) -> ExtractionResult:
    return ExtractionResult(text="", status="skipped", error=reason)


def failed(message: str) -> ExtractionResult:
    return ExtractionResult(text="", status="error", error=message)

