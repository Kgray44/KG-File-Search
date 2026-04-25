"""Auto-mode resolution helpers."""

from __future__ import annotations

from kgfs.search.engine import SearchAvailability
from kgfs.search.options import SearchMode


def auto_fallback_warning(availability: SearchAvailability) -> str:
    detail = f": {availability.message}" if availability.message else "."
    return f"Semantic search is unavailable{detail} Using keyword search instead."


AUTO_FALLBACK_MODE = SearchMode.KEYWORD
