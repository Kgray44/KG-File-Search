"""Vector backend registry compatibility exports."""

from __future__ import annotations

from kgfs.search.backends.base import (
    BackendAvailability,
    VectorBackend,
    VectorIndexStatus,
    VectorSearchHit,
    VectorSearchOptions,
)
from kgfs.search.backends.registry import (
    UnknownVectorBackend,
    backend_availability_by_name,
    get_vector_backend,
    list_vector_backend_names,
    vector_backend_install_hint,
)


__all__ = [
    "BackendAvailability",
    "UnknownVectorBackend",
    "VectorBackend",
    "VectorIndexStatus",
    "VectorSearchHit",
    "VectorSearchOptions",
    "backend_availability_by_name",
    "get_vector_backend",
    "list_vector_backend_names",
    "vector_backend_install_hint",
]
