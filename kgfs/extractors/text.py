"""Plain text extraction."""

from __future__ import annotations

from pathlib import Path

from kgfs.extractors.base import ExtractionResult, failed, ok


def extract_plain_text(path: Path) -> ExtractionResult:
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return ok(path.read_text(encoding=encoding))
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            return failed(str(exc))
    return failed("Unable to decode text file")

