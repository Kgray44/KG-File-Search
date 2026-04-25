from pathlib import Path

from kgfs.config import KGFSConfig
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.reset import rebuild_index, reset_index


def test_reset_index_dry_run_leaves_database_and_source_files(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    source = root / "notes.md"
    source.write_text("keep me", encoding="utf-8")
    db_path = tmp_path / "kgfs.sqlite3"
    conn = connect_database(db_path)
    initialize_database(conn)
    index_configured_folders(KGFSConfig(indexed_folders=[root]), conn)
    conn.close()

    summary = reset_index(db_path, dry_run=True)

    assert summary.would_remove is True
    assert db_path.exists()
    assert source.exists()


def test_reset_index_yes_removes_only_database_file(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    source = root / "notes.md"
    source.write_text("keep me", encoding="utf-8")
    db_path = tmp_path / "kgfs.sqlite3"
    connect_database(db_path).close()

    reset_index(db_path, yes=True)

    assert not db_path.exists()
    assert source.exists()


def test_rebuild_resets_database_then_indexes(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "notes.md").write_text("rebuild text", encoding="utf-8")
    db_path = tmp_path / "kgfs.sqlite3"

    summary = rebuild_index(KGFSConfig(indexed_folders=[root], database_path=db_path), db_path)

    conn = connect_database(db_path)
    assert summary.indexed == 1
    assert conn.execute("SELECT COUNT(*) AS count FROM files").fetchone()["count"] == 1

