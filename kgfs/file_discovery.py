"""Folder traversal for configured index roots."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

from kgfs.config import KGFSConfig
from kgfs.file_filters import should_index_file, should_skip_dir


def discover_files(config: KGFSConfig) -> Iterator[Path]:
    """Yield indexable files under explicitly configured folders."""

    for root in config.indexed_folders:
        root = root.expanduser()
        if not root.exists():
            continue
        if root.is_file():
            if should_index_file(root, config):
                yield root
            continue

        for current_dir, dir_names, file_names in os.walk(root, followlinks=config.follow_symlinks):
            current_path = Path(current_dir)
            dir_names[:] = sorted(
                dirname
                for dirname in dir_names
                if _should_descend(current_path / dirname, config)
            )
            for filename in sorted(file_names):
                file_path = current_path / filename
                if should_index_file(file_path, config):
                    yield file_path


def _should_descend(path: Path, config: KGFSConfig) -> bool:
    if path.is_symlink() and not config.follow_symlinks:
        return False
    return not should_skip_dir(path, config)

