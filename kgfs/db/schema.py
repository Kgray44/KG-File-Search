"""SQLite schema creation helpers."""

from __future__ import annotations

import sqlite3

from kgfs.db.migrations import migrate_database


def initialize_database(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL,
            normalized_path TEXT NOT NULL UNIQUE,
            file_name TEXT NOT NULL,
            extension TEXT NOT NULL,
            size INTEGER NOT NULL,
            modified_time REAL NOT NULL,
            modified_time_ns INTEGER,
            content_hash TEXT,
            extracted_text TEXT NOT NULL,
            indexed_at TEXT NOT NULL,
            platform_indexed_from TEXT NOT NULL,
            extraction_status TEXT NOT NULL,
            extraction_error TEXT
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
            file_name,
            path,
            extracted_text,
            tokenize='porter unicode61'
        );

        CREATE TABLE IF NOT EXISTS latest_results (
            result_id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            query TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            embedding BLOB NOT NULL,
            embedding_dim INTEGER NOT NULL,
            start_char INTEGER,
            end_char INTEGER,
            model_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(file_id, chunk_index, model_name)
        );

        CREATE INDEX IF NOT EXISTS idx_chunks_file_id ON chunks(file_id);
        CREATE INDEX IF NOT EXISTS idx_chunks_model_name ON chunks(model_name);
        """
    )
    migrate_database(conn)
    conn.commit()


def check_fts5_available() -> bool:
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute("CREATE VIRTUAL TABLE fts_check USING fts5(content)")
        return True
    except sqlite3.OperationalError:
        return False
    finally:
        conn.close()
