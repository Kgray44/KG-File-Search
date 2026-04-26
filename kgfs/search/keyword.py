"""SQLite FTS5 keyword search."""

from __future__ import annotations

import sqlite3
import re
from pathlib import Path

from kgfs.core.config import HybridSettings, KGFSConfig, SemanticSettings, VectorSettings
from kgfs.core.models import SearchResult
from kgfs.search.backends import get_vector_backend
from kgfs.search.backends.base import VectorSearchHit, VectorSearchOptions
from kgfs.search.filters import SearchFilters, row_matches_filters
from kgfs.search.query import build_fts_query
from kgfs.search.ranking import combine_hybrid_score, keyword_score
from kgfs.search.engine import SearchContext
from kgfs.search.semantic import Embedder
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
    media_rows = _run_media_text_search(conn, query, limit, filters=filters, highlight=highlight)
    return _merge_keyword_and_media_results(rows, media_rows, limit)


def semantic_search(
    conn: sqlite3.Connection,
    query: str,
    *,
    embedder: Embedder,
    model_name: str | None = None,
    backend_name: str = "sqlite_scan",
    limit: int = 10,
    filters: SearchFilters | None = None,
    highlight: bool = False,
) -> list[SearchResult]:
    model = model_name or semantic_model_name_from_embedder(embedder)
    query_vector = embedder.embed([query])[0]
    backend = get_vector_backend(backend_name)
    context = SearchContext(
        conn=conn,
        config=KGFSConfig(
            semantic=SemanticSettings(enabled=True, model_name=model),
            vectors=VectorSettings(backend=backend_name),
        ),
        semantic_embedder=embedder,
    )
    hits = backend.search(
        query_vector,
        VectorSearchOptions(model_name=model, limit=max(limit * 5, 25), filters=filters),
        context,
    )

    best_by_file: dict[int, SearchResult] = {}
    for hit in hits:
        file_id = hit.file_id
        existing = best_by_file.get(file_id)
        if existing is None or hit.score > existing.score:
            snippet = make_snippet(hit.text, query, highlight=highlight) or hit.text
            best_by_file[file_id] = SearchResult(
                result_id=0,
                file_id=file_id,
                file_name=hit.file_name,
                path=hit.path,
                extension=hit.extension,
                modified_time=hit.modified_time,
                score=hit.score,
                snippet=snippet,
                normalized_path=hit.normalized_path,
                score_breakdown={"semantic": hit.score, "final": hit.score},
                matched_chunk_id=hit.chunk_id,
                mode="semantic",
                source="semantic",
                metadata=hit.metadata,
            )

    ranked = sorted(best_by_file.values(), key=lambda item: item.score, reverse=True)[:limit]
    return [_renumber(result, index) for index, result in enumerate(ranked, start=1)]


def hybrid_search(
    conn: sqlite3.Connection,
    query: str,
    *,
    embedder: Embedder,
    model_name: str | None = None,
    backend_name: str = "sqlite_scan",
    limit: int = 10,
    filters: SearchFilters | None = None,
    highlight: bool = False,
    hybrid_settings: HybridSettings | None = None,
) -> list[SearchResult]:
    settings = hybrid_settings or HybridSettings()
    candidate_limit = max(limit * settings.candidate_limit_multiplier, 25)
    keyword_results = search(conn, query, limit=candidate_limit, filters=filters, highlight=highlight)
    semantic_results = semantic_search(
        conn,
        query,
        embedder=embedder,
        model_name=model_name,
        backend_name=backend_name,
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
        SELECT id, file_name, path, normalized_path, extension, modified_time, extracted_text,
               extraction_status, extraction_source
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
        keyword_component = keyword.score if keyword else 0.0
        semantic_component = semantic.score if semantic else 0.0
        combined, breakdown = combine_hybrid_score(
            query=query,
            file_name=row["file_name"],
            path=row["path"],
            extracted_text=row["extracted_text"],
            modified_time=float(row["modified_time"]),
            keyword_score_value=keyword_component,
            semantic_score_value=semantic_component,
            settings=settings,
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
                score_breakdown=breakdown,
                matched_chunk_id=semantic.matched_chunk_id if semantic else None,
                mode="hybrid",
                source="hybrid",
                metadata=_hybrid_metadata(row["extraction_source"], keyword, semantic),
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
                f.extraction_source,
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
                score_breakdown={"keyword": score, "bm25": rank, "final": score},
                mode="keyword",
                source="keyword",
                metadata={"extraction_source": row["extraction_source"]},
            )
        )
    results.sort(key=lambda item: item.score, reverse=True)
    return [_renumber(result, index) for index, result in enumerate(results[:limit], start=1)]


