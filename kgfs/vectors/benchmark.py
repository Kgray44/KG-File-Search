"""Vector backend benchmark helpers."""

from __future__ import annotations

import statistics
import struct
import time
from dataclasses import dataclass, field
from sqlite3 import Connection

from kgfs.core.config import KGFSConfig
from kgfs.search.backends import UnknownVectorBackend, get_vector_backend, list_vector_backend_names
from kgfs.search.backends.base import VectorSearchOptions
from kgfs.search.engine import SearchContext
from kgfs.search.semantic import Embedder, get_embedder, unpack_vector
from kgfs.vectors.chunks import count_chunks, count_files_with_chunks


@dataclass(frozen=True)
class VectorBenchmarkResult:
    backend_name: str
    available: bool
    chunk_count: int
    file_count: int
    query_count: int
    artifact_status: str = "unknown"
    average_query_seconds: float | None = None
    median_query_seconds: float | None = None
    max_query_seconds: float | None = None
    notes: list[str] = field(default_factory=list)


def benchmark_vector_backends(
    conn: Connection,
    config: KGFSConfig,
    *,
    backend_names: list[str] | None = None,
    query_texts: list[str] | None = None,
    embedder: Embedder | None = None,
    limit: int = 10,
) -> list[VectorBenchmarkResult]:
    names = backend_names or list_vector_backend_names()
    query_vectors = _query_vectors(conn, config, query_texts=query_texts, embedder=embedder)
    results: list[VectorBenchmarkResult] = []
    for name in names:
        results.append(_benchmark_one(conn, config, name=name, query_vectors=query_vectors, limit=limit))
    return results


def _benchmark_one(
    conn: Connection,
    config: KGFSConfig,
    *,
    name: str,
    query_vectors: list[list[float]],
    limit: int,
) -> VectorBenchmarkResult:
    chunk_count = count_chunks(conn, model_name=config.semantic.model_name)
    file_count = count_files_with_chunks(conn, model_name=config.semantic.model_name)
    notes: list[str] = []
    try:
        backend = get_vector_backend(name)
    except UnknownVectorBackend as exc:
        return VectorBenchmarkResult(name, False, chunk_count, file_count, 0, artifact_status="unknown", notes=[str(exc)])

    context = SearchContext(conn=conn, config=config)
    status = backend.status(context)
    availability = backend.available(context)
    if not availability.available:
        if availability.message:
            notes.append(availability.message)
        if availability.install_hint:
            notes.append(availability.install_hint)
        return VectorBenchmarkResult(
            name,
            False,
            chunk_count,
            file_count,
            0,
            artifact_status="unavailable" if availability.install_hint else str(status.metadata.get("artifact_status", "unavailable")),
            notes=notes,
        )
    if not query_vectors:
        return VectorBenchmarkResult(
            name,
            True,
            chunk_count,
            file_count,
            0,
            artifact_status=str(status.metadata.get("artifact_status", "ready")),
            notes=["No vectors are available to benchmark."],
        )

    timings: list[float] = []
    for vector in query_vectors:
        start = time.perf_counter()
        backend.search(
            vector,
            VectorSearchOptions(model_name=config.semantic.model_name, limit=max(1, limit)),
            context,
        )
        timings.append(time.perf_counter() - start)
    return VectorBenchmarkResult(
        backend_name=name,
        available=True,
        chunk_count=chunk_count,
        file_count=file_count,
        query_count=len(timings),
        artifact_status=str(status.metadata.get("artifact_status", "ready")),
        average_query_seconds=statistics.fmean(timings),
        median_query_seconds=statistics.median(timings),
        max_query_seconds=max(timings),
        notes=notes or ["Benchmark used existing local vectors."],
    )


def _query_vectors(
    conn: Connection,
    config: KGFSConfig,
    *,
    query_texts: list[str] | None,
    embedder: Embedder | None,
) -> list[list[float]]:
    if query_texts:
        active_embedder = embedder or get_embedder(config.semantic)
        return active_embedder.embed(query_texts)

    rows = conn.execute(
        """
        SELECT embedding, embedding_dim
        FROM chunks
        WHERE model_name = ?
        ORDER BY id
        LIMIT 3
        """,
        (config.semantic.model_name,),
    ).fetchall()
    vectors: list[list[float]] = []
    for row in rows:
        try:
            vectors.append(unpack_vector(row["embedding"], int(row["embedding_dim"])))
        except (struct.error, ValueError):
            continue
    return vectors
