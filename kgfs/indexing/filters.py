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
    is_ocr_image = config.ocr.enabled and suffix in set(config.ocr.include_extensions)
    is_media_photo = (
        config.media.enabled and config.media.photos.enabled and suffix in set(config.media.photos.include_extensions)
    )
    if not (is_ocr_image or is_media_photo):
        if suffix in set(config.ignored_extensions):
            return False
        if config.include_extensions and suffix not in set(config.include_extensions):
            return False

    posix_path = path.as_posix()
    for pattern in config.exclude_globs:
        if fnmatch(path.name, pattern) or fnmatch(posix_path, pattern):
            return False

    try:
        if is_ocr_image:
            max_size = config.ocr.max_image_size_bytes
        elif is_media_photo:
            max_size = config.media.max_media_file_size_bytes
        else:
            max_size = config.max_file_size_bytes
        if path.stat().st_size > max_size:
            return False
    except OSError:
        return False

    return True
