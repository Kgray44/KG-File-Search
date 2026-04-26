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
        if not config.ocr.paddle.download_enabled and config.ocr.paddle.model_dir is None:
            return OCRAvailability(
                False,
                "PaddleOCR downloads are disabled and ocr.paddle.model_dir is not set.",
                "Set ocr.paddle.model_dir to local PaddleOCR model files or explicitly enable downloads.",
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
            engine_kwargs: dict[str, object] = {
                "lang": request.config.ocr.paddle.language,
                "use_angle_cls": request.config.ocr.paddle.use_angle_cls,
                "use_gpu": request.config.ocr.paddle.use_gpu,
                "download_enabled": request.config.ocr.paddle.download_enabled,
                "show_log": False,
            }
            if request.config.ocr.paddle.model_dir is not None:
                model_dir = str(request.config.ocr.paddle.model_dir)
                engine_kwargs["det_model_dir"] = model_dir
                engine_kwargs["rec_model_dir"] = model_dir
                engine_kwargs["cls_model_dir"] = model_dir
            try:
                engine = PaddleOCR(**engine_kwargs)
            except TypeError as exc:
                if "download_enabled" not in str(exc):
                    raise
                engine_kwargs.pop("download_enabled", None)
                engine = PaddleOCR(**engine_kwargs)
            rows = engine.ocr(str(request.path), cls=request.config.ocr.paddle.use_angle_cls)
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
