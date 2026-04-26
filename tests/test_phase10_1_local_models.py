from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from pathlib import Path

from typer.testing import CliRunner

from kgfs.cli import app
from kgfs.config import KGFSConfig
from kgfs.core.models import FileRecord
from kgfs.database import connect_database, initialize_database
from kgfs.db.repositories import upsert_file
from kgfs.search import search

runner = CliRunner()


def _insert_file(conn, path: Path, *, text: str = "", extraction_source: str = "text") -> int:
    if not path.exists():
        path.write_text(text or path.name, encoding="utf-8")
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


def test_model_config_defaults_keep_downloads_disabled() -> None:
    config = KGFSConfig()

    assert config.models.local_files_only is True
    assert config.models.max_batch_size == 8
    assert config.models.benchmark_sample_size == 10
    assert config.ocr.default_backend == "tesseract"
    assert config.ocr.easyocr.download_enabled is False
    assert config.ocr.easyocr.model_storage_directory is None
    assert config.ocr.paddle.download_enabled is False
    assert config.ocr.paddle.use_angle_cls is True
    assert config.media.captions.download_enabled is False
    assert config.media.audio.download_enabled is False
    assert config.media.visual.download_enabled is False


def test_model_registry_lists_known_backends_without_importing_heavy_modules() -> None:
    for name in ("easyocr", "paddleocr", "transformers", "faster_whisper", "sentence_transformers"):
        sys.modules.pop(name, None)

    from kgfs.models.registry import collect_model_statuses, list_model_backends

    names = {(item.kind, item.name) for item in list_model_backends()}
    statuses = collect_model_statuses(KGFSConfig())

    assert ("ocr", "easyocr") in names
    assert ("ocr", "paddle") in names
    assert ("caption", "transformers") in names
    assert ("transcription", "faster_whisper") in names
    assert ("visual_embedding", "clip") in names
    assert any(item.name == "tesseract" for item in statuses)
    for name in ("easyocr", "paddleocr", "transformers", "faster_whisper", "sentence_transformers"):
        assert name not in sys.modules


def test_easyocr_backend_uses_lazy_reader_and_download_guard(tmp_path: Path, monkeypatch) -> None:
    from kgfs.ocr.base import OCRRequest
    from kgfs.ocr.easyocr import EasyOCRBackend

    image = tmp_path / "scan.png"
    image.write_bytes(b"image bytes")
    calls: dict[str, object] = {}

    class FakeReader:
        def __init__(self, languages, **kwargs):
            calls["languages"] = languages
            calls["kwargs"] = kwargs

        def readtext(self, path, detail=1):
            calls["path"] = path
            calls["detail"] = detail
            return [("box", "motor torque label", 0.8), ("box", "op amp gain", 0.6)]

    monkeypatch.setattr("kgfs.ocr.easyocr.find_spec", lambda name: object())
    monkeypatch.setitem(sys.modules, "easyocr", types.SimpleNamespace(Reader=FakeReader))
    config = KGFSConfig.model_validate(
        {
            "ocr": {
                "enabled": True,
                "backend": "easyocr",
                "easyocr": {
                    "enabled": True,
                    "languages": ["en"],
                    "gpu": False,
                    "model_storage_directory": str(tmp_path / "easy-models"),
                    "download_enabled": False,
                },
            }
        }
    )

    result = EasyOCRBackend().extract_image(OCRRequest(path=image, config=config, source_kind="image"))

    assert result.status == "ok"
    assert result.backend == "easyocr"
    assert "motor torque label" in result.text
    assert result.confidence == 0.7
    assert calls["languages"] == ["en"]
    assert calls["kwargs"]["download_enabled"] is False
    assert calls["kwargs"]["model_storage_directory"] == str(tmp_path / "easy-models")
    assert image.read_bytes() == b"image bytes"


