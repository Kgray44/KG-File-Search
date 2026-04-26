"""Local research mode built on deep search."""

from __future__ import annotations

import re
from dataclasses import dataclass
from sqlite3 import Connection

from kgfs.core.config import KGFSConfig
from kgfs.core.models import SearchResult
from kgfs.search.citations import format_citation_block
from kgfs.search.deep import deep_search
from kgfs.search.filters import SearchFilters
from kgfs.search.query import STOPWORDS


@dataclass(frozen=True)
class ResearchReport:
    query: str
    results: list[SearchResult]
    citations: str
    related_terms: list[str]
    followups: list[str]
    gaps: list[str]
    warnings: list[str]


def research_query(
    conn: Connection,
    query: str,
    config: KGFSConfig,
    *,
    limit: int | None = None,
    mode: str | None = None,
    filters: SearchFilters | None = None,
    semantic_embedder=None,
) -> ResearchReport:
    selected_limit = limit or config.research.max_files
    deep = deep_search(
        conn,
        query,
        config,
        limit=selected_limit,
        mode=mode,
        filters=filters,
        save_latest=config.search.save_latest_results,
        semantic_embedder=semantic_embedder,
    )
    related_terms = _related_terms(deep.results, query) if config.research.suggest_related_terms else []
    gaps: list[str] = []
    if not deep.results:
        gaps.append("No local indexed files matched this research question.")
    elif len(deep.results) < 3:
        gaps.append("Only a small number of local files matched; broaden the query if needed.")
    return ResearchReport(
        query=query,
        results=deep.results,
        citations=format_citation_block(deep.results),
        related_terms=related_terms,
        followups=deep.followups,
        gaps=gaps,
        warnings=deep.warnings,
    )


def _related_terms(results: list[SearchResult], query: str) -> list[str]:
    query_terms = {
        term.casefold()
        for term in re.findall(r"\b[\w]{3,}\b", query, flags=re.UNICODE)
        if term.casefold() not in STOPWORDS
    }
    counts: dict[str, int] = {}
    for result in results:
        text = _strip_rich_markup(f"{result.file_name} {result.snippet}")
        for term in re.findall(r"\b[\w]{3,}\b", text.casefold(), flags=re.UNICODE):
            if term in STOPWORDS:
                continue
            counts[term] = counts.get(term, 0) + 1
    ordered = [term for term, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]
    for term in sorted(query_terms):
        if term in ordered:
            ordered.remove(term)
            ordered.insert(0, term)
    return ordered[:12]


def _strip_rich_markup(text: str) -> str:
    return re.sub(r"\[/?bold\]", "", text)
