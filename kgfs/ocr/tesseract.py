"""Local Tesseract OCR backend."""

from __future__ import annotations

import shutil
import subprocess

from kgfs.core.config import KGFSConfig
from kgfs.ocr.base import OCRAvailability, OCRRequest, OCRResult

TESSERACT_INSTALL_HINT = (
    "Install Tesseract locally and put it on PATH, or set ocr.tesseract.command "
    "to the full executable path."
)


class TesseractOCRBackend:
    name = "tesseract"

    def available(self, config: KGFSConfig) -> OCRAvailability:
        command = config.ocr.tesseract.command
        if shutil.which(command):
            return OCRAvailability(True, "Tesseract command is available.")
        return OCRAvailability(
            False,
            f"Tesseract command not found: {command}",
            install_hint=TESSERACT_INSTALL_HINT,
        )

    def extract_image(self, request: OCRRequest) -> OCRResult:
        command = request.config.ocr.tesseract.command
        language = request.config.ocr.tesseract.language
        args = [command, str(request.path), "stdout", "-l", language]
        try:
            completed = subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
        except FileNotFoundError:
            return OCRResult(
                text="",
                status="error",
                error=f"Tesseract command not found: {command}. {TESSERACT_INSTALL_HINT}",
                backend=self.name,
                language=language,
                source_kind=request.source_kind,
            )
        except subprocess.TimeoutExpired:
            return OCRResult(
                text="",
                status="error",
                error="Tesseract OCR timed out.",
                backend=self.name,
                language=language,
                source_kind=request.source_kind,
            )
        except OSError as exc:
            return OCRResult(
                text="",
                status="error",
                error=f"Tesseract OCR failed to start: {exc}",
                backend=self.name,
                language=language,
                source_kind=request.source_kind,
            )

        if completed.returncode != 0:
            message = (completed.stderr or completed.stdout or "Tesseract OCR failed.").strip()
            return OCRResult(
                text="",
                status="error",
                error=message,
                backend=self.name,
                language=language,
                source_kind=request.source_kind,
            )

        return OCRResult(
            text=completed.stdout.strip(),
            status="ok",
            backend=self.name,
            language=language,
            source_kind=request.source_kind,
        )
