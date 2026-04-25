"""Image text extraction through optional local OCR."""

from __future__ import annotations

from pathlib import Path

from kgfs.core.config import KGFSConfig
from kgfs.extractors.base import ExtractionResult
from kgfs.ocr.base import OCRRequest
from kgfs.ocr.registry import get_ocr_backend


def extract_image_ocr(path: Path, config: KGFSConfig) -> ExtractionResult:
    try:
        backend = get_ocr_backend(config.ocr.backend)
    except ValueError as exc:
        return ExtractionResult(
            text="",
            status="error",
            error=str(exc),
            metadata={"extraction_source": "ocr", "ocr_source_kind": "image"},
        )
    result = backend.extract_image(OCRRequest(path=path, config=config, source_kind="image"))
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
