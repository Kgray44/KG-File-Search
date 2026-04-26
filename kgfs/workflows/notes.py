"""Local notes attached to indexed files."""

from __future__ import annotations

import sqlite3

from kgfs.workflows.models import FileNote, latest_file_id, utc_now


def add_note(conn: sqlite3.Connection, result_id: int, note: str) -> FileNote:
    text = str(note).strip()
    if not text:
        raise ValueError("Note text cannot be empty.")
    file_id = latest_file_id(conn, result_id)
    now = utc_now()
    cursor = conn.execute(
        "INSERT INTO file_notes(file_id, note, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (file_id, text, now, now),
    )
    conn.commit()
    return _get_note(conn, int(cursor.lastrowid))


def list_notes(conn: sqlite3.Connection, result_id: int) -> list[FileNote]:
    file_id = latest_file_id(conn, result_id)
    rows = conn.execute(
        "SELECT * FROM file_notes WHERE file_id = ? ORDER BY created_at, id",
        (file_id,),
    ).fetchall()
    return [_row_to_note(row) for row in rows]


def delete_note(conn: sqlite3.Connection, note_id: int) -> bool:
    cursor = conn.execute("DELETE FROM file_notes WHERE id = ?", (int(note_id),))
    conn.commit()
    return cursor.rowcount > 0


def notes_for_file(conn: sqlite3.Connection, file_id: int) -> list[FileNote]:
    rows = conn.execute("SELECT * FROM file_notes WHERE file_id = ? ORDER BY created_at, id", (file_id,)).fetchall()
    return [_row_to_note(row) for row in rows]


def _get_note(conn: sqlite3.Connection, note_id: int) -> FileNote:
    row = conn.execute("SELECT * FROM file_notes WHERE id = ?", (note_id,)).fetchone()
    if row is None:
        raise ValueError(f"Note {note_id} was not found.")
    return _row_to_note(row)


def _row_to_note(row) -> FileNote:
    return FileNote(
        id=int(row["id"]),
        file_id=int(row["file_id"]),
        note=row["note"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
