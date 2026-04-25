from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from kgfs.config import KGFSConfig, OCRSettings
from kgfs.extractors.pdf import extract_pdf


class _FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


def _install_fake_pypdf(monkeypatch, text: str) -> None:
    class FakeReader:
        def __init__(self, path: str) -> None:
            self.pages = [_FakePage(text)]

    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=FakeReader))


def test_text_pdf_does_not_invoke_ocr(tmp_path: Path, monkeypatch, mocker) -> None:
    pdf = tmp_path / "text.pdf"
    pdf.write_bytes(b"%PDF text")
    before = pdf.read_bytes()
    _install_fake_pypdf(monkeypatch, "normal selectable text in pdf")
    mocked_ocr = mocker.patch("kgfs.ocr.pdf.extract_scanned_pdf")
    config = KGFSConfig(ocr=OCRSettings(enabled=True, min_pdf_text_chars=20))

    result = extract_pdf(pdf, config=config)

    assert result.status == "ok"
    assert "selectable text" in result.text
    assert result.metadata == {}
    assert pdf.read_bytes() == before
    mocked_ocr.assert_not_called()


def test_empty_text_pdf_reports_scanned_pdf_fallback_without_modifying_source(tmp_path: Path, monkeypatch) -> None:
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF scanned")
    before = pdf.read_bytes()
    _install_fake_pypdf(monkeypatch, "")
    config = KGFSConfig(ocr=OCRSettings(enabled=True, min_pdf_text_chars=20))

    result = extract_pdf(pdf, config=config)

    assert result.status == "error"
    assert "Scanned PDF OCR" in (result.error or "")
    assert result.metadata["extraction_source"] == "ocr"
    assert result.metadata["scanned_pdf_candidate"] is True
    assert pdf.read_bytes() == before
    assert not list(tmp_path.glob("*.ocr*"))


def test_empty_text_pdf_without_ocr_keeps_plain_pdf_behavior(tmp_path: Path, monkeypatch) -> None:
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF scanned")
    _install_fake_pypdf(monkeypatch, "")
    config = KGFSConfig(ocr=OCRSettings(enabled=False))

    result = extract_pdf(pdf, config=config)

    assert result.status == "ok"
    assert result.text == ""
    assert result.metadata == {}
