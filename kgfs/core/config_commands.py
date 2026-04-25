"""Helpers for editing configured indexed folders."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from kgfs.core.path_utils import expand_user_path
from kgfs.core.safety import risk_warning


@dataclass(frozen=True)
class FolderChange:
    path: Path
    display_path: str
    added: bool = False
    removed: bool = False
    exists: bool = False
    warning: str = ""


def add_indexed_folder(config_path: Path, folder: str | Path) -> FolderChange:
    data = _load_config_data(config_path)
    display = str(folder)
    expanded = expand_user_path(display)
    folders = [str(item) for item in data.get("indexed_folders") or []]
    existing_normalized = {_folder_key(item) for item in folders}
    already_present = _folder_key(display) in existing_normalized
    if not already_present:
        folders.append(display)
        data["indexed_folders"] = folders
        _write_config_data(config_path, data)
    return FolderChange(
        path=expanded,
        display_path=display,
        added=not already_present,
        exists=expanded.exists(),
        warning=risk_warning(expanded),
    )


def remove_indexed_folder(config_path: Path, folder: str | Path) -> FolderChange:
    data = _load_config_data(config_path)
    display = str(folder)
    target_key = _folder_key(display)
    folders = [str(item) for item in data.get("indexed_folders") or []]
    kept = [item for item in folders if _folder_key(item) != target_key]
    removed = len(kept) != len(folders)
    if removed:
        data["indexed_folders"] = kept
        _write_config_data(config_path, data)
    expanded = expand_user_path(display)
    return FolderChange(
        path=expanded,
        display_path=display,
        removed=removed,
        exists=expanded.exists(),
        warning=risk_warning(expanded),
    )


def list_indexed_folders(config_path: Path) -> list[Path]:
    data = _load_config_data(config_path)
    return [expand_user_path(item) for item in data.get("indexed_folders") or []]


def _load_config_data(config_path: Path) -> dict[str, Any]:
    config_path = config_path.expanduser()
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return dict(raw)


def _write_config_data(config_path: Path, data: dict[str, Any]) -> None:
    config_path = config_path.expanduser()
    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _folder_key(value: str | Path) -> str:
    path = expand_user_path(value)
    return str(path).replace("\\", "/").rstrip("/").casefold()
