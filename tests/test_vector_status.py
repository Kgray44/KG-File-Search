from __future__ import annotations

from pathlib import Path

from kgfs.config import KGFSConfig, SemanticSettings, VectorSettings
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.vectors.status import get_vector_status


class FakeEmbedder:
    model_name = "fake-local-model"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in texts]


def test_vector_status_reports_semantic_disabled(tmp_path: Path) -> None:
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)

    status = get_vector_status(conn, KGFSConfig())

    assert status.semantic_enabled is False
    assert status.backend_name == "sqlite_scan"
    assert status.chunk_count == 0
    assert status.chunks_ready is False


def test_vector_status_reports_enabled_without_chunks(tmp_path: Path) -> None:
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    config = KGFSConfig(semantic=SemanticSettings(enabled=True, model_name="fake-local-model"))

    status = get_vector_status(conn, config)

    assert status.semantic_enabled is True
    assert status.chunk_count == 0
    assert status.chunks_ready is False
    assert any("No semantic chunks" in warning for warning in status.warnings)


def test_vector_status_reports_chunks_for_configured_model(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "motor.md").write_text("motor torque", encoding="utf-8")
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    config = KGFSConfig(
        indexed_folders=[root],
        semantic=SemanticSettings(enabled=True, model_name="fake-local-model"),
    )
    index_configured_folders(config, conn, semantic_embedder=FakeEmbedder())

    status = get_vector_status(conn, config)

    assert status.chunk_count > 0
    assert status.file_count_with_chunks == 1
    assert status.chunks_ready is True
    assert status.backend_available is True


def test_vector_status_reports_unknown_backend(tmp_path: Path) -> None:
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    config = KGFSConfig(vectors=VectorSettings(backend="missing_backend"))

    status = get_vector_status(conn, config)

    assert status.backend_available is False
    assert any("Unknown vector backend" in warning for warning in status.warnings)


def test_vector_status_reports_optional_backend_install_hint(tmp_path: Path) -> None:
    conn = connect_database(tmp_path / "kgfs.sqlite3")
    initialize_database(conn)
    config = KGFSConfig(vectors=VectorSettings(backend="hnsw"))

    status = get_vector_status(conn, config)

    assert status.backend_name == "hnsw"
    assert status.backend_available is False
    assert any("hnswlib" in warning for warning in status.warnings)
