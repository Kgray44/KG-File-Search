"""Vector backend interfaces for semantic search."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from kgfs.search.engine import SearchContext
from kgfs.search.filters import SearchFilters


@dataclass(frozen=True)
class BackendAvailability:
    available: bool
    message: str = ""
    install_hint: str | None = None


@dataclass(frozen=True)
class VectorSearchOptions:
    model_name: str
    limit: int = 10
    filters: SearchFilters | None = None


@dataclass(frozen=True)
class VectorSearchHit:
    chunk_id: int
    file_id: int
    chunk_index: int
    text: str
    embedding_dim: int
    file_name: str
    path: Path
    normalized_path: str
    extension: str
    modified_time: float
    score: float
    start_char: int | None = None
    end_char: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class VectorIndexStatus:
    backend_name: str
    semantic_enabled: bool
    model_name: str
    chunk_count: int
    file_count_with_chunks: int
    semantic_dependencies_available: bool
    chunks_ready: bool
    backend_available: bool
    warnings: list[str] = field(default_factory=list)
    install_hint: str | None = None
    artifact_path: Path | None = None
    backend_index_exists: bool | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class VectorBackendRebuild:
    backend_name: str
    chunk_count: int
    artifact_path: Path | None = None
    metadata_path: Path | None = None
    message: str = ""


class VectorBackend(Protocol):
    name: str

    def available(self, context: SearchContext) -> BackendAvailability:
        """Return whether this backend can be used for the current context."""

    def status(self, context: SearchContext) -> VectorIndexStatus:
        """Return vector index status for the current context."""

    def search(
        self,
        query_vector: list[float],
        options: VectorSearchOptions,
        context: SearchContext,
    ) -> list[VectorSearchHit]:
        """Return nearest chunk hits for a query vector."""

    def clear(self, context: SearchContext, *, model_name: str | None = None) -> int:
        """Clear vector data and return deleted chunk count."""

    def rebuild(self, context: SearchContext, *, model_name: str | None = None) -> VectorBackendRebuild:
        """Rebuild backend-specific vector artifacts from existing chunks."""

    def stats(self, context: SearchContext) -> dict[str, object]:
        return {}
