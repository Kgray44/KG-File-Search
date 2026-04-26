from pathlib import Path

import yaml

from kgfs.config import create_default_config_file, load_config
from kgfs.config_commands import add_indexed_folder, list_indexed_folders, remove_indexed_folder


def test_add_folder_expands_tilde_and_avoids_duplicates(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.yaml"
    create_default_config_file(config_path)
    home = tmp_path / "home"
    docs = home / "Documents"
    docs.mkdir(parents=True)
    monkeypatch.setattr("kgfs.path_utils.Path.home", lambda: home)

    first = add_indexed_folder(config_path, "~/Documents")
    second = add_indexed_folder(config_path, "~/Documents")

    config = load_config(config_path)
    assert first.added is True
    assert second.added is False
    assert config.indexed_folders == [docs]
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert raw["indexed_folders"] == ["~/Documents"]


def test_remove_and_list_folders(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    folder = tmp_path / "notes"
    folder.mkdir()
    create_default_config_file(config_path)
    add_indexed_folder(config_path, str(folder))

    assert list_indexed_folders(config_path) == [folder]
    result = remove_indexed_folder(config_path, str(folder))

    assert result.removed is True
    assert list_indexed_folders(config_path) == []
