"""Search engine protocol shared by search modes."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Protocol

from kgfs.core.config import KGFSConfig
from kgfs.search.options import SearchMode, SearchOptions
from kgfs.search.result import SearchExplanation, SearchResult
from kgfs.search.semantic import Embedder


@dataclass(frozen=True)
class SearchAvailability:
    available: bool
    message: str = ""


@dataclass
class SearchContext:
    conn: sqlite3.Connection
    config: KGFSConfig
    semantic_embedder: Embedder | None = None
    metadata: dict[str, object] = field(default_factory=dict)


class SearchEngine(Protocol):
    name: SearchMode

    def available(self, context: SearchContext) -> SearchAvailability:
        """Return whether this engine can run for the current context."""

    def search(self, query: str, options: SearchOptions, context: SearchContext) -> list[SearchResult]:
        """Return ranked search results."""

    def explain(
        self,
        result: SearchResult,
        query: str,
        options: SearchOptions,
        context: SearchContext,
    ) -> SearchExplanation:
        return SearchExplanation(
            mode=self.name,
            summary=f"{self.name.value} search result",
            score_breakdown=result.score_breakdown or {},
        )

    def stats(self, context: SearchContext) -> dict[str, object]:
        return {}
