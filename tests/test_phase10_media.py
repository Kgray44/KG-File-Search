from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from kgfs.cli import app
from kgfs.config import KGFSConfig
from kgfs.core.models import FileRecord
from kgfs.database import connect_database, initialize_database
from kgfs.db.repositories import upsert_file
from kgfs.migrations import CURRENT_SCHEMA_VERSION, get_schema_version
from kgfs.search import search

runner = CliRunner()


def _insert_file(conn, path: Path, *, text: str = "", extraction_source: str = "text") -> int:
    return upsert_file(
        conn,
        FileRecord(
            path=path,
            normalized_path=str(path),
            file_name=path.name,
            extension=path.suffix.lower(),
            size=path.stat().st_size,
            modified_time=path.stat().st_mtime,
            modified_time_ns=path.stat().st_mtime_ns,
            content_hash=None,
            extracted_text=text,
            indexed_at="2026-04-26T00:00:00+00:00",
            platform_indexed_from="test",
            extraction_status="ok",
            extraction_error=None,
            extraction_source=extraction_source,
        ),
    )


def test_phase10_media_config_defaults_are_safe_and_normalized() -> None:
    config = KGFSConfig.model_validate(
        {
            "media": {
                "max_media_file_size_mb": "-1",
                "photos": {
                    "include_extensions": ["JPG", "heic"],
                    "store_location_metadata": False,
                    "location_precision": "exact",
                },
                "audio": {"include_extensions": ["MP3", ".WAV"], "max_audio_minutes_per_file": 0},
            },
            "ocr": {
                "backend": "tesseract",
                "easyocr": {"enabled": True, "languages": ["EN"], "gpu": True},
                "paddle": {"enabled": True, "language": "EN"},
                "cloud_fallback": {"enabled": True, "provider": "example"},
            },
        }
    )

    assert config.media.enabled is False
    assert config.media.photos.enabled is False
    assert config.media.photos.include_extensions == [".jpg", ".heic"]
    assert config.media.photos.store_location_metadata is False
    assert config.media.photos.location_precision == "none"
    assert config.media.max_media_file_size_mb == 50
    assert config.media.audio.include_extensions == [".mp3", ".wav"]
    assert config.media.audio.max_audio_minutes_per_file == 60
    assert config.media.visual.enabled is False
    assert config.ocr.easyocr.enabled is True
    assert config.ocr.easyocr.languages == ["en"]
    assert config.ocr.paddle.language == "en"
    assert config.ocr.cloud_fallback.enabled is True
    assert config.ocr.cloud_fallback.require_confirmation is True
    assert config.ocr.cloud_fallback.preview_before_upload is True


def test_media_schema_tables_are_created(tmp_path: Path) -> None:
    conn = connect_database(tmp_path / "kgfs.sqlite3")

    initialize_database(conn)

    tables = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual table')").fetchall()
    }
    assert get_schema_version(conn) == CURRENT_SCHEMA_VERSION
    assert {"media_metadata", "media_text", "media_embeddings"}.issubset(tables)


def test_media_status_works_without_optional_dependencies(tmp_path: Path) -> None:
    from kgfs.media.status import get_media_status

    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)

    status = get_media_status(KGFSConfig(), conn)

    assert status.enabled is False
    assert status.photo_metadata_enabled is False
    assert status.media_metadata_count == 0
    assert status.media_text_count == 0
    assert status.media_embedding_count == 0
    assert status.caption_backend == "none"
    assert status.audio_backend == "none"
    assert status.visual_backend == "none"
    assert status.cloud_fallback_enabled is False


def test_photo_metadata_can_be_stored_without_gps_and_found_by_keyword_search(tmp_path: Path) -> None:
    from kgfs.media.exif import PhotoMetadata, store_photo_metadata

    photo = tmp_path / "lab-photo.jpg"
    photo.write_bytes(b"fake image bytes")
    before = photo.read_bytes()
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    config = KGFSConfig.model_validate(
        {
            "media": {
                "enabled": True,
                "photos": {"enabled": True, "index_exif": True, "store_location_metadata": False},
            }
        }
    )
    file_id = _insert_file(conn, photo)

    store_photo_metadata(
        conn,
        config,
        file_id=file_id,
        metadata=PhotoMetadata(
            width=640,
            height=480,
            camera_make="KG",
            camera_model="TestCam 42",
            captured_at="2026-04-26T12:00:00",
            gps_latitude=38.8977,
            gps_longitude=-77.0365,
            metadata={"LensModel": "Lab Lens"},
        ),
    )
    row = conn.execute("SELECT location_text, location_precision, metadata_json FROM media_metadata").fetchone()
    text_row = conn.execute("SELECT source_kind, text FROM media_text").fetchone()
    results = search(conn, "TestCam", limit=5)

    assert row["location_text"] is None
    assert row["location_precision"] == "none"
    assert "gps_latitude" not in row["metadata_json"]
    assert text_row["source_kind"] == "exif"
    assert "TestCam 42" in text_row["text"]
    assert results
    assert results[0].file_name == "lab-photo.jpg"
    assert results[0].metadata["extraction_source"] == "media:exif"
    assert photo.read_bytes() == before
    assert not list(tmp_path.glob("*.xmp"))


