"""Local multi-pass deep search."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from sqlite3 import Connection

from kgfs.core.config import KGFSConfig
from kgfs.core.models import SearchResult
from kgfs.db.latest_results import save_latest_results
from kgfs.search.engine import SearchContext
from kgfs.search.filters import SearchFilters
from kgfs.search.options import SearchOptions
from kgfs.search.query import STOPWORDS
from kgfs.search.registry import SearchModeError, build_default_search_registry


@dataclass(frozen=True)
class DeepSearchReport:
    query: str
    variants: list[str]
    results: list[SearchResult]
    followups: list[str]
    warnings: list[str]


def generate_query_variants(query: str, *, max_variants: int = 8) -> list[str]:
    """Generate deterministic local query variants without AI/cloud calls."""

    compact = re.sub(r"\s+", " ", query).strip()
    if not compact:
        return []
    terms = [
        term
        for term in re.findall(r"[\w]+(?:[-'][\w]+)*", compact, flags=re.UNICODE)
        if term.casefold() not in STOPWORDS
    ]
    variants: list[str] = [compact]
    for size in (2, 3):
        for index in range(0, max(0, len(terms) - size + 1)):
            variants.append(" ".join(terms[index : index + size]))
    variants.extend(terms)
    variants.extend(_simple_plural_variants(terms))
    return _dedupe([variant for variant in variants if variant])[:max_variants]


def deep_search(
    conn: Connection,
    query: str,
    config: KGFSConfig,
    *,
    limit: int | None = None,
    mode: str | None = None,
    passes: int | None = None,
    filters: SearchFilters | None = None,
    save_latest: bool | None = None,
    semantic_embedder=None,
) -> DeepSearchReport:
    selected_limit = limit or config.search.default_limit
    max_passes = max(1, passes or config.deep_search.max_passes)
    candidate_limit = max(selected_limit, config.deep_search.max_candidates)
    variants = generate_query_variants(query, max_variants=max_passes * 3 if config.deep_search.query_expansion else 1)
    variants = variants[:max_passes] if max_passes < len(variants) else variants
    registry = build_default_search_registry()
    context = SearchContext(conn=conn, config=config, semantic_embedder=semantic_embedder)
    requested_mode = mode or config.search.default_mode
    by_file: dict[int, SearchResult] = {}
    warnings: list[str] = []

    for variant in variants:
        options = SearchOptions(
            mode=requested_mode,
            limit=candidate_limit,
            filters=filters,
            highlight=config.search.highlight_matches,
            save_latest_results=False,
        )
        try:
            execution = registry.search(variant, options, context)
        except SearchModeError as exc:
            warnings.append(str(exc))
            continue
        warnings.extend(warning for warning in execution.warnings if warning not in warnings)
        for result in execution.results:
            existing = by_file.get(result.file_id)
            result = _as_deep_result(result, variant, query)
            if existing is None:
                by_file[result.file_id] = result
            else:
                by_file[result.file_id] = _merge_deep_results(existing, result)

    ranked = sorted(by_file.values(), key=lambda result: result.score, reverse=True)[:selected_limit]
    ranked = [_renumber(result, index) for index, result in enumerate(ranked, start=1)]
    should_save_latest = save_latest if save_latest is not None else config.search.save_latest_results
    if should_save_latest:
        save_latest_results(conn, query, ranked)
    return DeepSearchReport(
        query=query,
        variants=variants,
        results=ranked,
        followups=_suggest_followups(query, ranked) if config.deep_search.suggest_followups else [],
        warnings=warnings,
    )


def _as_deep_result(result: SearchResult, variant: str, original_query: str) -> SearchResult:
    metadata = dict(result.metadata)
    metadata["deep_subqueries"] = [variant]
    metadata["deep_modes"] = [result.mode or result.source or "unknown"]
    original_boost = 0.2 if variant.casefold() == original_query.casefold() else 0.0
    return replace(
        result,
        score=result.score + 0.05 + original_boost,
        mode="deep",
        source=result.source or result.mode,
        metadata=metadata,
    )


def _merge_deep_results(left: SearchResult, right: SearchResult) -> SearchResult:
    metadata = dict(left.metadata)
    subqueries = list(metadata.get("deep_subqueries", []))
    for item in right.metadata.get("deep_subqueries", []):
        if item not in subqueries:
            subqueries.append(item)
    metadata["deep_subqueries"] = subqueries
    modes = list(metadata.get("deep_modes", []))
    for item in right.metadata.get("deep_modes", []):
        if item not in modes:
            modes.append(item)
    metadata["deep_modes"] = modes
    score = max(left.score, right.score) + 0.05 * max(0, len(subqueries) - 1)
    best = left if left.score >= right.score else right
    return replace(best, score=score, metadata=metadata, mode="deep")


def _renumber(result: SearchResult, result_id: int) -> SearchResult:
    return replace(result, result_id=result_id)


def _suggest_followups(query: str, results: list[SearchResult]) -> list[str]:
    terms = _important_terms(" ".join([query, *[result.file_name for result in results[:3]]]))
    suggestions = [f"{query} notes", f"{query} calculations"]
    for term in terms[:3]:
        suggestions.append(f"{query} {term}")
    return _dedupe(suggestions)[:5]


def _important_terms(text: str) -> list[str]:
    return [
        term.casefold()
        for term in re.findall(r"\b[\w]{3,}\b", text, flags=re.UNICODE)
        if term.casefold() not in STOPWORDS
    ]


def _simple_plural_variants(terms: list[str]) -> list[str]:
    variants: list[str] = []
    for term in terms:
        if term.endswith("s") and len(term) > 3:
            variants.append(term[:-1])
        elif len(term) > 2:
            variants.append(f"{term}s")
    return variants


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        key = value.casefold()
        if key not in seen:
            output.append(value)
            seen.add(key)
    return output
