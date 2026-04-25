from __future__ import annotations

import subprocess
from pathlib import Path

from kgfs.config import KGFSConfig, OCRSettings, TesseractOCRSettings
from kgfs.ocr.base import OCRRequest
from kgfs.ocr.registry import get_ocr_backend, list_ocr_backends
from kgfs.ocr.status import get_ocr_status
from kgfs.ocr.tesseract import TesseractOCRBackend


def test_ocr_registry_contains_tesseract_backend() -> None:
    assert list_ocr_backends() == ["tesseract"]
    assert get_ocr_backend("tesseract").name == "tesseract"


def test_ocr_status_works_when_disabled() -> None:
    status = get_ocr_status(KGFSConfig())

    assert status.enabled is False
    assert status.backend_name == "tesseract"
    assert status.available is False
    assert "disabled" in status.message.lower()


def test_ocr_status_handles_unknown_backend_helpfully() -> None:
    status = get_ocr_status(KGFSConfig(ocr=OCRSettings(enabled=True, backend="unknown")))

    assert status.available is False
    assert "Unknown OCR backend" in status.message
    assert status.install_hint == "Set ocr.backend to tesseract."


def test_tesseract_backend_success_uses_stdout_and_does_not_modify_source(tmp_path: Path, mocker) -> None:
    image = tmp_path / "scan.png"
    image.write_bytes(b"not a real image but not modified")
    before = image.read_bytes()
    completed = subprocess.CompletedProcess(args=["tesseract"], returncode=0, stdout="Visible Motor Torque\n", stderr="")
    run = mocker.patch("kgfs.ocr.tesseract.subprocess.run", return_value=completed)
    config = KGFSConfig(
        ocr=OCRSettings(
            enabled=True,
            tesseract=TesseractOCRSettings(command="tesseract", language="eng"),
        )
    )

    result = TesseractOCRBackend().extract_image(OCRRequest(path=image, config=config))

    assert result.status == "ok"
    assert result.text == "Visible Motor Torque"
    assert result.backend == "tesseract"
    assert result.language == "eng"
    assert result.source_kind == "image"
    assert image.read_bytes() == before
    args = run.call_args.args[0]
    assert args[:3] == ["tesseract", str(image), "stdout"]
    assert "-l" in args


def test_tesseract_missing_command_returns_error(tmp_path: Path, mocker) -> None:
    image = tmp_path / "scan.png"
    image.write_bytes(b"image")
    mocker.patch("kgfs.ocr.tesseract.subprocess.run", side_effect=FileNotFoundError("missing"))
    config = KGFSConfig(ocr=OCRSettings(enabled=True))

    result = TesseractOCRBackend().extract_image(OCRRequest(path=image, config=config))

    assert result.status == "error"
    assert "Tesseract command not found" in (result.error or "")


def test_tesseract_subprocess_failure_returns_error(tmp_path: Path, mocker) -> None:
    image = tmp_path / "scan.png"
    image.write_bytes(b"image")
    completed = subprocess.CompletedProcess(args=["tesseract"], returncode=1, stdout="", stderr="bad image")
    mocker.patch("kgfs.ocr.tesseract.subprocess.run", return_value=completed)
    config = KGFSConfig(ocr=OCRSettings(enabled=True))

    result = TesseractOCRBackend().extract_image(OCRRequest(path=image, config=config))

    assert result.status == "error"
    assert "bad image" in (result.error or "")
