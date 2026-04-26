"""Media indexing helpers that operate only on KGFS database/cache data."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from kgfs.core.config import KGFSConfig
from kgfs.media.exif import extract_exif_metadata, store_photo_metadata


def index_existing_photo_metadata(conn: sqlite3.Connection, config: KGFSConfig) -> tuple[int, int]:
    """Index EXIF metadata for already indexed photo rows."""

    if not (config.media.enabled and config.media.photos.enabled and config.media.photos.index_exif):
        return (0, 0)
    extensions = tuple(config.media.photos.include_extensions)
    placeholders = ", ".join("?" for _ in extensions)
    rows = conn.execute(
        f"SELECT id, path, size FROM files WHERE extension IN ({placeholders})",
        extensions,
    ).fetchall()
    indexed = failed = 0
    for row in rows:
        path = Path(row["path"])
        if not path.exists() or int(row["size"]) > config.media.max_media_file_size_bytes:
            failed += 1
            continue
        try:
            metadata = extract_exif_metadata(path)
            store_photo_metadata(conn, config, file_id=int(row["id"]), metadata=metadata)
            indexed += 1
        except Exception:
            failed += 1
    return indexed, failed
