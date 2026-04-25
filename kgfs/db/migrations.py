"""SQLite schema versioning and migrations."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

CURRENT_SCHEMA_VERSION = 1


def migrate_database(conn: sqlite3.Connection) -> None:
    """Apply idempotent database migrations.

    Version 1 is the initial KGFS schema plus precise modified-time metadata.
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
    if current < 1:
        _set_schema_version(conn, 1)
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


def _set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(
        """
        INSERT INTO schema_version(id, version, applied_at)
        VALUES (1, ?, ?)
        ON CONFLICT(id) DO UPDATE SET version = excluded.version, applied_at = excluded.applied_at
        """,
        (version, datetime.now(timezone.utc).isoformat()),
    )
