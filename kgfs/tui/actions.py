"""Non-interactive helpers for the optional TUI."""

from __future__ import annotations

from kgfs.search.filters import SearchFilters
from kgfs.search.options import SearchOptions


def build_tui_search_options(*, mode: str, limit: int = 10) -> SearchOptions:
    return SearchOptions(mode=mode, limit=limit, filters=SearchFilters())
