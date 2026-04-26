"""Optional EasyOCR backend scaffold."""

from __future__ import annotations

from importlib.util import find_spec

from kgfs.core.config import KGFSConfig
from kgfs.ocr.base import OCRAvailability, OCRRequest, OCRResult


class EasyOCRBackend:
    name = "easyocr"

    def available(self, config: KGFSConfig) -> OCRAvailability:
        if not config.ocr.easyocr.enabled:
            return OCRAvailability(
                False,
                "EasyOCR backend is disabled.",
                'Install with python -m pip install -e ".[ocr-easyocr]" and enable ocr.easyocr.enabled.',
            )
        if find_spec("easyocr") is None:
            return OCRAvailability(
                False, "EasyOCR is not installed.", 'Install with python -m pip install -e ".[ocr-easyocr]".'
            )
        return OCRAvailability(True, "EasyOCR is available.")

    def extract_image(self, request: OCRRequest) -> OCRResult:
        availability = self.available(request.config)
        if not availability.available:
            return OCRResult(
                "",
                "error",
                availability.message,
                backend=self.name,
                language=",".join(request.config.ocr.easyocr.languages),
            )
        try:
            import easyocr
        except ImportError:
            return OCRResult("", "error", "EasyOCR is not installed.", backend=self.name)
        try:
            reader = easyocr.Reader(request.config.ocr.easyocr.languages, gpu=request.config.ocr.easyocr.gpu)
            rows = reader.readtext(str(request.path), detail=1)
        except Exception as exc:  # pragma: no cover - optional dependency behavior varies
            return OCRResult("", "error", f"EasyOCR failed: {exc}", backend=self.name)
        text_parts = [str(row[1]) for row in rows if len(row) >= 2 and str(row[1]).strip()]
        confidences = [float(row[2]) for row in rows if len(row) >= 3]
        confidence = sum(confidences) / len(confidences) if confidences else None
        return OCRResult(
            "\n".join(text_parts).strip(),
            "ok",
            backend=self.name,
            language=",".join(request.config.ocr.easyocr.languages),
            source_kind=request.source_kind,
            confidence=confidence,
        )
