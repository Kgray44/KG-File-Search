"""Chronological local search view."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from sqlite3 import Connection

from kgfs.core.config import KGFSConfig
from kgfs.core.models import SearchResult
from kgfs.db.latest_results import save_latest_results
from kgfs.search.engine import SearchContext
from kgfs.search.filters import SearchFilters
from kgfs.search.options import SearchOptions
from kgfs.search.registry import SearchModeError, build_default_search_registry


@dataclass(frozen=True)
class TimelineItem:
    result_id: int
    file_id: int
    file_name: str
    path: str
    modified_time: float
    group: str
    snippet: str
    source: str


@dataclass(frozen=True)
class TimelineReport:
    query: str
    items: list[TimelineItem]
    groups: dict[str, list[TimelineItem]]
    results: list[SearchResult]
    warnings: list[str]


def timeline_search(
    conn: Connection,
    query: str,
    config: KGFSConfig,
    *,
    limit: int | None = None,
    group: str = "month",
    mode: str | None = None,
    filters: SearchFilters | None = None,
    save_latest: bool | None = None,
    semantic_embedder=None,
) -> TimelineReport:
    selected_limit = limit or config.timeline.default_limit
    registry = build_default_search_registry()
    context = SearchContext(conn=conn, config=config, semantic_embedder=semantic_embedder)
    warnings: list[str] = []
    try:
        execution = registry.search(
            query,
            SearchOptions(
                mode=mode or config.search.default_mode,
                limit=selected_limit,
                filters=filters,
                highlight=config.search.highlight_matches,
                save_latest_results=False,
            ),
            context,
        )
    except SearchModeError as exc:
        return TimelineReport(query=query, items=[], groups={}, results=[], warnings=[str(exc)])
    warnings.extend(execution.warnings)
    ranked_results = execution.results
    chronological = sorted(ranked_results, key=lambda result: result.modified_time)
    chronological = [replace(result, result_id=index) for index, result in enumerate(chronological, start=1)]
    items = [_timeline_item(result, group=group) for result in chronological]
    groups: dict[str, list[TimelineItem]] = {}
    for item in items:
        groups.setdefault(item.group, []).append(item)
    should_save_latest = save_latest if save_latest is not None else config.search.save_latest_results
    if should_save_latest:
        save_latest_results(conn, query, chronological)
    return TimelineReport(query=query, items=items, groups=groups, results=chronological, warnings=warnings)


def _timeline_item(result: SearchResult, *, group: str) -> TimelineItem:
    source = "OCR" if str(result.metadata.get("extraction_source", "")).startswith("ocr") else (result.mode or "")
    return TimelineItem(
        result_id=result.result_id,
        file_id=result.file_id,
        file_name=result.file_name,
        path=str(result.path),
        modified_time=result.modified_time,
        group=_group_label(result.modified_time, group),
        snippet=result.snippet,
        source=source,
    )


def _group_label(modified_time: float, group: str) -> str:
    dt = datetime.fromtimestamp(modified_time)
    normalized = group.lower()
    if normalized == "day":
        return dt.strftime("%Y-%m-%d")
    if normalized == "year":
        return dt.strftime("%Y")
    return dt.strftime("%Y-%m")
