"""SQLite schema versioning and migrations."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

CURRENT_SCHEMA_VERSION = 2


def migrate_database(conn: sqlite3.Connection) -> None:
    """Apply idempotent database migrations.

    Version 1 is the initial KGFS schema plus precise modified-time metadata.
    Version 2 adds OCR extraction source metadata and the local OCR cache table.
    The function is intentionally safe to run after every initialization.
    """

    _ensure_schema_version_table(conn)
    _ensure_files_columns(conn)
    current = get_schema_version(conn)
    if current > CURRENT_SCHEMA_VERSION:
        raise RuntimeError(
            f"Database schema version {current} is newer than this KGFS version "
            f"({CURRENT_SCHEMA_VERSION})."
        )
    _ensure_ocr_cache_table(conn)
    if current < 2:
        _set_schema_version(conn, 2)
    conn.commit()


def get_schema_version(conn: sqlite3.Connection) -> int:
    try:
        row = conn.execute("SELECT version FROM schema_version WHERE id = 1").fetchone()
    except sqlite3.OperationalError:
        return 0
    return int(row["version"] if isinstance(row, sqlite3.Row) else row[0]) if row else 0


def _ensure_schema_version_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            version INTEGER NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


def _ensure_files_columns(conn: sqlite3.Connection) -> None:
    try:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(files)").fetchall()}
    except (sqlite3.OperationalError, TypeError):
        return
    if columns and "modified_time_ns" not in columns:
        conn.execute("ALTER TABLE files ADD COLUMN modified_time_ns INTEGER")
    if columns and "extraction_source" not in columns:
        conn.execute("ALTER TABLE files ADD COLUMN extraction_source TEXT NOT NULL DEFAULT 'text'")


def _ensure_ocr_cache_table(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS ocr_cache (
            id INTEGER PRIMARY KEY,
            file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
            normalized_path TEXT NOT NULL,
            content_hash TEXT,
            size INTEGER NOT NULL,
            modified_time_ns INTEGER NOT NULL,
            backend TEXT NOT NULL,
            language TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            text TEXT NOT NULL,
            status TEXT NOT NULL,
            error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(normalized_path, content_hash, size, modified_time_ns, backend, language, source_kind)
        );

        CREATE INDEX IF NOT EXISTS idx_ocr_cache_lookup
        ON ocr_cache(normalized_path, content_hash, size, modified_time_ns, backend, language, source_kind);
        """
    )


def _set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(
        """
        INSERT INTO schema_version(id, version, applied_at)
        VALUES (1, ?, ?)
        ON CONFLICT(id) DO UPDATE SET version = excluded.version, applied_at = excluded.applied_at
        """,
        (version, datetime.now(timezone.utc).isoformat()),
    )
