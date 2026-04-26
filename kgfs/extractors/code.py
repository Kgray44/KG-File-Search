"""Source code extraction."""

from __future__ import annotations

from pathlib import Path

from kgfs.extractors.base import ExtractionResult
from kgfs.extractors.text import extract_plain_text


def extract_code(path: Path) -> ExtractionResult:
    return extract_plain_text(path)
