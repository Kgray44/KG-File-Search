"""Local similar-file search."""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass, replace
from pathlib import Path
from sqlite3 import Connection

from kgfs.core.config import KGFSConfig
from kgfs.core.models import SearchResult
from kgfs.db.latest_results import get_latest_result_record, save_latest_results
from kgfs.search.backends import get_vector_backend
from kgfs.search.backends.base import VectorSearchOptions
from kgfs.search.engine import SearchContext
from kgfs.search.query import STOPWORDS
from kgfs.search.semantic import cosine_similarity, unpack_vector
from kgfs.search.snippets import make_snippet


@dataclass(frozen=True)
class SimilarSearchReport:
    source: SearchResult
    results: list[SearchResult]
    strategy: str
    warnings: list[str]


def similar_from_result(
    conn: Connection,
    result_id: int,
    config: KGFSConfig,
    *,
    limit: int | None = None,
    include_self: bool = False,
    save_latest: bool = False,
) -> SimilarSearchReport:
    latest = get_latest_result_record(conn, result_id)
    if latest is None:
        raise ValueError(f"No latest search result found for ID {result_id}. Run kgfs search first.")
    source = _load_file_result(conn, latest.file_id, result_id)
    report = _similar_for_source(conn, source, config, limit=limit, include_self=include_self)
    if save_latest:
        save_latest_results(conn, f"similar:{result_id}", report.results)
    return report


def similar_file(
    conn: Connection,
    path: Path,
    config: KGFSConfig,
    *,
    limit: int | None = None,
    include_self: bool = False,
) -> SimilarSearchReport:
    normalized = str(path.expanduser())
    row = conn.execute(
        "SELECT id FROM files WHERE path = ? OR normalized_path = ?",
        (normalized, normalized),
    ).fetchone()
    if row is None:
        resolved = path.expanduser()
        for candidate in conn.execute("SELECT id, path FROM files").fetchall():
            if Path(candidate["path"]) == resolved:
                row = candidate
                break
    if row is None:
        raise ValueError(f"File is not indexed: {path}")
    source = _load_file_result(conn, int(row["id"]), 1)
    return _similar_for_source(conn, source, config, limit=limit, include_self=include_self)


def _similar_for_source(
    conn: Connection,
    source: SearchResult,
    config: KGFSConfig,
    *,
    limit: int | None,
    include_self: bool,
) -> SimilarSearchReport:
    selected_limit = limit or config.similar.default_limit
    vector_report = _vector_similar(conn, source, config, limit=selected_limit, include_self=include_self)
    if vector_report.results:
        return vector_report
    return _keyword_similar(conn, source, config, limit=selected_limit, include_self=include_self)


def _vector_similar(
    conn: Connection,
    source: SearchResult,
    config: KGFSConfig,
    *,
    limit: int,
    include_self: bool,
) -> SimilarSearchReport:
    vector = _average_file_vector(conn, source.file_id, config.semantic.model_name)
    if vector is None:
        return SimilarSearchReport(source=source, results=[], strategy="keyword", warnings=["No source vectors found."])
    backend = get_vector_backend(config.vectors.backend)
    context = SearchContext(conn=conn, config=config)
    availability = backend.available(context)
    if not availability.available:
        return SimilarSearchReport(source=source, results=[], strategy="keyword", warnings=[availability.message])
    hits = backend.search(
        vector,
        VectorSearchOptions(model_name=config.semantic.model_name, limit=max(limit * 5, 25)),
        context,
    )
    best_by_file: dict[int, SearchResult] = {}
    for hit in hits:
        if not include_self and hit.file_id == source.file_id:
            continue
        existing = best_by_file.get(hit.file_id)
        if existing is not None and existing.score >= hit.score:
            continue
        metadata = dict(hit.metadata)
        metadata["similar_reason"] = "nearby semantic chunk"
        result = SearchResult(
            result_id=0,
            file_id=hit.file_id,
            file_name=hit.file_name,
            path=hit.path,
            extension=hit.extension,
            modified_time=hit.modified_time,
            score=hit.score,
            snippet=make_snippet(hit.text, source.file_name) or hit.text,
            normalized_path=hit.normalized_path,
            score_breakdown={"semantic_similarity": hit.score, "final": hit.score},
            matched_chunk_id=hit.chunk_id,
            mode="similar",
            source="vector",
            metadata=metadata,
        )
        best_by_file[hit.file_id] = result
    ranked = sorted(best_by_file.values(), key=lambda result: result.score, reverse=True)[:limit]
    return SimilarSearchReport(
        source=source,
        results=[replace(result, result_id=index) for index, result in enumerate(ranked, start=1)],
        strategy="vector",
        warnings=[],
    )


