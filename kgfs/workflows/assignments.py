"""Local assignment working-set helper."""

from __future__ import annotations

import sqlite3

from kgfs.core.config import KGFSConfig
from kgfs.core.models import SearchResult
from kgfs.search.citations import format_citation_block
from kgfs.search.deep import deep_search
from kgfs.search.filters import SearchFilters
from kgfs.workflows.collections import add_files_to_collection, create_collection
from kgfs.workflows.models import AssignmentReport, dumps_json, utc_now


def assignment_working_set(
    conn: sqlite3.Connection,
    topic: str,
    config: KGFSConfig,
    *,
    limit: int | None = None,
    create_collection_name: str | None = None,
) -> AssignmentReport:
    selected_limit = limit or config.assignment.default_limit
    filters = SearchFilters(extensions=config.assignment.include_extensions)
    report = deep_search(conn, topic, config, limit=selected_limit, filters=filters)
    categories = _categorize(report.results)
    collection_name = None
    if create_collection_name and report.results:
        collection = create_collection(conn, create_collection_name)
        add_files_to_collection(conn, collection.name, [result.file_id for result in report.results])
        collection_name = collection.name
    next_actions = [
        "Open top result with kgfs open 1.",
        "Collect the working set with kgfs collection create/add.",
        "Run kgfs research for a broader local brief.",
    ]
    conn.execute(
        "INSERT INTO assignment_runs(topic, created_at, query_json, result_json) VALUES (?, ?, ?, ?)",
        (
            topic,
            utc_now(),
            dumps_json({"topic": topic, "limit": selected_limit}),
            dumps_json([{"file_id": result.file_id, "file_name": result.file_name} for result in report.results]),
        ),
    )
    conn.commit()
    return AssignmentReport(
        topic=topic,
        results=report.results,
        categories=categories,
        citations=format_citation_block(report.results),
        next_actions=next_actions,
        collection_name=collection_name,
    )


def _categorize(results: list[SearchResult]) -> dict[str, list[SearchResult]]:
    categories: dict[str, list[SearchResult]] = {}
    for result in results:
        category = _category_for(result)
        categories.setdefault(category, []).append(result)
    return categories


def _category_for(result: SearchResult) -> str:
    ext = result.extension.lower()
    name = result.file_name.casefold()
    if ext in {".md", ".txt"} or "note" in name:
        return "notes"
    if ext in {".pdf", ".docx"}:
        return "reports/docs"
    if ext == ".csv":
        return "data"
    if ext in {".py", ".js", ".ts"}:
        return "scripts/code"
    return "other"
