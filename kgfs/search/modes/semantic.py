"""Semantic search engine wrapper."""

from __future__ import annotations

from kgfs.search.engine import SearchAvailability, SearchContext
from kgfs.search.keyword import semantic_search
from kgfs.search.options import SearchMode, SearchOptions
from kgfs.search.result import SearchResult
from kgfs.search.semantic import get_embedder, get_semantic_status
from kgfs.vectors.status import get_vector_status


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
            backend_name=context.config.vectors.backend,
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
    vector_status = get_vector_status(context.conn, context.config)
    if not vector_status.backend_available:
        return SearchAvailability(
            False,
            "; ".join(vector_status.warnings) or f"Vector backend {vector_status.backend_name} is unavailable.",
        )
    if vector_status.chunk_count <= 0:
        return SearchAvailability(
            False,
            "No semantic chunks are indexed for this model. Run kgfs semantic-index --rebuild.",
        )
    return SearchAvailability(True, "Semantic search is available.")
