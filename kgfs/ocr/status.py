"""OCR status helpers."""

from __future__ import annotations

import sqlite3

from kgfs.core.config import KGFSConfig
from kgfs.ocr.base import OCRStatus
from kgfs.ocr.registry import get_ocr_backend


def get_ocr_status(config: KGFSConfig, conn: sqlite3.Connection | None = None) -> OCRStatus:
    try:
        backend = get_ocr_backend(config.ocr.backend)
        availability = backend.available(config)
    except ValueError as exc:
        return OCRStatus(
            enabled=config.ocr.enabled,
            backend_name=config.ocr.backend,
            available=False,
            message=str(exc),
            command=config.ocr.tesseract.command,
            language=config.ocr.tesseract.language,
            supported_extensions=config.ocr.include_extensions,
            max_image_size_mb=config.ocr.max_image_size_mb,
            cache_enabled=config.ocr.cache_results,
            install_hint="Set ocr.backend to tesseract.",
            warnings=[str(exc)],
        )
    cache_entries = 0
    indexed_file_count = 0
    failure_count = 0
    if conn is not None:
        try:
            cache_entries = int(conn.execute("SELECT COUNT(*) AS count FROM ocr_cache").fetchone()["count"])
            indexed_file_count = int(
                conn.execute("SELECT COUNT(*) AS count FROM files WHERE extraction_source LIKE 'ocr%'").fetchone()["count"]
            )
            failure_count = int(
                conn.execute(
                    "SELECT COUNT(*) AS count FROM files WHERE extraction_source LIKE 'ocr%' AND extraction_status = 'error'"
                ).fetchone()["count"]
            )
        except sqlite3.Error:
            pass

    if not config.ocr.enabled:
        message = "OCR is disabled in config."
        available = False
    else:
        message = availability.message
        available = availability.available

    return OCRStatus(
        enabled=config.ocr.enabled,
        backend_name=config.ocr.backend,
        available=available,
        message=message,
        command=config.ocr.tesseract.command,
        language=config.ocr.tesseract.language,
        supported_extensions=config.ocr.include_extensions,
        max_image_size_mb=config.ocr.max_image_size_mb,
        cache_enabled=config.ocr.cache_results,
        cache_entries=cache_entries,
        indexed_file_count=indexed_file_count,
        failure_count=failure_count,
        install_hint=availability.install_hint,
    )
