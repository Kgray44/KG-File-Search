"""Keyword search engine wrapper."""

from __future__ import annotations

from kgfs.db import check_fts5_available
from kgfs.search.engine import SearchAvailability, SearchContext
from kgfs.search.keyword import search as keyword_search
from kgfs.search.options import SearchMode, SearchOptions
from kgfs.search.result import SearchResult


class KeywordSearchEngine:
    name = SearchMode.KEYWORD

    def available(self, context: SearchContext) -> SearchAvailability:
        if not check_fts5_available():
            return SearchAvailability(False, "SQLite FTS5 is not available in this Python SQLite build.")
        return SearchAvailability(True, "SQLite FTS5 keyword search is available.")

    def search(self, query: str, options: SearchOptions, context: SearchContext) -> list[SearchResult]:
        return keyword_search(
            context.conn,
            query,
            limit=options.limit,
            filters=options.filters,
            highlight=options.highlight,
        )