def test_paddle_backend_uses_lazy_engine_and_download_guard(tmp_path: Path, monkeypatch) -> None:
    from kgfs.ocr.base import OCRRequest
    from kgfs.ocr.paddle import PaddleOCRBackend

    image = tmp_path / "scan.png"
    image.write_bytes(b"image bytes")
    calls: dict[str, object] = {}

    class FakePaddleOCR:
        def __init__(self, **kwargs):
            calls["kwargs"] = kwargs

        def ocr(self, path, cls=False):
            calls["path"] = path
            calls["cls"] = cls
            return [[["box", ("paddle motor torque", 0.9)], ["box", ("gain worksheet", 0.7)]]]

    monkeypatch.setattr("kgfs.ocr.paddle.find_spec", lambda name: object())
    monkeypatch.setitem(sys.modules, "paddleocr", types.SimpleNamespace(PaddleOCR=FakePaddleOCR))
    config = KGFSConfig.model_validate(
        {
            "ocr": {
                "enabled": True,
                "backend": "paddle",
                "paddle": {
                    "enabled": True,
                    "language": "en",
                    "use_angle_cls": True,
                    "use_gpu": False,
                    "model_dir": str(tmp_path / "paddle-models"),
                    "download_enabled": False,
                },
            }
        }
    )

    result = PaddleOCRBackend().extract_image(OCRRequest(path=image, config=config, source_kind="image"))

    assert result.status == "ok"
    assert result.backend == "paddle"
    assert "paddle motor torque" in result.text
    assert result.confidence == 0.8
    assert calls["kwargs"]["lang"] == "en"
    assert calls["kwargs"]["use_angle_cls"] is True
    assert calls["kwargs"]["use_gpu"] is False
    assert calls["kwargs"]["download_enabled"] is False
    assert calls["kwargs"]["det_model_dir"] == str(tmp_path / "paddle-models")
    assert calls["cls"] is True
    assert image.read_bytes() == b"image bytes"


def test_ocr_backend_selector_cli_lists_and_selects_backend(tmp_path: Path, monkeypatch) -> None:
    from kgfs.ocr.base import OCRResult

    image = tmp_path / "scan.png"
    image.write_bytes(b"image bytes")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
indexed_folders: []
ocr:
  enabled: true
  default_backend: easyocr
  easyocr:
    enabled: true
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "kgfs.ocr.easyocr.EasyOCRBackend.extract_image",
        lambda self, request: OCRResult("mock easy text", "ok", backend="easyocr", language="en"),
    )
    monkeypatch.setattr(
        "kgfs.ocr.easyocr.EasyOCRBackend.available",
        lambda self, config: type("A", (), {"available": True, "message": "ok", "install_hint": None})(),
    )

    backends = runner.invoke(app, ["ocr", "backends", "--config", str(config_path)])
    result = runner.invoke(app, ["ocr", "test", str(image), "--backend", "easyocr", "--config", str(config_path)])

    assert backends.exit_code == 0
    assert "easyocr" in backends.output
    assert result.exit_code == 0
    assert "easyocr" in result.output
    assert "mock easy text" in result.output


@dataclass(frozen=True)
class FakeCaptionBackend:
    name: str = "fake-caption"

    def available(self, config):
        return True, "fake caption ready"

    def caption(self, path: Path, config):
        from kgfs.media.captions import CaptionResult

        return CaptionResult("photo of motor torque bench", "ok", backend=self.name, model_name="fake")


@dataclass(frozen=True)
class FakeAudioBackend:
    name: str = "fake-audio"

    def available(self, config):
        return True, "fake audio ready"

    def transcribe(self, path: Path, config):
        from kgfs.media.audio import TranscriptionResult

        return TranscriptionResult("lecture transcript about PID control", "ok", backend=self.name, model_name="fake")


@dataclass(frozen=True)
class FakeVisualBackend:
    name: str = "fake-visual"

    def available(self, config):
        return True, "fake visual ready"

    def embed(self, path: Path, config):
        from kgfs.media.visual import VisualEmbeddingResult

        first = path.read_bytes()[0] if path.read_bytes() else 0
        return VisualEmbeddingResult([float(first), 1.0], "ok", backend=self.name, model_name="fake")


