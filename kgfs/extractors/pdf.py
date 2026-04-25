"""PDF extraction using pypdf."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from kgfs.extractors.base import ExtractionResult, failed, ok

if TYPE_CHECKING:
    from kgfs.core.config import KGFSConfig


def extract_pdf(path: Path, *, max_pages: int = 250, config: "KGFSConfig | None" = None) -> ExtractionResult:
    try:
        from pypdf import PdfReader
    except ImportError:
        return failed("pypdf is not installed")

    try:
        reader = PdfReader(str(path))
        page_text = []
        for page in reader.pages[:max_pages]:
            page_text.append(page.extract_text() or "")
        text = "\n".join(page_text)
        if config is not None and config.ocr.enabled and len(text.strip()) < config.ocr.min_pdf_text_chars:
            from kgfs.ocr.pdf import extract_scanned_pdf

            result = extract_scanned_pdf(path, config)
            return ExtractionResult(
                text=result.text,
                status=result.status,
                error=result.error,
                metadata={
                    "extraction_source": "ocr",
                    "ocr_backend": result.backend,
                    "ocr_language": result.language,
                    "ocr_source_kind": result.source_kind,
                    **result.metadata,
                },
            )
        return ok(text)
    except Exception as exc:  # pypdf raises several parser-specific exceptions.
        return failed(str(exc))
