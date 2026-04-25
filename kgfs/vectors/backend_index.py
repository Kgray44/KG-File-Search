"""Shared helpers for backend vector indexes."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from sqlite3 import Connection

from kgfs.search.backends.base import VectorSearchHit, VectorSearchOptions
from kgfs.search.filters import row_matches_filters
from kgfs.search.semantic import unpack_vector


@dataclass(frozen=True)
class StoredChunkVector:
    chunk_id: int
    embedding: list[float]
    embedding_dim: int


def load_chunk_vectors(conn: Connection, model_name: str) -> list[StoredChunkVector]:
    rows = conn.execute(
        """
        SELECT id, embedding, embedding_dim
        FROM chunks
        WHERE model_name = ?
        ORDER BY id
        """,
        (model_name,),
    ).fetchall()
    vectors: list[StoredChunkVector] = []
    for row in rows:
        try:
            vector = unpack_vector(row["embedding"], int(row["embedding_dim"]))
        except (struct.error, ValueError):
            continue
        vectors.append(
            StoredChunkVector(
                chunk_id=int(row["id"]),
                embedding=vector,
                embedding_dim=int(row["embedding_dim"]),
            )
        )
    return vectors


def vector_hits_from_chunk_scores(
    conn: Connection,
    chunk_scores: list[tuple[int, float]],
    options: VectorSearchOptions,
) -> list[VectorSearchHit]:
    if not chunk_scores:
        return []
    chunk_ids = [chunk_id for chunk_id, _ in chunk_scores]
    placeholders = ", ".join("?" for _ in chunk_ids)
    rows = conn.execute(
        f"""
        SELECT
            c.id AS chunk_id,
            c.file_id,
            c.chunk_index,
            c.text,
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
        WHERE c.id IN ({placeholders}) AND c.model_name = ?
        """,
        (*chunk_ids, options.model_name),
    ).fetchall()
    by_chunk_id = {int(row["chunk_id"]): row for row in rows}

    hits: list[VectorSearchHit] = []
    for chunk_id, score in chunk_scores:
        row = by_chunk_id.get(chunk_id)
        if row is None or not row_matches_filters(row, options.filters):
            continue
        hits.append(
            VectorSearchHit(
                chunk_id=chunk_id,
                file_id=int(row["file_id"]),
                chunk_index=int(row["chunk_index"]),
                text=row["text"],
                embedding_dim=int(row["embedding_dim"]),
                file_name=row["file_name"],
                path=Path(row["path"]),
                normalized_path=row["normalized_path"],
                extension=row["extension"],
                modified_time=float(row["modified_time"]),
                score=float(score),
                start_char=row["start_char"],
                end_char=row["end_char"],
            )
        )
        if len(hits) >= options.limit:
            break
    return hits
