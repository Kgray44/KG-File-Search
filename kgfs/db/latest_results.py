"""Latest search result persistence for open/reveal commands."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path

from kgfs.core.models import SearchResult


@dataclass(frozen=True)
class LatestResultRecord:
    result_id: int
    file_id: int
    file_path: Path
    query: str
    created_at: str


def save_latest_results(conn: sqlite3.Connection, query: str, results: list[SearchResult]) -> None:
    created_at = datetime.now(timezone.utc).isoformat()
    conn.execute("DELETE FROM latest_results")
    conn.executemany(
        """
        INSERT INTO latest_results(result_id, file_id, file_path, query, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        [(item.result_id, item.file_id, str(item.path), query, created_at) for item in results],
    )
    conn.commit()


def get_latest_result_path(conn: sqlite3.Connection, result_id: int) -> Path | None:
    row = conn.execute(
        "SELECT file_path FROM latest_results WHERE result_id = ?",
        (result_id,),
    ).fetchone()
    return Path(row["file_path"]) if row else None


def get_latest_result_record(conn: sqlite3.Connection, result_id: int) -> LatestResultRecord | None:
    row = conn.execute(
        """
        SELECT result_id, file_id, file_path, query, created_at
        FROM latest_results
        WHERE result_id = ?
        """,
        (result_id,),
    ).fetchone()
    if row is None:
        return None
    return LatestResultRecord(
        result_id=int(row["result_id"]),
        file_id=int(row["file_id"]),
        file_path=Path(row["file_path"]),
        query=row["query"],
        created_at=row["created_at"],
    )
