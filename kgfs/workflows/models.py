"""Dataclasses and shared helpers for local workflow metadata."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kgfs.core.models import SearchResult
from kgfs.db.latest_results import get_latest_result_record
from kgfs.search.snippets import make_snippet


@dataclass(frozen=True)
class Profile:
    id: int
    name: str
    folders: list[str]
    extensions: list[str]
    default_mode: str
    boost_terms: list[str]
    description: str | None = None


@dataclass(frozen=True)
class SavedSearch:
    id: int
    name: str
    query: str
    mode: str | None
    filters: dict[str, Any]


@dataclass(frozen=True)
class WorkflowSearchReport:
    name: str
    query: str
    results: list[SearchResult]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Collection:
    id: int
    name: str
    description: str | None = None


@dataclass(frozen=True)
class WorkflowItem:
    id: int
    file_id: int
    file_name: str
    path: Path
    extension: str
    modified_time: float
    result_id: int | None = None
    note: str | None = None
    role: str | None = None


@dataclass(frozen=True)
class AddSummary:
    added: int
    skipped: int
    file_ids: list[int]


@dataclass(frozen=True)
class FileNote:
    id: int
    file_id: int
    note: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class AssignmentReport:
    topic: str
    results: list[SearchResult]
    categories: dict[str, list[SearchResult]]
    citations: str
    next_actions: list[str]
    collection_name: str | None = None


@dataclass(frozen=True)
class Project:
    id: int
    name: str
    description: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def dumps_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def loads_json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def normalize_name(name: str) -> str:
    text = str(name).strip()
    if not text:
        raise ValueError("Name cannot be empty.")
    return text


def normalize_tag(tag: str) -> str:
    text = str(tag).strip().casefold()
    if not text:
        raise ValueError("Tag cannot be empty.")
    return text


def normalize_extensions(values: list[str] | None) -> list[str]:
    normalized: list[str] = []
    for value in values or []:
        text = str(value).strip().lower()
        if text and not text.startswith("."):
            text = f".{text}"
        if text:
            normalized.append(text)
    return normalized


def latest_file_id(conn: sqlite3.Connection, result_id: int) -> int:
    latest = get_latest_result_record(conn, result_id)
    if latest is None:
        raise ValueError(f"No latest search result found for ID {result_id}. Run kgfs search first.")
    return latest.file_id


def load_file_result(conn: sqlite3.Connection, file_id: int, result_id: int = 0, query: str = "") -> SearchResult:
    row = conn.execute(
        """
        SELECT id, file_name, path, normalized_path, extension, modified_time,
               extracted_text, extraction_source
        FROM files
        WHERE id = ?
        """,
        (file_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"File record {file_id} no longer exists in the KGFS index.")
    text = row["extracted_text"] or ""
    snippet = make_snippet(text, query or row["file_name"]) or text[:220]
    return SearchResult(
        result_id=result_id,
        file_id=int(row["id"]),
        file_name=row["file_name"],
        path=Path(row["path"]),
        extension=row["extension"],
        modified_time=float(row["modified_time"]),
        score=0.0,
        snippet=snippet,
        normalized_path=row["normalized_path"],
        mode="workflow",
        source="workflow",
        metadata={"extraction_source": row["extraction_source"]},
    )


def load_workflow_item(conn: sqlite3.Connection, row, *, kind: str) -> WorkflowItem:
    note = row["note"] if "note" in row.keys() else None
    role = row["role"] if "role" in row.keys() else None
    result_id = row["result_id"] if "result_id" in row.keys() else None
    return WorkflowItem(
        id=int(row["id"]),
        file_id=int(row["file_id"]),
        result_id=int(result_id) if result_id is not None else None,
        file_name=row["file_name"],
        path=Path(row["path"]),
        extension=row["extension"],
        modified_time=float(row["modified_time"]),
        note=note,
        role=role,
    )
