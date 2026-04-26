"""Local project-candidate inference."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from pathlib import Path

from kgfs.core.config import KGFSConfig
from kgfs.intelligence.models import ProjectCandidate
from kgfs.workflows.models import utc_now
from kgfs.workflows.projects import add_files_to_project, create_project


def infer_project_candidates(
    conn: sqlite3.Connection,
    config: KGFSConfig,
    *,
    persist: bool = False,
) -> list[ProjectCandidate]:
    """Infer manual project candidates from local indexed metadata."""

    rows = conn.execute(
        """
        SELECT id, file_name, path, extension, modified_time
        FROM files
        ORDER BY path
        """
    ).fetchall()
    by_folder: dict[str, list] = defaultdict(list)
    for row in rows:
        by_folder[str(Path(row["path"]).parent)].append(row)

    candidates: list[ProjectCandidate] = []
    for folder, folder_rows in by_folder.items():
        if len(folder_rows) < 2:
            continue
        file_ids = [int(row["id"]) for row in folder_rows]
        extensions = {row["extension"] for row in folder_rows}
        score = min(1.0, 0.42 + len(folder_rows) * 0.08 + min(len(extensions), 4) * 0.04)
        if score < config.intelligence.project_min_score:
            continue
        name = _candidate_name(folder)
        evidence = [
            f"{len(folder_rows)} files in {folder}",
            f"file types: {', '.join(sorted(extensions))}",
        ]
        candidates.append(ProjectCandidate(id=0, name=name, score=score, file_ids=file_ids, evidence=evidence))

    candidates.sort(key=lambda candidate: (-candidate.score, candidate.name.casefold()))
    if persist:
        return _persist_candidates(conn, candidates)
    return [
        ProjectCandidate(index, c.name, c.score, c.file_ids, c.evidence) for index, c in enumerate(candidates, start=1)
    ]


def list_project_candidates(conn: sqlite3.Connection) -> list[ProjectCandidate]:
    rows = conn.execute(
        """
        SELECT id, name, score, evidence_json, accepted_project_id
        FROM project_candidates
        ORDER BY accepted_project_id IS NOT NULL, score DESC, id
        """
    ).fetchall()
    return [_row_to_candidate(row) for row in rows]


def accept_project_candidate(conn: sqlite3.Connection, candidate_id: int, *, name: str | None = None):
    candidate = _candidate(conn, candidate_id)
    project = create_project(conn, name or candidate.name)
    summary = add_files_to_project(conn, project.name, candidate.file_ids)
    conn.execute(
        "UPDATE project_candidates SET accepted_project_id = ? WHERE id = ?",
        (project.id, candidate_id),
    )
    conn.commit()
    return summary


def _persist_candidates(conn: sqlite3.Connection, candidates: list[ProjectCandidate]) -> list[ProjectCandidate]:
    conn.execute("DELETE FROM project_candidates WHERE accepted_project_id IS NULL")
    now = utc_now()
    for candidate in candidates:
        payload = {"file_ids": candidate.file_ids, "evidence": candidate.evidence}
        conn.execute(
            """
            INSERT INTO project_candidates(name, score, evidence_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (candidate.name, candidate.score, json.dumps(payload, ensure_ascii=False, sort_keys=True), now),
        )
    conn.commit()
    return list_project_candidates(conn)


def _candidate(conn: sqlite3.Connection, candidate_id: int) -> ProjectCandidate:
    row = conn.execute(
        """
        SELECT id, name, score, evidence_json, accepted_project_id
        FROM project_candidates
        WHERE id = ?
        """,
        (candidate_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Unknown project candidate: {candidate_id}")
    return _row_to_candidate(row)


def _row_to_candidate(row) -> ProjectCandidate:
    try:
        data = json.loads(row["evidence_json"] or "{}")
    except json.JSONDecodeError:
        data = {}
    return ProjectCandidate(
        id=int(row["id"]),
        name=row["name"],
        score=float(row["score"]),
        file_ids=[int(value) for value in data.get("file_ids", [])],
        evidence=[str(value) for value in data.get("evidence", [])],
        accepted_project_id=int(row["accepted_project_id"]) if row["accepted_project_id"] is not None else None,
    )


def _candidate_name(folder: str) -> str:
    name = Path(folder).name.strip() or "Inferred Project"
    return name.replace("_", " ").replace("-", " ").title()
