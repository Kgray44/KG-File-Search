"""FTS query parsing helpers."""

from __future__ import annotations

import re

STOPWORDS = {
    "a",
    "an",
    "and",
    "about",
    "find",
    "file",
    "files",
    "from",
    "i",
    "in",
    "my",
    "notes",
    "of",
    "or",
    "the",
    "to",
    "used",
    "where",
    "with",
}


def build_fts_query(query: str, *, use_or: bool = False) -> str:
    tokens = [token.lower() for token in re.findall(r"\w+", query, flags=re.UNICODE)]
    meaningful = [token for token in tokens if token not in STOPWORDS and len(token) > 1]
    selected = meaningful or tokens
    if not selected:
        return ""
    operator = " OR " if use_or else " AND "
    return operator.join(f"{token}*" for token in selected)


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
