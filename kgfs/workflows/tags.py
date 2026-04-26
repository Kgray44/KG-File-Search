"""Local file tags stored in KGFS SQLite."""

from __future__ import annotations

import sqlite3

from kgfs.core.models import SearchResult
from kgfs.db.latest_results import save_latest_results
from kgfs.workflows.models import latest_file_id, load_file_result, normalize_tag, utc_now


def tag_result(conn: sqlite3.Connection, result_id: int, tags: list[str]) -> list[str]:
    file_id = latest_file_id(conn, result_id)
    normalized = [normalize_tag(tag) for tag in tags]
    now = utc_now()
    for tag in normalized:
        conn.execute("INSERT OR IGNORE INTO tags(name, created_at) VALUES (?, ?)", (tag, now))
        tag_row = conn.execute("SELECT id FROM tags WHERE name = ?", (tag,)).fetchone()
        conn.execute(
            "INSERT OR IGNORE INTO file_tags(file_id, tag_id, created_at) VALUES (?, ?, ?)",
            (file_id, int(tag_row["id"]), now),
        )
    conn.commit()
    return list_file_tags(conn, result_id)


def untag_result(conn: sqlite3.Connection, result_id: int, tags: list[str]) -> list[str]:
    file_id = latest_file_id(conn, result_id)
    for tag in [normalize_tag(item) for item in tags]:
        row = conn.execute("SELECT id FROM tags WHERE name = ?", (tag,)).fetchone()
        if row:
            conn.execute("DELETE FROM file_tags WHERE file_id = ? AND tag_id = ?", (file_id, int(row["id"])))
    conn.commit()
    return list_file_tags(conn, result_id)


def list_file_tags(conn: sqlite3.Connection, result_id: int) -> list[str]:
    file_id = latest_file_id(conn, result_id)
    rows = conn.execute(
        """
        SELECT t.name
        FROM file_tags ft
        JOIN tags t ON t.id = ft.tag_id
        WHERE ft.file_id = ?
        ORDER BY t.name
        """,
        (file_id,),
    ).fetchall()
    return [row["name"] for row in rows]


def list_tagged_files(conn: sqlite3.Connection, tag: str, *, save_latest: bool = False) -> list[SearchResult]:
    normalized = normalize_tag(tag)
    rows = conn.execute(
        """
        SELECT ft.file_id
        FROM file_tags ft
        JOIN tags t ON t.id = ft.tag_id
        WHERE t.name = ?
        ORDER BY ft.file_id
        """,
        (normalized,),
    ).fetchall()
    results = [
        load_file_result(conn, int(row["file_id"]), result_id=index, query=normalized)
        for index, row in enumerate(rows, start=1)
    ]
    if save_latest:
        save_latest_results(conn, f"tag:{normalized}", results)
    return results


def list_all_tags(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name FROM tags ORDER BY name").fetchall()
    return [row["name"] for row in rows]
