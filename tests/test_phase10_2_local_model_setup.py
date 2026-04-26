from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from typer.testing import CliRunner

from kgfs.cli import app
from kgfs.config import KGFSConfig

runner = CliRunner()


def test_readiness_states_and_aliases_do_not_import_heavy_modules(tmp_path: Path) -> None:
    for name in ("easyocr", "paddleocr", "transformers", "faster_whisper", "sentence_transformers"):
        sys.modules.pop(name, None)

    from kgfs.models.validation import BackendReadiness, validate_backend

    config = KGFSConfig.model_validate(
        {
            "indexed_folders": [str(tmp_path / "corpus")],
            "media": {"enabled": True, "captions": {"enabled": True, "backend": "metadata"}},
        }
    )

    ready = validate_backend("metadata-caption", config)
    disabled = validate_backend("easyocr", KGFSConfig())

    assert ready.readiness == BackendReadiness.READY
    assert disabled.readiness == BackendReadiness.DISABLED
    assert ready.backend == "metadata-caption"
    for name in ("easyocr", "paddleocr", "transformers", "faster_whisper", "sentence_transformers"):
        assert name not in sys.modules


def test_model_paths_warn_when_configured_model_lives_inside_indexed_folder(tmp_path: Path) -> None:
    from kgfs.models.paths import collect_model_paths

    corpus = tmp_path / "corpus"
    model_dir = corpus / "models" / "easyocr"
    model_dir.mkdir(parents=True)
    config = KGFSConfig.model_validate(
        {
            "indexed_folders": [str(corpus)],
            "ocr": {"easyocr": {"enabled": True, "model_storage_directory": str(model_dir)}},
        }
    )

    paths = collect_model_paths(config, project_root=tmp_path)
    easyocr = next(item for item in paths if item.backend == "easyocr")

    assert easyocr.path == model_dir
    assert any("inside indexed folder" in warning for warning in easyocr.warnings)


def test_validate_reports_missing_dependency_and_missing_model_without_downloads(tmp_path: Path, monkeypatch) -> None:
    from kgfs.models.validation import BackendReadiness, validate_backend

    monkeypatch.setattr("kgfs.models.validation.find_spec", lambda name: None)
    config = KGFSConfig.model_validate(
        {
            "ocr": {
                "enabled": True,
                "backend": "easyocr",
                "easyocr": {"enabled": True, "download_enabled": False},
            }
        }
    )

    result = validate_backend("easyocr", config)

    assert result.readiness == BackendReadiness.MISSING_DEPENDENCY
    assert "ocr-easyocr" in (result.install_hint or "")
    assert any("downloads disabled" in message.lower() for message in result.messages)


def test_config_snippets_are_yaml_and_keep_downloads_disabled() -> None:
    from kgfs.models.snippets import config_snippet

    easy = config_snippet("easyocr")
    paddle = config_snippet("paddle")
    caption = config_snippet("transformers-caption")
    bytehash = config_snippet("bytehash-visual")

    assert "easyocr:" in easy
    assert "download_enabled: false" in easy
    assert "model_storage_directory:" in easy
    assert "paddle:" in paddle
    assert "model_dir:" in paddle
    assert "captions:" in caption
    assert "local_files_only: true" in caption
    assert 'backend: "bytehash"' in bytehash


@dataclass(frozen=True)
class FakeCaptionBackend:
    name: str = "fake-caption"

    def available(self, config):
        return True, "fake caption ready"

    def caption(self, path: Path, config):
        from kgfs.media.captions import CaptionResult

        return CaptionResult(f"caption for {path.name}", "ok", backend=self.name, model_name="fake")


def test_models_test_command_runs_mocked_caption_backend(tmp_path: Path) -> None:
    from kgfs.media.captions import register_caption_backend

    image = tmp_path / "bench.jpg"
    image.write_bytes(b"image bytes")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
indexed_folders: []
media:
  enabled: true
  captions:
    enabled: true
    backend: fake-caption
""",
        encoding="utf-8",
    )
    register_caption_backend("fake-caption", FakeCaptionBackend())

    result = runner.invoke(app, ["models", "test", "fake-caption", str(image), "--config", str(config_path)])

    assert result.exit_code == 0
    assert "caption for bench.jpg" in result.output
    assert image.read_bytes() == b"image bytes"


def test_models_cli_doctor_validate_paths_and_snippet(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("indexed_folders: []\n", encoding="utf-8")

    doctor = runner.invoke(app, ["models", "doctor", "--config", str(config_path)])
    validate = runner.invoke(app, ["models", "validate", "--config", str(config_path)])
    paths = runner.invoke(app, ["models", "paths", "--config", str(config_path)])
    snippet = runner.invoke(app, ["models", "config-snippet", "faster-whisper"])

    assert doctor.exit_code == 0
    assert "Readiness" in doctor.output
    assert validate.exit_code == 0
    assert "disabled" in validate.output.lower()
    assert paths.exit_code == 0
    assert "KGFS model cache" in paths.output
    assert snippet.exit_code == 0
    assert "faster_whisper" in snippet.output
    assert "download_enabled: false" in snippet.output
