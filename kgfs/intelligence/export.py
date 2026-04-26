"""Export/import KGFS workflow metadata without copying source files."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from kgfs.core.app_dirs import AppPaths
from kgfs.core.config import KGFSConfig
from kgfs.intelligence.models import MetadataExportSummary
from kgfs.workflows.models import utc_now

EXPORT_VERSION = 1


def export_metadata(conn: sqlite3.Connection) -> dict[str, Any]:
    """Return a JSON-serializable KGFS metadata backup.

    The export intentionally excludes source file contents, extracted text,
    vector blobs, OCR cache text, API keys, and model caches.
    """

    files = {int(row["id"]): _file_identity(row) for row in _file_rows(conn)}
    payload = {
        "export_version": EXPORT_VERSION,
        "created_at": utc_now(),
        "profiles": _table_rows(conn, "profiles"),
        "saved_searches": _table_rows(conn, "saved_searches"),
        "collections": _collections(conn, files),
        "tags": _tags(conn, files),
        "notes": _notes(conn, files),
        "projects": _projects(conn, files),
        "assignment_runs": _table_rows(conn, "assignment_runs"),
    }
    return payload


def import_metadata(conn: sqlite3.Connection, payload: dict[str, Any], *, yes: bool = False) -> MetadataExportSummary:
    if not yes:
        raise ValueError("metadata import requires yes=True")
    restored = 0
    unmatched = 0
    warnings: list[str] = []

    for row in payload.get("profiles", []):
        conn.execute(
            """
            INSERT INTO profiles(name, description, folders_json, extensions_json, default_mode, boost_terms_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                description = excluded.description,
                folders_json = excluded.folders_json,
                extensions_json = excluded.extensions_json,
                default_mode = excluded.default_mode,
                boost_terms_json = excluded.boost_terms_json,
                updated_at = excluded.updated_at
            """,
            (
                row["name"],
                row.get("description"),
                row.get("folders_json", "[]"),
                row.get("extensions_json", "[]"),
                row.get("default_mode", "auto"),
                row.get("boost_terms_json", "[]"),
                row.get("created_at", utc_now()),
                utc_now(),
            ),
        )
        restored += 1

    for row in payload.get("saved_searches", []):
        conn.execute(
            """
            INSERT INTO saved_searches(name, query, mode, filters_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                query = excluded.query,
                mode = excluded.mode,
                filters_json = excluded.filters_json,
                updated_at = excluded.updated_at
            """,
            (row["name"], row["query"], row.get("mode"), row.get("filters_json"), row.get("created_at", utc_now()), utc_now()),
        )
        restored += 1

    for collection in payload.get("collections", []):
        conn.execute(
            """
            INSERT INTO collections(name, description, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET description = excluded.description, updated_at = excluded.updated_at
            """,
            (collection["name"], collection.get("description"), collection.get("created_at", utc_now()), utc_now()),
        )
        collection_id = conn.execute("SELECT id FROM collections WHERE name = ?", (collection["name"],)).fetchone()["id"]
        restored += 1
        for item in collection.get("items", []):
            file_id = _match_file(conn, item.get("file"))
            if file_id is None:
                unmatched += 1
                warnings.append(f"Unmatched collection item in {collection['name']}: {item.get('file', {}).get('file_name', '?')}")
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO collection_items(collection_id, file_id, result_id, note, added_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (collection_id, file_id, item.get("result_id"), item.get("note"), item.get("added_at", utc_now())),
            )
            restored += 1

    for tag in payload.get("tags", []):
        tag_id = _ensure_tag(conn, tag["name"], tag.get("created_at"))
        restored += 1
        for file_identity in tag.get("files", []):
            file_id = _match_file(conn, file_identity)
            if file_id is None:
                unmatched += 1
                warnings.append(f"Unmatched tag item for {tag['name']}: {file_identity.get('file_name', '?')}")
                continue
            conn.execute(
                "INSERT OR IGNORE INTO file_tags(file_id, tag_id, created_at) VALUES (?, ?, ?)",
                (file_id, tag_id, utc_now()),
            )
            restored += 1

    for note in payload.get("notes", []):
        file_id = _match_file(conn, note.get("file"))
        if file_id is None:
            unmatched += 1
            warnings.append(f"Unmatched note item: {note.get('file', {}).get('file_name', '?')}")
            continue
        existing = conn.execute(
            "SELECT id FROM file_notes WHERE file_id = ? AND note = ?",
            (file_id, note["note"]),
        ).fetchone()
        if existing is None:
            conn.execute(
                "INSERT INTO file_notes(file_id, note, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (file_id, note["note"], note.get("created_at", utc_now()), utc_now()),
            )
        restored += 1

    for project in payload.get("projects", []):
        conn.execute(
            """
            INSERT INTO projects(name, description, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET description = excluded.description, updated_at = excluded.updated_at
            """,
            (project["name"], project.get("description"), project.get("created_at", utc_now()), utc_now()),
        )
        project_id = conn.execute("SELECT id FROM projects WHERE name = ?", (project["name"],)).fetchone()["id"]
        restored += 1
        for item in project.get("items", []):
            file_id = _match_file(conn, item.get("file"))
            if file_id is None:
                unmatched += 1
                warnings.append(f"Unmatched project item in {project['name']}: {item.get('file', {}).get('file_name', '?')}")
                continue
            conn.execute(
                "INSERT OR IGNORE INTO project_items(project_id, file_id, role, added_at) VALUES (?, ?, ?, ?)",
                (project_id, file_id, item.get("role"), item.get("added_at", utc_now())),
            )
            restored += 1

    for row in payload.get("assignment_runs", []):
        created_at = row.get("created_at", utc_now())
        query_json = row.get("query_json")
        result_json = row.get("result_json")
        existing = conn.execute(
            """
            SELECT id
            FROM assignment_runs
            WHERE topic = ? AND created_at = ? AND query_json IS ? AND result_json IS ?
            """,
            (row["topic"], created_at, query_json, result_json),
        ).fetchone()
        if existing is None:
            conn.execute(
                """
                INSERT INTO assignment_runs(topic, created_at, query_json, result_json)
                VALUES (?, ?, ?, ?)
                """,
                (row["topic"], created_at, query_json, result_json),
            )
        restored += 1

    conn.commit()
    return MetadataExportSummary(restored_items=restored, unmatched_items=unmatched, warnings=warnings)


def write_metadata_export(conn: sqlite3.Connection, output_path: Path) -> MetadataExportSummary:
    output_path = output_path.expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = export_metadata(conn)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return MetadataExportSummary(exported_items=_exported_item_count(payload), path=output_path)


def read_metadata_export(input_path: Path) -> dict[str, Any]:
    return json.loads(input_path.expanduser().read_text(encoding="utf-8"))


def create_metadata_backup(
    conn: sqlite3.Connection,
    app_paths: AppPaths,
    config: KGFSConfig,
    *,
    note: str | None = None,
) -> MetadataExportSummary:
    backup_dir = config.metadata.backup_dir or (app_paths.data_dir / "metadata-backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    output_path = backup_dir / f"kgfs-metadata-{utc_now().replace(':', '-').replace('.', '-')}.json"
    summary = write_metadata_export(conn, output_path)
    conn.execute(
        "INSERT INTO metadata_backups(path, created_at, note) VALUES (?, ?, ?)",
        (str(output_path), utc_now(), note),
    )
    conn.commit()
    return summary


def _file_rows(conn: sqlite3.Connection) -> list:
    return conn.execute(
        """
        SELECT id, normalized_path, path, file_name, size, modified_time, modified_time_ns, content_hash
        FROM files
        """
    ).fetchall()


def _file_identity(row) -> dict[str, Any]:
    return {
        "file_id": int(row["id"]),
        "normalized_path": row["normalized_path"],
        "path": row["path"],
        "file_name": row["file_name"],
        "size": int(row["size"]),
        "modified_time": float(row["modified_time"]),
        "modified_time_ns": int(row["modified_time_ns"]) if row["modified_time_ns"] is not None else None,
        "content_hash": row["content_hash"],
    }


def _table_rows(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()]


def _collections(conn: sqlite3.Connection, files: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    collections = _table_rows(conn, "collections")
    for collection in collections:
        rows = conn.execute("SELECT * FROM collection_items WHERE collection_id = ? ORDER BY id", (collection["id"],)).fetchall()
        collection["items"] = [
            {
                "file": files.get(int(row["file_id"])),
                "result_id": row["result_id"],
                "note": row["note"],
                "added_at": row["added_at"],
            }
            for row in rows
            if int(row["file_id"]) in files
        ]
    return collections


def _tags(conn: sqlite3.Connection, files: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    tags = _table_rows(conn, "tags")
    for tag in tags:
        rows = conn.execute("SELECT file_id FROM file_tags WHERE tag_id = ? ORDER BY file_id", (tag["id"],)).fetchall()
        tag["files"] = [files[int(row["file_id"])] for row in rows if int(row["file_id"]) in files]
    return tags


def _notes(conn: sqlite3.Connection, files: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM file_notes ORDER BY id").fetchall()
    return [
        {
            "file": files[int(row["file_id"])],
            "note": row["note"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
        if int(row["file_id"]) in files
    ]


def _projects(conn: sqlite3.Connection, files: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    projects = _table_rows(conn, "projects")
    for project in projects:
        rows = conn.execute("SELECT * FROM project_items WHERE project_id = ? ORDER BY id", (project["id"],)).fetchall()
        project["items"] = [
            {
                "file": files[int(row["file_id"])],
                "role": row["role"],
                "added_at": row["added_at"],
            }
            for row in rows
            if int(row["file_id"]) in files
        ]
    return projects


def _match_file(conn: sqlite3.Connection, identity: dict[str, Any] | None) -> int | None:
    if not identity:
        return None
    normalized_path = identity.get("normalized_path")
    if normalized_path:
        row = conn.execute("SELECT id FROM files WHERE normalized_path = ?", (normalized_path,)).fetchone()
        if row:
            return int(row["id"])
    path = identity.get("path")
    if path:
        row = conn.execute("SELECT id FROM files WHERE path = ?", (path,)).fetchone()
        if row:
            return int(row["id"])
    content_hash = identity.get("content_hash")
    if content_hash:
        row = conn.execute(
            """
            SELECT id
            FROM files
            WHERE content_hash = ? AND file_name = ? AND size = ?
            ORDER BY id
            LIMIT 1
            """,
            (content_hash, identity.get("file_name"), identity.get("size")),
        ).fetchone()
        if row:
            return int(row["id"])
        row = conn.execute("SELECT id FROM files WHERE content_hash = ? ORDER BY id LIMIT 1", (content_hash,)).fetchone()
        if row:
            return int(row["id"])
    row = conn.execute(
        "SELECT id FROM files WHERE file_name = ? AND size = ? ORDER BY id LIMIT 1",
        (identity.get("file_name"), identity.get("size")),
    ).fetchone()
    return int(row["id"]) if row else None


def _ensure_tag(conn: sqlite3.Connection, name: str, created_at: str | None = None) -> int:
    conn.execute(
        "INSERT OR IGNORE INTO tags(name, created_at) VALUES (?, ?)",
        (name, created_at or utc_now()),
    )
    return int(conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()["id"])


def _exported_item_count(payload: dict[str, Any]) -> int:
    total = 0
    for key, value in payload.items():
        if isinstance(value, list):
            total += len(value)
    return total
