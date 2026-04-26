"""Optional PaddleOCR backend scaffold."""

from __future__ import annotations

from importlib.util import find_spec

from kgfs.core.config import KGFSConfig
from kgfs.ocr.base import OCRAvailability, OCRRequest, OCRResult


class PaddleOCRBackend:
    name = "paddle"

    def available(self, config: KGFSConfig) -> OCRAvailability:
        if not config.ocr.paddle.enabled:
            return OCRAvailability(
                False,
                "PaddleOCR backend is disabled.",
                'Install with python -m pip install -e ".[ocr-paddle]" and enable ocr.paddle.enabled.',
            )
        if find_spec("paddleocr") is None:
            return OCRAvailability(
                False, "PaddleOCR is not installed.", 'Install with python -m pip install -e ".[ocr-paddle]".'
            )
        return OCRAvailability(True, "PaddleOCR is available.")

    def extract_image(self, request: OCRRequest) -> OCRResult:
        availability = self.available(request.config)
        if not availability.available:
            return OCRResult(
                "", "error", availability.message, backend=self.name, language=request.config.ocr.paddle.language
            )
        try:
            from paddleocr import PaddleOCR
        except ImportError:
            return OCRResult("", "error", "PaddleOCR is not installed.", backend=self.name)
        try:
            engine = PaddleOCR(lang=request.config.ocr.paddle.language, show_log=False)
            rows = engine.ocr(str(request.path), cls=False)
        except Exception as exc:  # pragma: no cover - optional dependency behavior varies
            return OCRResult("", "error", f"PaddleOCR failed: {exc}", backend=self.name)
        text_parts: list[str] = []
        confidences: list[float] = []
        for page in rows or []:
            for item in page or []:
                if len(item) >= 2 and isinstance(item[1], (tuple, list)):
                    text_parts.append(str(item[1][0]))
                    if len(item[1]) > 1:
                        confidences.append(float(item[1][1]))
        confidence = sum(confidences) / len(confidences) if confidences else None
        return OCRResult(
            "\n".join(part for part in text_parts if part.strip()).strip(),
            "ok",
            backend=self.name,
            language=request.config.ocr.paddle.language,
            source_kind=request.source_kind,
            confidence=confidence,
        )
