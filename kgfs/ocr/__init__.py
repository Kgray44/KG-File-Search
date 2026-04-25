"""Optional local OCR support for KGFS."""

from kgfs.ocr.base import OCRAvailability, OCRRequest, OCRResult, OCRStatus
from kgfs.ocr.registry import get_ocr_backend, list_ocr_backends

__all__ = [
    "OCRAvailability",
    "OCRRequest",
    "OCRResult",
    "OCRStatus",
    "get_ocr_backend",
    "list_ocr_backends",
]
