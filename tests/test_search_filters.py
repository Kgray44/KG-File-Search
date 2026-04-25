from datetime import datetime, timezone
from pathlib import Path

from kgfs.config import KGFSConfig
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.search import SearchFilters, search


def _set_mtime(path: Path, date_text: str) -> None:
    timestamp = datetime.fromisoformat(date_text).replace(tzinfo=timezone.utc).timestamp()
    path.touch()
    import os

    os.utime(path, (timestamp, timestamp))


def test_keyword_search_filters_by_extension_folder_and_dates(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    circuits = root / "Circuits Class"
    controls = root / "Controls"
    circuits.mkdir(parents=True)
    controls.mkdir()
    pdf = controls / "pid.PDF"
    md = circuits / "pid notes.md"
    pdf.write_text("pid control design", encoding="utf-8")
    md.write_text("pid control notes", encoding="utf-8")
    _set_mtime(pdf, "2024-01-15T12:00:00")
    _set_mtime(md, "2026-01-15T12:00:00")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    index_configured_folders(KGFSConfig(indexed_folders=[root], include_extensions=[".pdf", ".md"]), conn)

    assert [item.file_name for item in search(conn, "pid", filters=SearchFilters(extensions=[".pdf"]))] == ["pid.PDF"]
    assert [item.file_name for item in search(conn, "pid", filters=SearchFilters(folder="circuits class"))] == ["pid notes.md"]
    assert [item.file_name for item in search(conn, "pid", filters=SearchFilters(after="2025-01-01"))] == ["pid notes.md"]
    assert [item.file_name for item in search(conn, "pid", filters=SearchFilters(before="2025-01-01"))] == ["pid.PDF"]


def test_failed_only_filter_returns_extraction_failures(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    note = root / "bad.md"
    note.write_text("failed extraction sample", encoding="utf-8")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    index_configured_folders(KGFSConfig(indexed_folders=[root]), conn)
    conn.execute("UPDATE files SET extraction_status = 'error' WHERE file_name = 'bad.md'")
    conn.commit()

    results = search(conn, "failed", filters=SearchFilters(failed_only=True))

    assert [item.file_name for item in results] == ["bad.md"]