def test_media_photo_indexing_is_opt_in_and_does_not_modify_source(tmp_path: Path, monkeypatch) -> None:
    from kgfs.indexing.filters import should_index_file
    from kgfs.indexing.indexer import index_configured_folders
    from kgfs.media.exif import PhotoMetadata

    photo = tmp_path / "bench-photo.jpg"
    photo.write_bytes(b"not a real jpg but never modified")
    before = photo.read_bytes()
    disabled = KGFSConfig.model_validate({"indexed_folders": [tmp_path]})
    enabled = KGFSConfig.model_validate(
        {
            "indexed_folders": [tmp_path],
            "media": {
                "enabled": True,
                "photos": {"enabled": True, "index_exif": True, "store_location_metadata": False},
            },
        }
    )
    monkeypatch.setattr(
        "kgfs.indexing.indexer.extract_exif_metadata",
        lambda path: PhotoMetadata(width=100, height=50, camera_model="MockCam"),
    )
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)

    assert should_index_file(photo, disabled) is False
    assert should_index_file(photo, enabled) is True
    summary = index_configured_folders(enabled, conn)
    media_text = conn.execute("SELECT text FROM media_text WHERE source_kind = 'exif'").fetchone()["text"]

    assert summary.indexed == 1
    assert "MockCam" in media_text
    assert photo.read_bytes() == before
    assert not list(tmp_path.glob("*.xmp"))


def test_media_match_label_survives_filename_keyword_overlap(tmp_path: Path) -> None:
    from kgfs.media.exif import PhotoMetadata, store_photo_metadata

    photo = tmp_path / "metadata-photo.jpg"
    photo.write_bytes(b"fake image bytes")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    config = KGFSConfig.model_validate({"media": {"enabled": True, "photos": {"enabled": True}}})
    file_id = _insert_file(conn, photo)
    store_photo_metadata(
        conn,
        config,
        file_id=file_id,
        metadata=PhotoMetadata(width=20, height=10, camera_model="OverlapCam"),
    )

    results = search(conn, "photo metadata", limit=5)

    assert results
    assert results[0].file_name == "metadata-photo.jpg"
    assert results[0].metadata["extraction_source"] == "media:exif"
    assert "EXIF photo metadata" in results[0].snippet


def test_caption_audio_visual_scaffolds_are_safe_and_mockable(tmp_path: Path) -> None:
    from kgfs.media.audio import TranscriptionResult, get_audio_status, transcribe_audio
    from kgfs.media.captions import CaptionResult, caption_image, get_caption_status
    from kgfs.media.visual import VisualEmbeddingResult, get_visual_status, visual_embedding_for_file

    image = tmp_path / "image.jpg"
    audio = tmp_path / "lecture.mp3"
    image.write_bytes(b"image")
    audio.write_bytes(b"audio")
    config = KGFSConfig()

    assert get_caption_status(config).available is False
    assert get_audio_status(config).available is False
    assert get_visual_status(config).available is False
    assert caption_image(image, config).status == "skipped"
    assert transcribe_audio(audio, config).status == "skipped"
    assert visual_embedding_for_file(image, config).status == "skipped"

    assert CaptionResult(text="photo of motor lab", status="ok").text == "photo of motor lab"
    assert TranscriptionResult(text="lecture transcript PID control", status="ok").status == "ok"
    assert VisualEmbeddingResult(vector=[0.1, 0.2], status="ok").vector == [0.1, 0.2]


def test_advanced_ocr_backends_are_registered_lazy_and_helpful() -> None:
    from kgfs.ocr.registry import get_ocr_backend, list_ocr_backends

    config = KGFSConfig.model_validate({"ocr": {"enabled": True}})

    assert list_ocr_backends() == ["tesseract", "easyocr", "paddle"]
    easy = get_ocr_backend("easyocr").available(config)
    paddle = get_ocr_backend("paddle").available(config)
    assert easy.available is False
    assert "EasyOCR" in easy.message
    assert easy.install_hint
    assert paddle.available is False
    assert "PaddleOCR" in paddle.message
    assert paddle.install_hint


def test_cloud_ocr_fallback_never_allows_upload_by_default(tmp_path: Path) -> None:
    from kgfs.ocr.cloud import build_cloud_ocr_plan

    image = tmp_path / "scan.png"
    image.write_bytes(b"private image")
    disabled = build_cloud_ocr_plan(image, KGFSConfig(), allow_cloud=False, confirmed=False)
    configured = KGFSConfig.model_validate(
        {"ocr": {"cloud_fallback": {"enabled": True, "provider": "example", "require_confirmation": True}}}
    )
    unconfirmed = build_cloud_ocr_plan(image, configured, allow_cloud=True, confirmed=False)
    confirmed = build_cloud_ocr_plan(image, configured, allow_cloud=True, confirmed=True)

    assert disabled.allowed is False
    assert "disabled" in disabled.message.lower()
    assert unconfirmed.allowed is False
    assert "confirmation" in unconfirmed.message.lower()
    assert confirmed.allowed is False
    assert "not implemented" in confirmed.message.lower()
    assert confirmed.preview["path"] == str(image)


def test_media_cli_status_and_clear_are_safe(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    db_path = tmp_path / "kgfs.sqlite3"
    config_path.write_text(
        f"""
indexed_folders: []
database_path: "{db_path.as_posix()}"
media:
  enabled: false
""",
        encoding="utf-8",
    )
    conn = connect_database(db_path)
    initialize_database(conn)
    conn.close()

    status = runner.invoke(app, ["media", "status", "--config", str(config_path), "--database", str(db_path)])
    refused = runner.invoke(app, ["media", "clear", "--config", str(config_path), "--database", str(db_path)])
    advanced = runner.invoke(app, ["ocr", "advanced-status", "--config", str(config_path), "--database", str(db_path)])

    assert status.exit_code == 0
    assert "Media enabled" in status.output
    assert refused.exit_code != 0
    assert "--yes" in refused.output or "yes" in refused.output.lower()
    assert advanced.exit_code == 0
    assert "EasyOCR" in advanced.output
