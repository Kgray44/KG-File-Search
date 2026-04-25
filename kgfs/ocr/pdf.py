"""Scanned PDF OCR fallback helpers."""

from __future__ import annotations

from pathlib import Path

from kgfs.core.config import KGFSConfig
from kgfs.ocr.base import OCRResult


def extract_scanned_pdf(path: Path, config: KGFSConfig) -> OCRResult:
    """Return a safe, local-only placeholder for scanned PDF OCR.

    Tesseract works on images directly. Rasterizing PDF pages safely and
    cross-platform needs an optional renderer, so Phase 5 reports a helpful
    message instead of pretending scanned PDFs were processed.
    """

    return OCRResult(
        text="",
        status="error",
        error=(
            "This PDF appears to have little extractable text. Scanned PDF OCR "
            "requires a PDF rasterization helper before Tesseract can read pages; "
            "the original PDF was not modified."
        ),
        backend=config.ocr.backend,
        language=config.ocr.tesseract.language,
        source_kind="pdf",
        metadata={"scanned_pdf_candidate": True},
    )
