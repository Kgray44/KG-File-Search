"""Search result snippet helpers."""

from __future__ import annotations

import re


def make_snippet(text: str, query: str, *, max_chars: int = 180) -> str:
    if not text:
        return ""

    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= max_chars:
        return compact

    query_terms = [term.lower() for term in re.findall(r"\w+", query) if term]
    lower = compact.lower()
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
    return snippet
