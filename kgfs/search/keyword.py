"""SQLite FTS5 keyword search."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from kgfs.core.models import SearchResult
from kgfs.search.filters import SearchFilters, row_matches_filters
from kgfs.search.query import build_fts_query
from kgfs.search.ranking import filename_path_relevance, keyword_score, recent_modification_bonus
from kgfs.search.semantic import Embedder, cosine_similarity, unpack_vector
from kgfs.search.snippets import make_snippet


def search(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 10,
    filters: SearchFilters | None = None,
    highlight: bool = False,
) -> list[SearchResult]:
    fts_query = build_fts_query(query)
    if not fts_query:
        return []
    rows = _run_search(conn, query, fts_query, limit, filters=filters, highlight=highlight)
    if not rows and " AND " in fts_query:
        rows = _run_search(
            conn,
            query,
            build_fts_query(query, use_or=True),
            limit,
            filters=filters,
            highlight=highlight,
        )
    return rows


def semantic_search(
    conn: sqlite3.Connection,
    query: str,
    *,
    embedder: Embedder,
    model_name: str | None = None,
    limit: int = 10,
    filters: SearchFilters | None = None,
    highlight: bool = False,
) -> list[SearchResult]:
    model = model_name or semantic_model_name_from_embedder(embedder)
    query_vector = embedder.embed([query])[0]
    rows = conn.execute(
        """
        SELECT
            c.file_id,
            c.id AS chunk_id,
            c.text,
            c.embedding,
            c.embedding_dim,
            f.file_name,
            f.path,
            f.normalized_path,
            f.extension,
            f.modified_time,
            f.extraction_status
        FROM chunks c
        JOIN files f ON f.id = c.file_id
        WHERE c.model_name = ?
        """,
        (model,),
    ).fetchall()

    best_by_file: dict[int, SearchResult] = {}
    for row in rows:
        if not row_matches_filters(row, filters):
            continue
        vector = unpack_vector(row["embedding"], int(row["embedding_dim"]))
        similarity = cosine_similarity(query_vector, vector)
        score = max(0.0, similarity)
        file_id = int(row["file_id"])
        existing = best_by_file.get(file_id)
        if existing is None or score > existing.score:
            snippet = make_snippet(row["text"], query, highlight=highlight) or row["text"]
            best_by_file[file_id] = SearchResult(
                result_id=0,
                file_id=file_id,
                file_name=row["file_name"],
                path=Path(row["path"]),
                extension=row["extension"],
                modified_time=float(row["modified_time"]),
                score=score,
                snippet=snippet,
                normalized_path=row["normalized_path"],
                score_breakdown={"semantic": score},
                matched_chunk_id=int(row["chunk_id"]),
                mode="semantic",
                source="semantic",
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
    filters: SearchFilters | None = None,
    highlight: bool = False,
) -> list[SearchResult]:
    candidate_limit = max(limit * 5, 25)
    keyword_results = search(conn, query, limit=candidate_limit, filters=filters, highlight=highlight)
    semantic_results = semantic_search(
        conn,
        query,
        embedder=embedder,
        model_name=model_name,
        limit=candidate_limit,
        filters=filters,
        highlight=highlight,
    )
    keyword_by_file = {result.file_id: result for result in keyword_results}
    semantic_by_file = {result.file_id: result for result in semantic_results}
    file_ids = sorted(set(keyword_by_file) | set(semantic_by_file))
    if not file_ids:
        return []

    placeholders = ", ".join("?" for _ in file_ids)
    rows = conn.execute(
        f"""
        SELECT id, file_name, path, normalized_path, extension, modified_time, extracted_text, extraction_status
        FROM files
        WHERE id IN ({placeholders})
        """,
        tuple(file_ids),
    ).fetchall()

    ranked: list[SearchResult] = []
    for row in rows:
        file_id = int(row["id"])
        if not row_matches_filters(row, filters):
            continue
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
            else make_snippet(row["extracted_text"], query, highlight=highlight)
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
                normalized_path=row["normalized_path"],
                score_breakdown={
                    "semantic": semantic_score,
                    "keyword": keyword_score,
                    "filename_path": filename_score,
                    "recency": recency_score,
                },
                matched_chunk_id=semantic.matched_chunk_id if semantic else None,
                mode="hybrid",
                source="hybrid",
            )
        )

    ranked.sort(key=lambda item: item.score, reverse=True)
    return [_renumber(result, index) for index, result in enumerate(ranked[:limit], start=1)]


def _run_search(
    conn: sqlite3.Connection,
    query: str,
    fts_query: str,
    limit: int,
    *,
    filters: SearchFilters | None = None,
    highlight: bool = False,
) -> list[SearchResult]:
    candidate_limit = max(limit * 20, 100) if filters else limit
    try:
        rows = conn.execute(
            """
            SELECT
                f.id,
                f.file_name,
                f.path,
                f.normalized_path,
                f.extension,
                f.modified_time,
                f.extracted_text,
                f.extraction_status,
                bm25(files_fts) AS rank,
                snippet(files_fts, 2, '', '', '...', 18) AS fts_snippet
            FROM files_fts
            JOIN files f ON f.id = files_fts.rowid
            WHERE files_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts_query, candidate_limit),
        ).fetchall()
    except sqlite3.OperationalError:
        return []

    results: list[SearchResult] = []
    for row in rows:
        if not row_matches_filters(row, filters):
            continue
        rank = float(row["rank"])
        snippet = make_snippet(row["extracted_text"], query, highlight=highlight) or row["fts_snippet"] or ""
        score = keyword_score(query, row, rank)
        results.append(
            SearchResult(
                result_id=0,
                file_id=int(row["id"]),
                file_name=row["file_name"],
                path=Path(row["path"]),
                extension=row["extension"],
                modified_time=float(row["modified_time"]),
                score=score,
                snippet=snippet,
                normalized_path=row["normalized_path"],
                score_breakdown={"keyword": score, "bm25": rank},
                mode="keyword",
                source="keyword",
            )
        )
    results.sort(key=lambda item: item.score, reverse=True)
    return [_renumber(result, index) for index, result in enumerate(results[:limit], start=1)]


def semantic_model_name_from_embedder(embedder: Embedder) -> str:
    return getattr(embedder, "model_name", "")


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
        normalized_path=result.normalized_path,
        score_breakdown=result.score_breakdown,
        matched_chunk_id=result.matched_chunk_id,
        mode=result.mode,
        source=result.source,
        metadata=result.metadata,
    )
