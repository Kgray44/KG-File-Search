"""Search result and explanation models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from kgfs.core.models import SearchResult
from kgfs.search.options import SearchMode


@dataclass(frozen=True)
class SearchExplanation:
    mode: SearchMode
    summary: str
    score_breakdown: dict[str, float] = field(default_factory=dict)
    result_id: int | None = None
    file_name: str | None = None
    path: Path | None = None
    final_score: float | None = None
    snippet: str | None = None
    notes: list[str] = field(default_factory=list)


__all__ = ["SearchExplanation", "SearchResult"]
