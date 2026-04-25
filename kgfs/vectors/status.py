"""Vector index status helpers."""

from __future__ import annotations

import sqlite3

from kgfs.core.config import KGFSConfig
from kgfs.search.backends import UnknownVectorBackend, get_vector_backend, vector_backend_install_hint
from kgfs.search.backends.base import VectorIndexStatus
from kgfs.search.engine import SearchContext
from kgfs.search.semantic import get_semantic_status
from kgfs.vectors.chunks import count_chunks, count_files_with_chunks


def get_vector_status(conn: sqlite3.Connection, config: KGFSConfig) -> VectorIndexStatus:
    warnings: list[str] = []
    backend_name = config.vectors.backend
    semantic_status = get_semantic_status(config.semantic)
    chunk_count = count_chunks(conn, model_name=config.semantic.model_name)
    file_count = count_files_with_chunks(conn, model_name=config.semantic.model_name)

    backend_available = False
    try:
        backend = get_vector_backend(backend_name)
        availability = backend.available(SearchContext(conn=conn, config=config))
        backend_available = availability.available
        if not availability.available and availability.message:
            warnings.append(availability.message)
        if not availability.available and availability.install_hint:
            warnings.append(availability.install_hint)
    except UnknownVectorBackend as exc:
        warnings.append(str(exc))
        warnings.append(vector_backend_install_hint(backend_name))

    if config.semantic.enabled and chunk_count == 0:
        warnings.append("No semantic chunks are indexed for the configured model.")
    if config.semantic.enabled and not semantic_status.available:
        warnings.append(semantic_status.message)

    return VectorIndexStatus(
        backend_name=backend_name,
        semantic_enabled=config.semantic.enabled,
        model_name=config.semantic.model_name,
        chunk_count=chunk_count,
        file_count_with_chunks=file_count,
        semantic_dependencies_available=semantic_status.available,
        chunks_ready=chunk_count > 0,
        backend_available=backend_available,
        warnings=warnings,
        install_hint=next((warning for warning in warnings if "pip install" in warning), None),
    )
