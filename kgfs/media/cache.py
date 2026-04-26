"""SQLite helpers for KGFS media-derived metadata."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from kgfs.media.models import MediaTextRecord


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def dumps_json(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, sort_keys=True)


def store_media_text(conn: sqlite3.Connection, record: MediaTextRecord) -> int:
    now = utc_now()
    cursor = conn.execute(
        """
        INSERT INTO media_text(
            file_id, source_kind, backend, model_name, text, confidence,
            metadata_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record.file_id,
            record.source_kind,
            record.backend,
            record.model_name,
            record.text,
            record.confidence,
            dumps_json(record.metadata),
            now,
            now,
        ),
    )
    conn.commit()
    return int(cursor.lastrowid)


def clear_media_data(conn: sqlite3.Connection) -> dict[str, int]:
    counts = {
        "media_embeddings": _count_table(conn, "media_embeddings"),
        "media_text": _count_table(conn, "media_text"),
        "media_metadata": _count_table(conn, "media_metadata"),
    }
    conn.execute("DELETE FROM media_embeddings")
    conn.execute("DELETE FROM media_text")
    conn.execute("DELETE FROM media_metadata")
    conn.commit()
    return counts


def media_counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        "media_metadata": _count_table(conn, "media_metadata"),
        "media_text": _count_table(conn, "media_text"),
        "media_embeddings": _count_table(conn, "media_embeddings"),
        "cache_size_bytes": _sum_length(conn, "media_text", "text")
        + _sum_length(conn, "media_metadata", "metadata_json"),
    }


def _count_table(conn: sqlite3.Connection, table: str) -> int:
    try:
        return int(conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"])
    except sqlite3.Error:
        return 0


def _sum_length(conn: sqlite3.Connection, table: str, column: str) -> int:
    try:
        return int(conn.execute(f"SELECT COALESCE(SUM(LENGTH({column})), 0) AS bytes FROM {table}").fetchone()["bytes"])
    except sqlite3.Error:
        return 0
