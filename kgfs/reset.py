"""Database reset and rebuild helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kgfs.config import KGFSConfig
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.models import IndexSummary


@dataclass(frozen=True)
class ResetSummary:
    database_path: Path
    removed_paths: list[Path]
    would_remove: bool = False
    dry_run: bool = False


def reset_index(database_path: Path, *, dry_run: bool = False, yes: bool = False) -> ResetSummary:
    """Remove only KGFS database files, never indexed source files."""

    db_path = database_path.expanduser()
    targets = _database_targets(db_path)
    existing = [path for path in targets if path.exists()]
    if dry_run:
        return ResetSummary(database_path=db_path, removed_paths=[], would_remove=bool(existing), dry_run=True)
    if not yes:
        raise ValueError("reset_index requires yes=True unless dry_run=True")
    removed: list[Path] = []
    for path in existing:
        path.unlink()
        removed.append(path)
    return ResetSummary(database_path=db_path, removed_paths=removed, would_remove=False, dry_run=False)


def rebuild_index(
    config: KGFSConfig,
    database_path: Path,
    *,
    allow_risky_root: bool = False,
    force: bool = True,
    verify_hashes: bool = False,
) -> IndexSummary:
    reset_index(database_path, yes=True)
    conn = connect_database(database_path)
    initialize_database(conn)
    try:
        return index_configured_folders(
            config,
            conn,
            allow_risky_root=allow_risky_root,
            force=force,
            verify_hashes=verify_hashes,
        )
    finally:
        conn.close()


def _database_targets(database_path: Path) -> list[Path]:
    return [
        database_path,
        Path(f"{database_path}-wal"),
        Path(f"{database_path}-shm"),
        Path(f"{database_path}-journal"),
    ]
