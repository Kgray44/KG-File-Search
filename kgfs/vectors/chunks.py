"""SQLite chunk lifecycle helpers."""

from __future__ import annotations

import sqlite3


def count_chunks(conn: sqlite3.Connection, *, model_name: str | None = None) -> int:
    if model_name is None:
        row = conn.execute("SELECT COUNT(*) AS count FROM chunks").fetchone()
    else:
        row = conn.execute("SELECT COUNT(*) AS count FROM chunks WHERE model_name = ?", (model_name,)).fetchone()
    return int(row["count"] if row is not None else 0)


def count_files_with_chunks(conn: sqlite3.Connection, *, model_name: str | None = None) -> int:
    if model_name is None:
        row = conn.execute("SELECT COUNT(DISTINCT file_id) AS count FROM chunks").fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(DISTINCT file_id) AS count FROM chunks WHERE model_name = ?",
            (model_name,),
        ).fetchone()
    return int(row["count"] if row is not None else 0)


def clear_chunks(conn: sqlite3.Connection, *, model_name: str | None = None) -> int:
    before = count_chunks(conn, model_name=model_name)
    if model_name is None:
        conn.execute("DELETE FROM chunks")
    else:
        conn.execute("DELETE FROM chunks WHERE model_name = ?", (model_name,))
    conn.commit()
    return before
