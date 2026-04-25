"""SQLite FTS5 keyword search."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from kgfs.models import SearchResult
from kgfs.semantic import Embedder, cosine_similarity, unpack_vector
from kgfs.snippets import make_snippet

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


def search(conn: sqlite3.Connection, query: str, *, limit: int = 10) -> list[SearchResult]:
    fts_query = build_fts_query(query)
    if not fts_query:
        return []
    rows = _run_search(conn, query, fts_query, limit)
    if not rows and " AND " in fts_query:
        rows = _run_search(conn, query, build_fts_query(query, use_or=True), limit)
    return rows


def semantic_search(
    conn: sqlite3.Connection,
    query: str,
    *,
    embedder: Embedder,
    model_name: str | None = None,
    limit: int = 10,
) -> list[SearchResult]:
    model = model_name or semantic_model_name_from_embedder(embedder)
    query_vector = embedder.embed([query])[0]
    rows = conn.execute(
        """
        SELECT
            c.file_id,
            c.text,
            c.embedding,
            c.embedding_dim,
            f.file_name,
            f.path,
            f.extension,
            f.modified_time
        FROM chunks c
        JOIN files f ON f.id = c.file_id
        WHERE c.model_name = ?
        """,
        (model,),
    ).fetchall()

    best_by_file: dict[int, SearchResult] = {}
    for row in rows:
        vector = unpack_vector(row["embedding"], int(row["embedding_dim"]))
        similarity = cosine_similarity(query_vector, vector)
        score = max(0.0, similarity)
        file_id = int(row["file_id"])
        existing = best_by_file.get(file_id)
        if existing is None or score > existing.score:
            snippet = make_snippet(row["text"], query) or row["text"]
            best_by_file[file_id] = SearchResult(
                result_id=0,
                file_id=file_id,
                file_name=row["file_name"],
                path=Path(row["path"]),
                extension=row["extension"],
                modified_time=float(row["modified_time"]),
                score=score,
                snippet=snippet,
            )

    ranked = sorted(best_by_file.values(), key=lambda item: item.score, reverse=True)[:limit]
    return [_renumber(result, index) for index, result in enumerate(ranked, start=1)]


def hybrid_search(
    conn: sqlite3.Connection,
    query: str,
    *,
    embedder: Embedder,
    model_name: str | None = None,
    limit: int = 10,
) -> list[SearchResult]:
    candidate_limit = max(limit * 5, 25)
    keyword_results = search(conn, query, limit=candidate_limit)
    semantic_results = semantic_search(
        conn,
        query,
        embedder=embedder,
        model_name=model_name,
        limit=candidate_limit,
    )
    keyword_by_file = {result.file_id: result for result in keyword_results}
    semantic_by_file = {result.file_id: result for result in semantic_results}
    file_ids = sorted(set(keyword_by_file) | set(semantic_by_file))
    if not file_ids:
        return []

    placeholders = ", ".join("?" for _ in file_ids)
    rows = conn.execute(
        f"SELECT id, file_name, path, extension, modified_time, extracted_text FROM files WHERE id IN ({placeholders})",
        tuple(file_ids),
    ).fetchall()

    ranked: list[SearchResult] = []
    for row in rows:
        file_id = int(row["id"])
        keyword = keyword_by_file.get(file_id)
        semantic = semantic_by_file.get(file_id)
        keyword_score = keyword.score if keyword else 0.0
        semantic_score = semantic.score if semantic else 0.0
        filename_score = filename_path_relevance(query, row["file_name"], row["path"])
        recency_score = recent_modification_bonus(float(row["modified_time"]))
        combined = (
            0.45 * semantic_score
            + 0.35 * keyword_score
            + 0.15 * filename_score
            + 0.05 * recency_score
        )
        snippet = (
            semantic.snippet
            if semantic and semantic.snippet
            else keyword.snippet
            if keyword and keyword.snippet
            else make_snippet(row["extracted_text"], query)
        )
        ranked.append(
            SearchResult(
                result_id=0,
                file_id=file_id,
                file_name=row["file_name"],
                path=Path(row["path"]),
                extension=row["extension"],
                modified_time=float(row["modified_time"]),
                score=combined,
                snippet=snippet,
            )
        )

    ranked.sort(key=lambda item: item.score, reverse=True)
    return [_renumber(result, index) for index, result in enumerate(ranked[:limit], start=1)]


def _run_search(conn: sqlite3.Connection, query: str, fts_query: str, limit: int) -> list[SearchResult]:
    try:
        rows = conn.execute(
            """
            SELECT
                f.id,
                f.file_name,
                f.path,
                f.extension,
                f.modified_time,
                f.extracted_text,
                bm25(files_fts) AS rank,
                snippet(files_fts, 2, '', '', '...', 18) AS fts_snippet
            FROM files_fts
            JOIN files f ON f.id = files_fts.rowid
            WHERE files_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts_query, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        return []

    results: list[SearchResult] = []
    for index, row in enumerate(rows, start=1):
        rank = float(row["rank"])
        snippet = row["fts_snippet"] or make_snippet(row["extracted_text"], query)
        results.append(
            SearchResult(
                result_id=index,
                file_id=int(row["id"]),
                file_name=row["file_name"],
                path=Path(row["path"]),
                extension=row["extension"],
                modified_time=float(row["modified_time"]),
                score=1.0 / (1.0 + abs(rank)),
                snippet=snippet,
            )
        )
    return results


def semantic_model_name_from_embedder(embedder: Embedder) -> str:
    return getattr(embedder, "model_name", "")


def filename_path_relevance(query: str, file_name: str, path: str) -> float:
    terms = [term.lower() for term in re.findall(r"\w+", query, flags=re.UNICODE) if term.lower() not in STOPWORDS]
    if not terms:
        return 0.0
    haystack = f"{file_name} {path}".lower()
    matches = sum(1 for term in terms if term in haystack)
    return matches / len(terms)


def recent_modification_bonus(modified_time: float) -> float:
    age_seconds = max(0.0, datetime.now().timestamp() - modified_time)
    age_days = age_seconds / 86400
    return 1.0 / (1.0 + age_days / 30.0)


def _renumber(result: SearchResult, result_id: int) -> SearchResult:
    return SearchResult(
        result_id=result_id,
        file_id=result.file_id,
        file_name=result.file_name,
        path=result.path,
        extension=result.extension,
        modified_time=result.modified_time,
        score=result.score,
        snippet=result.snippet,
    )


def save_latest_results(conn: sqlite3.Connection, query: str, results: list[SearchResult]) -> None:
    created_at = datetime.now(timezone.utc).isoformat()
    conn.execute("DELETE FROM latest_results")
    conn.executemany(
        """
        INSERT INTO latest_results(result_id, file_id, file_path, query, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        [(item.result_id, item.file_id, str(item.path), query, created_at) for item in results],
    )
    conn.commit()


def get_latest_result_path(conn: sqlite3.Connection, result_id: int) -> Path | None:
    row = conn.execute(
        "SELECT file_path FROM latest_results WHERE result_id = ?",
        (result_id,),
    ).fetchone()
    return Path(row["file_path"]) if row else None
