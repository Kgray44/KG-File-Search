"""SQLite repository helpers for indexed files and semantic chunks."""

from __future__ import annotations

import sqlite3

from kgfs.core.models import FileRecord


def get_existing_file(conn: sqlite3.Connection, normalized_path: str):
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
        record.modified_time_ns,
        record.content_hash,
        record.extracted_text,
        record.indexed_at,
        record.platform_indexed_from,
        record.extraction_status,
        record.extraction_error,
        record.extraction_source,
    )
    if existing:
        file_id = int(existing["id"])
        conn.execute(
            """
            UPDATE files
            SET path = ?, normalized_path = ?, file_name = ?, extension = ?, size = ?,
                modified_time = ?, modified_time_ns = ?, content_hash = ?, extracted_text = ?, indexed_at = ?,
                platform_indexed_from = ?, extraction_status = ?, extraction_error = ?, extraction_source = ?
            WHERE id = ?
            """,
            values + (file_id,),
        )
    else:
        cursor = conn.execute(
            """
            INSERT INTO files (
                path, normalized_path, file_name, extension, size, modified_time,
                modified_time_ns, content_hash, extracted_text, indexed_at, platform_indexed_from,
                extraction_status, extraction_error, extraction_source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        file_id = int(cursor.lastrowid)

    replace_file_fts_row(conn, file_id, record)
    conn.commit()
    return file_id


def replace_file_fts_row(conn: sqlite3.Connection, file_id: int, record: FileRecord) -> None:
    """Replace the FTS row for a file after insert or update."""

    conn.execute("DELETE FROM files_fts WHERE rowid = ?", (file_id,))
    conn.execute(
        "INSERT INTO files_fts(rowid, file_name, path, extracted_text) VALUES (?, ?, ?, ?)",
        (file_id, record.file_name, str(record.path), record.extracted_text),
    )


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
