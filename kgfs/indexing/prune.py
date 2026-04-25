"""Prune stale KGFS database records without touching source files."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PruneSummary:
    stale_paths: list[Path]
    removed: int = 0
    dry_run: bool = False


def find_stale_files(conn: sqlite3.Connection) -> list[Path]:
    rows = conn.execute("SELECT path FROM files ORDER BY path").fetchall()
    return [Path(row["path"]) for row in rows if not Path(row["path"]).exists()]


def prune_stale_files(conn: sqlite3.Connection, *, dry_run: bool = False) -> PruneSummary:
    rows = conn.execute("SELECT id, path FROM files ORDER BY path").fetchall()
    stale_rows = [(int(row["id"]), Path(row["path"])) for row in rows if not Path(row["path"]).exists()]
    if dry_run or not stale_rows:
        return PruneSummary(stale_paths=[path for _, path in stale_rows], removed=0, dry_run=dry_run)

    file_ids = [file_id for file_id, _ in stale_rows]
    placeholders = ", ".join("?" for _ in file_ids)
    conn.execute(f"DELETE FROM latest_results WHERE file_id IN ({placeholders})", tuple(file_ids))
    conn.execute(f"DELETE FROM chunks WHERE file_id IN ({placeholders})", tuple(file_ids))
    conn.execute(f"DELETE FROM files_fts WHERE rowid IN ({placeholders})", tuple(file_ids))
    conn.execute(f"DELETE FROM files WHERE id IN ({placeholders})", tuple(file_ids))
    conn.commit()
    return PruneSummary(stale_paths=[path for _, path in stale_rows], removed=len(stale_rows), dry_run=False)
