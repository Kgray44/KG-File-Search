from __future__ import annotations

import yaml

from kgfs.config import KGFSConfig, create_default_config_file


def test_ocr_defaults_are_safe_and_disabled() -> None:
    config = KGFSConfig()

    assert config.ocr.enabled is False
    assert config.ocr.backend == "tesseract"
    assert config.ocr.include_extensions == [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]
    assert config.ocr.max_image_size_mb == 15
    assert config.ocr.cache_results is True
    assert config.ocr.modify_source_files is False
    assert config.ocr.tesseract.command == "tesseract"
    assert config.ocr.tesseract.language == "eng"


def test_ocr_config_normalizes_extensions_and_safe_sizes() -> None:
    config = KGFSConfig.model_validate(
        {
            "ocr": {
                "enabled": True,
                "include_extensions": ["PNG", "jpg", ".TIFF"],
                "max_image_size_mb": -5,
                "modify_source_files": True,
            }
        }
    )

    assert config.ocr.include_extensions == [".png", ".jpg", ".tiff"]
    assert config.ocr.max_image_size_mb == 15
    assert config.ocr.modify_source_files is False


def test_default_config_yaml_includes_disabled_ocr_section(tmp_path) -> None:
    config_path = tmp_path / "config.yaml"

    assert create_default_config_file(config_path) is True
    text = config_path.read_text(encoding="utf-8")
    loaded = KGFSConfig.model_validate(yaml.safe_load(text))

    assert loaded.ocr.enabled is False
    assert "ocr:" in text
    assert "modify_source_files: false" in text
