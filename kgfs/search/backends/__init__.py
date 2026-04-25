"""Vector backend registry."""

from __future__ import annotations

from kgfs.search.backends.base import (
    BackendAvailability,
    VectorBackend,
    VectorIndexStatus,
    VectorSearchHit,
    VectorSearchOptions,
)


class UnknownVectorBackend(ValueError):
    """Raised when a configured vector backend is unknown."""


def get_vector_backend(name: str) -> VectorBackend:
    from kgfs.search.backends.sqlite_scan import SqliteScanVectorBackend

    normalized = str(name).strip().lower()
    if normalized == SqliteScanVectorBackend.name:
        return SqliteScanVectorBackend()
    raise UnknownVectorBackend(f"Unknown vector backend: {name}")


__all__ = [
    "BackendAvailability",
    "UnknownVectorBackend",
    "VectorBackend",
    "VectorIndexStatus",
    "VectorSearchHit",
    "VectorSearchOptions",
    "get_vector_backend",
]
