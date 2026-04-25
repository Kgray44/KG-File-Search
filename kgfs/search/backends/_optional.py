"""Shared helpers for optional vector backend scaffolds."""

from __future__ import annotations

import importlib.util

from kgfs.search.backends.base import (
    BackendAvailability,
    VectorBackendRebuild,
    VectorIndexStatus,
    VectorSearchHit,
    VectorSearchOptions,
)
from kgfs.search.engine import SearchContext
from kgfs.vectors.metadata import backend_metadata_health
from kgfs.vectors.chunks import count_chunks, count_files_with_chunks
from kgfs.vectors.storage import backend_artifact_dir, clear_backend_artifacts


class OptionalArtifactVectorBackend:
    name = ""
    module_name = ""
    package_name = ""
    install_hint = ""
    config_section = ""
    experimental = False
    artifact_filenames: tuple[str, ...] = ()

    def available(self, context: SearchContext) -> BackendAvailability:
        dependency = self._dependency_availability(context)
        if not dependency.available:
            return dependency
        health = backend_metadata_health(
            context.conn,
            context.config,
            self.name,
            context.config.semantic.model_name,
            required_artifacts=self._artifact_paths(context),
        )
        if not health.ready:
            return BackendAvailability(
                False,
                f"{self.name} index is {health.status}. Run kgfs vector rebuild --backend {self.name}.",
            )
        return BackendAvailability(True, f"{self.name} backend is available.")

    def status(self, context: SearchContext) -> VectorIndexStatus:
        availability = self.available(context)
        artifact_dir = backend_artifact_dir(
            context.config,
            self.name,
            model_name=context.config.semantic.model_name,
        )
        warnings = []
        if not availability.available:
            warnings.append(availability.message)
            if availability.install_hint:
                warnings.append(availability.install_hint)
        health = backend_metadata_health(
            context.conn,
            context.config,
            self.name,
            context.config.semantic.model_name,
            required_artifacts=self._artifact_paths(context),
        )
        return VectorIndexStatus(
            backend_name=self.name,
            semantic_enabled=context.config.semantic.enabled,
            model_name=context.config.semantic.model_name,
            chunk_count=count_chunks(context.conn, model_name=context.config.semantic.model_name),
            file_count_with_chunks=count_files_with_chunks(context.conn, model_name=context.config.semantic.model_name),
            semantic_dependencies_available=False,
            chunks_ready=count_chunks(context.conn, model_name=context.config.semantic.model_name) > 0,
            backend_available=availability.available,
            warnings=warnings,
            install_hint=availability.install_hint,
            artifact_path=artifact_dir,
            backend_index_exists=artifact_dir.exists(),
            metadata={
                "experimental": self.experimental,
                "artifact_status": "unavailable" if availability.install_hint else health.status,
                "metadata_path": str(health.metadata_path) if health.metadata_path else None,
                "metadata_reasons": health.reasons,
                "embedding_dim": health.metadata.embedding_dim if health.metadata else 0,
                "chunk_count": health.metadata.chunk_count if health.metadata else 0,
            },
        )

    def search(
        self,
        query_vector: list[float],
        options: VectorSearchOptions,
        context: SearchContext,
    ) -> list[VectorSearchHit]:
        availability = self.available(context)
        raise RuntimeError(f"{self.name} vector search is unavailable: {availability.message}")

    def clear(self, context: SearchContext, *, model_name: str | None = None) -> int:
        return clear_backend_artifacts(context.config, self.name, model_name=model_name)

    def rebuild(self, context: SearchContext, *, model_name: str | None = None) -> VectorBackendRebuild:
        dependency = self._dependency_availability(context)
        if not dependency.available:
            message = dependency.message
            if dependency.install_hint:
                message = f"{message} {dependency.install_hint}"
            raise RuntimeError(message)
        raise RuntimeError(f"{self.name} backend rebuild is not implemented.")

    def stats(self, context: SearchContext) -> dict[str, object]:
        status = self.status(context)
        return {
            "backend": self.name,
            "available": status.backend_available,
            "artifact_path": str(status.artifact_path) if status.artifact_path else None,
            "backend_index_exists": status.backend_index_exists,
        }

    def _dependency_availability(self, context: SearchContext) -> BackendAvailability:
        if importlib.util.find_spec(self.module_name) is None:
            return BackendAvailability(False, f"{self.name} requires {self.package_name}.", self.install_hint)
        settings = getattr(context.config.vectors, self.config_section)
        if not getattr(settings, "enabled", False):
            return BackendAvailability(
                False,
                f"{self.name} is installed but disabled. Set vectors.{self.config_section}.enabled: true.",
                self.install_hint,
            )
        return BackendAvailability(True, f"{self.name} dependencies are available.")

    def _artifact_paths(self, context: SearchContext) -> list:
        artifact_dir = backend_artifact_dir(
            context.config,
            self.name,
            model_name=context.config.semantic.model_name,
        )
        return [artifact_dir / filename for filename in self.artifact_filenames]
