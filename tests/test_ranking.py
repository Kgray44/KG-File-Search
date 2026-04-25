from datetime import datetime, timezone
from pathlib import Path

from kgfs.config import KGFSConfig
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.search import search


def test_filename_match_gets_modest_ranking_bonus(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "motor torque notes.md").write_text("ordinary lab notes", encoding="utf-8")
    (root / "random.md").write_text("motor torque motor torque motor torque", encoding="utf-8")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    index_configured_folders(KGFSConfig(indexed_folders=[root]), conn)

    results = search(conn, "motor torque")

    assert results[0].file_name == "motor torque notes.md"


def test_exact_phrase_beats_weak_token_match(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "exact.md").write_text("speaker crossover design details", encoding="utf-8")
    (root / "weak.md").write_text("speaker notes and unrelated crossover notes and unrelated design notes", encoding="utf-8")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    index_configured_folders(KGFSConfig(indexed_folders=[root]), conn)

    results = search(conn, "speaker crossover design")

    assert results[0].file_name == "exact.md"


def test_recent_bonus_does_not_overpower_relevance(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    relevant = root / "relevant.md"
    recent = root / "recent.md"
    relevant.write_text("pid control loop pid control loop", encoding="utf-8")
    recent.write_text("pid mention", encoding="utf-8")
    old_time = datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp()
    new_time = datetime.now(timezone.utc).timestamp()
    import os

    os.utime(relevant, (old_time, old_time))
    os.utime(recent, (new_time, new_time))
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    index_configured_folders(KGFSConfig(indexed_folders=[root]), conn)

    results = search(conn, "pid control loop")

    assert results[0].file_name == "relevant.md"

