"""Auto-mode resolution helpers."""

from __future__ import annotations

from kgfs.search.engine import SearchAvailability
from kgfs.search.options import SearchMode


def auto_fallback_warning(availability: SearchAvailability) -> str:
    message = (availability.message or "").strip().rstrip(".")
    if not message:
        return "Semantic search is unavailable. Using keyword search instead."
    if "vector backend" in message.casefold():
        return f"Vector backend is unavailable: {message}. Using keyword search instead."
    if message.casefold().startswith("semantic search is unavailable"):
        return f"{message}. Using keyword search instead."
    return f"Semantic search is unavailable: {message}. Using keyword search instead."


AUTO_FALLBACK_MODE = SearchMode.KEYWORD
