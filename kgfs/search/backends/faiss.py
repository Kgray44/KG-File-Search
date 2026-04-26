"""Optional FAISS vector backend."""

from __future__ import annotations

from kgfs.search.backends._optional import OptionalArtifactVectorBackend
from kgfs.search.backends.base import BackendAvailability, VectorBackendRebuild, VectorSearchHit, VectorSearchOptions
from kgfs.search.engine import SearchContext
from kgfs.vectors.backend_index import load_chunk_vectors, vector_hits_from_chunk_scores
from kgfs.vectors.metadata import current_backend_metadata, write_backend_metadata
from kgfs.vectors.storage import backend_artifact_dir, backend_artifact_path


class FaissVectorBackend(OptionalArtifactVectorBackend):
    name = "faiss"
    module_name = "faiss"
    package_name = "faiss-cpu"
    install_hint = 'Install faiss-cpu support with: python -m pip install -e ".[faiss]"'
    config_section = "faiss"
    artifact_filenames = ("index.faiss",)

    def _dependency_availability(self, context: SearchContext) -> BackendAvailability:
        import importlib.util

        if importlib.util.find_spec("faiss") is None and importlib.util.find_spec("faiss_cpu") is None:
            return BackendAvailability(False, f"{self.name} requires {self.package_name}.", self.install_hint)
        settings = getattr(context.config.vectors, self.config_section)
        if not getattr(settings, "enabled", False):
            return BackendAvailability(
                False,
                f"{self.name} is installed but disabled. Set vectors.{self.config_section}.enabled: true.",
                self.install_hint,
            )
        return BackendAvailability(True, f"{self.name} dependencies are available.")

    def available(self, context: SearchContext) -> BackendAvailability:
        dependency = self._dependency_availability(context)
        if not dependency.available:
            return dependency
        if context.config.vectors.faiss.use_gpu:
            return BackendAvailability(
                False, "FAISS GPU mode is not supported by KGFS yet. Set vectors.faiss.use_gpu: false."
            )
        if not _numpy_available():
            return BackendAvailability(False, "faiss requires numpy.", self.install_hint)
        return super().available(context)

    def rebuild(self, context: SearchContext, *, model_name: str | None = None) -> VectorBackendRebuild:
        model = model_name or context.config.semantic.model_name
        dependency = self._dependency_availability(context)
        if not dependency.available:
            message = dependency.message
            if dependency.install_hint:
                message = f"{message} {dependency.install_hint}"
            raise RuntimeError(message)
        if context.config.vectors.faiss.use_gpu:
            raise RuntimeError("FAISS GPU mode is not supported by KGFS yet. Set vectors.faiss.use_gpu: false.")
        faiss, np = _load_faiss_dependencies()
        vectors = load_chunk_vectors(context.conn, model)
        if not vectors:
            raise RuntimeError("No semantic chunks are indexed for this model. Run kgfs vector rebuild first.")
        dim = vectors[0].embedding_dim
        if any(item.embedding_dim != dim for item in vectors):
            raise RuntimeError("Chunk embeddings have mixed dimensions. Rebuild semantic chunks before FAISS.")
        if context.config.vectors.faiss.index_type != "flat":
            raise RuntimeError("Only FAISS flat indexes are supported in KGFS right now.")

        artifact_dir = backend_artifact_dir(context.config, self.name, model_name=model)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        index_path = backend_artifact_path(context.config, self.name, "index.faiss", model_name=model)
        base = faiss.IndexFlatIP(dim)
        index = faiss.IndexIDMap(base)
        matrix = np.asarray([item.embedding for item in vectors], dtype=np.float32)
        ids = np.asarray([item.chunk_id for item in vectors], dtype=np.int64)
        index.add_with_ids(matrix, ids)
        faiss.write_index(index, str(index_path))
        metadata = current_backend_metadata(
            context.conn, context.config, self.name, model, artifact_files=["index.faiss"]
        )
        metadata_path = write_backend_metadata(context.config, metadata)
        return VectorBackendRebuild(
            backend_name=self.name,
            chunk_count=len(vectors),
            artifact_path=index_path,
            metadata_path=metadata_path,
            message=f"FAISS flat index rebuilt from {len(vectors)} chunks.",
        )

    def search(
        self,
        query_vector: list[float],
        options: VectorSearchOptions,
        context: SearchContext,
    ) -> list[VectorSearchHit]:
        availability = self.available(context)
        if not availability.available:
            raise RuntimeError(f"FAISS vector search is unavailable: {availability.message}")
        if not query_vector:
            return []
        faiss, np = _load_faiss_dependencies()
        status = self.status(context)
        dim = int(status.metadata.get("embedding_dim") or len(query_vector))
        if len(query_vector) != dim:
            raise RuntimeError("FAISS query vector dimension differs from the backend index. Rebuild vectors.")
        chunk_count = max(0, status.chunk_count)
        if chunk_count == 0:
            return []
        index = faiss.read_index(
            str(backend_artifact_path(context.config, self.name, "index.faiss", model_name=options.model_name))
        )
        k = chunk_count if options.filters else min(chunk_count, max(options.limit * 5, options.limit, 1))
        scores, ids = index.search(np.asarray([query_vector], dtype=np.float32), k)
        chunk_scores = [
            (int(chunk_id), max(0.0, float(score))) for chunk_id, score in zip(ids[0], scores[0]) if int(chunk_id) >= 0
        ]
        return vector_hits_from_chunk_scores(context.conn, chunk_scores, options)


def _load_faiss_dependencies():
    try:
        try:
            import faiss
        except ImportError:
            import faiss_cpu as faiss
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            'faiss requires faiss-cpu and numpy. Install with: python -m pip install -e ".[faiss]"'
        ) from exc
    return faiss, np


def _numpy_available() -> bool:
    import importlib.util

    return importlib.util.find_spec("numpy") is not None
