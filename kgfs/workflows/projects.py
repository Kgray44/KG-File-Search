"""Manual local project grouping and project-scoped search."""

from __future__ import annotations

import sqlite3

from kgfs.core.config import KGFSConfig
from kgfs.core.models import SearchResult
from kgfs.db.latest_results import save_latest_results
from kgfs.search import search
from kgfs.workflows.models import AddSummary, Project, WorkflowItem, latest_file_id, load_workflow_item, normalize_name, utc_now


def create_project(conn: sqlite3.Connection, name: str, description: str | None = None) -> Project:
    name = normalize_name(name)
    now = utc_now()
    conn.execute(
        """
        INSERT INTO projects(name, description, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET description = COALESCE(excluded.description, projects.description),
                                     updated_at = excluded.updated_at
        """,
        (name, description, now, now),
    )
    conn.commit()
    project = get_project(conn, name)
    assert project is not None
    return project


def get_project(conn: sqlite3.Connection, name: str) -> Project | None:
    row = conn.execute("SELECT * FROM projects WHERE name = ?", (normalize_name(name),)).fetchone()
    return Project(id=int(row["id"]), name=row["name"], description=row["description"]) if row else None


def list_projects(conn: sqlite3.Connection) -> list[Project]:
    return [
        Project(id=int(row["id"]), name=row["name"], description=row["description"])
        for row in conn.execute("SELECT * FROM projects ORDER BY name").fetchall()
    ]


def delete_project(conn: sqlite3.Connection, name: str) -> bool:
    cursor = conn.execute("DELETE FROM projects WHERE name = ?", (normalize_name(name),))
    conn.commit()
    return cursor.rowcount > 0


def add_results_to_project(conn: sqlite3.Connection, name: str, result_ids: list[int], role: str | None = None) -> AddSummary:
    file_ids = [latest_file_id(conn, int(result_id)) for result_id in result_ids]
    return add_files_to_project(conn, name, file_ids, role=role)


def add_files_to_project(conn: sqlite3.Connection, name: str, file_ids: list[int], role: str | None = None) -> AddSummary:
    project = _require_project(conn, name)
    before = _project_file_ids(conn, project.id)
    now = utc_now()
    for file_id in file_ids:
        conn.execute(
            """
            INSERT OR IGNORE INTO project_items(project_id, file_id, role, added_at)
            VALUES (?, ?, ?, ?)
            """,
            (project.id, int(file_id), role, now),
        )
    conn.commit()
    after = _project_file_ids(conn, project.id)
    added_ids = sorted(after - before)
    return AddSummary(added=len(added_ids), skipped=len(file_ids) - len(added_ids), file_ids=added_ids)


def remove_files_from_project(conn: sqlite3.Connection, name: str, file_ids: list[int]) -> int:
    project = _require_project(conn, name)
    known_file_ids = _project_file_ids(conn, project.id)
    removed = 0
    for value in file_ids:
        file_id = _resolve_project_file_id(conn, int(value), known_file_ids)
        cursor = conn.execute("DELETE FROM project_items WHERE project_id = ? AND file_id = ?", (project.id, int(file_id)))
        removed += cursor.rowcount
    conn.commit()
    return removed


def get_project_items(conn: sqlite3.Connection, name: str) -> list[WorkflowItem]:
    project = _require_project(conn, name)
    rows = conn.execute(
        """
        SELECT pi.id, pi.file_id, pi.role, f.file_name, f.path, f.extension, f.modified_time
        FROM project_items pi
        JOIN files f ON f.id = pi.file_id
        WHERE pi.project_id = ?
        ORDER BY pi.id
        """,
        (project.id,),
    ).fetchall()
    return [load_workflow_item(conn, row, kind="project") for row in rows]


def project_search(conn: sqlite3.Connection, name: str, query: str, config: KGFSConfig, *, limit: int | None = None) -> ProjectSearchReport:
    project = _require_project(conn, name)
    file_ids = _project_file_ids(conn, project.id)
    if not file_ids:
        return ProjectSearchReport(project=project, query=query, results=[])
    candidates = search(conn, query, limit=max((limit or config.projects.default_limit) * 10, 50), highlight=config.search.highlight_matches)
    scoped = [result for result in candidates if result.file_id in file_ids][: limit or config.projects.default_limit]
    results = [_renumber(result, index) for index, result in enumerate(scoped, start=1)]
    if config.search.save_latest_results:
        save_latest_results(conn, query, results)
    return ProjectSearchReport(project=project, query=query, results=results)


class ProjectSearchReport:
    def __init__(self, *, project: Project, query: str, results: list[SearchResult]) -> None:
        self.project = project
        self.query = query
        self.results = results


def _renumber(result: SearchResult, result_id: int) -> SearchResult:
    from dataclasses import replace

    return replace(result, result_id=result_id)


def _require_project(conn: sqlite3.Connection, name: str) -> Project:
    project = get_project(conn, name)
    if project is None:
        raise ValueError(f"Unknown project: {name}")
    return project


def _project_file_ids(conn: sqlite3.Connection, project_id: int) -> set[int]:
    rows = conn.execute("SELECT file_id FROM project_items WHERE project_id = ?", (project_id,)).fetchall()
    return {int(row["file_id"]) for row in rows}


def _resolve_project_file_id(conn: sqlite3.Connection, value: int, known_file_ids: set[int]) -> int:
    if value in known_file_ids:
        return value
    try:
        resolved = latest_file_id(conn, value)
    except ValueError:
        return value
    return resolved
