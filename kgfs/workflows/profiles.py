"""Search profile storage and execution."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from kgfs.core.config import KGFSConfig
from kgfs.db.latest_results import save_latest_results
from kgfs.search.engine import SearchContext
from kgfs.search.filters import SearchFilters
from kgfs.search.options import SearchOptions
from kgfs.search.registry import build_default_search_registry
from kgfs.workflows.models import (
    Profile,
    WorkflowSearchReport,
    dumps_json,
    loads_json,
    normalize_extensions,
    normalize_name,
    utc_now,
)


def create_profile(
    conn: sqlite3.Connection,
    name: str,
    *,
    folders: list[str | Path] | None = None,
    extensions: list[str] | None = None,
    default_mode: str = "auto",
    boost_terms: list[str] | None = None,
    description: str | None = None,
) -> Profile:
    name = normalize_name(name)
    now = utc_now()
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
            name,
            description,
            dumps_json([str(Path(folder).expanduser()) for folder in folders or []]),
            dumps_json(normalize_extensions(extensions)),
            default_mode,
            dumps_json([str(term).strip() for term in boost_terms or [] if str(term).strip()]),
            now,
            now,
        ),
    )
    conn.commit()
    profile = get_profile(conn, name)
    assert profile is not None
    return profile


def list_profiles(conn: sqlite3.Connection) -> list[Profile]:
    rows = conn.execute("SELECT * FROM profiles ORDER BY name").fetchall()
    return [_row_to_profile(row) for row in rows]


def get_profile(conn: sqlite3.Connection, name: str) -> Profile | None:
    row = conn.execute("SELECT * FROM profiles WHERE name = ?", (normalize_name(name),)).fetchone()
    return _row_to_profile(row) if row else None


def delete_profile(conn: sqlite3.Connection, name: str) -> bool:
    cursor = conn.execute("DELETE FROM profiles WHERE name = ?", (normalize_name(name),))
    conn.commit()
    return cursor.rowcount > 0


def profile_search(
    conn: sqlite3.Connection,
    name: str,
    query: str,
    config: KGFSConfig,
    *,
    limit: int | None = None,
    mode: str | None = None,
) -> WorkflowSearchReport:
    profile = get_profile(conn, name)
    if profile is None:
        raise ValueError(f"Unknown profile: {name}")
    expanded_query = " ".join([query, *profile.boost_terms]).strip()
    filters = SearchFilters(
        extensions=profile.extensions or None,
        folder=profile.folders[0] if profile.folders else None,
    )
    registry = build_default_search_registry()
    execution = registry.search(
        expanded_query,
        SearchOptions(
            mode=mode or profile.default_mode or config.search.default_mode,
            limit=limit or config.search.default_limit,
            filters=filters,
            highlight=config.search.highlight_matches,
            save_latest_results=False,
        ),
        SearchContext(conn=conn, config=config),
    )
    if config.search.save_latest_results:
        save_latest_results(conn, query, execution.results)
    return WorkflowSearchReport(name=profile.name, query=query, results=execution.results, warnings=execution.warnings)


def _row_to_profile(row) -> Profile:
    return Profile(
        id=int(row["id"]),
        name=row["name"],
        description=row["description"],
        folders=list(loads_json(row["folders_json"], [])),
        extensions=list(loads_json(row["extensions_json"], [])),
        default_mode=row["default_mode"],
        boost_terms=list(loads_json(row["boost_terms_json"], [])),
    )
