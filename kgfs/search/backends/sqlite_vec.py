"""Optional sqlite-vec backend."""

from __future__ import annotations

import sqlite3
import struct

from kgfs.search.backends._optional import OptionalArtifactVectorBackend
from kgfs.search.backends.base import BackendAvailability, VectorBackendRebuild, VectorSearchHit, VectorSearchOptions
from kgfs.search.engine import SearchContext
from kgfs.search.semantic import vector_to_blob
from kgfs.vectors.backend_index import load_chunk_vectors, vector_hits_from_chunk_scores
from kgfs.vectors.metadata import current_backend_metadata, write_backend_metadata
from kgfs.vectors.storage import backend_artifact_dir, clear_backend_artifacts


class SqliteVecVectorBackend(OptionalArtifactVectorBackend):
    name = "sqlite_vec"
    module_name = "sqlite_vec"
    package_name = "sqlite-vec"
    install_hint = 'Install sqlite-vec support with: python -m pip install -e ".[sqlite-vec]"'
    config_section = "sqlite_vec"
    experimental = True

    def available(self, context: SearchContext) -> BackendAvailability:
        dependency = self._dependency_availability(context)
        if not dependency.available:
            return dependency
        if not _table_exists(context.conn, _table_name(context.config.semantic.model_name)):
            return BackendAvailability(
                False,
                "sqlite_vec index table is missing. Run kgfs vector rebuild --backend sqlite_vec.",
            )
        return super().available(context)

    def rebuild(self, context: SearchContext, *, model_name: str | None = None) -> VectorBackendRebuild:
        model = model_name or context.config.semantic.model_name
        dependency = self._dependency_availability(context)
        if not dependency.available:
            message = dependency.message
            if dependency.install_hint:
                message = f"{message} {dependency.install_hint}"
            raise RuntimeError(message)

        sqlite_vec = _load_sqlite_vec(context.conn)
        vectors = load_chunk_vectors(context.conn, model)
        if not vectors:
            raise RuntimeError("No semantic chunks are indexed for this model. Run kgfs vector rebuild first.")
        dim = vectors[0].embedding_dim
        if any(item.embedding_dim != dim for item in vectors):
            raise RuntimeError("Chunk embeddings have mixed dimensions. Rebuild semantic chunks before sqlite_vec.")

        table = _table_name(model)
        context.conn.execute(f"DROP TABLE IF EXISTS {table}")
        context.conn.execute(f"CREATE VIRTUAL TABLE {table} USING vec0(embedding float[{dim}])")
        serialize = getattr(sqlite_vec, "serialize_float32", vector_to_blob)
        context.conn.executemany(
            f"INSERT INTO {table}(rowid, embedding) VALUES (?, ?)",
            [(item.chunk_id, serialize(item.embedding)) for item in vectors],
        )
        metadata = current_backend_metadata(context.conn, context.config, self.name, model)
        metadata_path = write_backend_metadata(context.config, metadata)
        context.conn.commit()
        return VectorBackendRebuild(
            backend_name=self.name,
            chunk_count=len(vectors),
            artifact_path=backend_artifact_dir(context.config, self.name, model_name=model),
            metadata_path=metadata_path,
            message=f"sqlite_vec table {table} rebuilt from {len(vectors)} chunks.",
        )

    def search(
        self,
        query_vector: list[float],
        options: VectorSearchOptions,
        context: SearchContext,
    ) -> list[VectorSearchHit]:
        availability = self.available(context)
        if not availability.available:
            raise RuntimeError(f"sqlite_vec vector search is unavailable: {availability.message}")
        if not query_vector:
            return []
        sqlite_vec = _load_sqlite_vec(context.conn)
        serialize = getattr(sqlite_vec, "serialize_float32", vector_to_blob)
        table = _table_name(options.model_name)
        candidate_limit = _candidate_limit(options)
        try:
            rows = context.conn.execute(
                f"""
                SELECT rowid AS chunk_id, distance
                FROM {table}
                WHERE embedding MATCH ? AND k = ?
                ORDER BY distance
                """,
                (serialize(query_vector), candidate_limit),
            ).fetchall()
        except sqlite3.Error as exc:
            raise RuntimeError(f"sqlite_vec search failed. Rebuild with kgfs vector rebuild --backend sqlite_vec. {exc}") from exc
        scores = [(int(row["chunk_id"]), max(0.0, 1.0 - float(row["distance"]))) for row in rows]
        return vector_hits_from_chunk_scores(context.conn, scores, options)

    def clear(self, context: SearchContext, *, model_name: str | None = None) -> int:
        model = model_name or context.config.semantic.model_name
        table = _table_name(model)
        existed = _table_exists(context.conn, table)
        context.conn.execute(f"DROP TABLE IF EXISTS {table}")
        context.conn.commit()
        return (1 if existed else 0) + clear_backend_artifacts(context.config, self.name, model_name=model)


def _load_sqlite_vec(conn: sqlite3.Connection):
    try:
        import sqlite_vec
    except ImportError as exc:
        raise RuntimeError('sqlite_vec requires sqlite-vec. Install with: python -m pip install -e ".[sqlite-vec]"') from exc
    try:
        conn.enable_load_extension(True)
    except (AttributeError, sqlite3.Error):
        pass
    try:
        sqlite_vec.load(conn)
    finally:
        try:
            conn.enable_load_extension(False)
        except (AttributeError, sqlite3.Error):
            pass
    return sqlite_vec


def _table_name(model_name: str) -> str:
    import hashlib

    digest = hashlib.sha256(model_name.encode("utf-8")).hexdigest()[:16]
    return f"kgfs_vec_sqlite_vec_{digest}"


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE name = ? AND type IN ('table', 'virtual table')",
        (table_name,),
    ).fetchone()
    return row is not None


def _candidate_limit(options: VectorSearchOptions) -> int:
    if options.filters:
        return max(options.limit * 20, 100)
    return max(options.limit * 5, options.limit, 1)
