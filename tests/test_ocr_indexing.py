from __future__ import annotations

from pathlib import Path

from kgfs.config import KGFSConfig, OCRSettings
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.file_filters import should_index_file
from kgfs.ocr.base import OCRResult
from kgfs.search import search


def test_ocr_disabled_keeps_images_out_of_index(tmp_path: Path) -> None:
    image = tmp_path / "scan.png"
    image.write_bytes(b"image")
    config = KGFSConfig(indexed_folders=[tmp_path])

    assert should_index_file(image, config) is False


def test_ocr_enabled_allows_configured_images_and_respects_ocr_size(tmp_path: Path) -> None:
    image = tmp_path / "scan.PNG"
    image.write_bytes(b"image")
    huge = tmp_path / "huge.png"
    huge.write_bytes(b"x" * 2048)
    config = KGFSConfig(
        indexed_folders=[tmp_path],
        ocr=OCRSettings(enabled=True, max_image_size_mb=1 / 1024),
    )

    assert should_index_file(image, config) is True
    assert should_index_file(huge, config) is False


def test_ocr_image_text_is_indexed_searchable_cached_and_labeled(tmp_path: Path, mocker) -> None:
    image = tmp_path / "scan.png"
    image.write_bytes(b"original image bytes")
    before = image.read_bytes()
    db_path = tmp_path / "kgfs.sqlite3"
    config = KGFSConfig(
        indexed_folders=[tmp_path],
        database_path=db_path,
        ocr=OCRSettings(enabled=True),
    )
    conn = connect_database(db_path)
    initialize_database(conn)
    extract = mocker.patch(
        "kgfs.ocr.tesseract.TesseractOCRBackend.extract_image",
        return_value=OCRResult(
            text="visible motor torque from screenshot",
            status="ok",
            backend="tesseract",
            language="eng",
            source_kind="image",
        ),
    )

    first = index_configured_folders(config, conn)
    second = index_configured_folders(config, conn, force=True)
    results = search(conn, "visible motor torque")

    assert first.indexed == 1
    assert second.indexed == 1
    assert extract.call_count == 1
    assert results[0].file_name == "scan.png"
    assert results[0].metadata["extraction_source"] == "ocr"
    row = conn.execute("SELECT extracted_text, extraction_source FROM files WHERE file_name = 'scan.png'").fetchone()
    assert "visible motor torque" in row["extracted_text"]
    assert row["extraction_source"] == "ocr"
    assert image.read_bytes() == before
    assert not list(tmp_path.glob("*.ocr*"))


def test_ocr_failure_is_stored_as_extraction_error(tmp_path: Path, mocker) -> None:
    image = tmp_path / "scan.png"
    image.write_bytes(b"image")
    db_path = tmp_path / "kgfs.sqlite3"
    config = KGFSConfig(indexed_folders=[tmp_path], database_path=db_path, ocr=OCRSettings(enabled=True))
    conn = connect_database(db_path)
    initialize_database(conn)
    mocker.patch(
        "kgfs.ocr.tesseract.TesseractOCRBackend.extract_image",
        return_value=OCRResult(
            text="",
            status="error",
            error="Tesseract command not found",
            backend="tesseract",
            language="eng",
            source_kind="image",
        ),
    )

    summary = index_configured_folders(config, conn)
    row = conn.execute("SELECT extraction_status, extraction_error, extraction_source FROM files WHERE file_name = 'scan.png'").fetchone()

    assert summary.failed == 1
    assert row["extraction_status"] == "error"
    assert "Tesseract" in row["extraction_error"]
    assert row["extraction_source"] == "ocr"
