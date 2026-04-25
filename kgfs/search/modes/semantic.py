"""Semantic search engine wrapper."""

from __future__ import annotations

import sqlite3

from kgfs.search.engine import SearchAvailability, SearchContext
from kgfs.search.keyword import semantic_search
from kgfs.search.options import SearchMode, SearchOptions
from kgfs.search.result import SearchResult
from kgfs.search.semantic import get_embedder, get_semantic_status


class SemanticSearchEngine:
    name = SearchMode.SEMANTIC

    def available(self, context: SearchContext) -> SearchAvailability:
        return semantic_availability(context)

    def search(self, query: str, options: SearchOptions, context: SearchContext) -> list[SearchResult]:
        embedder = context.semantic_embedder or get_embedder(context.config.semantic)
        return semantic_search(
            context.conn,
            query,
            embedder=embedder,
            model_name=context.config.semantic.model_name,
            limit=options.limit,
            filters=options.filters,
            highlight=options.highlight,
        )


def semantic_availability(context: SearchContext) -> SearchAvailability:
    settings = context.config.semantic
    if not settings.enabled:
        return SearchAvailability(
            False,
            "Semantic search is disabled. Set semantic.enabled: true and rebuild semantic chunks.",
        )
    if context.semantic_embedder is None:
        status = get_semantic_status(settings)
        if not status.available:
            return SearchAvailability(False, status.message)
    chunk_count = _semantic_chunk_count(context.conn, settings.model_name)
    if chunk_count <= 0:
        return SearchAvailability(
            False,
            "No semantic chunks are indexed for this model. Run kgfs semantic-index --rebuild.",
        )
    return SearchAvailability(True, "Semantic search is available.")


def _semantic_chunk_count(conn: sqlite3.Connection, model_name: str) -> int:
    row = conn.execute("SELECT COUNT(*) AS count FROM chunks WHERE model_name = ?", (model_name,)).fetchone()
    return int(row["count"] if row is not None else 0)
