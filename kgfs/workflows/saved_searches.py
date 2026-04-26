"""Saved search metadata and execution."""

from __future__ import annotations

import sqlite3
from typing import Any

from kgfs.core.config import KGFSConfig
from kgfs.db.latest_results import save_latest_results
from kgfs.search.engine import SearchContext
from kgfs.search.filters import SearchFilters
from kgfs.search.options import SearchOptions
from kgfs.search.registry import build_default_search_registry
from kgfs.workflows.models import SavedSearch, WorkflowSearchReport, dumps_json, loads_json, normalize_name, utc_now


def save_search(
    conn: sqlite3.Connection,
    name: str,
    query: str,
    *,
    mode: str | None = None,
    filters: dict[str, Any] | None = None,
    replace: bool = False,
) -> SavedSearch:
    name = normalize_name(name)
    if not str(query).strip():
        raise ValueError("Saved search query cannot be empty.")
    existing = get_saved_search(conn, name)
    if existing is not None and not replace:
        raise ValueError(f"Saved search already exists: {name}. Use --replace to update it.")
    now = utc_now()
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
        (name, query, mode, dumps_json(filters or {}), now, now),
    )
    conn.commit()
    saved = get_saved_search(conn, name)
    assert saved is not None
    return saved


def get_saved_search(conn: sqlite3.Connection, name: str) -> SavedSearch | None:
    row = conn.execute("SELECT * FROM saved_searches WHERE name = ?", (normalize_name(name),)).fetchone()
    return _row_to_saved_search(row) if row else None


def list_saved_searches(conn: sqlite3.Connection) -> list[SavedSearch]:
    return [_row_to_saved_search(row) for row in conn.execute("SELECT * FROM saved_searches ORDER BY name").fetchall()]


def delete_saved_search(conn: sqlite3.Connection, name: str) -> bool:
    cursor = conn.execute("DELETE FROM saved_searches WHERE name = ?", (normalize_name(name),))
    conn.commit()
    return cursor.rowcount > 0


def run_saved_search(
    conn: sqlite3.Connection,
    name: str,
    config: KGFSConfig,
    *,
    limit: int | None = None,
) -> WorkflowSearchReport:
    saved = get_saved_search(conn, name)
    if saved is None:
        raise ValueError(f"Unknown saved search: {name}")
    filters = _filters_from_dict(saved.filters)
    registry = build_default_search_registry()
    execution = registry.search(
        saved.query,
        SearchOptions(
            mode=saved.mode or config.search.default_mode,
            limit=limit or config.search.default_limit,
            filters=filters,
            highlight=config.search.highlight_matches,
            save_latest_results=False,
        ),
        SearchContext(conn=conn, config=config),
    )
    if config.search.save_latest_results:
        save_latest_results(conn, saved.query, execution.results)
    return WorkflowSearchReport(
        name=saved.name, query=saved.query, results=execution.results, warnings=execution.warnings
    )


def _filters_from_dict(data: dict[str, Any]) -> SearchFilters:
    return SearchFilters(
        extensions=data.get("extensions"),
        file_type=data.get("file_type"),
        folder=data.get("folder"),
        after=data.get("after"),
        before=data.get("before"),
        failed_only=bool(data.get("failed_only", False)),
    )


def _row_to_saved_search(row) -> SavedSearch:
    return SavedSearch(
        id=int(row["id"]),
        name=row["name"],
        query=row["query"],
        mode=row["mode"],
        filters=dict(loads_json(row["filters_json"], {})),
    )
