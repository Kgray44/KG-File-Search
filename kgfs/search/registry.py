"""Search engine registry and mode resolution."""

from __future__ import annotations

from dataclasses import dataclass, field

from kgfs.search.engine import SearchContext, SearchEngine
from kgfs.search.modes.auto import AUTO_FALLBACK_MODE, auto_fallback_warning
from kgfs.search.modes.hybrid import HybridSearchEngine
from kgfs.search.modes.keyword import KeywordSearchEngine
from kgfs.search.modes.semantic import SemanticSearchEngine
from kgfs.search.options import SearchMode, SearchOptions
from kgfs.search.result import SearchResult


class SearchModeError(ValueError):
    """Base error for search mode resolution."""


class UnknownSearchMode(SearchModeError):
    """Raised when a search mode name is unknown."""


class SearchModeUnavailable(SearchModeError):
    """Raised when a known search mode cannot run in the current context."""


@dataclass(frozen=True)
class SearchExecution:
    results: list[SearchResult]
    mode_requested: SearchMode
    mode_used: SearchMode
    warnings: list[str] = field(default_factory=list)


class SearchRegistry:
    def __init__(self) -> None:
        self._engines: dict[SearchMode, SearchEngine] = {}

    def register(self, engine: SearchEngine) -> None:
        self._engines[engine.name] = engine

    def get(self, mode: SearchMode | str) -> SearchEngine:
        try:
            search_mode = SearchMode.coerce(mode)
        except ValueError as exc:
            raise UnknownSearchMode(str(exc)) from exc
        if search_mode is SearchMode.AUTO:
            raise UnknownSearchMode("Auto mode is resolved by the registry and is not a concrete engine.")
        try:
            return self._engines[search_mode]
        except KeyError as exc:
            raise UnknownSearchMode(f"Unknown search mode: {search_mode.value}") from exc

    def modes(self) -> list[SearchMode]:
        return list(self._engines)

    def available_modes(self, context: SearchContext) -> list[SearchMode]:
        return [mode for mode, engine in self._engines.items() if engine.available(context).available]

    def search(self, query: str, options: SearchOptions, context: SearchContext) -> SearchExecution:
        engine, mode_used, warnings = self._resolve_engine(options.mode, context)
        availability = engine.available(context)
        if not availability.available:
            raise SearchModeUnavailable(f"{mode_used.value.title()} search is unavailable: {availability.message}")
        results = engine.search(query, options, context)
        return SearchExecution(
            results=results,
            mode_requested=options.mode,
            mode_used=mode_used,
            warnings=warnings,
        )

    def _resolve_engine(
        self,
        requested_mode: SearchMode,
        context: SearchContext,
    ) -> tuple[SearchEngine, SearchMode, list[str]]:
        if requested_mode is not SearchMode.AUTO:
            return self.get(requested_mode), requested_mode, []

        hybrid = self.get(SearchMode.HYBRID)
        availability = hybrid.available(context)
        if availability.available:
            return hybrid, SearchMode.HYBRID, []
        if context.config.semantic.enabled:
            return self.get(AUTO_FALLBACK_MODE), AUTO_FALLBACK_MODE, [auto_fallback_warning(availability)]
        return self.get(AUTO_FALLBACK_MODE), AUTO_FALLBACK_MODE, []


def build_default_search_registry() -> SearchRegistry:
    registry = SearchRegistry()
    registry.register(KeywordSearchEngine())
    registry.register(SemanticSearchEngine())
    registry.register(HybridSearchEngine())
    return registry
