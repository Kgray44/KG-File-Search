"""SQLite schema versioning and migrations."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

CURRENT_SCHEMA_VERSION = 3


def migrate_database(conn: sqlite3.Connection) -> None:
    """Apply idempotent database migrations.

    Version 1 is the initial KGFS schema plus precise modified-time metadata.
    Version 2 adds OCR extraction source metadata and the local OCR cache table.
    Version 3 adds local personal workflow metadata tables.
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
    _ensure_workflow_tables(conn)
    if current < 3:
        _set_schema_version(conn, 3)
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


def _ensure_workflow_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            folders_json TEXT NOT NULL DEFAULT '[]',
            extensions_json TEXT NOT NULL DEFAULT '[]',
            default_mode TEXT NOT NULL DEFAULT 'auto',
            boost_terms_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS saved_searches (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            query TEXT NOT NULL,
            mode TEXT,
            filters_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS collections (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS collection_items (
            id INTEGER PRIMARY KEY,
            collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
            file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
            result_id INTEGER,
            note TEXT,
            added_at TEXT NOT NULL,
            UNIQUE(collection_id, file_id)
        );

        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS file_tags (
            file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
            tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            PRIMARY KEY(file_id, tag_id)
        );

        CREATE TABLE IF NOT EXISTS file_notes (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
            note TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS project_items (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
            role TEXT,
            added_at TEXT NOT NULL,
            UNIQUE(project_id, file_id)
        );

        CREATE TABLE IF NOT EXISTS assignment_runs (
            id INTEGER PRIMARY KEY,
            topic TEXT NOT NULL,
            created_at TEXT NOT NULL,
            query_json TEXT,
            result_json TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_profiles_name ON profiles(name);
        CREATE INDEX IF NOT EXISTS idx_saved_searches_name ON saved_searches(name);
        CREATE INDEX IF NOT EXISTS idx_collections_name ON collections(name);
        CREATE INDEX IF NOT EXISTS idx_collection_items_collection ON collection_items(collection_id);
        CREATE INDEX IF NOT EXISTS idx_collection_items_file ON collection_items(file_id);
        CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
        CREATE INDEX IF NOT EXISTS idx_file_tags_tag ON file_tags(tag_id);
        CREATE INDEX IF NOT EXISTS idx_file_notes_file ON file_notes(file_id);
        CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);
        CREATE INDEX IF NOT EXISTS idx_project_items_project ON project_items(project_id);
        CREATE INDEX IF NOT EXISTS idx_project_items_file ON project_items(file_id);
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
