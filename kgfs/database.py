"""SQLite database schema and persistence helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterator

from kgfs.models import FileRecord


def connect_database(database_path: Path) -> sqlite3.Connection:
    database_path = database_path.expanduser()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database_path)
    conn.row_factory = _row_factory
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


class KGFSRow:
    def __init__(self, keys: list[str], values: tuple[Any, ...]) -> None:
        self._keys = keys
        self._values = values
        self._index = {key: index for index, key in enumerate(keys)}

    def __getitem__(self, key: str | int) -> Any:
        if isinstance(key, str):
            return self._values[self._index[key]]
        return self._values[key]

    def __iter__(self) -> Iterator[Any]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, tuple):
            return self._values == other
        if isinstance(other, KGFSRow):
            return self._values == other._values
        return False

    def keys(self) -> list[str]:
        return self._keys.copy()


def _row_factory(cursor: sqlite3.Cursor, row: tuple[Any, ...]) -> KGFSRow:
    return KGFSRow([description[0] for description in cursor.description], row)


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


def get_existing_file(conn: sqlite3.Connection, normalized_path: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM files WHERE normalized_path = ?",
        (normalized_path,),
    ).fetchone()


def upsert_file(conn: sqlite3.Connection, record: FileRecord) -> int:
    existing = get_existing_file(conn, record.normalized_path)
    values = (
        str(record.path),
        record.normalized_path,
        record.file_name,
        record.extension,
        record.size,
        record.modified_time,
        record.content_hash,
        record.extracted_text,
        record.indexed_at,
        record.platform_indexed_from,
        record.extraction_status,
        record.extraction_error,
    )
    if existing:
        file_id = int(existing["id"])
        conn.execute(
            """
            UPDATE files
            SET path = ?, normalized_path = ?, file_name = ?, extension = ?, size = ?,
                modified_time = ?, content_hash = ?, extracted_text = ?, indexed_at = ?,
                platform_indexed_from = ?, extraction_status = ?, extraction_error = ?
            WHERE id = ?
            """,
            values + (file_id,),
        )
        conn.execute("DELETE FROM files_fts WHERE rowid = ?", (file_id,))
    else:
        cursor = conn.execute(
            """
            INSERT INTO files (
                path, normalized_path, file_name, extension, size, modified_time,
                content_hash, extracted_text, indexed_at, platform_indexed_from,
                extraction_status, extraction_error
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        file_id = int(cursor.lastrowid)

    conn.execute(
        "INSERT INTO files_fts(rowid, file_name, path, extracted_text) VALUES (?, ?, ?, ?)",
        (file_id, record.file_name, str(record.path), record.extracted_text),
    )
    conn.commit()
    return file_id


def delete_chunks_for_file(conn: sqlite3.Connection, file_id: int, model_name: str | None = None) -> None:
    if model_name is None:
        conn.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))
    else:
        conn.execute("DELETE FROM chunks WHERE file_id = ? AND model_name = ?", (file_id, model_name))
    conn.commit()


def count_chunks_for_file(conn: sqlite3.Connection, file_id: int, model_name: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS count FROM chunks WHERE file_id = ? AND model_name = ?",
        (file_id, model_name),
    ).fetchone()
    return int(row["count"])


def get_database_stats(conn: sqlite3.Connection, database_path: Path | None = None) -> dict[str, Any]:
    total = conn.execute("SELECT COUNT(*) AS count, COALESCE(SUM(size), 0) AS bytes FROM files").fetchone()
    types = conn.execute(
        "SELECT extension, COUNT(*) AS count FROM files GROUP BY extension ORDER BY count DESC"
    ).fetchall()
    largest = conn.execute(
        "SELECT file_name, path, size FROM files ORDER BY size DESC LIMIT 5"
    ).fetchall()
    failures = conn.execute(
        "SELECT COUNT(*) AS count FROM files WHERE extraction_status = 'error'"
    ).fetchone()
    last_indexed = conn.execute("SELECT MAX(indexed_at) AS last_indexed FROM files").fetchone()
    chunks = conn.execute("SELECT COUNT(*) AS count, COALESCE(SUM(LENGTH(embedding)), 0) AS bytes FROM chunks").fetchone()
    db_size = database_path.stat().st_size if database_path and database_path.exists() else 0
    return {
        "total_files": int(total["count"]),
        "total_size": int(total["bytes"]),
        "total_chunks": int(chunks["count"]),
        "embedding_bytes": int(chunks["bytes"]),
        "file_types": [(row["extension"], int(row["count"])) for row in types],
        "largest_files": [(row["file_name"], row["path"], int(row["size"])) for row in largest],
        "extraction_failures": int(failures["count"]),
        "last_indexed": last_indexed["last_indexed"],
        "database_size": db_size,
    }
