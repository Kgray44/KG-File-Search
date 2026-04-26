from pathlib import Path

from kgfs.config import KGFSConfig, SemanticSettings
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.prune import find_stale_files, prune_stale_files


class FakeEmbedder:
    model_name = "fake"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


def test_prune_dry_run_reports_stale_records_without_db_changes(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    source_file = root / "notes.md"
    source_file.write_text("temporary notes", encoding="utf-8")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    index_configured_folders(KGFSConfig(indexed_folders=[root]), conn)
    source_file.unlink()

    stale = find_stale_files(conn)
    summary = prune_stale_files(conn, dry_run=True)

    assert len(stale) == 1
    assert summary.removed == 0
    assert summary.stale_paths == [source_file]
    assert conn.execute("SELECT COUNT(*) AS count FROM files").fetchone()["count"] == 1


def test_prune_removes_only_database_records_and_related_rows(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    stale_file = root / "stale.md"
    kept_file = root / "kept.md"
    stale_file.write_text("stale semantic text", encoding="utf-8")
    kept_file.write_text("kept semantic text", encoding="utf-8")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    config = KGFSConfig(
        indexed_folders=[root],
        semantic=SemanticSettings(enabled=True, model_name="fake", chunk_size_chars=20, chunk_overlap_chars=0),
    )
    index_configured_folders(config, conn, semantic_embedder=FakeEmbedder())
    stale_id = conn.execute("SELECT id FROM files WHERE file_name = 'stale.md'").fetchone()["id"]
    conn.execute(
        "INSERT INTO latest_results(result_id, file_id, file_path, query, created_at) VALUES (?, ?, ?, ?, ?)",
        (1, stale_id, str(stale_file), "stale", "now"),
    )
    conn.commit()
    stale_file.unlink()

    summary = prune_stale_files(conn)

    assert summary.removed == 1
    assert kept_file.exists()
    assert conn.execute("SELECT COUNT(*) AS count FROM files WHERE file_name = 'stale.md'").fetchone()["count"] == 0
    assert conn.execute("SELECT COUNT(*) AS count FROM chunks WHERE file_id = ?", (stale_id,)).fetchone()["count"] == 0
    assert conn.execute("SELECT COUNT(*) AS count FROM latest_results").fetchone()["count"] == 0
