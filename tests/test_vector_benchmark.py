from __future__ import annotations

from pathlib import Path

from kgfs.config import KGFSConfig, SemanticSettings
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.vectors.benchmark import benchmark_vector_backends


class FakeEmbedder:
    model_name = "fake-local-model"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in texts]


def _indexed_vector_db(tmp_path: Path):
    root = tmp_path / "docs"
    root.mkdir()
    (root / "motor.md").write_text("motor torque benchmark notes", encoding="utf-8")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    config = KGFSConfig(
        indexed_folders=[root],
        semantic=SemanticSettings(enabled=True, model_name="fake-local-model"),
    )
    index_configured_folders(config, conn, semantic_embedder=FakeEmbedder())
    return conn, config


def test_vector_benchmark_runs_sqlite_scan_without_semantic_dependencies(tmp_path: Path) -> None:
    conn, config = _indexed_vector_db(tmp_path)

    results = benchmark_vector_backends(conn, config, backend_names=["sqlite_scan"], limit=3)

    assert len(results) == 1
    assert results[0].backend_name == "sqlite_scan"
    assert results[0].available is True
    assert results[0].chunk_count > 0
    assert results[0].query_count >= 1
    assert results[0].average_query_seconds is not None


def test_vector_benchmark_reports_missing_optional_backend(tmp_path: Path) -> None:
    conn, config = _indexed_vector_db(tmp_path)

    results = benchmark_vector_backends(conn, config, backend_names=["hnsw"], limit=3)

    assert results[0].backend_name == "hnsw"
    assert results[0].available is False
    assert any("hnswlib" in note for note in results[0].notes)


def test_vector_benchmark_handles_no_chunks(tmp_path: Path) -> None:
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)

    results = benchmark_vector_backends(conn, KGFSConfig(), backend_names=["sqlite_scan"], limit=3)

    assert results[0].available is True
    assert results[0].chunk_count == 0
    assert results[0].query_count == 0
    assert any("No vectors" in note for note in results[0].notes)
