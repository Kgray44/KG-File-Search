"""Search result snippet helpers."""

from __future__ import annotations

import re


def make_snippet(text: str, query: str, *, max_chars: int = 180, highlight: bool = False) -> str:
    if not text:
        return ""

    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= max_chars:
        return _highlight_terms(compact, query) if highlight else compact

    query_terms = [term.casefold() for term in _query_terms(query)]
    lower = compact.casefold()
    first_hit = min((lower.find(term) for term in query_terms if lower.find(term) >= 0), default=0)
    start = max(0, first_hit - max_chars // 3)
    has_prefix = start > 0
    has_suffix = start + max_chars < len(compact)
    body_limit = max_chars - (3 if has_prefix else 0) - (3 if has_suffix else 0)
    body_limit = max(12, body_limit)
    end = min(len(compact), start + body_limit)
    snippet = compact[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(compact):
        snippet = snippet + "..."
    return _highlight_terms(snippet, query) if highlight else snippet


def _query_terms(query: str) -> list[str]:
    return [term for term in re.findall(r"[\w]+(?:[-'][\w]+)*", query, flags=re.UNICODE) if term]


def _highlight_terms(text: str, query: str) -> str:
    highlighted = text
    terms = sorted(set(_query_terms(query)), key=len, reverse=True)
    for term in terms:
        pattern = re.compile(re.escape(term), flags=re.IGNORECASE)
        highlighted = pattern.sub(lambda match: f"[bold]{match.group(0)}[/bold]", highlighted)
    return highlighted
