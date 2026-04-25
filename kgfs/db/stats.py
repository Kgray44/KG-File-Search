"""Database statistics helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from kgfs.db.migrations import get_schema_version


def get_database_stats(conn: sqlite3.Connection, database_path: Path | None = None) -> dict[str, Any]:
    total = conn.execute(
        """
        SELECT
            COUNT(*) AS count,
            COALESCE(SUM(size), 0) AS bytes,
            COALESCE(SUM(LENGTH(extracted_text)), 0) AS text_bytes
        FROM files
        """
    ).fetchone()
    folders = conn.execute("SELECT path FROM files").fetchall()
    types = conn.execute(
        "SELECT extension, COUNT(*) AS count FROM files GROUP BY extension ORDER BY count DESC"
    ).fetchall()
    largest = conn.execute(
        "SELECT file_name, path, size FROM files ORDER BY size DESC LIMIT 5"
    ).fetchall()
    failures = conn.execute(
        "SELECT COUNT(*) AS count FROM files WHERE extraction_status = 'error'"
    ).fetchone()
    successes = conn.execute(
        "SELECT COUNT(*) AS count FROM files WHERE extraction_status != 'error'"
    ).fetchone()
    last_indexed = conn.execute("SELECT MAX(indexed_at) AS last_indexed FROM files").fetchone()
    chunks = conn.execute("SELECT COUNT(*) AS count, COALESCE(SUM(LENGTH(embedding)), 0) AS bytes FROM chunks").fetchone()
    db_size = database_path.stat().st_size if database_path and database_path.exists() else 0
    stale_count = sum(1 for row in folders if not Path(row["path"]).exists())
    indexed_folders = {str(Path(row["path"]).parent) for row in folders}
    return {
        "total_files": int(total["count"]),
        "total_size": int(total["bytes"]),
        "total_folders": len(indexed_folders),
        "total_extracted_text_size": int(total["text_bytes"]),
        "total_chunks": int(chunks["count"]),
        "embedding_bytes": int(chunks["bytes"]),
        "file_types": [(row["extension"], int(row["count"])) for row in types],
        "largest_files": [(row["file_name"], row["path"], int(row["size"])) for row in largest],
        "extraction_successes": int(successes["count"]),
        "extraction_failures": int(failures["count"]),
        "stale_records": stale_count,
        "last_indexed": last_indexed["last_indexed"],
        "database_size": db_size,
        "schema_version": get_schema_version(conn),
    }
