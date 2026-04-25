"""Lightweight search ranking helpers."""

from __future__ import annotations

import re
from datetime import datetime

from kgfs.core.config import HybridSettings
from kgfs.search.query import STOPWORDS, compact_text


def filename_relevance(query: str, file_name: str) -> float:
    return _term_relevance(query, file_name)


def path_relevance(query: str, path: str) -> float:
    return _term_relevance(query, path)


def filename_path_relevance(query: str, file_name: str, path: str) -> float:
    return _term_relevance(query, f"{file_name} {path}")


def exact_phrase_relevance(query: str, text: str) -> float:
    phrase = compact_text(query).casefold()
    if not phrase:
        return 0.0
    return 1.0 if phrase in compact_text(text).casefold() else 0.0


def keyword_score(query: str, row, rank: float) -> float:
    base = 1.0 / (1.0 + abs(rank))
    filename_score = filename_path_relevance(query, row["file_name"], "")
    path_score = filename_path_relevance(query, "", row["path"])
    exact_score = exact_phrase_relevance(query, row["extracted_text"])
    recency_score = recent_modification_bonus(float(row["modified_time"]))
    return base + (1.25 * filename_score) + (0.40 * path_score) + (0.85 * exact_score) + (0.08 * recency_score)


def recent_modification_bonus(modified_time: float) -> float:
    age_seconds = max(0.0, datetime.now().timestamp() - modified_time)
    age_days = age_seconds / 86400
    return 1.0 / (1.0 + age_days / 30.0)


def combine_hybrid_score(
    *,
    query: str,
    file_name: str,
    path: str,
    extracted_text: str,
    modified_time: float,
    keyword_score_value: float,
    semantic_score_value: float,
    settings: HybridSettings | None = None,
) -> tuple[float, dict[str, float]]:
    """Combine hybrid score components using safe, normalized positive weights."""

    hybrid_settings = settings or HybridSettings()
    components = {
        "keyword": max(0.0, float(keyword_score_value)),
        "semantic": max(0.0, float(semantic_score_value)),
        "filename": filename_relevance(query, file_name),
        "path": path_relevance(query, path),
        "exact_phrase": exact_phrase_relevance(query, extracted_text),
        "recency": recent_modification_bonus(modified_time),
    }
    weights = {
        "keyword": _safe_weight(hybrid_settings.keyword_weight),
        "semantic": _safe_weight(hybrid_settings.semantic_weight),
        "filename": _safe_weight(hybrid_settings.filename_weight),
        "path": _safe_weight(hybrid_settings.path_weight),
        "exact_phrase": _safe_weight(hybrid_settings.exact_phrase_weight),
        "recency": _safe_weight(hybrid_settings.recency_weight),
    }
    total_weight = sum(weights.values())
    if total_weight <= 0:
        final = 0.0
    else:
        final = sum(components[name] * weight for name, weight in weights.items()) / total_weight
    breakdown = {**components, "final": final}
    return final, breakdown


def _term_relevance(query: str, text: str) -> float:
    terms = [term.lower() for term in re.findall(r"\w+", query, flags=re.UNICODE) if term.lower() not in STOPWORDS]
    if not terms:
        return 0.0
    haystack = text.lower()
    matches = sum(1 for term in terms if term in haystack)
    return matches / len(terms)


def _safe_weight(value: float) -> float:
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 0.0
