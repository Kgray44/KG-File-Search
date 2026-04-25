from pathlib import Path

from kgfs.config import KGFSConfig
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.search import search


def test_indexing_stores_metadata_and_text_for_search(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    note = root / "lab report.md"
    note.write_text("I calculated motor torque in this lab report.", encoding="utf-8")
    db_path = tmp_path / "kgfs.sqlite3"
    config = KGFSConfig(indexed_folders=[root], database_path=db_path)
    conn = connect_database(db_path)
    initialize_database(conn)

    summary = index_configured_folders(config, conn)
    results = search(conn, "motor torque")

    assert summary.indexed == 1
    assert summary.failed == 0
    assert results[0].file_name == "lab report.md"
    assert "motor" in results[0].snippet.lower()


def test_indexing_skips_unchanged_files_on_second_run(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "notes.md").write_text("speaker crossover design", encoding="utf-8")
    db_path = tmp_path / "kgfs.sqlite3"
    config = KGFSConfig(indexed_folders=[root], database_path=db_path)
    conn = connect_database(db_path)
    initialize_database(conn)

    first = index_configured_folders(config, conn)
    second = index_configured_folders(config, conn)

    assert first.indexed == 1
    assert second.skipped_unchanged == 1