def _run_media_text_search(
    conn: sqlite3.Connection,
    query: str,
    limit: int,
    *,
    filters: SearchFilters | None,
    highlight: bool,
) -> list[SearchResult]:
    terms = _media_query_terms(query)
    if not terms:
        return []
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
                f.extraction_source,
                mt.id AS media_text_id,
                mt.source_kind,
                mt.backend,
                mt.model_name,
                mt.text,
                mt.confidence
            FROM media_text mt
            JOIN files f ON f.id = mt.file_id
            ORDER BY mt.updated_at DESC, mt.id DESC
            LIMIT ?
            """,
            (max(limit * 20, 100),),
        ).fetchall()
    except sqlite3.OperationalError:
        return []

    results: list[SearchResult] = []
    for row in rows:
        if not row_matches_filters(row, filters):
            continue
        text = str(row["text"] or "")
        haystack = text.casefold()
        matches = sum(1 for term in terms if term in haystack)
        if matches <= 0:
            continue
        score = 0.75 + matches / max(len(terms), 1)
        if row["confidence"] is not None:
            score += max(0.0, min(1.0, float(row["confidence"]))) * 0.1
        source_kind = str(row["source_kind"] or "media")
        snippet = make_snippet(text, query, highlight=highlight) or text[:220]
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
                score_breakdown={"media": score, "final": score},
                mode="keyword",
                source="media",
                metadata={
                    "extraction_source": f"media:{source_kind}",
                    "media_source_kind": source_kind,
                    "media_backend": row["backend"],
                    "media_text_id": int(row["media_text_id"]),
                },
            )
        )
    results.sort(key=lambda item: item.score, reverse=True)
    return results[:limit]


def _merge_keyword_and_media_results(
    keyword_results: list[SearchResult],
    media_results: list[SearchResult],
    limit: int,
) -> list[SearchResult]:
    by_file: dict[int, SearchResult] = {}
    for result in keyword_results + media_results:
        existing = by_file.get(result.file_id)
        if existing is None:
            by_file[result.file_id] = result
        else:
            by_file[result.file_id] = _merge_same_file_result(existing, result)
    ranked = sorted(by_file.values(), key=lambda item: item.score, reverse=True)[:limit]
    return [_renumber(result, index) for index, result in enumerate(ranked, start=1)]


def _merge_same_file_result(left: SearchResult, right: SearchResult) -> SearchResult:
    media_result = _media_result(left) or _media_result(right)
    winner = right if right.score > left.score else left
    if media_result is None:
        return winner
    breakdown = dict(winner.score_breakdown or {})
    breakdown.update({f"media_{key}": value for key, value in (media_result.score_breakdown or {}).items()})
    breakdown["final"] = winner.score
    snippet = media_result.snippet if not winner.snippet else winner.snippet
    if winner.source != "media" and not winner.snippet:
        snippet = media_result.snippet
    return SearchResult(
        result_id=winner.result_id,
        file_id=winner.file_id,
        file_name=winner.file_name,
        path=winner.path,
        extension=winner.extension,
        modified_time=winner.modified_time,
        score=winner.score,
        snippet=snippet,
        normalized_path=winner.normalized_path,
        score_breakdown=breakdown,
        matched_chunk_id=winner.matched_chunk_id,
        mode=winner.mode,
        source="media" if winner.source == "media" else winner.source,
        metadata=dict(media_result.metadata),
    )


def _media_result(result: SearchResult) -> SearchResult | None:
    source = str(result.metadata.get("extraction_source", "") if result.metadata else "")
    return result if source.startswith("media:") else None


def _hybrid_metadata(extraction_source: str, keyword: SearchResult | None, semantic: SearchResult | None) -> dict[str, object]:
    for result in (keyword, semantic):
        if not result or not result.metadata:
            continue
        source = str(result.metadata.get("extraction_source", ""))
        if source.startswith("media:") or source.startswith("ocr"):
            return dict(result.metadata)
    return {"extraction_source": extraction_source}


def _media_query_terms(query: str) -> list[str]:
    return [term.casefold() for term in re.findall(r"[\w-]{2,}", query, flags=re.UNICODE)]


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
