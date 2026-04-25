"""Lightweight search ranking helpers."""

from __future__ import annotations

import re
from datetime import datetime

from kgfs.search.query import STOPWORDS, compact_text


def filename_path_relevance(query: str, file_name: str, path: str) -> float:
    terms = [term.lower() for term in re.findall(r"\w+", query, flags=re.UNICODE) if term.lower() not in STOPWORDS]
    if not terms:
        return 0.0
    haystack = f"{file_name} {path}".lower()
    matches = sum(1 for term in terms if term in haystack)
    return matches / len(terms)


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
