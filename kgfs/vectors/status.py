"""Vector index status helpers."""

from __future__ import annotations

import sqlite3

from kgfs.core.config import KGFSConfig
from kgfs.search.backends import UnknownVectorBackend, get_vector_backend, list_vector_backend_names, vector_backend_install_hint
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
    artifact_path = None
    backend_index_exists = None
    metadata: dict[str, object] = {"known_backends": list_vector_backend_names()}
    try:
        backend = get_vector_backend(backend_name)
        availability = backend.available(SearchContext(conn=conn, config=config))
        backend_available = availability.available
        if not availability.available and availability.message:
            warnings.append(availability.message)
        if not availability.available and availability.install_hint:
            warnings.append(availability.install_hint)
        if backend.name != "sqlite_scan":
            backend_status = backend.status(SearchContext(conn=conn, config=config))
            artifact_path = backend_status.artifact_path
            backend_index_exists = backend_status.backend_index_exists
            metadata.update(backend_status.metadata)
        else:
            metadata["artifact_status"] = "ready"
    except UnknownVectorBackend as exc:
        warnings.append(str(exc))
        warnings.append(vector_backend_install_hint(backend_name))
        metadata["artifact_status"] = "unknown"

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
        artifact_path=artifact_path,
        backend_index_exists=backend_index_exists,
        metadata=metadata,
    )
