"""Vector index rebuild helpers."""

from __future__ import annotations

from dataclasses import dataclass
from sqlite3 import Connection

from kgfs.core.config import KGFSConfig
from kgfs.db.repositories import count_chunks_for_file
from kgfs.search.semantic import Embedder, chunk_text, get_embedder, replace_file_chunks, semantic_model_name


@dataclass(frozen=True)
class VectorRebuildSummary:
    files_considered: int = 0
    files_indexed: int = 0
    chunks_indexed: int = 0
    skipped_no_text: int = 0
    skipped_existing: int = 0


def rebuild_vector_index(
    config: KGFSConfig,
    conn: Connection,
    *,
    embedder: Embedder | None = None,
    force: bool = True,
) -> VectorRebuildSummary:
    if not config.semantic.enabled:
        raise ValueError("Semantic search is disabled. Set semantic.enabled: true before rebuilding vectors.")

    active_embedder = get_embedder(config.semantic, embedder)
    model_name = semantic_model_name(config.semantic, active_embedder)
    files_considered = files_indexed = chunks_indexed = skipped_no_text = skipped_existing = 0

    rows = conn.execute(
        """
        SELECT id, extracted_text
        FROM files
        WHERE extraction_status != 'error'
        ORDER BY id
        """
    ).fetchall()
    for row in rows:
        files_considered += 1
        file_id = int(row["id"])
        text = row["extracted_text"] or ""
        if not text.strip():
            skipped_no_text += 1
            continue
        if not force and count_chunks_for_file(conn, file_id, model_name) > 0:
            skipped_existing += 1
            continue
        chunks = chunk_text(
            text,
            chunk_size_chars=config.semantic.chunk_size_chars,
            chunk_overlap_chars=config.semantic.chunk_overlap_chars,
        )
        if not chunks:
            skipped_no_text += 1
            continue
        embeddings = active_embedder.embed([chunk.text for chunk in chunks])
        chunks_indexed += replace_file_chunks(
            conn,
            file_id=file_id,
            chunks=chunks,
            embeddings=embeddings,
            model_name=model_name,
        )
        files_indexed += 1

    return VectorRebuildSummary(
        files_considered=files_considered,
        files_indexed=files_indexed,
        chunks_indexed=chunks_indexed,
        skipped_no_text=skipped_no_text,
        skipped_existing=skipped_existing,
    )
