"""Compare two latest KGFS search results."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from sqlite3 import Connection

from kgfs.core.config import KGFSConfig
from kgfs.core.models import SearchResult
from kgfs.db.latest_results import get_latest_result_record
from kgfs.search.query import STOPWORDS
from kgfs.search.similar import semantic_file_similarity, text_similarity
from kgfs.search.snippets import make_snippet


@dataclass(frozen=True)
class CompareReport:
    left: SearchResult
    right: SearchResult
    shared_terms: list[str]
    left_unique_terms: list[str]
    right_unique_terms: list[str]
    text_similarity: float
    semantic_similarity: float | None
    notes: list[str]


def compare_results(conn: Connection, left_result_id: int, right_result_id: int, config: KGFSConfig) -> CompareReport:
    left_latest = get_latest_result_record(conn, left_result_id)
    right_latest = get_latest_result_record(conn, right_result_id)
    if left_latest is None:
        raise ValueError(f"No latest search result found for ID {left_result_id}. Run kgfs search first.")
    if right_latest is None:
        raise ValueError(f"No latest search result found for ID {right_result_id}. Run kgfs search first.")
    left = _load_file(conn, left_latest.file_id, left_result_id)
    right = _load_file(conn, right_latest.file_id, right_result_id)
    left_text = _file_text(conn, left.file_id)
    right_text = _file_text(conn, right.file_id)
    left_terms = set(_terms(f"{left.file_name} {left_text}"))
    right_terms = set(_terms(f"{right.file_name} {right_text}"))
    shared = sorted(left_terms & right_terms)
    semantic = semantic_file_similarity(conn, left.file_id, right.file_id, config.semantic.model_name)
    notes: list[str] = []
    for result in (left, right):
        if str(result.metadata.get("extraction_source", "")).startswith("ocr"):
            notes.append(f"{result.file_name} includes OCR-derived text.")
    return CompareReport(
        left=left,
        right=right,
        shared_terms=shared[:20],
        left_unique_terms=sorted(left_terms - right_terms)[:20],
        right_unique_terms=sorted(right_terms - left_terms)[:20],
        text_similarity=text_similarity(left_text, right_text),
        semantic_similarity=semantic,
        notes=notes,
    )


def _load_file(conn: Connection, file_id: int, result_id: int) -> SearchResult:
    row = conn.execute(
        """
        SELECT id, file_name, path, normalized_path, extension, modified_time, extracted_text, extraction_source
        FROM files WHERE id = ?
        """,
        (file_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"File record {file_id} no longer exists in the KGFS index.")
    return SearchResult(
        result_id=result_id,
        file_id=int(row["id"]),
        file_name=row["file_name"],
        path=Path(row["path"]),
        extension=row["extension"],
        modified_time=float(row["modified_time"]),
        score=0.0,
        snippet=make_snippet(row["extracted_text"], row["file_name"]),
        normalized_path=row["normalized_path"],
        metadata={"extraction_source": row["extraction_source"]},
    )


def _file_text(conn: Connection, file_id: int) -> str:
    row = conn.execute("SELECT extracted_text FROM files WHERE id = ?", (file_id,)).fetchone()
    return row["extracted_text"] if row else ""


def _terms(text: str) -> list[str]:
    return [term for term in re.findall(r"\b[\w]{3,}\b", text.casefold(), flags=re.UNICODE) if term not in STOPWORDS]
