"""Index configured folders into SQLite."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from sqlite3 import Connection

from kgfs.core.config import KGFSConfig
from kgfs.core.models import FileRecord, IndexSummary
from kgfs.core.platform_utils import current_platform_name, normalize_path
from kgfs.core.safety import RiskyRootError, find_risky_index_roots, format_risky_roots
from kgfs.db.repositories import count_chunks_for_file, get_existing_file, upsert_file
from kgfs.extractors import ExtractionResult, extract_text
from kgfs.indexing.discovery import discover_files
from kgfs.indexing.hashing import sha256_file
from kgfs.media.exif import extract_exif_metadata, store_photo_metadata
from kgfs.ocr.cache import attach_ocr_cache_file_id, get_cached_ocr_result, store_ocr_cache_result
from kgfs.search.semantic import Embedder, chunk_text, get_embedder, replace_file_chunks, semantic_model_name


def index_configured_folders(
    config: KGFSConfig,
    conn: Connection,
    *,
    dry_run: bool = False,
    semantic_embedder: Embedder | None = None,
    rebuild_embeddings: bool = False,
    allow_risky_root: bool = False,
    force: bool = False,
    verify_hashes: bool = False,
) -> IndexSummary:
    risky_roots = find_risky_index_roots(config.indexed_folders)
    if risky_roots and not allow_risky_root:
        raise RiskyRootError(
            "Refusing to index risky root folders:\n"
            f"{format_risky_roots(risky_roots)}\n"
            "Pass --allow-risky-root only if you intentionally want this scan."
        )

    discovered = indexed = skipped_unchanged = failed = bytes_indexed = 0

    for file_path in discover_files(config):
        discovered += 1
        try:
            stat = file_path.stat()
        except OSError:
            failed += 1
            continue

        _, normalized_path = normalize_path(file_path)
        existing = get_existing_file(conn, normalized_path)
        stat_mtime_ns = _stat_mtime_ns(stat)
        content_hash: str | None = None
        metadata_matches = (
            not force
            and existing
            and config.indexing.skip_unchanged_files
            and int(existing["size"]) == stat.st_size
            and _modified_time_matches(existing, stat.st_mtime, stat_mtime_ns)
        )
        if metadata_matches:
            if verify_hashes:
                content_hash = sha256_file(file_path)
                existing_hash = existing["content_hash"]
                if existing_hash is not None and existing_hash != content_hash:
                    metadata_matches = False
            if metadata_matches:
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

        if content_hash is None and (config.indexing.hash_files or verify_hashes):
            content_hash = sha256_file(file_path)
        if dry_run:
            continue

        extraction = _extract_with_ocr_cache(
            config,
            conn,
            file_path,
            normalized_path=normalized_path,
            content_hash=content_hash,
            size=stat.st_size,
            modified_time_ns=stat_mtime_ns,
        )
        if extraction.status == "error":
            failed += 1

        text = extraction.text if config.indexing.store_extracted_text else ""
        extraction_source = str(extraction.metadata.get("extraction_source", "text"))
        record = FileRecord(
            path=file_path,
            normalized_path=normalized_path,
            file_name=file_path.name,
            extension=file_path.suffix.lower(),
            size=stat.st_size,
            modified_time=stat.st_mtime,
            modified_time_ns=stat_mtime_ns,
            content_hash=content_hash,
            extracted_text=text,
            indexed_at=datetime.now(timezone.utc).isoformat(),
            platform_indexed_from=current_platform_name(),
            extraction_status=extraction.status,
            extraction_error=extraction.error,
            extraction_source=extraction_source,
        )
        file_id = upsert_file(conn, record)
        _attach_ocr_cache_if_needed(
            config,
            conn,
            file_id=file_id,
            file_path=file_path,
            normalized_path=normalized_path,
            content_hash=content_hash,
            size=stat.st_size,
            modified_time_ns=stat_mtime_ns,
            extraction=extraction,
        )
        media_text = _index_media_metadata_if_needed(config, conn, file_id=file_id, file_path=file_path, size=stat.st_size)
        semantic_text = "\n\n".join(part for part in (text, media_text) if part.strip())
        _index_semantic_chunks(
            config,
            conn,
            file_id,
            semantic_text,
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
    return index_configured_folders(local_config, conn, allow_risky_root=True)


def _stat_mtime_ns(stat_result) -> int:
    return int(getattr(stat_result, "st_mtime_ns", int(stat_result.st_mtime * 1_000_000_000)))


def _modified_time_matches(existing, modified_time: float, modified_time_ns: int) -> bool:
    try:
        existing_ns = existing["modified_time_ns"]
    except (KeyError, IndexError):
        existing_ns = None
    if existing_ns is not None:
        return int(existing_ns) == modified_time_ns
    return float(existing["modified_time"]) == modified_time


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
        stat = file_path.stat()
        _, normalized_path = normalize_path(file_path)
        content_hash = sha256_file(file_path) if config.indexing.hash_files else None
        extraction = _extract_with_ocr_cache(
            config,
            conn,
            file_path,
            normalized_path=normalized_path,
            content_hash=content_hash,
            size=stat.st_size,
            modified_time_ns=_stat_mtime_ns(stat),
        )
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


def _extract_with_ocr_cache(
    config: KGFSConfig,
    conn: Connection,
    file_path: Path,
    *,
    normalized_path: str,
    content_hash: str | None,
    size: int,
    modified_time_ns: int,
) -> ExtractionResult:
    source_kind = _ocr_candidate_kind(config, file_path)
    if source_kind is not None:
        cached = get_cached_ocr_result(
            conn,
            config,
            normalized_path=normalized_path,
            content_hash=content_hash,
            size=size,
            modified_time_ns=modified_time_ns,
            source_kind=source_kind,
        )
        if cached is not None:
            return ExtractionResult(
                text=cached.text,
                status=cached.status,
                error=cached.error,
                metadata={
                    "extraction_source": "ocr",
                    "ocr_backend": config.ocr.backend,
                    "ocr_language": config.ocr.tesseract.language,
                    "ocr_source_kind": source_kind,
                    "ocr_cached": True,
                },
            )

    extraction = extract_text(file_path, pdf_max_pages=config.extraction.pdf_max_pages, config=config)
    if (
        source_kind is not None
        and config.ocr.cache_results
        and str(extraction.metadata.get("extraction_source", "")) == "ocr"
    ):
        store_ocr_cache_result(
            conn,
            config,
            normalized_path=normalized_path,
            content_hash=content_hash,
            size=size,
            modified_time_ns=modified_time_ns,
            source_kind=source_kind,
            text=extraction.text,
            status=extraction.status,
            error=extraction.error,
        )
    return extraction


def _attach_ocr_cache_if_needed(
    config: KGFSConfig,
    conn: Connection,
    *,
    file_id: int,
    file_path: Path,
    normalized_path: str,
    content_hash: str | None,
    size: int,
    modified_time_ns: int,
    extraction: ExtractionResult,
) -> None:
    source_kind = _ocr_candidate_kind(config, file_path)
    if source_kind is None or str(extraction.metadata.get("extraction_source", "")) != "ocr":
        return
    attach_ocr_cache_file_id(
        conn,
        config,
        file_id=file_id,
        normalized_path=normalized_path,
        content_hash=content_hash,
        size=size,
        modified_time_ns=modified_time_ns,
        source_kind=source_kind,
    )


def _ocr_candidate_kind(config: KGFSConfig, file_path: Path) -> str | None:
    if not config.ocr.enabled:
        return None
    suffix = file_path.suffix.lower()
    if suffix in set(config.ocr.include_extensions):
        return "image"
    if suffix == ".pdf":
        return "pdf"
    return None


def _index_media_metadata_if_needed(config: KGFSConfig, conn: Connection, *, file_id: int, file_path: Path, size: int) -> str:
    if not (config.media.enabled and config.media.photos.enabled and config.media.photos.index_exif):
        return ""
    suffix = file_path.suffix.lower()
    if suffix not in set(config.media.photos.include_extensions):
        return ""
    if size > config.media.max_media_file_size_bytes:
        return ""
    try:
        metadata = extract_exif_metadata(file_path)
        return store_photo_metadata(conn, config, file_id=file_id, metadata=metadata)
    except Exception:
        return ""
