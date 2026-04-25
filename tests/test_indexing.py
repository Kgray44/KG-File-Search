from pathlib import Path

from kgfs.config import KGFSConfig
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.search import search
from kgfs.safety import RiskyRootError


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


def test_force_reindexes_unchanged_files(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "notes.md").write_text("speaker crossover design", encoding="utf-8")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    config = KGFSConfig(indexed_folders=[root])

    index_configured_folders(config, conn)
    second = index_configured_folders(config, conn, force=True)

    assert second.indexed == 1
    assert second.skipped_unchanged == 0


def test_verify_hashes_detects_same_size_same_mtime_content_change(tmp_path: Path) -> None:
    import os

    root = tmp_path / "docs"
    root.mkdir()
    note = root / "notes.md"
    note.write_text("alpha motor", encoding="utf-8")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    config = KGFSConfig(indexed_folders=[root])

    index_configured_folders(config, conn)
    original_stat = note.stat()
    note.write_text("bravo motor", encoding="utf-8")
    os.utime(note, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))

    second = index_configured_folders(config, conn, verify_hashes=True)

    assert second.indexed == 1
    assert search(conn, "bravo motor")[0].file_name == "notes.md"
    assert search(conn, "alpha") == []


def test_reindex_updates_fts_row_for_existing_file(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    note = root / "notes.md"
    note.write_text("initial motor torque text", encoding="utf-8")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    config = KGFSConfig(indexed_folders=[root])

    index_configured_folders(config, conn)
    assert search(conn, "initial motor") != []

    note.write_text("updated speaker crossover text", encoding="utf-8")
    index_configured_folders(config, conn)

    assert search(conn, "updated speaker")[0].file_name == "notes.md"
    assert search(conn, "initial motor") == []
    row = conn.execute(
        "SELECT COUNT(*) AS count FROM files_fts WHERE rowid = (SELECT id FROM files WHERE file_name = ?)",
        ("notes.md",),
    ).fetchone()
    assert row["count"] == 1


def test_unchanged_files_skip_hashing_after_metadata_match(tmp_path: Path, mocker) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "notes.md").write_text("speaker crossover design", encoding="utf-8")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    config = KGFSConfig(indexed_folders=[root])

    index_configured_folders(config, conn)
    mocked_hash = mocker.patch("kgfs.indexing.indexer.sha256_file", return_value="new-hash")
    second = index_configured_folders(config, conn)

    assert second.skipped_unchanged == 1
    mocked_hash.assert_not_called()


def test_indexing_refuses_risky_roots_by_default(tmp_path: Path) -> None:
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    config = KGFSConfig(indexed_folders=[Path("/")])

    try:
        index_configured_folders(config, conn)
    except RiskyRootError as exc:
        assert "Refusing to index risky root" in str(exc)
    else:
        raise AssertionError("Expected risky root protection to refuse /")
