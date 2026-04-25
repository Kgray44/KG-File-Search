"""Optional hnswlib vector backend."""

from __future__ import annotations

from kgfs.search.backends._optional import OptionalArtifactVectorBackend
from kgfs.search.backends.base import BackendAvailability, VectorBackendRebuild, VectorSearchHit, VectorSearchOptions
from kgfs.search.engine import SearchContext
from kgfs.vectors.backend_index import load_chunk_vectors, vector_hits_from_chunk_scores
from kgfs.vectors.metadata import current_backend_metadata, write_backend_metadata
from kgfs.vectors.storage import backend_artifact_dir, backend_artifact_path


class HnswVectorBackend(OptionalArtifactVectorBackend):
    name = "hnsw"
    module_name = "hnswlib"
    package_name = "hnswlib"
    install_hint = 'Install hnswlib support with: python -m pip install -e ".[hnsw]"'
    config_section = "hnsw"
    artifact_filenames = ("index.bin",)

    def available(self, context: SearchContext) -> BackendAvailability:
        dependency = self._dependency_availability(context)
        if not dependency.available:
            return dependency
        numpy_available = _numpy_available()
        if not numpy_available:
            return BackendAvailability(False, "hnsw requires numpy.", self.install_hint)
        return super().available(context)

    def rebuild(self, context: SearchContext, *, model_name: str | None = None) -> VectorBackendRebuild:
        model = model_name or context.config.semantic.model_name
        dependency = self._dependency_availability(context)
        if not dependency.available:
            message = dependency.message
            if dependency.install_hint:
                message = f"{message} {dependency.install_hint}"
            raise RuntimeError(message)
        hnswlib, np = _load_hnsw_dependencies()
        vectors = load_chunk_vectors(context.conn, model)
        if not vectors:
            raise RuntimeError("No semantic chunks are indexed for this model. Run kgfs vector rebuild first.")
        dim = vectors[0].embedding_dim
        if any(item.embedding_dim != dim for item in vectors):
            raise RuntimeError("Chunk embeddings have mixed dimensions. Rebuild semantic chunks before hnsw.")

        artifact_dir = backend_artifact_dir(context.config, self.name, model_name=model)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        index_path = backend_artifact_path(context.config, self.name, "index.bin", model_name=model)
        settings = context.config.vectors.hnsw
        index = hnswlib.Index(space=settings.space, dim=dim)
        index.init_index(max_elements=len(vectors), ef_construction=settings.ef_construction, M=settings.m)
        matrix = np.asarray([item.embedding for item in vectors], dtype=np.float32)
        labels = np.asarray([item.chunk_id for item in vectors], dtype=np.int64)
        index.add_items(matrix, labels)
        index.set_ef(settings.ef_search)
        index.save_index(str(index_path))
        metadata = current_backend_metadata(context.conn, context.config, self.name, model, artifact_files=["index.bin"])
        metadata_path = write_backend_metadata(context.config, metadata)
        return VectorBackendRebuild(
            backend_name=self.name,
            chunk_count=len(vectors),
            artifact_path=index_path,
            metadata_path=metadata_path,
            message=f"hnsw index rebuilt from {len(vectors)} chunks.",
        )

    def search(
        self,
        query_vector: list[float],
        options: VectorSearchOptions,
        context: SearchContext,
    ) -> list[VectorSearchHit]:
        availability = self.available(context)
        if not availability.available:
            raise RuntimeError(f"hnsw vector search is unavailable: {availability.message}")
        if not query_vector:
            return []
        hnswlib, np = _load_hnsw_dependencies()
        status = self.status(context)
        dim = int(status.metadata.get("embedding_dim") or len(query_vector))
        if len(query_vector) != dim:
            raise RuntimeError("hnsw query vector dimension differs from the backend index. Rebuild vectors.")
        chunk_count = max(0, status.chunk_count)
        if chunk_count == 0:
            return []
        settings = context.config.vectors.hnsw
        index = hnswlib.Index(space=settings.space, dim=dim)
        index.load_index(str(backend_artifact_path(context.config, self.name, "index.bin", model_name=options.model_name)), max_elements=chunk_count)
        index.set_ef(settings.ef_search)
        k = chunk_count if options.filters else min(chunk_count, max(options.limit * 5, options.limit, 1))
        labels, distances = index.knn_query(np.asarray([query_vector], dtype=np.float32), k=k)
        scores = [
            (int(label), _distance_to_score(float(distance), settings.space))
            for label, distance in zip(labels[0], distances[0])
            if int(label) >= 0
        ]
        return vector_hits_from_chunk_scores(context.conn, scores, options)


def _load_hnsw_dependencies():
    try:
        import hnswlib
        import numpy as np
    except ImportError as exc:
        raise RuntimeError('hnsw requires hnswlib and numpy. Install with: python -m pip install -e ".[hnsw]"') from exc
    return hnswlib, np


def _numpy_available() -> bool:
    import importlib.util

    return importlib.util.find_spec("numpy") is not None


def _distance_to_score(distance: float, space: str) -> float:
    if space in {"cosine", "ip"}:
        return max(0.0, 1.0 - distance)
    return 1.0 / (1.0 + max(0.0, distance))
