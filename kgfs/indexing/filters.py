"""Safe file and directory filtering."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

from kgfs.core.config import KGFSConfig


def should_skip_dir(path: Path, config: KGFSConfig) -> bool:
    """Return true when a directory should be skipped by name."""

    return path.name in set(config.ignored_folders)


def should_index_file(path: Path, config: KGFSConfig) -> bool:
    """Return true when a file is small, supported, and not explicitly ignored."""

    if path.is_symlink() and not config.follow_symlinks:
        return False

    suffix = path.suffix.lower()
    if suffix in set(config.ignored_extensions):
        return False
    if config.include_extensions and suffix not in set(config.include_extensions):
        return False

    posix_path = path.as_posix()
    for pattern in config.exclude_globs:
        if fnmatch(path.name, pattern) or fnmatch(posix_path, pattern):
            return False

    try:
        if path.stat().st_size > config.max_file_size_bytes:
            return False
    except OSError:
        return False

    return True
