"""SQLite-backed OCR result cache."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from kgfs.core.config import KGFSConfig


@dataclass(frozen=True)
class CachedOCRResult:
    text: str
    status: str
    error: str | None


def get_cached_ocr_result(
    conn: sqlite3.Connection,
    config: KGFSConfig,
    *,
    normalized_path: str,
    content_hash: str | None,
    size: int,
    modified_time_ns: int,
    source_kind: str,
) -> CachedOCRResult | None:
    if not config.ocr.cache_results:
        return None
    row = conn.execute(
        """
        SELECT text, status, error
        FROM ocr_cache
        WHERE normalized_path = ?
          AND content_hash IS ?
          AND size = ?
          AND modified_time_ns = ?
          AND backend = ?
          AND language = ?
          AND source_kind = ?
        """,
        (
            normalized_path,
            content_hash,
            size,
            modified_time_ns,
            config.ocr.backend,
            config.ocr.tesseract.language,
            source_kind,
        ),
    ).fetchone()
    if row is None:
        return None
    return CachedOCRResult(text=row["text"], status=row["status"], error=row["error"])


def store_ocr_cache_result(
    conn: sqlite3.Connection,
    config: KGFSConfig,
    *,
    normalized_path: str,
    content_hash: str | None,
    size: int,
    modified_time_ns: int,
    source_kind: str,
    text: str,
    status: str,
    error: str | None,
    file_id: int | None = None,
) -> None:
    if not config.ocr.cache_results:
        return
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO ocr_cache (
            file_id, normalized_path, content_hash, size, modified_time_ns,
            backend, language, source_kind, text, status, error, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(normalized_path, content_hash, size, modified_time_ns, backend, language, source_kind)
        DO UPDATE SET
            file_id = COALESCE(excluded.file_id, ocr_cache.file_id),
            text = excluded.text,
            status = excluded.status,
            error = excluded.error,
            updated_at = excluded.updated_at
        """,
        (
            file_id,
            normalized_path,
            content_hash,
            size,
            modified_time_ns,
            config.ocr.backend,
            config.ocr.tesseract.language,
            source_kind,
            text,
            status,
            error,
            now,
            now,
        ),
    )
    conn.commit()


def attach_ocr_cache_file_id(
    conn: sqlite3.Connection,
    config: KGFSConfig,
    *,
    file_id: int,
    normalized_path: str,
    content_hash: str | None,
    size: int,
    modified_time_ns: int,
    source_kind: str,
) -> None:
    conn.execute(
        """
        UPDATE ocr_cache
        SET file_id = ?
        WHERE normalized_path = ?
          AND content_hash IS ?
          AND size = ?
          AND modified_time_ns = ?
          AND backend = ?
          AND language = ?
          AND source_kind = ?
        """,
        (
            file_id,
            normalized_path,
            content_hash,
            size,
            modified_time_ns,
            config.ocr.backend,
            config.ocr.tesseract.language,
            source_kind,
        ),
    )
    conn.commit()


def count_ocr_cache_entries(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS count FROM ocr_cache").fetchone()
    return int(row["count"])
