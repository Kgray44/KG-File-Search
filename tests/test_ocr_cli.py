from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from kgfs.cli import app
from kgfs.ocr.base import OCRResult


runner = CliRunner()


def test_ocr_cli_group_is_registered() -> None:
    result = runner.invoke(app, ["ocr", "--help"])

    assert result.exit_code == 0
    assert "status" in result.output
    assert "test" in result.output
    assert "index" in result.output


def test_ocr_status_command_works_when_disabled(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("indexed_folders: []\n", encoding="utf-8")

    result = runner.invoke(app, ["ocr", "status", "--config", str(config_path)])

    assert result.exit_code == 0
    assert "OCR enabled" in result.output
    assert "False" in result.output


def test_ocr_test_command_prints_preview_without_indexing(tmp_path: Path, mocker) -> None:
    image = tmp_path / "scan.png"
    image.write_bytes(b"source image")
    config_path = tmp_path / "config.yaml"
    config_path.write_text("indexed_folders: []\nocr:\n  enabled: true\n", encoding="utf-8")
    mocker.patch(
        "kgfs.ocr.tesseract.TesseractOCRBackend.extract_image",
        return_value=OCRResult(
            text="preview motor torque",
            status="ok",
            backend="tesseract",
            language="eng",
            source_kind="image",
        ),
    )

    result = runner.invoke(app, ["ocr", "test", str(image), "--config", str(config_path)])

    assert result.exit_code == 0
    assert "preview motor torque" in result.output
    assert not (tmp_path / "kgfs.sqlite3").exists()


def test_ocr_index_command_runs_indexing(tmp_path: Path, mocker) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "scan.png").write_bytes(b"image")
    config_path = tmp_path / "config.yaml"
    db_path = tmp_path / "kgfs.sqlite3"
    config_path.write_text(f"indexed_folders:\n  - {root.as_posix()!r}\nocr:\n  enabled: true\n", encoding="utf-8")
    mocker.patch(
        "kgfs.ocr.tesseract.TesseractOCRBackend.extract_image",
        return_value=OCRResult(
            text="ocr index motor torque",
            status="ok",
            backend="tesseract",
            language="eng",
            source_kind="image",
        ),
    )

    result = runner.invoke(app, ["ocr", "index", "--config", str(config_path), "--database", str(db_path)])

    assert result.exit_code == 0
    assert "indexed 1" in result.output.lower()


def test_why_mentions_ocr_source_for_ocr_result(tmp_path: Path, mocker) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "scan.png").write_bytes(b"image")
    config_path = tmp_path / "config.yaml"
    db_path = tmp_path / "kgfs.sqlite3"
    config_path.write_text(f"indexed_folders:\n  - {root.as_posix()!r}\nocr:\n  enabled: true\n", encoding="utf-8")
    mocker.patch(
        "kgfs.ocr.tesseract.TesseractOCRBackend.extract_image",
        return_value=OCRResult(
            text="ocr why motor torque",
            status="ok",
            backend="tesseract",
            language="eng",
            source_kind="image",
        ),
    )
    index_result = runner.invoke(app, ["index", "--config", str(config_path), "--database", str(db_path)])
    assert index_result.exit_code == 0
    search_result = runner.invoke(
        app,
        ["search", "motor torque", "--mode", "keyword", "--config", str(config_path), "--database", str(db_path)],
    )
    assert search_result.exit_code == 0

    result = runner.invoke(
        app,
        ["why", "1", "motor torque", "--mode", "keyword", "--config", str(config_path), "--database", str(db_path)],
    )

    assert result.exit_code == 0
    assert "OCR-derived text" in result.output
