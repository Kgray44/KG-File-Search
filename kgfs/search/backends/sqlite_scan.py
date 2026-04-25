"""SQLite brute-force vector backend."""

from __future__ import annotations

import sqlite3
import struct
from pathlib import Path

from kgfs.search.backends.base import BackendAvailability, VectorIndexStatus, VectorSearchHit, VectorSearchOptions
from kgfs.search.engine import SearchContext
from kgfs.search.filters import row_matches_filters
from kgfs.search.semantic import cosine_similarity, unpack_vector
from kgfs.vectors.chunks import clear_chunks, count_chunks, count_files_with_chunks


class SqliteScanVectorBackend:
    name = "sqlite_scan"

    def available(self, context: SearchContext) -> BackendAvailability:
        if _table_exists(context.conn, "chunks"):
            return BackendAvailability(True, "SQLite chunks table is available.")
        return BackendAvailability(False, "SQLite chunks table is missing.")

    def status(self, context: SearchContext) -> VectorIndexStatus:
        from kgfs.vectors.status import get_vector_status

        return get_vector_status(context.conn, context.config)

    def search(
        self,
        query_vector: list[float],
        options: VectorSearchOptions,
        context: SearchContext,
    ) -> list[VectorSearchHit]:
        if not query_vector:
            return []
        rows = context.conn.execute(
            """
            SELECT
                c.id AS chunk_id,
                c.file_id,
                c.chunk_index,
                c.text,
                c.embedding,
                c.embedding_dim,
                c.start_char,
                c.end_char,
                f.file_name,
                f.path,
                f.normalized_path,
                f.extension,
                f.modified_time,
                f.extraction_status
            FROM chunks c
            JOIN files f ON f.id = c.file_id
            WHERE c.model_name = ?
            """,
            (options.model_name,),
        ).fetchall()

        hits: list[VectorSearchHit] = []
        for row in rows:
            if not row_matches_filters(row, options.filters):
                continue
            try:
                vector = unpack_vector(row["embedding"], int(row["embedding_dim"]))
            except (struct.error, ValueError):
                continue
            if len(vector) != len(query_vector):
                continue
            score = max(0.0, cosine_similarity(query_vector, vector))
            hits.append(
                VectorSearchHit(
                    chunk_id=int(row["chunk_id"]),
                    file_id=int(row["file_id"]),
                    chunk_index=int(row["chunk_index"]),
                    text=row["text"],
                    embedding_dim=int(row["embedding_dim"]),
                    file_name=row["file_name"],
                    path=Path(row["path"]),
                    normalized_path=row["normalized_path"],
                    extension=row["extension"],
                    modified_time=float(row["modified_time"]),
                    score=score,
                    start_char=row["start_char"],
                    end_char=row["end_char"],
                )
            )
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[: options.limit]

    def clear(self, context: SearchContext, *, model_name: str | None = None) -> int:
        return clear_chunks(context.conn, model_name=model_name)

    def stats(self, context: SearchContext) -> dict[str, object]:
        model_name = context.config.semantic.model_name
        return {
            "backend": self.name,
            "chunk_count": count_chunks(context.conn, model_name=model_name),
            "file_count_with_chunks": count_files_with_chunks(context.conn, model_name=model_name),
        }


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)).fetchone()
    return row is not None
