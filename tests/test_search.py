from pathlib import Path

from kgfs.config import KGFSConfig
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.search import SearchResult, save_latest_results, search


def test_search_returns_ranked_results_with_stable_result_ids(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "pid.pdf.txt").write_text("PDF about PID control loops", encoding="utf-8")
    (root / "circuits.md").write_text("notes about op-amps", encoding="utf-8")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    index_configured_folders(KGFSConfig(indexed_folders=[root]), conn)

    results = search(conn, "PID control")

    assert results[0].result_id == 1
    assert "pid" in results[0].file_name.lower()
    assert results[0].score >= 0
    assert results[0].normalized_path == str(results[0].path)
    assert results[0].mode == "keyword"
    assert results[0].score_breakdown is not None


def test_save_latest_results_persists_paths_for_open_commands(tmp_path: Path) -> None:
    result = SearchResult(
        result_id=1,
        file_id=42,
        file_name="notes.md",
        path=tmp_path / "notes.md",
        extension=".md",
        modified_time=1.0,
        score=0.5,
        snippet="notes",
    )
    db_path = tmp_path / "kgfs.sqlite3"
    conn = connect_database(db_path)
    initialize_database(conn)

    save_latest_results(conn, "notes", [result])
    rows = conn.execute("select result_id, file_path from latest_results").fetchall()

    assert rows == [(1, str(tmp_path / "notes.md"))]
