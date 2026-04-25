"""Index configured folders into SQLite."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from sqlite3 import Connection

from kgfs.config import KGFSConfig
from kgfs.database import count_chunks_for_file, get_existing_file, upsert_file
from kgfs.extractors import extract_text
from kgfs.file_discovery import discover_files
from kgfs.hashing import sha256_file
from kgfs.models import FileRecord, IndexSummary
from kgfs.platform_utils import current_platform_name, normalize_path
from kgfs.semantic import Embedder, chunk_text, get_embedder, replace_file_chunks, semantic_model_name


def index_configured_folders(
    config: KGFSConfig,
    conn: Connection,
    *,
    dry_run: bool = False,
    semantic_embedder: Embedder | None = None,
    rebuild_embeddings: bool = False,
) -> IndexSummary:
    discovered = indexed = skipped_unchanged = failed = bytes_indexed = 0

    for file_path in discover_files(config):
        discovered += 1
        try:
            stat = file_path.stat()
        except OSError:
            failed += 1
            continue

        content_hash = sha256_file(file_path) if config.indexing.hash_files else None
        _, normalized_path = normalize_path(file_path)
        existing = get_existing_file(conn, normalized_path)
        if (
            existing
            and config.indexing.skip_unchanged_files
            and int(existing["size"]) == stat.st_size
            and float(existing["modified_time"]) == stat.st_mtime
            and existing["content_hash"] == content_hash
        ):
            _ensure_semantic_chunks(
                config,
                conn,
                file_path,
                int(existing["id"]),
                existing["extracted_text"],
                semantic_embedder=semantic_embedder,
                rebuild_embeddings=rebuild_embeddings,
                dry_run=dry_run,
            )
            skipped_unchanged += 1
            continue

        if dry_run:
            continue

        extraction = extract_text(file_path, pdf_max_pages=config.extraction.pdf_max_pages)
        if extraction.status == "error":
            failed += 1

        text = extraction.text if config.indexing.store_extracted_text else ""
        record = FileRecord(
            path=file_path,
            normalized_path=normalized_path,
            file_name=file_path.name,
            extension=file_path.suffix.lower(),
            size=stat.st_size,
            modified_time=stat.st_mtime,
            content_hash=content_hash,
            extracted_text=text,
            indexed_at=datetime.now(timezone.utc).isoformat(),
            platform_indexed_from=current_platform_name(),
            extraction_status=extraction.status,
            extraction_error=extraction.error,
        )
        file_id = upsert_file(conn, record)
        _index_semantic_chunks(
            config,
            conn,
            file_id,
            text,
            semantic_embedder=semantic_embedder,
            rebuild_embeddings=True,
        )
        indexed += 1
        bytes_indexed += stat.st_size

    return IndexSummary(
        discovered=discovered,
        indexed=indexed,
        skipped_unchanged=skipped_unchanged,
        failed=failed,
        bytes_indexed=bytes_indexed,
        dry_run=dry_run,
    )


def index_single_file(config: KGFSConfig, conn: Connection, file_path: Path) -> IndexSummary:
    local_config = config.model_copy(update={"indexed_folders": [file_path]})
    return index_configured_folders(local_config, conn)


def _ensure_semantic_chunks(
    config: KGFSConfig,
    conn: Connection,
    file_path: Path,
    file_id: int,
    stored_text: str,
    *,
    semantic_embedder: Embedder | None,
    rebuild_embeddings: bool,
    dry_run: bool,
) -> None:
    if not config.semantic.enabled or dry_run:
        return
    model_name = semantic_model_name(config.semantic, semantic_embedder)
    if not rebuild_embeddings and count_chunks_for_file(conn, file_id, model_name) > 0:
        return

    text = stored_text
    if not text:
        extraction = extract_text(file_path, pdf_max_pages=config.extraction.pdf_max_pages)
        text = extraction.text
    _index_semantic_chunks(
        config,
        conn,
        file_id,
        text,
        semantic_embedder=semantic_embedder,
        rebuild_embeddings=True,
    )


def _index_semantic_chunks(
    config: KGFSConfig,
    conn: Connection,
    file_id: int,
    text: str,
    *,
    semantic_embedder: Embedder | None,
    rebuild_embeddings: bool,
) -> None:
    if not config.semantic.enabled or not text.strip():
        return
    embedder = get_embedder(config.semantic, semantic_embedder)
    model_name = semantic_model_name(config.semantic, embedder)
    if not rebuild_embeddings and count_chunks_for_file(conn, file_id, model_name) > 0:
        return

    chunks = chunk_text(
        text,
        chunk_size_chars=config.semantic.chunk_size_chars,
        chunk_overlap_chars=config.semantic.chunk_overlap_chars,
    )
    embeddings = embedder.embed([chunk.text for chunk in chunks])
    replace_file_chunks(conn, file_id=file_id, chunks=chunks, embeddings=embeddings, model_name=model_name)
