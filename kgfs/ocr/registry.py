"""Lazy OCR backend registry."""

from __future__ import annotations

from kgfs.ocr.base import OCRBackend

KNOWN_BACKENDS = ("tesseract", "easyocr", "paddle")


def list_ocr_backends() -> list[str]:
    return list(KNOWN_BACKENDS)


def get_ocr_backend(name: str) -> OCRBackend:
    backend_name = (name or "tesseract").strip().lower()
    if backend_name == "tesseract":
        from kgfs.ocr.tesseract import TesseractOCRBackend

        return TesseractOCRBackend()
    if backend_name == "easyocr":
        from kgfs.ocr.easyocr import EasyOCRBackend

        return EasyOCRBackend()
    if backend_name == "paddle":
        from kgfs.ocr.paddle import PaddleOCRBackend

        return PaddleOCRBackend()
    valid = ", ".join(KNOWN_BACKENDS)
    raise ValueError(f"Unknown OCR backend '{name}'. Known OCR backends: {valid}.")
