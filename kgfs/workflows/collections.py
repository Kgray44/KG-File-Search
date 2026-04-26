"""Local file collections stored in the KGFS database."""

from __future__ import annotations

import sqlite3

from kgfs.search.citations import format_citation
from kgfs.workflows.models import (
    AddSummary,
    Collection,
    WorkflowItem,
    latest_file_id,
    load_file_result,
    load_workflow_item,
    normalize_name,
    utc_now,
)


def create_collection(conn: sqlite3.Connection, name: str, description: str | None = None) -> Collection:
    name = normalize_name(name)
    now = utc_now()
    conn.execute(
        """
        INSERT INTO collections(name, description, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET description = COALESCE(excluded.description, collections.description),
                                        updated_at = excluded.updated_at
        """,
        (name, description, now, now),
    )
    conn.commit()
    collection = get_collection(conn, name)
    assert collection is not None
    return collection


def get_collection(conn: sqlite3.Connection, name: str) -> Collection | None:
    row = conn.execute("SELECT * FROM collections WHERE name = ?", (normalize_name(name),)).fetchone()
    return Collection(id=int(row["id"]), name=row["name"], description=row["description"]) if row else None


def list_collections(conn: sqlite3.Connection) -> list[Collection]:
    return [
        Collection(id=int(row["id"]), name=row["name"], description=row["description"])
        for row in conn.execute("SELECT * FROM collections ORDER BY name").fetchall()
    ]


def delete_collection(conn: sqlite3.Connection, name: str) -> bool:
    cursor = conn.execute("DELETE FROM collections WHERE name = ?", (normalize_name(name),))
    conn.commit()
    return cursor.rowcount > 0


def add_results_to_collection(conn: sqlite3.Connection, name: str, result_ids: list[int]) -> AddSummary:
    collection = _require_collection(conn, name)
    file_ids = [latest_file_id(conn, int(result_id)) for result_id in result_ids]
    return add_files_to_collection(conn, collection.name, file_ids, result_ids=result_ids)


def add_files_to_collection(
    conn: sqlite3.Connection,
    name: str,
    file_ids: list[int],
    *,
    result_ids: list[int] | None = None,
) -> AddSummary:
    collection = _require_collection(conn, name)
    before = _collection_file_ids(conn, collection.id)
    now = utc_now()
    for index, file_id in enumerate(file_ids):
        result_id = result_ids[index] if result_ids and index < len(result_ids) else None
        conn.execute(
            """
            INSERT OR IGNORE INTO collection_items(collection_id, file_id, result_id, added_at)
            VALUES (?, ?, ?, ?)
            """,
            (collection.id, int(file_id), result_id, now),
        )
    conn.commit()
    after = _collection_file_ids(conn, collection.id)
    added_ids = sorted(after - before)
    return AddSummary(added=len(added_ids), skipped=len(file_ids) - len(added_ids), file_ids=added_ids)


def remove_files_from_collection(conn: sqlite3.Connection, name: str, file_ids: list[int]) -> int:
    collection = _require_collection(conn, name)
    known_file_ids = _collection_file_ids(conn, collection.id)
    removed = 0
    for value in file_ids:
        file_id = _resolve_collection_file_id(conn, int(value), known_file_ids)
        cursor = conn.execute(
            "DELETE FROM collection_items WHERE collection_id = ? AND file_id = ?",
            (collection.id, file_id),
        )
        removed += cursor.rowcount
    conn.commit()
    return removed


def get_collection_items(conn: sqlite3.Connection, name: str) -> list[WorkflowItem]:
    collection = _require_collection(conn, name)
    rows = conn.execute(
        """
        SELECT ci.id, ci.file_id, ci.result_id, ci.note, f.file_name, f.path, f.extension, f.modified_time
        FROM collection_items ci
        JOIN files f ON f.id = ci.file_id
        WHERE ci.collection_id = ?
        ORDER BY ci.id
        """,
        (collection.id,),
    ).fetchall()
    return [load_workflow_item(conn, row, kind="collection") for row in rows]


def export_collection_markdown(conn: sqlite3.Connection, name: str) -> str:
    collection = _require_collection(conn, name)
    lines = [f"# {collection.name}", ""]
    if collection.description:
        lines.extend([collection.description, ""])
    for index, item in enumerate(get_collection_items(conn, name), start=1):
        result = load_file_result(conn, item.file_id, result_id=index)
        lines.append(f"- {format_citation(result)} - {item.path}")
        if item.note:
            lines.append(f"  - Note: {item.note}")
    return "\n".join(lines) + "\n"


def _require_collection(conn: sqlite3.Connection, name: str) -> Collection:
    collection = get_collection(conn, name)
    if collection is None:
        raise ValueError(f"Unknown collection: {name}")
    return collection


def _collection_file_ids(conn: sqlite3.Connection, collection_id: int) -> set[int]:
    rows = conn.execute("SELECT file_id FROM collection_items WHERE collection_id = ?", (collection_id,)).fetchall()
    return {int(row["file_id"]) for row in rows}


def _resolve_collection_file_id(conn: sqlite3.Connection, value: int, known_file_ids: set[int]) -> int:
    if value in known_file_ids:
        return value
    try:
        resolved = latest_file_id(conn, value)
    except ValueError:
        return value
    return resolved