def _keyword_similar(
    conn: Connection,
    source: SearchResult,
    config: KGFSConfig,
    *,
    limit: int,
    include_self: bool,
) -> SimilarSearchReport:
    source_text = _file_text(conn, source.file_id)
    terms = _top_terms(f"{source.file_name} {source_text}", limit=8)
    source_terms = set(terms)
    ranked: list[SearchResult] = []
    rows = conn.execute(
        """
        SELECT id, file_name, path, normalized_path, extension, modified_time, extracted_text, extraction_source
        FROM files
        """
    ).fetchall()
    for row in rows:
        file_id = int(row["id"])
        if not include_self and file_id == source.file_id:
            continue
        candidate_terms = set(_top_terms(f"{row['file_name']} {row['extracted_text']}", limit=12))
        score = _jaccard(source_terms, candidate_terms)
        if score <= config.similar.min_score:
            continue
        metadata = {"extraction_source": row["extraction_source"]}
        metadata["similar_reason"] = "shared local terms"
        ranked.append(
            SearchResult(
                result_id=0,
                file_id=file_id,
                file_name=row["file_name"],
                path=Path(row["path"]),
                extension=row["extension"],
                modified_time=float(row["modified_time"]),
                score=score,
                snippet=make_snippet(
                    row["extracted_text"], " ".join(terms[:3]), highlight=config.search.highlight_matches
                ),
                normalized_path=row["normalized_path"],
                mode="similar",
                source="keyword",
                score_breakdown={"term_overlap": score, "final": score},
                metadata=metadata,
            )
        )
    ranked.sort(key=lambda result: result.score, reverse=True)
    return SimilarSearchReport(
        source=source,
        results=[replace(result, result_id=index) for index, result in enumerate(ranked[:limit], start=1)],
        strategy="keyword",
        warnings=[],
    )


def _load_file_result(conn: Connection, file_id: int, result_id: int) -> SearchResult:
    row = conn.execute(
        """
        SELECT id, file_name, path, normalized_path, extension, modified_time, extracted_text, extraction_source
        FROM files
        WHERE id = ?
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
        score=1.0,
        snippet=make_snippet(row["extracted_text"], row["file_name"]),
        normalized_path=row["normalized_path"],
        mode="similar-source",
        source="latest",
        metadata={"extraction_source": row["extraction_source"]},
    )


def _file_text(conn: Connection, file_id: int) -> str:
    row = conn.execute("SELECT extracted_text FROM files WHERE id = ?", (file_id,)).fetchone()
    return row["extracted_text"] if row else ""


def _top_terms(text: str, *, limit: int) -> list[str]:
    counts: dict[str, int] = {}
    for term in re.findall(r"\b[\w]{3,}\b", text.casefold(), flags=re.UNICODE):
        if term in STOPWORDS:
            continue
        counts[term] = counts.get(term, 0) + 1
    return [term for term, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _average_file_vector(conn: Connection, file_id: int, model_name: str) -> list[float] | None:
    rows = conn.execute(
        "SELECT embedding, embedding_dim FROM chunks WHERE file_id = ? AND model_name = ?",
        (file_id, model_name),
    ).fetchall()
    vectors: list[list[float]] = []
    for row in rows:
        try:
            vectors.append(unpack_vector(row["embedding"], int(row["embedding_dim"])))
        except (struct.error, ValueError):
            continue
    if not vectors:
        return None
    dimension = len(vectors[0])
    if dimension == 0:
        return None
    return [sum(vector[index] for vector in vectors) / len(vectors) for index in range(dimension)]


def text_similarity(left: str, right: str) -> float:
    return _jaccard(set(_top_terms(left, limit=40)), set(_top_terms(right, limit=40)))


def semantic_file_similarity(conn: Connection, left_file_id: int, right_file_id: int, model_name: str) -> float | None:
    left = _average_file_vector(conn, left_file_id, model_name)
    right = _average_file_vector(conn, right_file_id, model_name)
    if left is None or right is None:
        return None
    return cosine_similarity(left, right)
