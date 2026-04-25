from __future__ import annotations

from pathlib import Path

from kgfs.config import KGFSConfig, OCRSettings
from kgfs.database import connect_database, initialize_database
from kgfs.ocr.cache import count_ocr_cache_entries, get_cached_ocr_result, store_ocr_cache_result


def test_ocr_cache_roundtrip_and_miss_on_changed_file(tmp_path: Path) -> None:
    db_path = tmp_path / "kgfs.sqlite3"
    conn = connect_database(db_path)
    initialize_database(conn)
    image = tmp_path / "scan.png"
    image.write_bytes(b"first")
    stat = image.stat()
    config = KGFSConfig(database_path=db_path, ocr=OCRSettings(enabled=True))

    store_ocr_cache_result(
        conn,
        config,
        normalized_path=str(image),
        content_hash="hash-1",
        size=stat.st_size,
        modified_time_ns=stat.st_mtime_ns,
        source_kind="image",
        text="cached motor torque",
        status="ok",
        error=None,
    )

    cached = get_cached_ocr_result(
        conn,
        config,
        normalized_path=str(image),
        content_hash="hash-1",
        size=stat.st_size,
        modified_time_ns=stat.st_mtime_ns,
        source_kind="image",
    )
    changed = get_cached_ocr_result(
        conn,
        config,
        normalized_path=str(image),
        content_hash="hash-2",
        size=stat.st_size,
        modified_time_ns=stat.st_mtime_ns,
        source_kind="image",
    )

    assert cached is not None
    assert cached.text == "cached motor torque"
    assert changed is None
    assert count_ocr_cache_entries(conn) == 1
    assert not list(tmp_path.glob("*.ocr*"))
