"""Read-only SQLite integrity and metadata sanity checks."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from kgfs.core.config import KGFSConfig
from kgfs.db.migrations import CURRENT_SCHEMA_VERSION, get_schema_version
from kgfs.models.storage import model_cache_dir
from kgfs.vectors.storage import vector_backends_root

FILE_REFERENCE_COLUMNS = (
    ("chunks", "file_id"),
    ("ocr_cache", "file_id"),
    ("collection_items", "file_id"),
    ("file_tags", "file_id"),
    ("file_notes", "file_id"),
    ("project_items", "file_id"),
    ("graph_edges", "source_file_id"),
    ("graph_edges", "target_file_id"),
    ("media_metadata", "file_id"),
    ("media_text", "file_id"),
    ("media_embeddings", "file_id"),
)


@dataclass(frozen=True)
class DatabaseCheckReport:
    database_path: Path
    integrity_check: str
    schema_version: int
    expected_schema_version: int
    foreign_key_violations: list[tuple[object, ...]] = field(default_factory=list)
    orphaned_metadata: dict[str, int] = field(default_factory=dict)
    artifact_sanity: str = "ok"

    @property
    def ok(self) -> bool:
        return (
            self.integrity_check.lower() == "ok"
            and self.schema_version == self.expected_schema_version
            and not self.foreign_key_violations
            and sum(self.orphaned_metadata.values()) == 0
            and self.artifact_sanity.startswith("ok")
        )


def check_database(database_path: Path, config: KGFSConfig) -> DatabaseCheckReport:
    """Run read-only sanity checks against an existing KGFS SQLite database."""

    path = database_path.expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Database does not exist: {path}")

    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        integrity_row = conn.execute("PRAGMA integrity_check").fetchone()
        integrity = str(integrity_row[0]) if integrity_row else "unknown"
        foreign_key_violations = [tuple(row) for row in conn.execute("PRAGMA foreign_key_check").fetchall()]
        schema_version = get_schema_version(conn)
        orphaned_metadata = _count_orphaned_metadata(conn)
    finally:
        conn.close()

    return DatabaseCheckReport(
        database_path=path,
        integrity_check=integrity,
        schema_version=schema_version,
        expected_schema_version=CURRENT_SCHEMA_VERSION,
        foreign_key_violations=foreign_key_violations,
        orphaned_metadata=orphaned_metadata,
        artifact_sanity=_check_artifact_sanity(config),
    )


def _count_orphaned_metadata(conn: sqlite3.Connection) -> dict[str, int]:
    if not _table_exists(conn, "files"):
        return {}
    counts: dict[str, int] = {}
    for table, column in FILE_REFERENCE_COLUMNS:
        if not _table_exists(conn, table):
            continue
        query = (
            f"SELECT COUNT(*) FROM {table} AS child "
            f"LEFT JOIN files ON child.{column} = files.id "
            f"WHERE child.{column} IS NOT NULL AND files.id IS NULL"
        )
        count = int(conn.execute(query).fetchone()[0])
        if count:
            counts[f"{table}.{column}"] = count
    return counts


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _check_artifact_sanity(config: KGFSConfig) -> str:
    root = vector_backends_root(config)
    notes: list[str] = []
    if not root.exists():
        notes.append("no vector backend artifacts found")
    else:
        if config.database_path is not None:
            expected_parent = config.database_path.expanduser().parent.resolve()
            resolved = root.resolve()
            if expected_parent != resolved and expected_parent not in resolved.parents:
                return f"warning: vector artifact root is outside the database directory ({resolved})"
        artifact_count = sum(1 for item in root.rglob("*") if item.is_file())
        notes.append(f"{artifact_count} vector backend artifact file(s)")
    model_root = model_cache_dir(config, _dummy_app_paths(config))
    if model_root.exists():
        notes.append(f"{sum(1 for item in model_root.rglob('*') if item.is_file())} model cache file(s)")
    else:
        notes.append("no model cache artifacts found")
    return "ok: " + "; ".join(notes)


def _dummy_app_paths(config: KGFSConfig):
    class _Paths:
        cache_dir: Path

    paths = _Paths()
    if config.database_path is not None:
        paths.cache_dir = config.database_path.expanduser().parent / "cache"
    else:
        paths.cache_dir = Path(".kgfs") / "cache"
    return paths