def test_caption_backend_contract_stores_searchable_media_text(tmp_path: Path) -> None:
    from kgfs.media.captions import index_existing_captions, register_caption_backend

    image = tmp_path / "bench.jpg"
    image.write_bytes(b"image")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    _insert_file(conn, image)
    register_caption_backend("fake-caption", FakeCaptionBackend())
    config = KGFSConfig.model_validate(
        {"media": {"enabled": True, "captions": {"enabled": True, "backend": "fake-caption"}}}
    )

    indexed, failed = index_existing_captions(conn, config)
    results = search(conn, "motor torque bench", limit=5)

    assert (indexed, failed) == (1, 0)
    assert results
    assert results[0].metadata["extraction_source"] == "media:caption"
    assert "photo of motor torque bench" in results[0].snippet
    assert image.read_bytes() == b"image"


def test_audio_backend_contract_stores_searchable_transcript(tmp_path: Path) -> None:
    from kgfs.media.audio import index_existing_transcripts, register_audio_backend

    audio = tmp_path / "lecture.mp3"
    audio.write_bytes(b"audio")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    _insert_file(conn, audio)
    register_audio_backend("fake-audio", FakeAudioBackend())
    config = KGFSConfig.model_validate(
        {
            "media": {
                "enabled": True,
                "audio": {"enabled": True, "transcription_enabled": True, "backend": "fake-audio"},
            }
        }
    )

    indexed, failed = index_existing_transcripts(conn, config)
    results = search(conn, "PID control", limit=5)

    assert (indexed, failed) == (1, 0)
    assert results
    assert results[0].metadata["extraction_source"] == "media:transcript"
    assert audio.read_bytes() == b"audio"


def test_visual_backend_contract_indexes_and_finds_similar_media(tmp_path: Path) -> None:
    from kgfs.media.visual import find_visual_similar, index_existing_visual_embeddings, register_visual_backend

    left = tmp_path / "left.jpg"
    right = tmp_path / "right.jpg"
    far = tmp_path / "far.jpg"
    left.write_bytes(bytes([10, 1]))
    right.write_bytes(bytes([10, 2]))
    far.write_bytes(bytes([200, 1]))
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    left_id = _insert_file(conn, left)
    _insert_file(conn, right)
    _insert_file(conn, far)
    register_visual_backend("fake-visual", FakeVisualBackend())
    config = KGFSConfig.model_validate(
        {"media": {"enabled": True, "visual": {"enabled": True, "backend": "fake-visual"}}}
    )

    indexed, failed = index_existing_visual_embeddings(conn, config)
    results = find_visual_similar(conn, left_id, config, limit=2)

    assert (indexed, failed) == (3, 0)
    assert results
    assert results[0].file_name == "right.jpg"
    assert results[0].metadata["extraction_source"] == "media:visual_embedding"
    assert left.read_bytes() == bytes([10, 1])


def test_models_cli_status_benchmark_and_recommend_work(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("indexed_folders: []\n", encoding="utf-8")

    status = runner.invoke(app, ["models", "status", "--config", str(config_path)])
    list_result = runner.invoke(app, ["models", "list", "--config", str(config_path)])
    benchmark = runner.invoke(app, ["models", "benchmark", "--config", str(config_path)])
    recommend = runner.invoke(app, ["models", "recommend", "--config", str(config_path)])

    assert status.exit_code == 0
    assert "EasyOCR" in status.output
    assert "downloads disabled" in status.output.lower()
    assert list_result.exit_code == 0
    assert "caption" in list_result.output
    assert benchmark.exit_code == 0
    assert "KGFS Model Benchmark" in benchmark.output
    assert recommend.exit_code == 0
    assert "Recommended" in recommend.output


def test_store_media_embedding_round_trip(tmp_path: Path) -> None:
    from kgfs.media.cache import store_media_embedding

    image = tmp_path / "image.jpg"
    image.write_bytes(b"image")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    file_id = _insert_file(conn, image)

    store_media_embedding(
        conn,
        file_id=file_id,
        source_kind="image",
        backend="fake",
        model_name="tiny",
        vector=[0.25, 0.75],
        metadata={"unit": "test"},
    )
    row = conn.execute("SELECT embedding_dim, backend, model_name FROM media_embeddings").fetchone()

    assert row["embedding_dim"] == 2
    assert row["backend"] == "fake"
    assert row["model_name"] == "tiny"
