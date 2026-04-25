"""Search mode and option models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from kgfs.search.filters import SearchFilters


class SearchMode(str, Enum):
    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    AUTO = "auto"

    @classmethod
    def coerce(cls, value: "SearchMode | str") -> "SearchMode":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().lower())
        except ValueError as exc:
            raise ValueError(f"Unknown search mode: {value}") from exc


@dataclass(frozen=True)
class SearchOptions:
    mode: SearchMode | str = SearchMode.AUTO
    limit: int = 10
    filters: SearchFilters | None = None
    backend: str | None = None
    explain: bool = False
    save_latest_results: bool = True
    highlight: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", SearchMode.coerce(self.mode))
        if self.limit < 1:
            raise ValueError("Search limit must be at least 1")
