"""Lazy OCR backend registry."""

from __future__ import annotations

from kgfs.ocr.base import OCRBackend

KNOWN_BACKENDS = ("tesseract",)


def list_ocr_backends() -> list[str]:
    return list(KNOWN_BACKENDS)


def get_ocr_backend(name: str) -> OCRBackend:
    backend_name = (name or "tesseract").strip().lower()
    if backend_name == "tesseract":
        from kgfs.ocr.tesseract import TesseractOCRBackend

        return TesseractOCRBackend()
    valid = ", ".join(KNOWN_BACKENDS)
    raise ValueError(f"Unknown OCR backend '{name}'. Known OCR backends: {valid}.")
