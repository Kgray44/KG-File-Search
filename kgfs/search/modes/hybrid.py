"""Hybrid search engine wrapper."""

from __future__ import annotations

from kgfs.search.engine import SearchAvailability, SearchContext
from kgfs.search.keyword import hybrid_search
from kgfs.search.modes.semantic import semantic_availability
from kgfs.search.options import SearchMode, SearchOptions
from kgfs.search.result import SearchResult
from kgfs.search.semantic import get_embedder


class HybridSearchEngine:
    name = SearchMode.HYBRID

    def available(self, context: SearchContext) -> SearchAvailability:
        availability = semantic_availability(context)
        if not availability.available:
            return SearchAvailability(False, availability.message)
        return SearchAvailability(True, "Hybrid search is available.")

    def search(self, query: str, options: SearchOptions, context: SearchContext) -> list[SearchResult]:
        embedder = context.semantic_embedder or get_embedder(context.config.semantic)
        return hybrid_search(
            context.conn,
            query,
            embedder=embedder,
            model_name=context.config.semantic.model_name,
            backend_name=context.config.vectors.backend,
            limit=options.limit,
            filters=options.filters,
            highlight=options.highlight,
        )
