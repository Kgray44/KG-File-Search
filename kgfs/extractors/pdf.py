"""PDF extraction using pypdf."""

from __future__ import annotations

from pathlib import Path

from kgfs.extractors.base import ExtractionResult, failed, ok


def extract_pdf(path: Path, *, max_pages: int = 250) -> ExtractionResult:
    try:
        from pypdf import PdfReader
    except ImportError:
        return failed("pypdf is not installed")

    try:
        reader = PdfReader(str(path))
        page_text = []
        for page in reader.pages[:max_pages]:
            page_text.append(page.extract_text() or "")
        return ok("\n".join(page_text))
    except Exception as exc:  # pypdf raises several parser-specific exceptions.
        return failed(str(exc))

