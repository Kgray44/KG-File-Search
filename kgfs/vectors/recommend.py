"""Vector backend recommendation helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from sqlite3 import Connection

from kgfs.core.config import KGFSConfig
from kgfs.search.backends import UnknownVectorBackend, backend_availability_by_name, get_vector_backend
from kgfs.search.engine import SearchContext
from kgfs.vectors.chunks import count_chunks


@dataclass(frozen=True)
class VectorRecommendation:
    backend_name: str
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def recommend_vector_backend(conn: Connection, config: KGFSConfig) -> VectorRecommendation:
    chunk_count = count_chunks(conn, model_name=config.semantic.model_name)
    context = SearchContext(conn=conn, config=config)
    try:
        configured = get_vector_backend(config.vectors.backend)
        configured_availability = configured.available(context)
        configured_warning = "" if configured_availability.available else configured_availability.message
    except UnknownVectorBackend as exc:
        configured_warning = str(exc)

    if chunk_count == 0:
        return VectorRecommendation(
            "sqlite_scan",
            reasons=[
                "No semantic chunks are indexed yet.",
                "Build vectors first, then benchmark backends against your local data.",
            ],
            warnings=[configured_warning] if configured_warning else [],
        )

    availability = backend_availability_by_name(context)
    warnings = [configured_warning] if configured_warning else []
    if configured_warning:
        reasons = [
            f"Configured backend {config.vectors.backend!r} is unavailable.",
            "sqlite_scan is the built-in fallback and works without optional dependencies.",
        ]
        return VectorRecommendation("sqlite_scan", reasons=reasons, warnings=warnings)

    if chunk_count >= 10000 and availability.get("hnsw") and availability["hnsw"].available:
        return VectorRecommendation(
            "hnsw",
            reasons=[
                f"Your index has a large vector set ({chunk_count} chunks).",
                "hnsw is available and is a practical local ANN backend for larger indexes.",
            ],
            warnings=warnings,
        )

    return VectorRecommendation(
        "sqlite_scan",
        reasons=[
            f"Your index has {chunk_count} chunks.",
            "sqlite_scan is simple and reliable at this size.",
            "Benchmark optional backends before adding heavier dependencies.",
        ],
        warnings=warnings,
    )
