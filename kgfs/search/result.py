"""Search result and explanation models."""

from __future__ import annotations

from dataclasses import dataclass, field

from kgfs.core.models import SearchResult
from kgfs.search.options import SearchMode


@dataclass(frozen=True)
class SearchExplanation:
    mode: SearchMode
    summary: str
    score_breakdown: dict[str, float] = field(default_factory=dict)


__all__ = ["SearchExplanation", "SearchResult"]
